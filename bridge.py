#!/usr/bin/env python3
"""
Music Lab DB 브릿지 — 텔레그램 봇 대화/아이디어를 CLI에서 조회.

텔레그램에서 기록한 영감과 대화를 여기서 이어받아 작업하기 위한 도구.

사용법:
  python3 bridge.py recent          # 최근 대화 20건
  python3 bridge.py recent 50       # 최근 대화 50건
  python3 bridge.py session         # 현재 활성 세션 대화 전체
  python3 bridge.py sessions        # 세션 목록
  python3 bridge.py ideas           # 아이디어 라이브러리
  python3 bridge.py idea 3          # 아이디어 #3 상세 (midi_json 포함)
  python3 bridge.py search 재즈     # 대화/아이디어에서 키워드 검색
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

DB_PATH = "data/music-lab.db"


def _conn() -> sqlite3.Connection:
    if not Path(DB_PATH).is_file():
        print(f"DB 파일 없음: {DB_PATH}")
        print("텔레그램 봇을 먼저 실행해서 DB를 생성하세요.")
        sys.exit(1)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def cmd_recent(limit: int = 20) -> None:
    """최근 대화 메시지 조회."""
    conn = _conn()
    rows = conn.execute(
        "SELECT m.role, m.content, m.has_midi, m.created_at, m.session_id "
        "FROM messages m ORDER BY m.created_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()

    if not rows:
        print("대화 기록이 없습니다.")
        return

    print(f"=== 최근 대화 {len(rows)}건 (최신순) ===\n")
    for row in reversed(rows):
        role = "🧑" if row["role"] == "user" else "🤖"
        midi = " 🎹" if row["has_midi"] else ""
        ts = row["created_at"][:16] if row["created_at"] else ""
        content = row["content"]
        # midi-json 블록 요약
        if "```midi-json" in content:
            import re
            content = re.sub(
                r"```midi-json\s*\n.*?\n```",
                "[MIDI 데이터]",
                content,
                flags=re.DOTALL,
            )
        # 길면 자르기
        if len(content) > 300:
            content = content[:300] + "..."
        print(f"[{ts}] [{row['session_id'][:8]}] {role}{midi}")
        print(f"  {content}\n")


def cmd_session() -> None:
    """현재 활성 세션의 전체 대화."""
    conn = _conn()
    session = conn.execute(
        "SELECT session_id FROM sessions WHERE is_active = 1 "
        "ORDER BY created_at DESC LIMIT 1",
    ).fetchone()

    if not session:
        print("활성 세션이 없습니다.")
        conn.close()
        return

    sid = session["session_id"]
    rows = conn.execute(
        "SELECT role, content, has_midi, created_at FROM messages "
        "WHERE session_id = ? ORDER BY created_at",
        (sid,),
    ).fetchall()
    conn.close()

    print(f"=== 활성 세션 [{sid}] — {len(rows)}건 ===\n")
    for row in rows:
        role = "🧑 USER" if row["role"] == "user" else "🤖 ASSISTANT"
        midi = " 🎹" if row["has_midi"] else ""
        ts = row["created_at"][:16] if row["created_at"] else ""
        print(f"--- {role}{midi} [{ts}] ---")
        print(row["content"])
        print()


def cmd_sessions() -> None:
    """전체 세션 목록."""
    conn = _conn()
    rows = conn.execute(
        "SELECT s.session_id, s.title, s.is_active, s.created_at, "
        "  (SELECT COUNT(*) FROM messages m WHERE m.session_id = s.session_id) as msg_count "
        "FROM sessions s ORDER BY s.created_at DESC",
    ).fetchall()
    conn.close()

    if not rows:
        print("세션이 없습니다.")
        return

    print("=== 세션 목록 ===\n")
    for row in rows:
        active = "🟢" if row["is_active"] else "⚪"
        ts = row["created_at"][:16] if row["created_at"] else ""
        print(f"  {active} [{row['session_id']}] {row['title']} — {row['msg_count']}건 ({ts})")


def cmd_ideas() -> None:
    """아이디어 라이브러리."""
    conn = _conn()
    rows = conn.execute(
        "SELECT id, description, tags, midi_path, created_at FROM ideas "
        "ORDER BY created_at DESC",
    ).fetchall()
    conn.close()

    if not rows:
        print("저장된 아이디어가 없습니다.")
        return

    print(f"=== 아이디어 라이브러리 ({len(rows)}개) ===\n")
    for row in rows:
        tags = json.loads(row["tags"]) if row["tags"] else []
        tag_str = " ".join(f"#{t}" for t in tags)
        midi = " 🎹" if row["midi_path"] else ""
        ts = row["created_at"][:16] if row["created_at"] else ""
        print(f"  #{row['id']}  {row['description']}{midi}")
        if tag_str:
            print(f"      {tag_str}")
        print(f"      {ts}")
        print()


def cmd_idea(idea_id: int) -> None:
    """아이디어 상세 조회 (midi_json 포함)."""
    conn = _conn()
    row = conn.execute(
        "SELECT * FROM ideas WHERE id = ?", (idea_id,),
    ).fetchone()
    conn.close()

    if not row:
        print(f"아이디어 #{idea_id}를 찾을 수 없습니다.")
        return

    tags = json.loads(row["tags"]) if row["tags"] else []
    print(f"=== 아이디어 #{row['id']} ===\n")
    print(f"  설명: {row['description']}")
    print(f"  태그: {' '.join(f'#{t}' for t in tags)}")
    print(f"  생성: {row['created_at']}")
    if row["midi_path"]:
        print(f"  MIDI: {row['midi_path']}")
    if row["midi_json"]:
        print(f"\n  MIDI JSON:")
        try:
            data = json.loads(row["midi_json"])
            print(json.dumps(data, indent=2, ensure_ascii=False))
        except json.JSONDecodeError:
            print(f"  {row['midi_json']}")


def cmd_search(keyword: str) -> None:
    """대화와 아이디어에서 키워드 검색."""
    conn = _conn()

    # 메시지 검색
    msg_rows = conn.execute(
        "SELECT role, content, session_id, created_at FROM messages "
        "WHERE content LIKE ? ORDER BY created_at DESC LIMIT 20",
        (f"%{keyword}%",),
    ).fetchall()

    # 아이디어 검색
    idea_rows = conn.execute(
        "SELECT id, description, tags FROM ideas "
        "WHERE description LIKE ? OR tags LIKE ?",
        (f"%{keyword}%", f"%{keyword}%"),
    ).fetchall()
    conn.close()

    print(f"=== '{keyword}' 검색 결과 ===\n")

    if idea_rows:
        print(f"📌 아이디어 {len(idea_rows)}건:")
        for row in idea_rows:
            print(f"  #{row['id']} {row['description']}")
        print()

    if msg_rows:
        print(f"💬 대화 {len(msg_rows)}건:")
        for row in msg_rows:
            role = "🧑" if row["role"] == "user" else "🤖"
            content = row["content"][:150]
            ts = row["created_at"][:16] if row["created_at"] else ""
            print(f"  {role} [{ts}] {content}")
        print()

    if not msg_rows and not idea_rows:
        print("  결과 없음.")


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]

    if cmd == "recent":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        cmd_recent(limit)
    elif cmd == "session":
        cmd_session()
    elif cmd == "sessions":
        cmd_sessions()
    elif cmd == "ideas":
        cmd_ideas()
    elif cmd == "idea":
        if len(sys.argv) < 3:
            print("사용법: python3 bridge.py idea [번호]")
            return
        cmd_idea(int(sys.argv[2]))
    elif cmd == "search":
        if len(sys.argv) < 3:
            print("사용법: python3 bridge.py search [키워드]")
            return
        cmd_search(" ".join(sys.argv[2:]))
    else:
        print(f"알 수 없는 명령: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
