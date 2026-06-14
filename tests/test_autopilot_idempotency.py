"""
autopilot/idempotency.py 테스트 — 같은 키 2회 호출 시 1회만 실행.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from autopilot.store import Store
from autopilot.idempotency import idempotency_key, run_once


@pytest.fixture
def store(tmp_path):
    """테스트마다 임시 DB."""
    return Store(str(tmp_path / "idem_test.db"))


# ---------------------------------------------------------------------------
# 시나리오 3: 멱등성
# ---------------------------------------------------------------------------
class TestIdempotency:
    def test_idempotency_key_안정성(self):
        """같은 인수를 넣으면 항상 같은 해시가 반환된다."""
        k1 = idempotency_key("album-spring", "generate", "track_01")
        k2 = idempotency_key("album-spring", "generate", "track_01")
        assert k1 == k2
        assert len(k1) == 64  # sha256 hex

    def test_idempotency_key_다른값_다른_해시(self):
        """서로 다른 인수는 다른 해시를 반환한다."""
        k1 = idempotency_key("album-a", "generate")
        k2 = idempotency_key("album-b", "generate")
        assert k1 != k2

    def test_run_once_두번_호출_한번만_실행(self, store):
        """같은 키로 두 번 호출하면 fn은 1회만 실행된다."""
        call_count = {"n": 0}

        def expensive_fn():
            call_count["n"] += 1
            return {"track": "generated.mp3"}

        key = idempotency_key("album-spring", "generate", "track_01")
        result1 = run_once(store, key, expensive_fn)
        result2 = run_once(store, key, expensive_fn)

        assert call_count["n"] == 1
        assert result1 == result2
        assert result2["track"] == "generated.mp3"

    def test_run_once_다른키_모두_실행(self, store):
        """서로 다른 키는 각각 실행된다."""
        call_count = {"n": 0}

        def fn():
            call_count["n"] += 1
            return {"ok": True}

        key1 = idempotency_key("album-a", "generate")
        key2 = idempotency_key("album-b", "generate")
        run_once(store, key1, fn)
        run_once(store, key2, fn)
        assert call_count["n"] == 2
