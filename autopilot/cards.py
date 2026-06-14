"""
autopilot/cards.py — F02 후보 선택 카드 코어 (텔레그램 비의존).

PIPE-AUTO selection 게이트(awaiting_selection)에 도달한 run에 대해
프리필터 통과 후보(v1/v2…)를 나열한 "카드" dict를 만들고, 사용자가 고른
인덱스를 selection 게이트에 주입해 resume_song으로 재개한다.

설계 원칙:
- 이 모듈은 텔레그램을 import하지 않는다 (순수 코어, 단위 테스트 가능).
- bot.py는 build_selection_card / apply_selection / parse_select_callback 을
  lazy import 로 호출해 InlineKeyboardButton 으로 렌더한다.
- callback_data 형식: "pipeauto:select:{run_id}:{i}"
  run_id 는 12 hex 문자 → 전체 길이 ≤ 약 30바이트 (텔레그램 64바이트 제한 안전).
  i = 프리필터 passed 리스트 인덱스 = resume_song 답변 {"selected_index": i}.
"""
from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger("autopilot.cards")

# ---------------------------------------------------------------------------
# callback_data 스킴
# ---------------------------------------------------------------------------

CALLBACK_PREFIX = "pipeauto:select:"
"""후보 선택 콜백 prefix. 전체 형식: pipeauto:select:{run_id}:{i}"""

CANCEL_DATA = "pipeauto:cancel"
"""취소 버튼 콜백 데이터."""

_PREFILTER_STEP = "프리필터"
_PLANNING_STEP = "기획"
_LYRICS_STEP = "작사"
_SELECTION_KIND = "selection"


# ---------------------------------------------------------------------------
# 내부 헬퍼
# ---------------------------------------------------------------------------

def _concept_from_step(store: Any, run_id: str, step_name: str) -> dict | None:
    """주어진 step의 input_json을 concept dict로 파싱한다.

    step이 없거나 input_json이 비어있거나 dict가 아니면 None을 반환한다.
    (None = "이 step에는 쓸 만한 concept이 없음" → 다음 폴백으로 진행)
    """
    step = store.get_step(run_id, step_name)
    if step is None:
        return None
    raw = step["input_json"]
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    if isinstance(data, dict) and data:
        return data
    return None


def _load_concept(store: Any, run_id: str) -> dict:
    """concept dict를 복원한다.

    우선순위:
      1. '기획'(planning) step input_json — run_album이 canonical 하게 영속화.
      2. '작사' step input_json — 폴백 (@step은 input_data를 저장하지 않으므로
         보통 NULL 이지만, 외부에서 채운 경우를 대비한 방어).
      3. 빈 dict.
    """
    concept = _concept_from_step(store, run_id, _PLANNING_STEP)
    if concept is not None:
        return concept
    concept = _concept_from_step(store, run_id, _LYRICS_STEP)
    if concept is not None:
        return concept
    return {}


def _load_prefilter(store: Any, run_id: str) -> dict:
    """프리필터 step output_json 을 dict 로 로드한다. 없으면 빈 구조."""
    step = store.get_step(run_id, _PREFILTER_STEP)
    if step is None:
        return {"passed": [], "rejected": []}
    raw = step["output_json"]
    if not raw:
        return {"passed": [], "rejected": []}
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {"passed": [], "rejected": []}
    if not isinstance(data, dict):
        return {"passed": [], "rejected": []}
    data.setdefault("passed", [])
    data.setdefault("rejected", [])
    return data


def _fmt_duration(seconds: Any) -> str:
    """초 → 'M:SS' 문자열. 값이 없으면 '?:??'."""
    try:
        total = int(round(float(seconds)))
    except (TypeError, ValueError):
        return "?:??"
    minutes, sec = divmod(max(total, 0), 60)
    return f"{minutes}:{sec:02d}"


def _fmt_lufs(metrics: dict) -> str:
    """metrics 에서 LUFS 표시 문자열을 만든다."""
    lufs = metrics.get("lufs")
    try:
        return f"LUFS {float(lufs):.1f}"
    except (TypeError, ValueError):
        return "LUFS ?"


def _candidate_label(i: int, cand: dict) -> str:
    """버튼 라벨: '▶ 후보 1 · LUFS -14.2 · 1:58'."""
    metrics = cand.get("metrics") or {}
    lufs = _fmt_lufs(metrics)
    dur = _fmt_duration(metrics.get("duration_sec"))
    return f"▶ 후보 {i + 1} · {lufs} · {dur}"


# ---------------------------------------------------------------------------
# callback 파싱
# ---------------------------------------------------------------------------

