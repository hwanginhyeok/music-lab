"""
autopilot/nodes/prefilter.py — 기술적 결함 필터 노드 (Phase 3).

F01 역할 재정의: 기술적 결함(클리핑/무음/짧은길이/파일깨짐)만 필터링.
취향/컨셉 판단 없음 — 그것은 사람이 담당(Phase 5 human_gate).

pyloudnorm / librosa: 미설치 시 ImportError를 피하기 위해 함수 내부에서 지연 import.
"""
from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path
from typing import Any

from autopilot import trace as _trace
from autopilot.engine import Ctx, step

logger = logging.getLogger("autopilot.nodes.prefilter")

# ---------------------------------------------------------------------------
# 기술적 결함 임계값
# ---------------------------------------------------------------------------

# 길이 최소치 (초) — 이 미만이면 생성 실패로 판단
_MIN_DURATION_SEC: float = float(os.environ.get("PREFILTER_MIN_DURATION", "30.0"))
# 피크 클리핑 임계값 (dBFS) — 이 이상이면 클리핑으로 판단 (-0.1 dBFS = 거의 0)
_CLIP_PEAK_DBFS: float = float(os.environ.get("PREFILTER_CLIP_PEAK", "-0.1"))
# 무음 LUFS 임계값 — 이 미만이면 거의 무음으로 판단
_SILENCE_LUFS: float = float(os.environ.get("PREFILTER_SILENCE_LUFS", "-70.0"))


# ---------------------------------------------------------------------------
# 노드
# ---------------------------------------------------------------------------

@step("프리필터")
def prefilter_node(ctx: Ctx, candidates: list[dict]) -> dict:
    """오디오 후보에서 기술적 결함만 걸러낸다. 취향/컨셉 판단 없음.

    candidates: [{"path": str, "sha256": str}, ...] (generate_node 출력)

    필터 기준 (기술적 결함만):
    - 파일 읽기 불가 (손상)
    - 길이 < MIN_DURATION_SEC
    - 피크 >= CLIP_PEAK_DBFS (클리핑)
    - 통합 LUFS < SILENCE_LUFS (사실상 무음)

    returns: {
        "passed": [{"path": str, "sha256": str, "metrics": {...}}, ...],
        "rejected": [{"path": str, "reason": str, "metrics": {...}}, ...]
    }
    """
    passed = []
    rejected = []

    for cand in candidates:
        audio_path = cand["path"]
        sha = cand.get("sha256", "")

        metrics, reason = _analyze(audio_path)

        # artifact에 metrics 추가
        if os.path.exists(audio_path):
            ctx.store.add_artifact(
                run_id=ctx.run_id,
                step_name="프리필터",
                kind="prefilter_metrics",
                path=audio_path,
                sha256=sha,
                meta={"metrics": metrics, "result": reason or "pass"},
            )

        # trace 기록
        _trace.emit({
            "event": "prefilter_candidate",
            "run_id": ctx.run_id,
            "path": audio_path,
            "metrics": metrics,
            "result": reason or "pass",
        })

        if reason is None:
            passed.append({"path": audio_path, "sha256": sha, "metrics": metrics})
        else:
            rejected.append({"path": audio_path, "reason": reason, "metrics": metrics})
            logger.info("프리필터 제외: %s (%s)", audio_path, reason)

    logger.info(
        "프리필터 완료: 통과 %d / 제외 %d (총 %d)",
        len(passed), len(rejected), len(candidates)
    )

    _trace.emit({
        "event": "prefilter_done",
        "run_id": ctx.run_id,
        "passed_count": len(passed),
        "rejected_count": len(rejected),
    })

    return {"passed": passed, "rejected": rejected}


# ---------------------------------------------------------------------------
# 내부: 오디오 분석 (pyloudnorm + librosa 지연 import)
# ---------------------------------------------------------------------------

def _analyze(audio_path: str) -> tuple[dict[str, Any], str | None]:
    """오디오 파일을 분석해 (metrics, reason) 를 반환한다.

    reason이 None이면 통과, 문자열이면 해당 이유로 제외.
    metrics: {lufs, peak_dbfs, duration_sec} (분석 실패 시 빈 dict)
    """
    # 1. 파일 존재/읽기 가능 여부
    if not os.path.exists(audio_path):
        return {}, "파일 없음"

    try:
        # pyloudnorm, librosa 지연 import — 미설치 시 모듈 임포트 실패 방지
        import numpy as np                      # noqa: PLC0415
        import pyloudnorm as pyln               # noqa: PLC0415
        import librosa                          # noqa: PLC0415
    except ImportError as e:
        logger.warning("pyloudnorm/librosa 미설치 — 프리필터 분석 스킵 (%s)", e)
        # 미설치 환경에서는 기술적 결함 판단 불가 → 일단 통과로 처리
        return {"skipped": True, "reason": "pyloudnorm/librosa 미설치"}, None

    try:
        # 오디오 로드
        y, sr = librosa.load(audio_path, sr=None, mono=True)
    except Exception as e:
        return {}, f"파일 손상/읽기 실패: {e}"

    # 2. 길이 검사
    duration_sec = float(len(y)) / float(sr)
    if duration_sec < _MIN_DURATION_SEC:
        metrics = {"duration_sec": duration_sec}
        return metrics, f"길이 너무 짧음 ({duration_sec:.1f}s < {_MIN_DURATION_SEC}s)"

    # 3. LUFS (통합 라우드니스)
    meter = pyln.Meter(sr)
    try:
        loudness = float(meter.integrated_loudness(y))
    except Exception:
        loudness = -70.0

    # 4. 피크 (dBFS)
    peak_linear = float(np.max(np.abs(y)))
    import math
    peak_dbfs = 20.0 * math.log10(peak_linear) if peak_linear > 0 else -120.0

    metrics: dict[str, Any] = {
        "duration_sec": duration_sec,
        "lufs": loudness,
        "peak_dbfs": peak_dbfs,
    }

    # 5. 무음 검사
    if loudness < _SILENCE_LUFS:
        return metrics, f"무음/거의 무음 (LUFS={loudness:.1f} < {_SILENCE_LUFS})"

    # 6. 클리핑 검사
    if peak_dbfs >= _CLIP_PEAK_DBFS:
        return metrics, f"클리핑 (peak={peak_dbfs:.2f} dBFS >= {_CLIP_PEAK_DBFS})"

    # 통과
    return metrics, None


# ---------------------------------------------------------------------------
# 하위 호환성 stub — 사용하지 말 것
# ---------------------------------------------------------------------------

def prefilter(candidates: list[str]) -> list[str]:
    """[DEPRECATED] Phase 2 stub. 사용하지 마세요."""
    raise NotImplementedError("Phase 3에서 prefilter_node(ctx, candidates)로 교체됨")
