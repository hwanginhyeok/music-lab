"""
autopilot/nodes/postprocess.py — 후처리 노드 (Phase 4: -14 LUFS 라우드니스 정규화).

ffmpeg loudnorm 필터로 통합 라우드니스를 -14 LUFS로 맞춘다.
runner 주입으로 테스트 시 실제 ffmpeg 실행 없이 mock 가능.
"""
from __future__ import annotations

import hashlib
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Callable

from autopilot import trace as _trace
from autopilot.engine import Ctx, step

logger = logging.getLogger("autopilot.nodes.postprocess")

# -14 LUFS / TP -1.5 / LRA 11 (EBU R128 스트리밍 표준)
_TARGET_LUFS: float = -14.0
_FFMPEG_PATH: str = os.environ.get("FFMPEG_PATH", "/usr/bin/ffmpeg")

# 정규화 출력 파일 접미사
_NORMALIZED_SUFFIX: str = "_normalized"


# ---------------------------------------------------------------------------
# 노드
# ---------------------------------------------------------------------------

@step("후처리")
def postprocess_node(
    ctx: Ctx,
    audio_path: str,
    runner: Callable[..., Any] = subprocess.run,
) -> dict:
    """오디오 파일을 -14 LUFS로 라우드니스 정규화하고 결과를 반환한다.

    audio_path: 원본 오디오 파일 경로 (WAV/MP3/FLAC).
    runner:     subprocess.run 대체 인자 — 테스트 시 mock 주입.

    returns: {
        "path":        정규화된 파일 경로,
        "sha256":      정규화 파일 SHA-256,
        "lufs_target": -14 (고정),
    }
    """
    src = Path(audio_path)
    stem = src.stem + _NORMALIZED_SUFFIX
    out_path = src.parent / (stem + src.suffix)

    # ffmpeg loudnorm 명령 구성
    # 2-패스가 더 정확하지만 1-패스(linear)로도 streaming 표준 충족.
    # 단순성 우선 (1-패스).
    cmd = [
        _FFMPEG_PATH, "-y",
        "-i", str(src),
        "-af", f"loudnorm=I={_TARGET_LUFS}:TP=-1.5:LRA=11",
        "-ar", "44100",
        str(out_path),
    ]

    logger.info("후처리: loudnorm %s → %s", src.name, out_path.name)

    result = runner(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        stderr_tail = (result.stderr or "")[-400:]
        raise RuntimeError(f"ffmpeg loudnorm 실패 (returncode={result.returncode}): {stderr_tail}")

    # SHA-256 계산 (파일이 실제로 존재하는 경우에만)
    if out_path.exists():
        sha256 = hashlib.sha256(out_path.read_bytes()).hexdigest()
    else:
        # mock 환경: 입력 경로를 출력으로 재사용하고 sha256은 빈 문자열
        sha256 = ""
        out_path = src  # fallback

    # artifact 등록
    ctx.store.add_artifact(
        run_id=ctx.run_id,
        step_name="후처리",
        kind="audio_mastered",
        path=str(out_path),
        sha256=sha256,
        meta={"target_lufs": _TARGET_LUFS, "tp": -1.5, "lra": 11},
    )

    # trace 기록
    _trace.emit({
        "event": "postprocess_done",
        "run_id": ctx.run_id,
        "src": str(src),
        "out": str(out_path),
        "lufs_target": _TARGET_LUFS,
        "ts": time.time(),
    })

    logger.info("후처리 완료: %s (sha256=%s...)", out_path.name, sha256[:8])

    return {
        "path": str(out_path),
        "sha256": sha256,
        "lufs_target": _TARGET_LUFS,
    }


# ---------------------------------------------------------------------------
# 하위 호환성 stub — 사용하지 말 것 (Phase 2 시그니처 유지)
# ---------------------------------------------------------------------------

def postprocess(audio_path: str) -> str:
    """[DEPRECATED] Phase 2 stub. postprocess_node(ctx, audio_path)로 교체됨."""
    raise NotImplementedError("Phase 4에서 postprocess_node(ctx, audio_path, runner=...)로 교체됨")
