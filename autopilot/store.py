"""
autopilot/store.py — SQLite canonical state store.

설계 원칙:
- Store 클래스에 명시적 path를 전달해 테스트마다 독립적인 DB 사용.
- bytes/BLOB 저장 금지. artifact는 경로+sha256만.
- state_version 마이그레이션 훅: MIGRATIONS 리스트 기반.
"""
from __future__ import annotations

import json
import sqlite3
import time
import uuid
from typing import Any

# ---------------------------------------------------------------------------
# 스키마 버전 상수 + 마이그레이션 목록
# ---------------------------------------------------------------------------

SCHEMA_VERSION: int = 1
"""현재 지원하는 최신 state_version."""


def _migration_v0_to_v1(conn: sqlite3.Connection, run_id: str) -> None:
    """v0 → v1: 예시 no-op 마이그레이션 (훅 작동 증명용)."""
    # 실제 컬럼 변경이 필요하면 여기서 ALTER TABLE 실행.
    # Phase 2에서는 state_version 숫자만 올려 훅 실행을 증명.
    conn.execute(
        "UPDATE runs SET state_version = state_version + 1, updated_at = ? WHERE id = ?",
        (time.time(), run_id),
    )
    conn.commit()


MIGRATIONS: list[Any] = [
    # 인덱스 = from_version.  MIGRATIONS[0] = v0→v1 전환 함수.
    _migration_v0_to_v1,
]


def migrate(conn: sqlite3.Connection, run_id: str, from_version: int) -> None:
    """run의 state_version을 from_version 에서 SCHEMA_VERSION 까지 순차 마이그레이션.

    각 MIGRATIONS[i]는 (conn, run_id) 시그니처를 가진다.
    """
    for i in range(from_version, SCHEMA_VERSION):
        MIGRATIONS[i](conn, run_id)


# ---------------------------------------------------------------------------
# ID 헬퍼
# ---------------------------------------------------------------------------

def _new_id() -> str:
    """12자 hex UUID."""
    return uuid.uuid4().hex[:12]


# ---------------------------------------------------------------------------
# Store 클래스
# ---------------------------------------------------------------------------

