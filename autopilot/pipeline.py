"""
autopilot/pipeline.py — 앨범 단위 파이프라인 오케스트레이터 (PIPE-AUTO Phase 3+4).

아키텍처 결정:
  앨범(album) = run 여러 개의 컬렉션.
  steps PK 가 (run_id, step_name) 이므로 곡마다 독립 run을 생성한다.
  album_slug는 모든 곡 run에 동일하게 저장되어 앨범 단위 조회가 가능하다.

게이트 설계:
  1. selection_gate(@human_gate("selection"))
     — prefilter 통과 후보 중 선택 대기.
     — 답변 예: {"selected_index": 0}
  2. publish_approval_gate(@human_gate("publish_approval"))
     — YouTube 업로드 직전 최종 승인 대기.
     — 답변 예: {"approved": True}
     — publish_gate_check(ctx) (upload_node 내부) 도 동일 kind="publish_approval" 의
       answered task를 확인하므로 이 게이트 통과 = upload_node 내부 체크도 자동 통과.

흐름:
  1. lyrics_node       → lyrics_path
  2. suno_prompt_node  → prompt_path
  3. generate_node     → candidates
  4. prefilter_node    → passed/rejected
  5. selection_gate    → {"selected_index": N}  ← 첫 번째 human_gate (Paused)
  6. postprocess_node  → mastered_path
  7. video_node        → video_path
  8. publish_approval_gate → {"approved": True}  ← 두 번째 human_gate (Paused)
  9. upload_node       → {video_id, url, privacy}
"""
from __future__ import annotations

import dataclasses
import logging
import subprocess
from typing import Any

from autopilot.engine import Ctx, human_gate, run_pipeline
from autopilot.nodes.generate import generate_node
from autopilot.nodes.lyrics import lyrics_node
from autopilot.nodes.postprocess import postprocess_node
from autopilot.nodes.prefilter import prefilter_node
from autopilot.nodes.suno_prompt import suno_prompt_node
from autopilot.nodes.upload import upload_node
from autopilot.nodes.video import video_node
from autopilot.resume import resume_run

logger = logging.getLogger("autopilot.pipeline")


# ---------------------------------------------------------------------------
# PipelineDeps — 외부 의존성 주입 컨테이너 (테스트 격리용)
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class PipelineDeps:
    """파이프라인이 사용하는 외부 의존성을 묶은 dataclass.

    runner: subprocess.run 호환 callable.
            테스트 시 ffmpeg 없이 mock 실행 가능.
    youtube: YouTube 서비스 클라이언트. None이면 upload_node가 실제 OAuth 빌드.
    n:       generate_node 에 전달할 후보 수 (Suno는 기본 2곡 동시 생성).
    """
    runner: Any = dataclasses.field(default=subprocess.run)
    youtube: Any = None
    n: int = 2


# ---------------------------------------------------------------------------
# human_gate 함수 (데코레이터 적용 — body는 절대 실행되지 않음)
# ---------------------------------------------------------------------------

@human_gate("selection")
def selection_gate(ctx: Ctx, passed_candidates: list[dict]) -> dict:  # noqa: ARG001
    """후보 선택 게이트.

    answered human_task 존재 시 answer dict 반환 (예: {"selected_index": 0}).
    없으면 open task 생성 + run status='awaiting_selection' + Paused raise.

    NOTE: @human_gate 데코레이터 때문에 이 body는 절대 실행되지 않는다.
    실제 반환값은 store에 주입된 answer_json 에서 온다.
    """
    return {"selected_index": 0}  # pragma: no cover


@human_gate("publish_approval")
def publish_approval_gate(ctx: Ctx) -> dict:  # noqa: ARG001
    """YouTube 게시 승인 게이트.

    kind = "publish_approval" — gate.py PUBLISH_APPROVAL_KIND 와 동일.
    이 게이트를 통과(answered)하면 upload_node 내부의 publish_gate_check(ctx)도
    동일 answered task를 찾으므로 자동으로 통과한다 (defense-in-depth 충족).

    NOTE: @human_gate 데코레이터 때문에 이 body는 절대 실행되지 않는다.
    """
    return {"approved": True}  # pragma: no cover