def parse_select_callback(data: str) -> tuple[str, int] | None:
    """'pipeauto:select:{run_id}:{i}' → (run_id, i). 형식 불일치면 None.

    run_id 에 콜론이 없다고 가정(12 hex). 마지막 토큰이 정수 인덱스.
    """
    if not isinstance(data, str) or not data.startswith(CALLBACK_PREFIX):
        return None
    rest = data[len(CALLBACK_PREFIX):]
    # rest = "{run_id}:{i}"
    if ":" not in rest:
        return None
    run_id, _, idx_str = rest.rpartition(":")
    if not run_id:
        return None
    try:
        idx = int(idx_str)
    except (TypeError, ValueError):
        return None
    if idx < 0:
        return None
    return run_id, idx


# ---------------------------------------------------------------------------
# 카드 빌더
# ---------------------------------------------------------------------------

def build_selection_card(store: Any, run_id: str) -> dict:
    """selection 게이트 카드 dict 를 만든다.

    returns:
        {
          "run_id": str,
          "text": str,          # 한국어 요약 (제목 + 후보 수 + 제외 목록)
          "buttons": [(label, callback_data), ...],   # passed 후보 1개당 1버튼
          "rejected": [ {...}, ... ],
        }

    프리필터 step 이 없거나 통과 후보가 0개면 buttons 는 빈 리스트,
    text 는 "후보 없음" 안내를 반환한다 (크래시 없음).
    """
    concept = _load_concept(store, run_id)
    title = concept.get("title") or "무제"

    prefilter = _load_prefilter(store, run_id)
    passed = prefilter.get("passed") or []
    rejected = prefilter.get("rejected") or []

    buttons: list[tuple[str, str]] = []
    for i, cand in enumerate(passed):
        label = _candidate_label(i, cand)
        callback_data = f"{CALLBACK_PREFIX}{run_id}:{i}"
        buttons.append((label, callback_data))

    if not passed:
        text = (
            f"🎵 {title}\n"
            f"run: {run_id}\n\n"
            "선택 가능한 후보가 없습니다 (프리필터 통과 0개).\n"
            "생성 단계를 다시 확인하세요."
        )
        return {
            "run_id": run_id,
            "text": text,
            "buttons": [],
            "rejected": rejected,
        }

    lines = [
        f"🎵 {title}",
        f"run: {run_id}",
        "",
        f"통과 후보 {len(passed)}개 — 사용할 테이크를 고르세요:",
    ]
    for i, cand in enumerate(passed):
        metrics = cand.get("metrics") or {}
        lines.append(
            f"  후보 {i + 1}: {_fmt_lufs(metrics)} · {_fmt_duration(metrics.get('duration_sec'))}"
        )

    if rejected:
        lines.append("")
        lines.append(f"제외된 테이크 {len(rejected)}개:")
        for rej in rejected:
            reason = rej.get("reason", "사유 불명")
            lines.append(f"  ✗ {reason}")

    return {
        "run_id": run_id,
        "text": "\n".join(lines),
        "buttons": buttons,
        "rejected": rejected,
    }


# ---------------------------------------------------------------------------
# 선택 적용 → resume
# ---------------------------------------------------------------------------

def apply_selection(
    store: Any,
    run_id: str,
    selected_index: int,
    deps: Any = None,
    concept: dict | None = None,
) -> dict:
    """선택된 후보 인덱스를 selection 게이트에 주입하고 파이프라인을 재개한다.

    - run 이 실제로 awaiting_selection 상태가 아니면(이미 답변/만료/다른 게이트)
      resume_song 을 호출하지 않고 {"status": "noop", "reason": ...} 반환.
    - concept 미지정 시 작사 step input_json 에서 복원.
    - resume_song → resume_run 이 open task 를 answer 처리하므로
      여기서 별도 answer_human_task 를 호출하지 않는다 (이중 답변 방지).

    returns: resume_song 결과 dict (보통 {"status": "awaiting_publish_approval"} 등)
             또는 {"status": "noop", "reason": ...}.
    """
    # lazy import — bot.py import 안전 + 순환 import 회피
    from autopilot.pipeline import PipelineDeps, resume_song

    run_row = store.get_run(run_id)
    if run_row is None:
        return {"status": "noop", "reason": f"run_id 없음: {run_id}"}

    status = run_row["status"]
    if status != "awaiting_selection":
        return {
            "status": "noop",
            "reason": f"awaiting_selection 아님 (현재 status={status})",
        }

    if concept is None:
        concept = _load_concept(store, run_id)

    if deps is None:
        deps = PipelineDeps()

    logger.info(
        "apply_selection: run_id=%s, selected_index=%d", run_id, selected_index
    )
    return resume_song(
        store,
        run_id,
        concept,
        deps,
        {"selected_index": selected_index},
    )