class Store:
    """SQLite를 이용한 파이프라인 canonical state 저장소."""

    def __init__(self, path: str) -> None:
        """지정 경로에 DB를 열거나 생성한다."""
        self.path = path
        self.conn: sqlite3.Connection = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._init_tables()

    # ------------------------------------------------------------------
    # 내부: 테이블 초기화
    # ------------------------------------------------------------------

    def _init_tables(self) -> None:
        """필요한 테이블을 모두 생성한다 (없으면)."""
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS runs (
                id          TEXT PRIMARY KEY,
                album_slug  TEXT NOT NULL,
                status      TEXT NOT NULL DEFAULT 'pending',
                current_step TEXT,
                state_version INTEGER NOT NULL DEFAULT 0,
                created_at  REAL NOT NULL,
                updated_at  REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS steps (
                run_id      TEXT NOT NULL,
                step_name   TEXT NOT NULL,
                status      TEXT NOT NULL DEFAULT 'pending',
                attempt     INTEGER NOT NULL DEFAULT 0,
                input_json  TEXT,
                output_json TEXT,
                error_json  TEXT,
                started_at  REAL,
                ended_at    REAL,
                PRIMARY KEY (run_id, step_name)
            );

            CREATE TABLE IF NOT EXISTS human_tasks (
                id          TEXT PRIMARY KEY,
                run_id      TEXT NOT NULL,
                kind        TEXT NOT NULL,
                payload_json TEXT,
                status      TEXT NOT NULL DEFAULT 'open',
                answer_json TEXT,
                created_at  REAL NOT NULL,
                expires_at  REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS artifacts (
                id          TEXT PRIMARY KEY,
                run_id      TEXT NOT NULL,
                step_name   TEXT NOT NULL,
                kind        TEXT NOT NULL,
                path        TEXT NOT NULL,
                sha256      TEXT NOT NULL,
                meta_json   TEXT
            );

            CREATE TABLE IF NOT EXISTS idempotency (
                key         TEXT PRIMARY KEY,
                result_json TEXT NOT NULL,
                created_at  REAL NOT NULL
            );
        """)
        self.conn.commit()

    # ------------------------------------------------------------------
    # runs CRUD
    # ------------------------------------------------------------------

    def create_run(self, album_slug: str) -> str:
        """새 run을 생성하고 ID를 반환한다."""
        run_id = _new_id()
        now = time.time()
        self.conn.execute(
            """INSERT INTO runs (id, album_slug, status, state_version, created_at, updated_at)
               VALUES (?, ?, 'pending', 0, ?, ?)""",
            (run_id, album_slug, now, now),
        )
        self.conn.commit()
        return run_id

    def get_run(self, run_id: str) -> sqlite3.Row | None:
        """run을 조회한다. 없으면 None."""
        row = self.conn.execute(
            "SELECT * FROM runs WHERE id = ?", (run_id,)
        ).fetchone()
        return row  # type: ignore[return-value]

    def update_run_status(
        self,
        run_id: str,
        status: str,
        current_step: str | None = None,
    ) -> None:
        """run의 status(와 선택적으로 current_step)을 업데이트한다."""
        now = time.time()
        self.conn.execute(
            """UPDATE runs
               SET status = ?, current_step = ?, updated_at = ?
               WHERE id = ?""",
            (status, current_step, now, run_id),
        )
        self.conn.commit()

    # ------------------------------------------------------------------
    # steps CRUD
    # ------------------------------------------------------------------

    def start_step(
        self,
        run_id: str,
        step_name: str,
        input_data: dict[str, Any] | None = None,
    ) -> None:
        """step을 running 상태로 시작하거나 재시도 시 attempt를 증가시킨다."""
        now = time.time()
        input_json = json.dumps(input_data) if input_data is not None else None

        existing = self.get_step(run_id, step_name)
        if existing is None:
            self.conn.execute(
                """INSERT INTO steps
                       (run_id, step_name, status, attempt, input_json, started_at)
                   VALUES (?, ?, 'running', 1, ?, ?)""",
                (run_id, step_name, input_json, now),
            )
        else:
            self.conn.execute(
                """UPDATE steps
                   SET status = 'running', attempt = attempt + 1,
                       input_json = ?, started_at = ?, ended_at = NULL,
                       output_json = NULL, error_json = NULL
                   WHERE run_id = ? AND step_name = ?""",
                (input_json, now, run_id, step_name),
            )
        self.conn.commit()

    def finish_step(
        self,
        run_id: str,
        step_name: str,
        output_data: dict[str, Any] | None = None,
    ) -> None:
        """step을 done 상태로 완료한다."""
        now = time.time()
        output_json = json.dumps(output_data) if output_data is not None else None
        self.conn.execute(
            """UPDATE steps
               SET status = 'done', output_json = ?, ended_at = ?
               WHERE run_id = ? AND step_name = ?""",
            (output_json, now, run_id, step_name),
        )
        self.conn.commit()

    def fail_step(
        self,
        run_id: str,
        step_name: str,
        error_data: dict[str, Any] | None = None,
    ) -> None:
        """step을 failed 상태로 기록한다."""
        now = time.time()
        error_json = json.dumps(error_data) if error_data is not None else None
        self.conn.execute(
            """UPDATE steps
               SET status = 'failed', error_json = ?, ended_at = ?
               WHERE run_id = ? AND step_name = ?""",
            (error_json, now, run_id, step_name),
        )
        self.conn.commit()

    def get_step(self, run_id: str, step_name: str) -> sqlite3.Row | None:
        """step을 조회한다. 없으면 None."""
        row = self.conn.execute(
            "SELECT * FROM steps WHERE run_id = ? AND step_name = ?",
            (run_id, step_name),
        ).fetchone()
        return row  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # human_tasks CRUD
    # ------------------------------------------------------------------

    def create_human_task(
        self,
        run_id: str,
        kind: str,
        payload: dict[str, Any],
        expires_at: float,
    ) -> str:
        """새 human_task를 생성하고 ID를 반환한다."""
        task_id = _new_id()
        now = time.time()
        self.conn.execute(
            """INSERT INTO human_tasks
                   (id, run_id, kind, payload_json, status, created_at, expires_at)
               VALUES (?, ?, ?, ?, 'open', ?, ?)""",
            (task_id, run_id, kind, json.dumps(payload), now, expires_at),
        )
        self.conn.commit()
        return task_id

    def get_open_human_task(
        self, run_id: str, kind: str
    ) -> sqlite3.Row | None:
        """open 상태인 human_task를 반환한다. 없으면 None."""
        row = self.conn.execute(
            """SELECT * FROM human_tasks
               WHERE run_id = ? AND kind = ? AND status = 'open'
               ORDER BY created_at DESC LIMIT 1""",
            (run_id, kind),
        ).fetchone()
        return row  # type: ignore[return-value]

    def answer_human_task(
        self, task_id: str, answer: dict[str, Any]
    ) -> None:
        """human_task에 답변을 기록하고 answered 상태로 전이한다."""
        self.conn.execute(
            """UPDATE human_tasks
               SET status = 'answered', answer_json = ?
               WHERE id = ?""",
            (json.dumps(answer), task_id),
        )
        self.conn.commit()

    def expire_due_tasks(self, now_ts: float) -> None:
        """만료 시각이 지난 open task를 expired로 전이한다."""
        self.conn.execute(
            """UPDATE human_tasks
               SET status = 'expired'
               WHERE status = 'open' AND expires_at <= ?""",
            (now_ts,),
        )
        self.conn.commit()

    def get_answered_human_task(
        self, run_id: str, kind: str
    ) -> sqlite3.Row | None:
        """answered 상태인 human_task를 반환한다. 없으면 None."""
        row = self.conn.execute(
            """SELECT * FROM human_tasks
               WHERE run_id = ? AND kind = ? AND status = 'answered'
               ORDER BY created_at DESC LIMIT 1""",
            (run_id, kind),
        ).fetchone()
        return row  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # artifacts CRUD
    # ------------------------------------------------------------------

    def add_artifact(
        self,
        run_id: str,
        step_name: str,
        kind: str,
        path: str,
        sha256: str,
        meta: dict[str, Any] | None = None,
    ) -> str:
        """산출물 메타데이터를 등록하고 ID를 반환한다. bytes 저장 금지."""
        art_id = _new_id()
        self.conn.execute(
            """INSERT INTO artifacts (id, run_id, step_name, kind, path, sha256, meta_json)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (art_id, run_id, step_name, kind, path, sha256, json.dumps(meta)),
        )
        self.conn.commit()
        return art_id

    # ------------------------------------------------------------------
    # idempotency 테이블 접근 (idempotency.py 에서 사용)
    # ------------------------------------------------------------------

    def get_idempotency(self, key: str) -> sqlite3.Row | None:
        """저장된 멱등성 결과를 반환한다."""
        return self.conn.execute(  # type: ignore[return-value]
            "SELECT * FROM idempotency WHERE key = ?", (key,)
        ).fetchone()

    def set_idempotency(self, key: str, result: Any) -> None:
        """멱등성 키-결과를 저장한다."""
        now = time.time()
        self.conn.execute(
            """INSERT OR REPLACE INTO idempotency (key, result_json, created_at)
               VALUES (?, ?, ?)""",
            (key, json.dumps(result), now),
        )
        self.conn.commit()
