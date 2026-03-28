"""
MIDI → 오디오 변환 모듈 (FluidSynth 기반)

FluidSynth CLI를 subprocess로 호출하여 MIDI 바이트를 .ogg 오디오로 변환한다.
사운드폰트 경로는 환경변수 SOUNDFONT_PATH로 지정하거나,
시스템 기본 경로에서 자동 탐색한다.
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

# 시스템 기본 사운드폰트 경로 목록 (우선순위 순)
_DEFAULT_SOUNDFONT_PATHS: list[str] = [
    "/usr/share/sounds/sf2/FluidR3_GM.sf2",
    "/usr/share/soundfonts/FluidR3_GM.sf2",
]


def _find_soundfont() -> str | None:
    """사운드폰트 파일 경로를 찾는다.

    1. 환경변수 SOUNDFONT_PATH가 설정되어 있으면 해당 경로 사용
    2. 없으면 시스템 기본 경로에서 순서대로 탐색
    3. 모두 없으면 None 반환
    """
    # 환경변수 우선 확인
    env_path = os.environ.get("SOUNDFONT_PATH")
    if env_path:
        if Path(env_path).is_file():
            return env_path
        logger.warning("SOUNDFONT_PATH 환경변수 경로에 파일이 없음: %s", env_path)

    # 시스템 기본 경로 탐색
    for path in _DEFAULT_SOUNDFONT_PATHS:
        if Path(path).is_file():
            return path

    return None


def midi_to_audio(midi_bytes: bytes) -> bytes | None:
    """MIDI 바이트 데이터를 .ogg 오디오 바이트로 변환한다.

    Args:
        midi_bytes: MIDI 파일의 바이트 데이터

    Returns:
        변환된 .ogg 오디오 바이트, 실패 시 None
    """
    # FluidSynth 설치 여부 확인
    if shutil.which("fluidsynth") is None:
        logger.error("FluidSynth가 설치되어 있지 않음 (fluidsynth 명령을 찾을 수 없음)")
        return None

    # 사운드폰트 탐색
    soundfont = _find_soundfont()
    if soundfont is None:
        logger.error("사운드폰트 파일을 찾을 수 없음. SOUNDFONT_PATH 환경변수를 설정하세요")
        return None

    # 임시 파일로 변환 작업 수행
    tmp_dir = tempfile.mkdtemp(prefix="music_lab_")
    midi_path = os.path.join(tmp_dir, "input.mid")
    ogg_path = os.path.join(tmp_dir, "output.ogg")

    try:
        # MIDI 바이트를 임시 파일에 기록
        with open(midi_path, "wb") as f:
            f.write(midi_bytes)

        # FluidSynth로 MIDI → OGG 변환
        cmd: list[str] = [
            "fluidsynth",
            "-ni",          # -n: MIDI 플레이어 없이 실행, -i: 인터랙티브 모드 비활성화
            soundfont,
            midi_path,
            "-F", ogg_path, # 출력 파일 지정
            "-T", "oga",    # 출력 형식: Ogg/Vorbis
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=60,
            check=False,
        )

        if result.returncode != 0:
            stderr_text = result.stderr.decode("utf-8", errors="replace")
            logger.error("FluidSynth 변환 실패 (returncode=%d): %s", result.returncode, stderr_text)
            return None

        # 변환된 오디오 파일 읽기
        ogg_file = Path(ogg_path)
        if not ogg_file.is_file() or ogg_file.stat().st_size == 0:
            logger.error("FluidSynth 변환 결과 파일이 없거나 비어 있음: %s", ogg_path)
            return None

        return ogg_file.read_bytes()

    except subprocess.TimeoutExpired:
        logger.error("FluidSynth 변환 타임아웃 (60초 초과)")
        return None
    except OSError as exc:
        logger.error("파일 I/O 오류: %s", exc)
        return None
    finally:
        # 임시 파일 정리
        for path in (midi_path, ogg_path):
            try:
                os.remove(path)
            except OSError:
                pass
        try:
            os.rmdir(tmp_dir)
        except OSError:
            pass
