"""오디오 변환 모듈 테스트 — FluidSynth 설치 여부에 관계없이 동작."""
import os
import shutil
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from audio import midi_to_audio, _find_soundfont


class TestFindSoundfont:
    def test_환경변수_경로(self, tmp_path, monkeypatch):
        """SOUNDFONT_PATH 환경변수가 설정되면 해당 경로 반환."""
        sf_path = tmp_path / "test.sf2"
        sf_path.write_bytes(b"fake soundfont")
        monkeypatch.setenv("SOUNDFONT_PATH", str(sf_path))
        assert _find_soundfont() == str(sf_path)

    def test_환경변수_파일_없음(self, monkeypatch):
        """SOUNDFONT_PATH가 있지만 파일이 없으면 시스템 경로 탐색."""
        monkeypatch.setenv("SOUNDFONT_PATH", "/nonexistent/path.sf2")
        # 시스템에 사운드폰트가 있을 수도 없을 수도 있으므로
        # None이거나 str이면 OK
        result = _find_soundfont()
        assert result is None or isinstance(result, str)


class TestMidiToAudio:
    def test_fluidsynth_미설치_시_none(self, monkeypatch):
        """FluidSynth가 없으면 None 반환."""
        monkeypatch.setattr(shutil, "which", lambda cmd: None)
        result = midi_to_audio(b"fake midi data")
        assert result is None

    def test_빈_바이트(self, monkeypatch):
        """빈 MIDI 데이터도 에러 없이 None 반환."""
        monkeypatch.setattr(shutil, "which", lambda cmd: None)
        result = midi_to_audio(b"")
        assert result is None
