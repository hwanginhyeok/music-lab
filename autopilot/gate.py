"""
autopilot/gate.py — 게시 승인 게이트 (Publish-Gate).

글로벌 publish-gate 규칙:
- 모든 외부 게시(YouTube unlisted 포함)는 사용자의 명시적 "올려" 승인이 있어야만 실행.
- 기본 상태 = BLOCKED.
- 승인 = store에 kind='publish_approval' 인 answered human_task 존재.

사용 방법:
    # 승인 부여 (봇 "올려" 명령 또는 테스트)
    from autopilot.gate import approve_publish
    approve_publish(store, run_id)

    # 게이트 체크 (upload_node 내부에서 자동 호출)
    from autopilot.gate import publish_gate_check
    publish_gate_check(ctx)  # 미승인이면 PublishGateBlocked 발생
"""
from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger("autopilot.gate")

# human_task kind 상수
PUBLISH_APPROVAL_KIND: str = "publish_approval"

# human_task 기본 TTL (30일)
_TTL_SECONDS: float = 30 * 24 * 3600


class PublishGateBlocked(Exception):
    """YouTube 업로드가 사용자 승인 없이 시도될 때 발생한다.

    글로벌 publish-gate 규칙(publish-gate.md):
      - unlisted 포함 모든 외부 게시는 사용자 "올려" 승인 필수.
      - 기본 상태 = BLOCKED.
    """

    def __init__(self, run_id: str) -> None:
        super().__init__(
            f"YouTube 업로드가 게시 승인 게이트에 의해 차단됨 "
            f"(run_id={run_id}). "
            f"텔레그램에서 '올려'라고 입력하거나 /resume 명령으로 승인하세요."
        )
        self.run_id = run_id


def publish_gate_check(ctx: Any) -> None:
    """게시 승인 여부를 확인한다. 미승인이면 PublishGateBlocked를 발생시킨다.

    ctx: autopilot.engine.Ctx 인스턴스.
    """
    answered = ctx.store.get_answered_human_task(ctx.run_id, PUBLISH_APPROVAL_KIND)
    if answered is None:
        logger.warning(
            "게시 승인 없음 — 업로드 차단 (run_id=%s)", ctx.run_id
        )
        raise PublishGateBlocked(ctx.run_id)
    logger.info("게시 승인 확인 완료 (run_id=%s)", ctx.run_id)


def approve_publish(store: Any, run_id: str) -> str:
    """사용자 승인을 store에 기록한다 (봇 "올려" 명령 + 테스트 헬퍼).

    이미 open task가 있으면 그것을 answer, 없으면 새 task를 만들어 즉시 answer.

    returns: answered human_task id.
    """
    existing_open = store.get_open_human_task(run_id, PUBLISH_APPROVAL_KIND)
    if existing_open is not None:
        task_id = existing_open["id"]
    else:
        # open task가 없으면 새로 생성 (즉시 answer 예정이므로 TTL은 의미 없음)
        expires_at = time.time() + _TTL_SECONDS
        task_id = store.create_human_task(
            run_id,
            PUBLISH_APPROVAL_KIND,
            payload={"approved_by": "user", "approved_at": time.time()},
            expires_at=expires_at,
        )

    store.answer_human_task(task_id, {"approved": True, "ts": time.time()})
    logger.info("게시 승인 기록 완료 (run_id=%s, task_id=%s)", run_id, task_id)
    return task_id
