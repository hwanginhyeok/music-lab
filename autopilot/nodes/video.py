"""
autopilot/nodes/video.py — 영상 생성 노드 (Phase 4).

커버 이미지(또는 검정 배경) + 오디오 → MP4 영상.
ffmpeg를 runner 주입으로 mock 가능하므로 테스트 시 실제 ffmpeg 실행 없음.

scripts/create_video.create_video는 subprocess.run을 모듈 레벨로 직접 호출하므로
runner 주입이 불가능하다. 따라서 이 노드는 ffmpeg 명령을 최소 재구현하되,
runner 파라미터로 격리한다 (scripts/create_video의 로직과 동일한 정지-이미지 명령).
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

logger = logging.getLogger("autopilot.nodes.video")

_FFMPEG_PATH: str = os.environ.get("FFMPEG_PATH", "/usr/bin/ffmpeg")


# ---------------------------------------------------------------------------
# 노드
# ---------------------------------------------------------------------------

@step("영상")
def video_node(
    ctx: Ctx,
    audio_path: str,
    title: str,
    cover_path: str | None = None,
    runner: Callable[..., Any] = subprocess.run,
) -> dict:
    """오디오 + 커버(없으면 검정 배경)로 1920x1080 MP4를 생성한다.

    audio_path: 정규화된 오디오 파일 경로.
    title:      곡 제목 (검정 배경 fallback 시 텍스트 표시용).
    cover_path: 커버 이미지 경로. None이거나 파일 없으면 검정 배경.
    runner:     subprocess.run 대체 인자 — 테스트 시 mock 주입.

    returns: {"path": MP4 경로, "sha256": SHA-256}
    """
    src_audio = Path(audio_path)
    # 출력 MP4는 오디오와 같은 디렉토리에 저장
    out_path = src_audio.parent / (src_audio.stem + ".mp4")

    # 커버 이미지 결정
    use_cover = cover_path and Path(cover_path).is_file()
    image_arg = str(cover_path) if use_cover else None

    if use_cover:
        cmd = _cmd_with_cover(image_arg, str(src_audio), str(out_path))
    else:
        cmd = _cmd_black_bg(title, str(src_audio), str(out_path))

    logger.info("영상 생성: %s → %s", src_audio.name, out_path.name)

    result = runner(cmd, capture_output=True, text=True, timeout=600)

    if result.returncode != 0:
        stderr_tail = (result.stderr or "")[-400:]
        raise RuntimeError(f"ffmpeg 영상 생성 실패 (returncode={result.returncode}): {stderr_tail}")

    # SHA-256 (실제 파일이 있는 경우)
    if out_path.exists():
        sha256 = hashlib.sha256(out_path.read_bytes()).hexdigest()
    else:
        sha256 = ""  # mock 환경

    # artifact 등록
    ctx.store.add_artifact(
        run_id=ctx.run_id,
        step_name="영상",
        kind="video",
        path=str(out_path),
        sha256=sha256,
        meta={"title": title, "cover_used": bool(use_cover)},
    )

    _trace.emit({
        "event": "video_done",
        "run_id": ctx.run_id,
        "out": str(out_path),
        "sha256": sha256[:8] if sha256 else "",
        "ts": time.time(),
    })

    logger.info("영상 생성 완료: %s", out_path.name)

    return {"path": str(out_path), "sha256": sha256}


# ---------------------------------------------------------------------------
# 내부: ffmpeg 명령 빌더
# ---------------------------------------------------------------------------

def _cmd_with_cover(image_path: str, audio_path: str, out_path: str) -> list[str]:
    """정지 커버 이미지 + 오디오 → MP4 명령 (scripts/create_video 기존 방식)."""
    vf = (
        "scale=1920:1080:force_original_aspect_ratio=decrease,"
        "pad=1920:1080:(ow-iw)/2:(oh-ih)/2"
    )
    return [
        _FFMPEG_PATH, "-y",
        "-loop", "1",
        "-i", image_path,
        "-i", audio_path,
        "-c:v", "libx264",
        "-tune", "stillimage",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-vf", vf,
        "-shortest",
        out_path,
    ]


def _cmd_black_bg(title: str, audio_path: str, out_path: str) -> list[str]:
    """검정 배경 + 오디오 → MP4 명령 (커버 이미지 없을 때 fallback)."""
    # drawtext는 폰트가 없으면 실패할 수 있으므로 간단히 color 필터로 배경만 생성.
    # 노드 범위에서는 title을 메타데이터로만 기록하고 영상은 단순 검정 배경.
    vf = "color=c=black:s=1920x1080"
    return [
        _FFMPEG_PATH, "-y",
        "-f", "lavfi", "-i", vf,
        "-i", audio_path,
        "-c:v", "libx264",
        "-tune", "stillimage",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        out_path,
    ]
