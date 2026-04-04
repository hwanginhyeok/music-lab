"""
Music Lab 데이터베이스 — SQLite 대화 히스토리 + 아이디어 저장

간소화 스키마: messages 단일 테이블 (user_id + session_id).
단일 사용자 프로젝트이므로 users/conversations 테이블 불필요.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import uuid
from pathlib import Path

logger = logging.getLogger("music-lab")

DB_PATH = os.environ.get("MUSIC_LAB_DB", "data/music-lab.db")


_conn: sqlite3.Connection | None = None


def _get_conn() -> sqlite3.Connection:
    """싱글턴 DB 연결. 최초 호출 시 생성, 이후 재사용."""
    global _conn
    if _conn is None:
        Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
    return _conn


def init_db() -> None:
    """테이블 생성 (봇 시작 시 호출)."""
    conn = _get_conn()
    conn.executescript("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                session_id TEXT NOT NULL DEFAULT 'default',
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                has_midi INTEGER DEFAULT 0,
                midi_json TEXT,
                midi_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_messages_session
                ON messages(session_id, created_at);

            CREATE TABLE IF NOT EXISTS ideas (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                description TEXT NOT NULL,
                tags TEXT,
                midi_json TEXT,
                midi_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                title TEXT DEFAULT '새 대화',
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS suno_songs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                title TEXT,
                song_id TEXT,
                status TEXT DEFAULT 'pending',
                style TEXT,
                lyrics TEXT,
                local_path TEXT,
                drive_url TEXT,
                duration_sec REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
    conn.commit()


def get_or_create_session(user_id: int) -> str:
    """활성 세션 ID 반환. 없으면 새로 생성."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT session_id FROM sessions WHERE user_id = ? AND is_active = 1 "
        "ORDER BY created_at DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    if row:
        return row["session_id"]
    session_id = str(uuid.uuid4())[:8]
    conn.execute(
        "INSERT INTO sessions (session_id, user_id) VALUES (?, ?)",
        (session_id, user_id),
    )
    conn.commit()
    return session_id


def new_session(user_id: int) -> str:
    """현재 세션 비활성화하고 새 세션 생성."""
    conn = _get_conn()
    conn.execute(
        "UPDATE sessions SET is_active = 0 WHERE user_id = ? AND is_active = 1",
        (user_id,),
    )
    session_id = str(uuid.uuid4())[:8]
    conn.execute(
        "INSERT INTO sessions (session_id, user_id) VALUES (?, ?)",
        (session_id, user_id),
    )
    conn.commit()
    return session_id


def save_message(
    user_id: int,
    session_id: str,
    role: str,
    content: str,
    midi_json: str | None = None,
    midi_path: str | None = None,
) -> None:
    """메시지 저장."""
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT INTO messages (user_id, session_id, role, content, has_midi, midi_json, midi_path) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, session_id, role, content, 1 if midi_json else 0, midi_json, midi_path),
        )
        conn.commit()
    except sqlite3.Error as e:
        logger.error("DB 저장 오류: %s", e)


def get_history(session_id: str, limit: int = 10) -> list[dict]:
    """최근 N쌍 (user+assistant) 히스토리 조회. limit=10이면 최근 20행."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE session_id = ? "
            "ORDER BY created_at DESC LIMIT ?",
            (session_id, limit * 2),
        ).fetchall()
        # 역순으로 정렬 (오래된 것부터)
        return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]
    except sqlite3.Error as e:
        logger.error("DB 조회 오류: %s", e)
        return []


def save_idea(
    user_id: int,
    description: str,
    tags: list[str] | None = None,
    midi_json: str | None = None,
    midi_path: str | None = None,
) -> int:
    """아이디어 저장. 생성된 ID 반환."""
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "INSERT INTO ideas (user_id, description, tags, midi_json, midi_path) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, description, json.dumps(tags or [], ensure_ascii=False), midi_json, midi_path),
        )
        conn.commit()
        return cursor.lastrowid or 0
    except sqlite3.Error as e:
        logger.error("아이디어 저장 오류: %s", e)
        return 0


def get_ideas(user_id: int, limit: int = 20) -> list[dict]:
    """아이디어 목록 조회."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT id, description, tags, midi_path, created_at FROM ideas "
            "WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [
            {
                "id": r["id"],
                "description": r["description"],
                "tags": json.loads(r["tags"]) if r["tags"] else [],
                "midi_path": r["midi_path"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]
    except sqlite3.Error as e:
        logger.error("아이디어 조회 오류: %s", e)
        return []


def save_suno_song(
    user_id: int,
    title: str,
    song_id: str,
    style: str = "",
    lyrics: str = "",
) -> int:
    """Suno 곡 메타데이터 저장."""
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "INSERT INTO suno_songs (user_id, title, song_id, style, lyrics) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, title, song_id, style, lyrics),
        )
        conn.commit()
        return cursor.lastrowid or 0
    except sqlite3.Error as e:
        logger.error("Suno 곡 저장 오류: %s", e)
        return 0


def update_suno_status(
    song_id: str,
    status: str,
    local_path: str | None = None,
    drive_url: str | None = None,
    duration_sec: float | None = None,
) -> None:
    """Suno 곡 상태 업데이트."""
    conn = _get_conn()
    try:
        conn.execute(
            "UPDATE suno_songs SET status=?, local_path=?, drive_url=?, duration_sec=? "
            "WHERE song_id=?",
            (status, local_path, drive_url, duration_sec, song_id),
        )
        conn.commit()
    except sqlite3.Error as e:
        logger.error("Suno 상태 업데이트 오류: %s", e)


def get_suno_songs(user_id: int, limit: int = 20) -> list[dict]:
    """사용자의 Suno 곡 목록."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT id, title, song_id, status, drive_url, duration_sec, created_at "
            "FROM suno_songs WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.Error as e:
        logger.error("Suno 곡 조회 오류: %s", e)
        return []


def get_suno_song(song_id: str) -> dict | None:
    """song_id로 Suno 곡 조회."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM suno_songs WHERE song_id = ?", (song_id,)
        ).fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        logger.error("Suno 곡 조회 오류: %s", e)
        return None


def get_session_messages(session_id: str, limit: int = 50) -> list[dict]:
    """세션 전체 메시지 조회 (role + content). /save용 — 가사/코드 추출에 사용."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT role, content, created_at FROM messages WHERE session_id = ? "
            "ORDER BY created_at DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
        return [
            {"role": r["role"], "content": r["content"], "created_at": r["created_at"]}
            for r in reversed(rows)
        ]
    except sqlite3.Error as e:
        logger.error("세션 메시지 조회 오류: %s", e)
        return []


def get_idea_by_id(idea_id: int) -> dict | None:
    """ID로 아이디어 조회 (midi_json 포함)."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT id, description, tags, midi_json, midi_path, created_at FROM ideas WHERE id = ?",
            (idea_id,),
        ).fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "description": row["description"],
            "tags": json.loads(row["tags"]) if row["tags"] else [],
            "midi_json": row["midi_json"],
            "midi_path": row["midi_path"],
            "created_at": row["created_at"],
        }
    except sqlite3.Error as e:
        logger.error("아이디어 조회 오류: %s", e)
        return None
