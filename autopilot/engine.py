"""
autopilot/engine.py — @step / @human_gate 데코레이터 + 파이프라인 러너.

설계 원칙 (PIPE-AUTO.md § 4.2):
- @step: done인 step은 실행 skip, 캐시된 output 반환 (재개 멱등성 보장).
- @human_gate: 미답변이면 Paused raise + run status 'awaiting_{kind}'.
- interrupt() 금지. DB 상태 + 외부 answer 주입 방식만 사용.
- run_pipeline: Paused/예외를 catch해 상태 객체로 반환.
"""
from __future__ import annotations

import functools
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from autopilot import trace as _trace

logger = logging.getLogger("autopilot.engine")


# ---------------------------------------------------------------------------
# Ctx — 파이프라인 실행 컨텍스트
# ---------------------------------------------------------------------------

@dataclass
class Ctx:
    """파이프라인 실행 컨텍스트.

    run_id: 현재 실행 ID.
    store:  canonical state 저장소.
    answers: human_gate 답변 맵 (kind → answer dict).
    """
    run_id: str
    store: Any  # Store 타입 (순환 import 방지를 위해 Any)
    answers: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Paused — human_gate 정지 예외
# ---------------------------------------------------------------------------

class Paused(Exception):
    """human_gate가 미답변 상태에서 파이프라인을 멈출 때 발생한다."""

    def __init__(self, kind: str, human_task_id: str) -> None:
        super().__init__(f"파이프라인 대기 중: kind={kind}, task_id={human_task_id}")
        self.kind = kind
        self.human_task_id = human_task_id


# ---------------------------------------------------------------------------
# @step 데코레이터
# ---------------------------------------------------------------------------

def step(name: str, max_attempts: int = 3) -> Callable:
    """step 데코레이터.

    - done 상태면 fn 호출 없이 저장된 output 반환.
    - 실패 시 max_attempts 까지 재시도. 초과하면 run status='failed' 후 re-raise.
    """

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(ctx: Ctx, *args: Any, **kwargs: Any) -> Any:
            store = ctx.store
            run_id = ctx.run_id

            # 이미 done이면 캐시된 output 반환 (resume 멱등성)
            existing = store.get_step(run_id, name)
            if existing is not None and existing["status"] == "done":
                logger.debug("step '%s' skip (이미 done)", name)
                cached = existing["output_json"]
                return json.loads(cached) if cached is not None else None

            # 최대 시도 횟수만큼 실행
            last_exc: Exception | None = None
            # 현재 attempt 숫자 파악 (이전 실패 포함)
            current_attempt = existing["attempt"] if existing is not None else 0

            remaining = max_attempts - current_attempt
            if remaining <= 0:
                remaining = 1  # 최소 1번은 시도

            for _ in range(remaining):
                store.start_step(run_id, name)
                _trace.emit(
                    {"event": "step_start", "run_id": run_id, "step": name,
                     "ts": time.time()},
                )
                try:
                    result = fn(ctx, *args, **kwargs)
                    store.finish_step(run_id, name, result)
                    _trace.emit(
                        {"event": "step_done", "run_id": run_id, "step": name,
                         "ts": time.time()},
                    )
                    return result
                except Exception as exc:  # noqa: BLE001
                    last_exc = exc
                    logger.warning("step '%s' 실패: %s", name, exc)
                    store.fail_step(run_id, name, {"error": str(exc), "type": type(exc).__name__})
                    _trace.emit(
                        {"event": "step_failed", "run_id": run_id, "step": name,
                         "error": str(exc), "ts": time.time()},
                    )

            # 모든 시도 소진 → run failed
            store.update_run_status(run_id, "failed", current_step=name)
            raise last_exc  # type: ignore[misc]

        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# @human_gate 데코레이터
# ---------------------------------------------------------------------------

_GATE_TTL_SECONDS: float = 7 * 24 * 3600  # 기본 TTL: 7일


def human_gate(kind: str) -> Callable:
    """human_gate 데코레이터.

    - answered 상태 task가 있으면 answer를 반환해 pipeline 계속.
    - 없으면 open task 생성 + run status='awaiting_{kind}' + Paused raise.
    재개 모델: 외부에서 answer_human_task() 호출 후 동일 pipeline 함수 재호출.
    """

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(ctx: Ctx, *args: Any, **kwargs: Any) -> Any:
            store = ctx.store
            run_id = ctx.run_id

            # 이미 answered 상태 task가 있으면 answer 반환 (gate 통과)
            answered = store.get_answered_human_task(run_id, kind)
            if answered is not None:
                answer = json.loads(answered["answer_json"])
                logger.debug("human_gate '%s' 통과 (answer 존재)", kind)
                return answer

            # open task가 이미 있으면 재사용, 없으면 새로 생성
            existing_open = store.get_open_human_task(run_id, kind)
            if existing_open is not None:
                task_id = existing_open["id"]
            else:
                expires_at = time.time() + _GATE_TTL_SECONDS
                task_id = store.create_human_task(
                    run_id, kind, payload={}, expires_at=expires_at
                )

            store.update_run_status(run_id, f"awaiting_{kind}")
            _trace.emit(
                {"event": "human_gate", "run_id": run_id, "kind": kind,
                 "task_id": task_id, "ts": time.time()},
            )
            raise Paused(kind=kind, human_task_id=task_id)

        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# run_pipeline — 파이프라인 실행 헬퍼
# ---------------------------------------------------------------------------

def run_pipeline(ctx: Ctx, pipeline_fn: Callable) -> dict[str, Any]:
    """pipeline_fn(ctx)를 실행하고 상태 객체를 반환한다.

    반환 형식:
    - {"status": "done"}
    - {"status": "awaiting_{kind}", "human_task_id": ...}
    - {"status": "failed", "error": ...}
    """
    try:
        pipeline_fn(ctx)
        ctx.store.update_run_status(ctx.run_id, "done")
        return {"status": "done"}
    except Paused as exc:
        # human_gate가 이미 status를 'awaiting_{kind}'로 설정함
        return {"status": f"awaiting_{exc.kind}", "human_task_id": exc.human_task_id}
    except Exception as exc:  # noqa: BLE001
        # @step 데코레이터가 이미 run status='failed'로 설정함
        logger.error("파이프라인 실패: %s", exc)
        return {"status": "failed", "error": str(exc)}
