"""DB 모듈 테스트 — 대화 히스토리 저장/조회, 세션 관리, 아이디어 CRUD."""
import os
import tempfile
import pytest

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import db


@pytest.fixture(autouse=True)
def 임시_db(tmp_path):
    """각 테스트마다 임시 DB 사용."""
    db_path = str(tmp_path / "test.db")
    db.DB_PATH = db_path
    db._conn = None  # 싱글턴 커넥션 리셋
    db.init_db()
    yield db_path
    db._conn = None  # 테스트 후 정리


# ---------------------------------------------------------------------------
# 세션 관리 테스트
# ---------------------------------------------------------------------------
class TestSession:
    def test_새_세션_생성(self):
        session_id = db.get_or_create_session(12345)
        assert session_id is not None
        assert len(session_id) == 8

    def test_기존_세션_반환(self):
        s1 = db.get_or_create_session(12345)
        s2 = db.get_or_create_session(12345)
        assert s1 == s2

    def test_new_session_이전_비활성화(self):
        s1 = db.get_or_create_session(12345)
        s2 = db.new_session(12345)
        assert s1 != s2
        # 새로 조회하면 s2가 반환되어야 함
        s3 = db.get_or_create_session(12345)
        assert s3 == s2


# ---------------------------------------------------------------------------
# 메시지 저장/조회 테스트
# ---------------------------------------------------------------------------
class TestMessages:
    def test_메시지_저장_조회(self):
        session_id = db.get_or_create_session(12345)
        db.save_message(12345, session_id, "user", "안녕하세요")
        db.save_message(12345, session_id, "assistant", "반갑습니다!")

        history = db.get_history(session_id)
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "안녕하세요"
        assert history[1]["role"] == "assistant"

    def test_히스토리_limit(self):
        session_id = db.get_or_create_session(12345)
        # 25쌍(50행) 저장
        for i in range(25):
            db.save_message(12345, session_id, "user", f"질문 {i}")
            db.save_message(12345, session_id, "assistant", f"답변 {i}")

        # limit=10이면 최근 10쌍 = 20행
        history = db.get_history(session_id, limit=10)
        assert len(history) == 20
        # 가장 오래된 것이 첫 번째 (15번부터)
        assert "질문 15" in history[0]["content"]

    def test_히스토리_0건(self):
        history = db.get_history("nonexistent")
        assert history == []

    def test_세션별_필터링(self):
        s1 = db.get_or_create_session(12345)
        s2 = db.new_session(12345)
        db.save_message(12345, s1, "user", "세션1 메시지")
        db.save_message(12345, s2, "user", "세션2 메시지")

        h1 = db.get_history(s1)
        h2 = db.get_history(s2)
        assert len(h1) == 1
        assert len(h2) == 1
        assert "세션1" in h1[0]["content"]
        assert "세션2" in h2[0]["content"]

    def test_midi_json_저장(self):
        session_id = db.get_or_create_session(12345)
        db.save_message(
            12345, session_id, "assistant", "MIDI 생성됨",
            midi_json='{"title":"test","tracks":[]}',
            midi_path="data/midi/12345/test.mid",
        )
        history = db.get_history(session_id)
        assert len(history) == 1


# ---------------------------------------------------------------------------
# 아이디어 CRUD 테스트
# ---------------------------------------------------------------------------
class TestIdeas:
    def test_아이디어_저장_조회(self):
        idea_id = db.save_idea(12345, "비오는 날 피아노", tags=["재즈", "피아노"])
        assert idea_id > 0

        ideas = db.get_ideas(12345)
        assert len(ideas) == 1
        assert ideas[0]["description"] == "비오는 날 피아노"
        assert "재즈" in ideas[0]["tags"]

    def test_아이디어_id_조회(self):
        idea_id = db.save_idea(
            12345, "멜로디 아이디어",
            midi_json='{"title":"test"}',
        )
        idea = db.get_idea_by_id(idea_id)
        assert idea is not None
        assert idea["midi_json"] == '{"title":"test"}'

    def test_존재하지_않는_아이디어(self):
        assert db.get_idea_by_id(9999) is None
