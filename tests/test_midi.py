"""MIDI 파싱, 생성, 피아노롤 시각화 테스트."""
import json
import pytest

# bot.py에서 함수 직접 import
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from bot import parse_midi_json, generate_midi
from midi_utils import render_piano_roll


# ---------------------------------------------------------------------------
# parse_midi_json 테스트
# ---------------------------------------------------------------------------
class TestParseMidiJson:
    def test_정상_파싱(self):
        text = '''설명입니다.
```midi-json
{"title": "테스트", "bpm": 120, "tracks": [{"name": "멜로디", "instrument": 0, "channel": 0, "notes": [{"pitch": 60, "start": 0, "duration": 1, "velocity": 100}]}]}
```
추가 설명.'''
        result = parse_midi_json(text)
        assert result is not None
        assert result["title"] == "테스트"
        assert result["bpm"] == 120
        assert len(result["tracks"]) == 1
        assert result["tracks"][0]["notes"][0]["pitch"] == 60

    def test_블록_없음(self):
        text = "MIDI 없는 일반 텍스트 응답입니다."
        assert parse_midi_json(text) is None

    def test_잘못된_json(self):
        text = '```midi-json\n{잘못된 json}\n```'
        assert parse_midi_json(text) is None

    def test_빈_문자열(self):
        assert parse_midi_json("") is None


# ---------------------------------------------------------------------------
# generate_midi 테스트
# ---------------------------------------------------------------------------
class TestGenerateMidi:
    def test_정상_생성(self):
        data = {
            "bpm": 120,
            "tracks": [{
                "name": "멜로디",
                "instrument": 0,
                "channel": 0,
                "notes": [
                    {"pitch": 60, "start": 0.0, "duration": 1.0, "velocity": 100},
                    {"pitch": 62, "start": 1.0, "duration": 1.0, "velocity": 100},
                ],
            }],
        }
        result = generate_midi(data)
        assert isinstance(result, bytes)
        assert len(result) > 0
        # MIDI 파일 매직 바이트: MThd
        assert result[:4] == b"MThd"

    def test_빈_트랙(self):
        data = {"bpm": 120, "tracks": [{"name": "빈트랙", "instrument": 0, "channel": 0, "notes": []}]}
        result = generate_midi(data)
        assert isinstance(result, bytes)
        assert result[:4] == b"MThd"

    def test_트랙_없음(self):
        data = {"bpm": 120, "tracks": []}
        result = generate_midi(data)
        assert isinstance(result, bytes)

    def test_멀티트랙(self):
        data = {
            "bpm": 100,
            "tracks": [
                {"name": "멜로디", "instrument": 0, "channel": 0,
                 "notes": [{"pitch": 60, "start": 0, "duration": 2, "velocity": 80}]},
                {"name": "베이스", "instrument": 33, "channel": 1,
                 "notes": [{"pitch": 36, "start": 0, "duration": 4, "velocity": 90}]},
            ],
        }
        result = generate_midi(data)
        assert isinstance(result, bytes)
        assert len(result) > 50


# ---------------------------------------------------------------------------
# render_piano_roll 테스트
# ---------------------------------------------------------------------------
class TestRenderPianoRoll:
    def test_정상_렌더링(self):
        data = {
            "tracks": [{
                "notes": [
                    {"pitch": 60, "start": 0, "duration": 2},
                    {"pitch": 64, "start": 2, "duration": 1},
                    {"pitch": 67, "start": 3, "duration": 1},
                ],
            }],
        }
        result = render_piano_roll(data)
        assert "```" in result
        assert "C4" in result
        assert "E4" in result
        assert "G4" in result
        assert "█" in result

    def test_빈_노트(self):
        data = {"tracks": [{"notes": []}]}
        result = render_piano_roll(data)
        assert "노트 없음" in result

    def test_트랙_없음(self):
        data = {"tracks": []}
        result = render_piano_roll(data)
        assert "노트 없음" in result

    def test_16비트_초과_축소(self):
        """16비트 초과 시 자동 스케일링 확인."""
        data = {
            "tracks": [{
                "notes": [
                    {"pitch": 60, "start": 0, "duration": 1},
                    {"pitch": 62, "start": 20, "duration": 1},  # 20비트 시점
                ],
            }],
        }
        result = render_piano_roll(data)
        # 정상적으로 렌더링되어야 함
        assert "```" in result
        assert "█" in result
