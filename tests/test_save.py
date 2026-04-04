"""/save 명령어 테스트 — 가사/코드 추출, 곡 번호 계산, 파일 저장."""
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pathlib import Path

from bot import _extract_lyrics, _extract_chords, _next_song_number, _build_concept, SONGS_DIR
import bot
import db


@pytest.fixture(autouse=True)
def 임시_db(tmp_path):
    """각 테스트마다 임시 DB 사용."""
    db_path = str(tmp_path / "test.db")
    db.DB_PATH = db_path
    db._conn = None
    db.init_db()
    yield db_path
    db._conn = None


@pytest.fixture(autouse=True)
def songs_dir_복원():
    """테스트 후 SONGS_DIR 원래 값으로 복원."""
    original = bot.SONGS_DIR
    yield
    bot.SONGS_DIR = original


# ---------------------------------------------------------------------------
# 가사 추출 테스트
# ---------------------------------------------------------------------------
class TestExtractLyrics:
    def test_기본_가사_추출(self):
        messages = [
            {"role": "user", "content": "이별 발라드 가사 써줘"},
            {"role": "assistant", "content": (
                "좋은 주제네요! 가사를 써볼게요.\n\n"
                "[Verse 1]\n"
                "거리에 비가 내리면\n"
                "네 생각이 나곤 해\n\n"
                "[Chorus]\n"
                "보고 싶다 말할 수 없어\n"
                "그저 바라보기만 해\n\n"
                "이런 느낌으로 작성했어요."
            )},
        ]
        lyrics = _extract_lyrics(messages)
        assert lyrics is not None
        assert "[Verse 1]" in lyrics
        assert "[Chorus]" in lyrics
        assert "거리에 비가 내리면" in lyrics
        assert "보고 싶다" in lyrics

    def test_가사_없는_대화(self):
        messages = [
            {"role": "user", "content": "C 코드가 뭐야?"},
            {"role": "assistant", "content": "C 코드는 도미솔(C-E-G)입니다."},
        ]
        assert _extract_lyrics(messages) is None

    def test_최근_가사_우선(self):
        messages = [
            {"role": "assistant", "content": "[Verse 1]\n첫 번째 가사"},
            {"role": "user", "content": "다시 써줘"},
            {"role": "assistant", "content": "[Verse 1]\n두 번째 가사\n[Chorus]\n수정된 코러스"},
        ]
        lyrics = _extract_lyrics(messages)
        assert "두 번째 가사" in lyrics
        assert "수정된 코러스" in lyrics

    def test_다양한_섹션_마커(self):
        messages = [
            {"role": "assistant", "content": (
                "[Intro]\n음악이 시작되고\n\n"
                "[Verse 1]\n걸어가는 길 위에\n\n"
                "[Pre-Chorus]\n숨을 참고\n\n"
                "[Chorus]\n날아올라\n\n"
                "[Bridge]\n멈추지 마\n\n"
                "[Outro]\n끝나지 않아"
            )},
        ]
        lyrics = _extract_lyrics(messages)
        assert lyrics is not None
        assert "[Intro]" in lyrics
        assert "[Bridge]" in lyrics
        assert "[Outro]" in lyrics

    def test_빈_메시지_목록(self):
        assert _extract_lyrics([]) is None

    def test_user_메시지만(self):
        messages = [
            {"role": "user", "content": "[Verse 1]\n내가 쓴 가사"},
        ]
        # user 메시지는 무시 (assistant만 추출)
        assert _extract_lyrics(messages) is None


