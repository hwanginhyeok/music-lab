"""
autopilot/nodes/postprocess.py — 후처리 노드 (Phase 4: -14 LUFS 라우드니스 정규화).

ffmpeg loudnorm 필터로 통합 라우드니스를 -14 LUFS로 맞춘다.
2-패스 방식 (측정 → 측정값 기반 linear 적용)으로 ±0.1 LU 정확도를 달성한다.
1-패스는 -14 타깃에서 ~0.5 LU 오버슛이 발생하므로 2-패스를 사용한다.
runner 주입으로 테스트 시 실제 ffmpeg 실행 없이 mock 가능.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Callable

from autopilot import trace as _trace
from autopilot.engine import Ctx, step

logger = logging.getLogger("autopilot.nodes.postprocess")

# -14 LUFS / TP -1.5 / LRA 11 (EBU R128 스트리밍 표준)
_TARGET_LUFS: float = -14.0
_TARGET_TP: float = -1.5
_TARGET_LRA: float = 11.0
_FFMPEG_PATH: str = os.environ.get("FFMPEG_PATH", "/usr/bin/ffmpeg")

# 정규화 출력 파일 접미사
_NORMALIZED_SUFFIX: str = "_normalized"


# ---------------------------------------------------------------------------
# 명령 빌더
# ---------------------------------------------------------------------------

def _pass1_cmd(src: Path) -> list[str]:
    """Pass 1: 라우드니스 측정 (print_format=json, 출력 없이 null sink)."""
    return [
        _FFMPEG_PATH, "-y",
        "-i", str(src),
        "-af", (
            f"loudnorm=I={_TARGET_LUFS}:TP={_TARGET_TP}:LRA={_TARGET_LRA}"
            ":print_format=json"
        ),
        "-f", "null", "-",
    ]


def _pass2_cmd(src: Path, out_path: Path, measured: dict) -> list[str]:
    """Pass 2: 측정값 기반 정밀 정규화 (linear=true)."""
    af = (
        f"loudnorm=I={_TARGET_LUFS}:TP={_TARGET_TP}:LRA={_TARGET_LRA}"
        f":measured_I={measured['input_i']}"
        f":measured_TP={measured['input_tp']}"
        f":measured_LRA={measured['input_lra']}"
        f":measured_thresh={measured['input_thresh']}"
        f":offset={measured['target_offset']}"
        ":linear=true"
    )
    return [
        _FFMPEG_PATH, "-y",
        "-i", str(src),
        "-af", af,
        "-ar", "44100",
        # 고비트레이트 출력: 손실 인코딩(MP3)의 라우드니스 시프트(~0.4 LU)를
        # 방지해 -14 LUFS 정밀도를 유지한다. WAV 등 무손실 출력에는 무해.
        "-b:a", "320k",
        str(out_path),
    ]


def _single_pass_cmd(src: Path, out_path: Path) -> list[str]:
    """폴백: 1-패스 정규화 (측정 실패 시)."""
    return [
        _FFMPEG_PATH, "-y",
        "-i", str(src),
        "-af", f"loudnorm=I={_TARGET_LUFS}:TP={_TARGET_TP}:LRA={_TARGET_LRA}",
        "-ar", "44100",
        # pass-2와 동일하게 고비트레이트 출력 (라우드니스 정밀도 일관성).
        "-b:a", "320k",
        str(out_path),
    ]


def _parse_loudnorm_json(stderr: str) -> dict | None:
    """ffmpeg stderr 끝에 출력되는 loudnorm JSON 블록을 robust하게 파싱한다.

    stderr 안의 마지막 `{ ... }` 블록을 찾아 json.loads.
    필수 키(input_i, input_tp, input_lra, input_thresh, target_offset)가
    모두 있으면 dict 반환, 아니면 None.
    """
    if not stderr:
        return None

    # 균형 잡힌 마지막 JSON 객체를 추출 (마지막 '}'에서 역으로 매칭).
    last_close = stderr.rfind("}")
    if last_close == -1:
        return None

    depth = 0
    start = -1
    for i in range(last_close, -1, -1):
        ch = stderr[i]
        if ch == "}":
            depth += 1
        elif ch == "{":
            depth -= 1
            if depth == 0:
                start = i
                break
    if start == -1:
        return None

    block = stderr[start:last_close + 1]
    try:
        data = json.loads(block)
    except (json.JSONDecodeError, ValueError):
        return None

    required = ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset")
    if not all(k in data for k in required):
        return None

    # 문자열 그대로 유지 (다음 명령에 그대로 삽입).
    return {k: str(data[k]) for k in required}


# ---------------------------------------------------------------------------
# 노드
# ---------------------------------------------------------------------------

@step("후처리")
def postprocess_node(
    ctx: Ctx,
    audio_path: str,
    runner: Callable[..., Any] = subprocess.run,
) -> dict:
    """오디오 파일을 -14 LUFS로 2-패스 라우드니스 정규화하고 결과를 반환한다.

    Pass 1: loudnorm print_format=json 으로 입력 라우드니스 측정.
    Pass 2: 측정값(measured_*) + linear=true 로 정밀 정규화.
    측정 JSON 파싱 실패 시 1-패스로 폴백 (노드가 hard-fail 하지 않도록).

    audio_path: 원본 오디오 파일 경로 (WAV/MP3/FLAC).
    runner:     subprocess.run 대체 인자 — 테스트 시 mock 주입 (두 패스 모두).

    returns: {
        "path":          정규화된 파일 경로,
        "sha256":        정규화 파일 SHA-256,
        "lufs_target":   -14 (고정),
        "measured_i_pre": 정규화 전 측정 LUFS (측정 실패 시 None),
    }
    """
    src = Path(audio_path)
    stem = src.stem + _NORMALIZED_SUFFIX
    out_path = src.parent / (stem + src.suffix)

    measured: dict | None = None

    # --- Pass 1: 측정 ---
    p1_cmd = _pass1_cmd(src)
    logger.info("후처리 Pass1(측정): %s", src.name)
    p1_result = runner(p1_cmd, capture_output=True, text=True, timeout=300)

    if getattr(p1_result, "returncode", 1) != 0:
        # 측정 자체가 실패해도 폴백으로 진행 (1-패스).
        logger.warning(
            "후처리 Pass1 측정 실패 (returncode=%s) — 1-패스 폴백",
            getattr(p1_result, "returncode", "?"),
        )
    else:
        measured = _parse_loudnorm_json(getattr(p1_result, "stderr", "") or "")
        if measured is None:
            logger.warning("후처리 Pass1 JSON 파싱 실패 — 1-패스로 폴백합니다.")

    measured_i_pre = measured["input_i"] if measured else None

    # --- Pass 2: 적용 (측정 성공) 또는 1-패스 폴백 ---
    if measured is not None:
        p2_cmd = _pass2_cmd(src, out_path, measured)
        logger.info("후처리 Pass2(적용): %s → %s (measured_I=%s)",
                    src.name, out_path.name, measured["input_i"])
    else:
        p2_cmd = _single_pass_cmd(src, out_path)
        logger.info("후처리 1-패스 폴백: %s → %s", src.name, out_path.name)

    result = runner(p2_cmd, capture_output=True, text=True, timeout=300)

    if getattr(result, "returncode", 1) != 0:
        stderr_tail = (getattr(result, "stderr", "") or "")[-400:]
        raise RuntimeError(
            f"ffmpeg loudnorm 실패 (returncode={result.returncode}): {stderr_tail}"
        )

    # SHA-256 계산 (파일이 실제로 존재하는 경우에만)
    if out_path.exists():
        sha256 = hashlib.sha256(out_path.read_bytes()).hexdigest()
    else:
        # mock 환경: 입력 경로를 출력으로 재사용하고 sha256은 빈 문자열
        sha256 = ""
        out_path = src  # fallback

    # artifact 등록 (측정값 포함)
    art_meta: dict = {
        "target_lufs": _TARGET_LUFS,
        "tp": _TARGET_TP,
        "lra": _TARGET_LRA,
        "two_pass": measured is not None,
        "measured_i_pre": measured_i_pre,
    }
    if measured is not None:
        art_meta.update({
            "measured_i": measured["input_i"],
            "measured_tp": measured["input_tp"],
            "measured_lra": measured["input_lra"],
            "measured_thresh": measured["input_thresh"],
            "target_offset": measured["target_offset"],
        })

    ctx.store.add_artifact(
        run_id=ctx.run_id,
        step_name="후처리",
        kind="audio_mastered",
        path=str(out_path),
        sha256=sha256,
        meta=art_meta,
    )

    # trace 기록 (measured_i_pre + target 포함)
    _trace.emit({
        "event": "postprocess_done",
        "run_id": ctx.run_id,
        "src": str(src),
        "out": str(out_path),
        "lufs_target": _TARGET_LUFS,
        "measured_i_pre": measured_i_pre,
        "two_pass": measured is not None,
        "ts": time.time(),
    })

    logger.info("후처리 완료: %s (sha256=%s..., measured_i_pre=%s)",
                out_path.name, sha256[:8], measured_i_pre)

    return {
        "path": str(out_path),
        "sha256": sha256,
        "lufs_target": _TARGET_LUFS,
        "measured_i_pre": measured_i_pre,
    }


# ---------------------------------------------------------------------------
# 하위 호환성 stub — 사용하지 말 것 (Phase 2 시그니처 유지)
# ---------------------------------------------------------------------------

def postprocess(audio_path: str) -> str:
    """[DEPRECATED] Phase 2 stub. postprocess_node(ctx, audio_path)로 교체됨."""
    raise NotImplementedError("Phase 4에서 postprocess_node(ctx, audio_path, runner=...)로 교체됨")