# ---------------------------------------------------------------------------
# song_pipeline — 단일 곡 파이프라인 함수
# ---------------------------------------------------------------------------

def song_pipeline(ctx: Ctx, concept: dict, deps: PipelineDeps | None = None) -> dict:
    """하나의 곡을 처음부터 YouTube 업로드까지 실행하는 파이프라인.

    양쪽 human_gate (@human_gate로 선언)가 resume 메커니즘을 통해
    외부 answer 주입으로 재개된다.

    Args:
        ctx:     파이프라인 실행 컨텍스트 (run_id, store, answers).
        concept: 곡 컨셉 dict (title, mood, theme, style 등).
        deps:    외부 의존성. None이면 PipelineDeps() 기본값 사용.

    Returns:
        {"video_url", "video_id", "selected", "lyrics_path", "prompt_path"}
    """
    if deps is None:
        deps = PipelineDeps()

    # ── Phase 3: 가사 + Suno 프롬프트 + 생성 + 필터 ─────────────────────────

    lyrics_result = lyrics_node(ctx, concept)
    lyrics_path = lyrics_result["lyrics_path"]

    prompt_result = suno_prompt_node(ctx, concept, lyrics_path)
    prompt_path = prompt_result["prompt_path"]

    generate_result = generate_node(ctx, prompt_path, n=deps.n)
    candidates = generate_result["candidates"]

    prefilter_result = prefilter_node(ctx, candidates)
    passed = prefilter_result["passed"]

    # ── Gate 1: 후보 선택 (human_gate) ───────────────────────────────────────
    # answered task 없으면 Paused("selection") raise → run_pipeline이 catch →
    # {"status": "awaiting_selection"} 반환.
    choice = selection_gate(ctx, passed)

    # 선택된 후보 결정
    idx = choice.get("selected_index", 0)
    if not passed:
        raise RuntimeError("selection_gate: 프리필터 통과 후보 없음 — 파이프라인 중단")
    if idx < 0 or idx >= len(passed):
        logger.warning(
            "selection_gate: 유효하지 않은 selected_index=%d (passed=%d개) → 0번으로 폴백",
            idx, len(passed),
        )
        idx = 0
    selected = passed[idx]

    # ── Phase 4: 후처리 + 영상 + 업로드 ─────────────────────────────────────

    pp_result = postprocess_node(ctx, selected["path"], runner=deps.runner)
    mastered_path = pp_result["path"]

    title = concept.get("title", "무제")
    vid_result = video_node(ctx, mastered_path, title, runner=deps.runner)
    video_path = vid_result["path"]

    # ── Gate 2: 게시 승인 (human_gate) ───────────────────────────────────────
    # kind="publish_approval" 은 gate.py PUBLISH_APPROVAL_KIND 와 동일.
    # answered task 없으면 Paused("publish_approval") raise.
    # 통과 후 upload_node 내부 publish_gate_check(ctx)도 동일 answered task를
    # 찾으므로 PublishGateBlocked 없이 통과한다 (defense-in-depth).
    publish_approval_gate(ctx)

    description = (
        f"🎵 {title}\n\n"
        f"분위기: {concept.get('mood', '')}\n"
        f"주제: {concept.get('theme', '')}\n\n"
        "AI 작사/작곡 + Suno 생성 | Music Lab"
    )
    upload_result = upload_node(
        ctx,
        video_path,
        title=title,
        description=description,
        youtube=deps.youtube,
    )

    return {
        "video_url": upload_result["url"],
        "video_id": upload_result["video_id"],
        "selected": selected,
        "lyrics_path": lyrics_path,
        "prompt_path": prompt_path,
    }


# ---------------------------------------------------------------------------
# run_album — 앨범 단위 엔트리포인트
# ---------------------------------------------------------------------------

