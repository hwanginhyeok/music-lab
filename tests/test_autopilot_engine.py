"""
autopilot/engine.py 테스트 — FSM 상태전이, 재개, human_gate.
"""
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from autopilot.store import Store
from autopilot.engine import Ctx, Paused, step, human_gate, run_pipeline


@pytest.fixture
def store(tmp_path):
    """테스트마다 임시 DB를 사용하는 Store 인스턴스."""
    return Store(str(tmp_path / "engine_test.db"))


@pytest.fixture
def ctx(store):
    """기본 실행 컨텍스트."""
    run_id = store.create_run("test-album")
    store.update_run_status(run_id, "running")
    return Ctx(run_id=run_id, store=store)


# ---------------------------------------------------------------------------
# 시나리오 1: FSM 상태전이 — 2~3단계 파이프라인이 done으로 완료
# ---------------------------------------------------------------------------
class TestFSMTransition:
    def test_2단계_파이프라인_done(self, ctx):
        """2개 step을 가진 파이프라인이 완전히 실행되면 run.status='done'."""

        @step(name="step_a")
        def step_a(ctx):
            return {"a": 1}

        @step(name="step_b")
        def step_b(ctx):
            return {"b": 2}

        def pipeline(ctx):
            step_a(ctx)
            step_b(ctx)

        result = run_pipeline(ctx, pipeline)
        assert result["status"] == "done"

        run = ctx.store.get_run(ctx.run_id)
        assert run["status"] == "done"

        sa = ctx.store.get_step(ctx.run_id, "step_a")
        sb = ctx.store.get_step(ctx.run_id, "step_b")
        assert sa["status"] == "done"
        assert sb["status"] == "done"

    def test_step_출력_기록(self, ctx):
        """step이 반환한 값이 output_json에 저장된다."""
        import json

        @step(name="step_with_output")
        def step_with_output(ctx):
            return {"answer": 42}

        def pipeline(ctx):
            step_with_output(ctx)

        run_pipeline(ctx, pipeline)
        s = ctx.store.get_step(ctx.run_id, "step_with_output")
        output = json.loads(s["output_json"])
        assert output["answer"] == 42


# ---------------------------------------------------------------------------
# 시나리오 2: 재개 — step1 완료 후 step2 실패 → 재실행 시 step1 skip
# ---------------------------------------------------------------------------
class TestResume:
    def test_완료된_step은_재실행_안됨(self, ctx):
        """step1이 done이면 재실행 시 side-effect가 발생하지 않는다."""
        call_count = {"step1": 0, "step2": 0}
        fail_flag = {"active": True}

        @step(name="resume_step1", max_attempts=1)
        def resume_step1(ctx):
            call_count["step1"] += 1
            return {"done": True}

        @step(name="resume_step2", max_attempts=3)
        def resume_step2(ctx):
            call_count["step2"] += 1
            if fail_flag["active"]:
                raise RuntimeError("의도적 실패")
            return {"done": True}

        def pipeline(ctx):
            resume_step1(ctx)
            resume_step2(ctx)

        # 첫 번째 실행: step2가 실패해서 전체 실패
        result1 = run_pipeline(ctx, pipeline)
        assert result1["status"] == "failed"
        assert call_count["step1"] == 1
        # step2는 max_attempts=3회 시도
        assert call_count["step2"] == 3

        # step2 실패 플래그 해제
        fail_flag["active"] = False
        # run 상태를 running으로 되돌려 재개 가능하게
        ctx.store.update_run_status(ctx.run_id, "running")

        # 두 번째 실행: step1은 skip, step2만 실행
        result2 = run_pipeline(ctx, pipeline)
        assert result2["status"] == "done"
        assert call_count["step1"] == 1  # 추가 실행 없음 — skip
        assert call_count["step2"] == 4  # 한 번 더 실행

    def test_step_캐시된_출력_반환(self, ctx):
        """done 상태 step은 실행 대신 저장된 output을 반환한다."""
        call_count = {"n": 0}

        @step(name="cached_step")
        def cached_step(ctx):
            call_count["n"] += 1
            return {"value": 99}

        def pipeline(ctx):
            return cached_step(ctx)

        run_pipeline(ctx, pipeline)
        first_count = call_count["n"]

        # run 상태 초기화 후 재실행
        ctx.store.update_run_status(ctx.run_id, "running")
        result = pipeline(ctx)  # 직접 호출 — run_pipeline 없이
        assert result["value"] == 99
        assert call_count["n"] == first_count  # 추가 호출 없음


# ---------------------------------------------------------------------------
# 시나리오 4: human_gate — Paused 발생, 답변 주입 후 완료
# ---------------------------------------------------------------------------
class TestHumanGate:
    def test_human_gate_Paused_발생(self, ctx):
        """human_gate 에서 미답변 시 Paused가 발생하고 run status가 awaiting_이 된다."""

        @human_gate(kind="selection")
        def select_track(ctx):
            pass

        def pipeline(ctx):
            select_track(ctx)

        result = run_pipeline(ctx, pipeline)
        assert result["status"] == "awaiting_selection"

        run = ctx.store.get_run(ctx.run_id)
        assert run["status"] == "awaiting_selection"

        task = ctx.store.get_open_human_task(ctx.run_id, "selection")
        assert task is not None

    def test_human_gate_답변_주입_후_완료(self, ctx):
        """answer 주입 후 재실행하면 gate를 통과하고 pipeline이 done이 된다."""

        @step(name="before_gate")
        def before_gate(ctx):
            return {"ready": True}

        @human_gate(kind="selection")
        def select_track(ctx):
            # gate 통과 시 answer를 반환 — 여기서는 사용 안 함
            pass

        @step(name="after_gate")
        def after_gate(ctx):
            return {"uploaded": True}

        def pipeline(ctx):
            before_gate(ctx)
            select_track(ctx)
            after_gate(ctx)

        # 첫 실행: gate에서 멈춤
        result = run_pipeline(ctx, pipeline)
        assert result["status"] == "awaiting_selection"

        # 답변 주입
        task = ctx.store.get_open_human_task(ctx.run_id, "selection")
        ctx.store.answer_human_task(task["id"], {"chosen": "track_a"})
        ctx.store.update_run_status(ctx.run_id, "running")

        # 재실행: gate 통과 → 완료
        result2 = run_pipeline(ctx, pipeline)
        assert result2["status"] == "done"

        after = ctx.store.get_step(ctx.run_id, "after_gate")
        assert after["status"] == "done"