# ---------------------------------------------------------------------------
# 코드 진행 추출 테스트
# ---------------------------------------------------------------------------
class TestExtractChords:
    def test_기본_코드_추출(self):
        messages = [
            {"role": "assistant", "content": (
                "밝은 팝 코드 진행을 추천할게요!\n\n"
                "| C  | G  | Am | F  |\n"
                "| C  | G  | Em | F  |\n"
                "분석: I - V - vi - IV\n"
                "분위기: 밝고 편안함"
            )},
        ]
        chords = _extract_chords(messages)
        assert chords is not None
        assert "| C" in chords
        assert "분석:" in chords

    def test_코드_없는_대화(self):
        messages = [
            {"role": "assistant", "content": "음악 이론에 대해 설명할게요."},
        ]
        assert _extract_chords(messages) is None

    def test_화살표_코드_진행(self):
        messages = [
            {"role": "assistant", "content": (
                "추천 진행:\n"
                "C → G → Am → F\n"
                "밝은 느낌의 진행입니다."
            )},
        ]
        chords = _extract_chords(messages)
        assert chords is not None
        assert "C → G" in chords

    def test_빈_메시지_목록(self):
        assert _extract_chords([]) is None


# ---------------------------------------------------------------------------
# 곡 번호 계산 테스트
# ---------------------------------------------------------------------------
class TestNextSongNumber:
    def test_빈_디렉토리(self, tmp_path):
        bot.SONGS_DIR = tmp_path / "songs"
        bot.SONGS_DIR.mkdir()
        assert _next_song_number() == 1

    def test_기존_곡_있을_때(self, tmp_path):
        songs_dir = tmp_path / "songs"
        songs_dir.mkdir()
        (songs_dir / "01_첫곡").mkdir()
        (songs_dir / "02_두번째").mkdir()
        bot.SONGS_DIR = songs_dir
        assert _next_song_number() == 3

    def test_번호_빠진_경우(self, tmp_path):
        songs_dir = tmp_path / "songs"
        songs_dir.mkdir()
        (songs_dir / "01_첫곡").mkdir()
        (songs_dir / "05_다섯번째").mkdir()
        bot.SONGS_DIR = songs_dir
        assert _next_song_number() == 6

    def test_template_무시(self, tmp_path):
        songs_dir = tmp_path / "songs"
        songs_dir.mkdir()
        (songs_dir / "template").mkdir()
        (songs_dir / "01_곡").mkdir()
        bot.SONGS_DIR = songs_dir
        assert _next_song_number() == 2

    def test_songs_디렉토리_없으면_1(self, tmp_path):
        bot.SONGS_DIR = tmp_path / "nonexistent"
        assert _next_song_number() == 1


# ---------------------------------------------------------------------------
# concept.md 생성 테스트
# ---------------------------------------------------------------------------
class TestBuildConcept:
    def test_기본_생성(self):
        messages = [
            {"role": "user", "content": "슬픈 발라드 가사 써줘"},
            {"role": "assistant", "content": "[Verse 1]\n눈물이 흐르고"},
        ]
        concept = _build_concept("슬픈 밤", messages, has_lyrics=True, has_chords=False)
        assert "슬픈 밤" in concept
        assert "lyrics_v1.md" in concept
        assert "chord_ref.md" not in concept

    def test_가사_코드_모두_포함(self):
        messages = [{"role": "user", "content": "작업해줘"}]
        concept = _build_concept("테스트곡", messages, has_lyrics=True, has_chords=True)
        assert "lyrics_v1.md" in concept
        assert "chord_ref.md" in concept


# ---------------------------------------------------------------------------
# DB: get_session_messages 테스트
# ---------------------------------------------------------------------------
class TestGetSessionMessages:
    def test_세션_메시지_조회(self):
        session_id = db.get_or_create_session(12345)
        db.save_message(12345, session_id, "user", "가사 써줘")
        db.save_message(12345, session_id, "assistant", "[Verse 1]\n가사")

        messages = db.get_session_messages(session_id)
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        assert "created_at" in messages[0]

    def test_빈_세션(self):
        messages = db.get_session_messages("nonexistent")
        assert messages == []

    def test_limit_적용(self):
        session_id = db.get_or_create_session(12345)
        for i in range(10):
            db.save_message(12345, session_id, "user", f"질문 {i}")
            db.save_message(12345, session_id, "assistant", f"답변 {i}")

        messages = db.get_session_messages(session_id, limit=4)
        assert len(messages) == 4