def run_album(
    store: Any,
    album_slug: str,
    song_concepts: list[dict],
    deps: PipelineDeps | None = None,
) -> list[dict]:
    """앨범에 속한 모든 곡을 순차적으로 파이프라인에 투입한다.

    곡마다 독립적인 run을 생성하는 이유:
        steps 테이블의 PK가 (run_id, step_name) 이므로 하나의 run에 여러 곡의
        "작사" step 등을 동시에 넣을 수 없다. 곡별 run = 명확한 분리 + 독립 재개.
        album_slug를 공유하면 앨범 단위 조회(SELECT … WHERE album_slug=?)가 가능하다.

    Args:
        store:         autopilot.store.Store 인스턴스.
        album_slug:    앨범 식별자 (예: "2026-무색무취").
        song_concepts: 곡 컨셉 dict 리스트.
        deps:          외부 의존성. None이면 PipelineDeps() 기본값 사용.

    Returns:
        [{"run_id", "title", "status", "result"}, ...] 형태 리스트.
        status: "done" / "awaiting_selection" / "awaiting_publish_approval" / "failed"
    """
    if deps is None:
        deps = PipelineDeps()

    results = []

    for concept in song_concepts:
        title = concept.get("title", "무제")
        run_id = store.create_run(album_slug)
        store.update_run_status(run_id, "running")
        ctx = Ctx(run_id=run_id, store=store)

        # pipeline_fn은 클로저로 concept + deps를 캡처한다.
        # lambda 루프 변수 캡처 버그를 피하기 위해 기본인자로 바인딩한다.
        def make_pipeline(c=concept, d=deps):
            def _pipeline(ctx_inner: Ctx) -> None:
                song_pipeline(ctx_inner, c, d)
            return _pipeline

        pipeline_fn = make_pipeline()
        run_result = run_pipeline(ctx, pipeline_fn)
        status = run_result.get("status", "unknown")

        logger.info(
            "run_album: '%s' (run_id=%s) → status=%s",
            title, run_id, status,
        )

        results.append({
            "run_id": run_id,
            "title": title,
            "status": status,
            "result": run_result,
        })

    return results


# ---------------------------------------------------------------------------
# resume_song — 특정 곡 run의 human_gate를 재개하는 헬퍼
# ---------------------------------------------------------------------------

def resume_song(
    store: Any,
    run_id: str,
    concept: dict,
    deps: PipelineDeps | None = None,
    answer: dict | None = None,
) -> dict:
    """특정 곡 run에서 열려 있는 human_gate에 답변을 주입하고 파이프라인을 재개한다.

    open gate의 kind를 자동 감지하므로 호출자가 kind를 명시할 필요가 없다.
    봇/테스트 양쪽에서 run_id + concept + answer 만으로 재개 가능하다.

    Args:
        store:   autopilot.store.Store 인스턴스.
        run_id:  재개할 run ID.
        concept: 곡 컨셉 dict (pipeline 클로저 재구성에 사용).
        deps:    외부 의존성. None이면 PipelineDeps() 기본값 사용.
        answer:  주입할 답변 dict. None이면 빈 dict.

    Returns:
        resume_run 결과 dict: {"status": "done"|"awaiting_*"|"failed", ...}

    Raises:
        RuntimeError: 열려 있는 human_task 를 찾을 수 없을 때.
    """
    if deps is None:
        deps = PipelineDeps()
    if answer is None:
        answer = {}

    # open task의 kind를 자동으로 감지한다.
    open_tasks = store.conn.execute(
        "SELECT kind FROM human_tasks WHERE run_id=? AND status='open' ORDER BY created_at DESC LIMIT 1",
        (run_id,),
    ).fetchone()

    if open_tasks is None:
        # open task가 없으면 run 상태를 직접 확인해 kind를 추론한다.
        run_row = store.get_run(run_id)
        if run_row is None:
            raise RuntimeError(f"resume_song: run_id={run_id} 를 찾을 수 없음")
        status = run_row["status"]
        if status.startswith("awaiting_"):
            kind = status.removeprefix("awaiting_")
        else:
            raise RuntimeError(
                f"resume_song: run_id={run_id} 에 open human_task 없음 (status={status})"
            )
    else:
        kind = open_tasks["kind"]

    def make_pipeline(c=concept, d=deps):
        def _pipeline(ctx_inner: Ctx) -> None:
            song_pipeline(ctx_inner, c, d)
        return _pipeline

    pipeline_fn = make_pipeline()

    logger.info("resume_song: run_id=%s, kind=%s", run_id, kind)
    return resume_run(
        store=store,
        run_id=run_id,
        kind=kind,
        answer=answer,
        pipeline_fn=pipeline_fn,
    )
