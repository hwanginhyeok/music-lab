"""
autopilot/trace.py — 파이프라인 이벤트 trace.jsonl 기록 + LangSmith 미러.

원칙:
- canonical state = SQLite. trace.jsonl은 뷰용.
- LangSmith SDK 없으면 no-op fallback (파이프라인은 그대로 작동).
- 대용량 필드는 사이드카 파일로 저장 후 경로+sha256만 기록.
- 프로세스 종료 전 flush() 호출로 이벤트 유실 방지.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("autopilot.trace")

# ---------------------------------------------------------------------------
# LangSmith 가용성 감지 (no-op fallback)
# ---------------------------------------------------------------------------

try:
    import langsmith  # type: ignore[import-not-found]
    from langsmith import traceable as _traceable  # type: ignore[import-not-found]
    LANGSMITH_AVAILABLE: bool = True
except ImportError:
    LANGSMITH_AVAILABLE = False
    _traceable = None  # no-op

# ---------------------------------------------------------------------------
# 기본 trace 경로
# ---------------------------------------------------------------------------

_DEFAULT_TRACE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "logs", "traces"
)
_DEFAULT_TRACE_PATH = os.path.join(_DEFAULT_TRACE_DIR, "trace.jsonl")

# 대용량 필드 임계값 (기본 2048자)
_LARGE_FIELD_THRESHOLD: int = 2048

# ---------------------------------------------------------------------------
# 사이드카 헬퍼
# ---------------------------------------------------------------------------


def _sidecar_path(trace_path: str, sha256: str) -> str:
    """사이드카 파일 경로 — trace.jsonl 옆에 .sidecar/ 디렉토리."""
    sidecar_dir = os.path.join(os.path.dirname(trace_path), ".sidecar")
    os.makedirs(sidecar_dir, exist_ok=True)
    return os.path.join(sidecar_dir, f"{sha256[:16]}.txt")


def _maybe_offload(value: str, trace_path: str) -> str | dict[str, str]:
    """값이 임계값을 초과하면 사이드카 파일에 저장하고 {path, sha256}을 반환한다."""
    if len(value) <= _LARGE_FIELD_THRESHOLD:
        return value
    digest = hashlib.sha256(value.encode()).hexdigest()
    sc_path = _sidecar_path(trace_path, digest)
    Path(sc_path).write_text(value, encoding="utf-8")
    return {"__sidecar__": True, "path": sc_path, "sha256": digest}


# ---------------------------------------------------------------------------
# emit / flush
# ---------------------------------------------------------------------------


def emit(event: dict[str, Any], trace_path: str = _DEFAULT_TRACE_PATH) -> None:
    """이벤트를 trace.jsonl에 한 줄 JSON으로 추가한다.

    대용량 'prompt' 필드는 사이드카 파일로 오프로드.
    LangSmith가 설치되어 있으면 미러링 시도 (실패해도 무시).
    """
    if "ts" not in event:
        event = {**event, "ts": time.time()}

    # 대용량 필드 오프로드
    sanitized: dict[str, Any] = {}
    for k, v in event.items():
        if isinstance(v, str):
            sanitized[k] = _maybe_offload(v, trace_path)
        else:
            sanitized[k] = v

    # jsonl 기록
    try:
        os.makedirs(os.path.dirname(trace_path), exist_ok=True)
        with open(trace_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(sanitized, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
    except Exception as exc:  # noqa: BLE001
        logger.warning("trace.jsonl 기록 실패: %s", exc)

    # LangSmith 미러 (no-op if unavailable)
    if LANGSMITH_AVAILABLE:
        try:
            # langsmith 클라이언트 직접 사용 (traceable 데코레이터 없이)
            client = langsmith.Client()
            client.create_run(
                name=sanitized.get("event", "trace_event"),
                inputs=sanitized,
                run_type="chain",
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("LangSmith 미러 실패 (무시): %s", exc)


def flush(trace_path: str = _DEFAULT_TRACE_PATH) -> None:
    """trace 파일이 디스크에 완전히 기록됐는지 확인한다.

    emit()에서 이미 fsync를 수행하므로 여기서는 파일 존재 여부만 확인.
    프로세스 종료 전 명시적으로 호출하는 의미를 가진다.
    """
    if os.path.exists(trace_path):
        try:
            with open(trace_path, "a", encoding="utf-8") as f:
                f.flush()
                os.fsync(f.fileno())
        except Exception as exc:  # noqa: BLE001
            logger.warning("trace flush 실패: %s", exc)
