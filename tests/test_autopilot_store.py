"""
autopilot/store.py 테스트 — SQLite canonical state CRUD, 마이그레이션 훅.
"""
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from autopilot.store import (
    Store,
    SCHEMA_VERSION,
    migrate,
)


@pytest.fixture
def store(tmp_path):
    """테스트마다 임시 DB를 사용하는 Store 인스턴스."""
    s = Store(str(tmp_path / "test.db"))
    return s


# ---------------------------------------------------------------------------
# runs 테이블
# ---------------------------------------------------------------------------
class TestRuns:
    def test_run_생성_조회(self, store):
        """run을 생성하면 pending 상태로 조회된다."""
        run_id = store.create_run("album-spring-2026")
        row = store.get_run(run_id)
        assert row["id"] == run_id
        assert row["album_slug"] == "album-spring-2026"
        assert row["status"] == "pending"
        assert row["state_version"] == 0

    def test_run_status_업데이트(self, store):
        """update_run_status 로 status, current_step 변경."""
        run_id = store.create_run("test-album")
        store.update_run_status(run_id, "running", current_step="write_lyrics")
        row = store.get_run(run_id)
        assert row["status"] == "running"
        assert row["current_step"] == "write_lyrics"

    def test_run_없으면_None(self, store):
        assert store.get_run("nonexistent") is None


# ---------------------------------------------------------------------------
# steps 테이블
# ---------------------------------------------------------------------------
class TestSteps:
    def test_step_시작_완료(self, store):
        """start_step → finish_step 흐름."""
        run_id = store.create_run("album")
        store.start_step(run_id, "write_lyrics")
        step = store.get_step(run_id, "write_lyrics")
        assert step["status"] == "running"
        assert step["attempt"] == 1

        store.finish_step(run_id, "write_lyrics", {"text": "가사 완성"})
        step = store.get_step(run_id, "write_lyrics")
        assert step["status"] == "done"

    def test_step_실패_재시도_증가(self, store):
        """실패 후 다시 start_step 하면 attempt가 증가한다."""
        run_id = store.create_run("album")
        store.start_step(run_id, "generate")
        store.fail_step(run_id, "generate", {"msg": "timeout"})
        step = store.get_step(run_id, "generate")
        assert step["status"] == "failed"

        store.start_step(run_id, "generate")
        step = store.get_step(run_id, "generate")
        assert step["attempt"] == 2

    def test_step_없으면_None(self, store):
        run_id = store.create_run("album")
        assert store.get_step(run_id, "no_such_step") is None


# ---------------------------------------------------------------------------
# human_tasks 테이블
# ---------------------------------------------------------------------------
class TestHumanTasks:
    def test_human_task_생성_조회_답변(self, store):
        """create → get_open → answer 흐름."""
        run_id = store.create_run("album")
        now = time.time()
        task_id = store.create_human_task(
            run_id, "selection", {"candidates": ["a", "b"]}, expires_at=now + 3600
        )
        task = store.get_open_human_task(run_id, "selection")
        assert task is not None
        assert task["id"] == task_id
        assert task["status"] == "open"

        store.answer_human_task(task_id, {"chosen": "a"})
        task = store.get_open_human_task(run_id, "selection")
        # answered 상태이므로 open 조회에서 None 반환
        assert task is None

    def test_human_task_만료(self, store):
        """expire_due_tasks 호출 시 만료 시각 지난 open task가 expired로 전이."""
        run_id = store.create_run("album")
        past = time.time() - 10
        store.create_human_task(run_id, "selection", {}, expires_at=past)
        store.expire_due_tasks(time.time())
        task = store.get_open_human_task(run_id, "selection")
        assert task is None  # 만료됨


# ---------------------------------------------------------------------------
# artifacts 테이블
# ---------------------------------------------------------------------------
class TestArtifacts:
    def test_artifact_추가(self, store):
        """artifact는 경로+sha256만 저장한다."""
        run_id = store.create_run("album")
        art_id = store.add_artifact(
            run_id, "generate", "audio", "/data/suno/track.mp3",
            "abc123sha256", {"duration": 180}
        )
        assert art_id is not None


# ---------------------------------------------------------------------------
# state_version 마이그레이션 훅
# ---------------------------------------------------------------------------
class TestMigration:
    def test_migration_훅_state_version_증가(self, store):
        """migrate() 함수를 호출하면 run의 state_version이 올라간다."""
        run_id = store.create_run("album")
        before = store.get_run(run_id)["state_version"]
        # 마이그레이션: from_version=0 → 1
        migrate(store.conn, run_id, from_version=0)
        after = store.get_run(run_id)["state_version"]
        assert after == before + 1

    def test_schema_version_상수_존재(self):
        """SCHEMA_VERSION 상수가 정수여야 한다."""
        assert isinstance(SCHEMA_VERSION, int)
        assert SCHEMA_VERSION >= 1
