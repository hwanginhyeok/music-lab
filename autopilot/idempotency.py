"""
autopilot/idempotency.py — 멱등성 키 생성 + run_once 실행 보호.

목적: 생성/업로드 노드의 중복 실행 차단 (DIFFICULTY D-004 가짜 mp3 재발 방지).
백엔드: Store의 idempotency 테이블 (store.py 에서 초기화).
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Callable


def idempotency_key(*parts: str) -> str:
    """인수들을 결합해 sha256 hex digest(64자)를 반환한다.

    같은 인수 조합 → 항상 동일한 키.
    예: idempotency_key("album-spring", "generate", "track_01")
    """
    combined = "\x00".join(parts)  # null byte 구분자로 조합
    return hashlib.sha256(combined.encode()).hexdigest()


def run_once(store: Any, key: str, fn: Callable[[], Any]) -> Any:
    """key 가 처음 호출이면 fn()을 실행하고 결과를 저장한다.

    key 가 이미 존재하면 fn()을 호출하지 않고 저장된 결과를 반환한다.
    store: autopilot.store.Store 인스턴스.
    """
    existing = store.get_idempotency(key)
    if existing is not None:
        return json.loads(existing["result_json"])

    result = fn()
    store.set_idempotency(key, result)
    return result
