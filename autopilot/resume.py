"""
autopilot/resume.py — human-gate 재개 로직 (텔레그램 비의존 코어).

설계 원칙 (PIPE-AUTO.md § 4.2):
- interrupt() 금지. DB 상태 + 외부 answer 주입 방식만 사용.
- resume_run: open task를 answer → run_pipeline 재호출 → done/awaiting 반환.
- list_awaiting: awaiting_* 상태인 run 목록 반환 (봇 UI용).

텔레그램 핸들러(bot.py)는 이 모듈을 lazy import로 사용한다.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Callable

from autopilot.engine import Ctx, run_pipeline

logger = logging.getLogger("autopilot.resume")


# ---------------------------------------------------------------------------
# resume_run — 핵심 재개 함수 (테스트 가능)
# ---------------------------------------------------------------------------

def resume_run(
    store: Any,
    run_id: str,
    kind: str,
    answer: dict[str, Any],
    pipeline_fn: Callable[[Ctx], None],
    ctx: Ctx | None = None,
) -> dict[str, Any]:
    """open human_task에 답변을 주입하고 파이프라인을 재개한다.

    1. kind에 맞는 open human_task를 찾아 answer 기록.
    2. ctx가 없으면 새 Ctx(run_id, store) 생성.
    3. run_pipeline(ctx, pipeline_fn) 호출 — 완료 step은 @step이 자동 skip.

    store:       autopilot.store.Store 인스턴스.
    run_id:      재개할 run ID.
    kind:        답변할 human_task kind (예: "publish_approval", "track_selection").
    answer:      답변 dict (JSON 직렬화 가능).
    pipeline_fn: run_pipeline에 넘길 파이프라인 함수 (fn(ctx) -> None).
    ctx:         기존 Ctx 재사용 시 전달. None이면 새로 생성.

    returns: run_pipeline 결과 dict
             {"status": "done"} 또는
             {"status": "awaiting_{kind}", "human_task_id": ...} 또는
             {"status": "failed", "error": ...}
    """
    # open task 찾아 answer 기록
    open_task = store.get_open_human_task(run_id, kind)
    if open_task is None:
        logger.warning(
            "resume_run: kind='%s' 에 해당하는 open task 없음 (run_id=%s)", kind, run_id
        )
        # open task가 없어도 파이프라인 재실행 시도 (이미 answered 상태일 수 있음)
    else:
        store.answer_human_task(open_task["id"], answer)
        logger.info(
            "human_task answered: kind=%s, task_id=%s (run_id=%s)",
            kind, open_task["id"], run_id,
        )

    # Ctx 준비
    if ctx is None:
        ctx = Ctx(run_id=run_id, store=store)

    # run 상태를 running으로 전환 (awaiting_* → running)
    store.update_run_status(run_id, "running")

    # 파이프라인 재실행 (완료 step은 @step이 skip)
    result = run_pipeline(ctx, pipeline_fn)
    logger.info("resume_run 완료: run_id=%s status=%s", run_id, result.get("status"))
    return result


# ---------------------------------------------------------------------------
# list_awaiting — 대기 중인 run 목록 (봇 UI용)
# ---------------------------------------------------------------------------

def list_awaiting(store: Any) -> list[dict[str, Any]]:
    """awaiting_* 상태인 run 목록을 반환한다.

    봇에서 /resume (인수 없이) 호출 시 대기 중인 게이트를 안내하는 데 사용.

    returns: [{"run_id": str, "status": str, "kind": str, "updated_at": float}, ...]
    """
    rows = store.conn.execute(
        "SELECT id, status, updated_at FROM runs WHERE status LIKE 'awaiting_%' ORDER BY updated_at DESC",
    ).fetchall()

    result = []
    for row in rows:
        run_id = row["id"]
        status = row["status"]
        # "awaiting_publish_approval" → kind = "publish_approval"
        kind = status.removeprefix("awaiting_") if status.startswith("awaiting_") else status

        # open human_task 정보 보강
        open_task = store.get_open_human_task(run_id, kind)
        task_id = open_task["id"] if open_task else None

        result.append({
            "run_id": run_id,
            "status": status,
            "kind": kind,
            "task_id": task_id,
            "updated_at": row["updated_at"],
        })

    return result
