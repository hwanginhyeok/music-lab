"""
tests/test_autopilot_cards.py — F02 후보 선택 카드 코어 단위 테스트.

대상: autopilot/cards.py (텔레그램 비의존 코어)
- build_selection_card: 버튼 수/콜백 형식/라벨 메트릭/제외 목록/제목.
- parse_select_callback: 정상 + malformed.
- apply_selection: resume_song monkeypatch → 호출 인자 + 반환값 검증,
                    awaiting_selection 가드(noop).
- 프리필터 step 없음/빈 경우 → 빈 버튼 + 안내 (크래시 없음).
"""
from __future__ import annotations

import json
import time

import pytest

from autopilot.store import Store
from autopilot import cards


# ---------------------------------------------------------------------------
# 헬퍼: awaiting_selection 상태 run 시드
# ---------------------------------------------------------------------------

def _seed_awaiting_selection(store: Store) -> tuple[str, dict]:
    """작사 step(concept) + 프리필터 step(2 passed + 1 rejected) +
    awaiting_selection 상태 + open selection human_task 를 시드한다.

    returns: (run_id, concept)
    """
    concept = {
        "title": "봄이라고 부를게",
        "mood": "포근한",
        "theme": "봄",
        "style": "indie band",
    }
    run_id = store.create_run("2026-테스트앨범")

    # 작사 step (done, input_json = concept)
    store.start_step(run_id, "작사", input_data=concept)
    store.finish_step(run_id, "작사", {"lyrics_path": "/tmp/lyrics.md"})

    # 프리필터 step (done, output_json = passed 2 + rejected 1)
    prefilter_out = {
        "passed": [
            {
                "path": "/tmp/v1.wav",
                "sha256": "aaa",
                "metrics": {"lufs": -14.2, "duration_sec": 118.0, "peak_dbfs": -1.2},
            },
            {
                "path": "/tmp/v2.wav",
                "sha256": "bbb",
                "metrics": {"lufs": -13.5, "duration_sec": 132.0, "peak_dbfs": -0.8},
            },
        ],
        "rejected": [
            {
                "path": "/tmp/v3.wav",
                "reason": "길이 너무 짧음 (12.0s < 30.0s)",
                "metrics": {"duration_sec": 12.0},
            },
        ],
    }
    store.start_step(run_id, "프리필터")
    store.finish_step(run_id, "프리필터", prefilter_out)

    # open selection human_task + awaiting_selection 상태
    store.create_human_task(
        run_id, "selection", payload={}, expires_at=time.time() + 3600
    )
    store.update_run_status(run_id, "awaiting_selection")

    return run_id, concept


@pytest.fixture()
def store(tmp_path) -> Store:
    return Store(str(tmp_path / "test_cards.db"))


# ---------------------------------------------------------------------------
# build_selection_card
# ---------------------------------------------------------------------------

def test_build_selection_card_basic(store):
    run_id, concept = _seed_awaiting_selection(store)
    card = cards.build_selection_card(store, run_id)

    assert card["run_id"] == run_id

    # 통과 후보 2개 → 버튼 2개
    assert len(card["buttons"]) == 2

    # 콜백 데이터 형식
    labels = [b[0] for b in card["buttons"]]
    cbs = [b[1] for b in card["buttons"]]
    assert cbs[0] == f"pipeauto:select:{run_id}:0"
    assert cbs[1] == f"pipeauto:select:{run_id}:1"

    # 콜백 64바이트 제한 안전
    for cb in cbs:
        assert len(cb.encode("utf-8")) <= 64

    # 라벨에 메트릭(LUFS, 길이) 포함
    assert "후보 1" in labels[0]
    assert "LUFS" in labels[0]
    assert "-14.2" in labels[0]
    assert "1:58" in labels[0]  # 118초 = 1:58

    # 제목이 text 에 포함
    assert concept["title"] in card["text"]

    # 제외 테이크 사유가 text 에 나열
    assert "제외" in card["text"]
    assert "길이 너무 짧음" in card["text"]

    # rejected 리스트도 반환
    assert len(card["rejected"]) == 1


def test_build_selection_card_missing_prefilter(store):
    """프리필터 step 없음 → 빈 버튼 + 안내 (크래시 없음)."""
    run_id = store.create_run("앨범")
    store.update_run_status(run_id, "awaiting_selection")

    card = cards.build_selection_card(store, run_id)
    assert card["buttons"] == []
    assert "후보가 없습니다" in card["text"]
    assert card["run_id"] == run_id


def test_build_selection_card_empty_passed(store):
    """프리필터 step 있으나 passed 0개 → 빈 버튼 + 안내."""
    run_id = store.create_run("앨범")
    store.start_step(run_id, "프리필터")
    store.finish_step(
        run_id, "프리필터",
        {"passed": [], "rejected": [{"path": "/tmp/x.wav", "reason": "클리핑", "metrics": {}}]},
    )
    store.update_run_status(run_id, "awaiting_selection")

    card = cards.build_selection_card(store, run_id)
    assert card["buttons"] == []
    assert "후보가 없습니다" in card["text"]
    # rejected 는 그대로 반환
    assert len(card["rejected"]) == 1


# ---------------------------------------------------------------------------
# parse_select_callback
# ---------------------------------------------------------------------------

def test_parse_select_callback_valid():
    assert cards.parse_select_callback("pipeauto:select:abc123def456:0") == (
        "abc123def456", 0,
    )
    assert cards.parse_select_callback("pipeauto:select:abc123def456:7") == (
        "abc123def456", 7,
    )


def test_parse_select_callback_malformed():
    assert cards.parse_select_callback("pipeauto:cancel") is None
    assert cards.parse_select_callback("pipeauto:select:onlyrunid") is None
    assert cards.parse_select_callback("pipeauto:select:run:notanint") is None
    assert cards.parse_select_callback("garbage") is None
    assert cards.parse_select_callback("") is None
    assert cards.parse_select_callback("pipeauto:select:run:-1") is None
    assert cards.parse_select_callback(None) is None  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# apply_selection
# ---------------------------------------------------------------------------

def test_apply_selection_resumes(store, monkeypatch):
    run_id, concept = _seed_awaiting_selection(store)

    captured = {}

    def fake_resume_song(s, rid, c, d, answer):
        captured["store"] = s
        captured["run_id"] = rid
        captured["concept"] = c
        captured["answer"] = answer
        return {"status": "awaiting_publish_approval"}

    # cards.apply_selection 은 autopilot.pipeline.resume_song 을 lazy import
    monkeypatch.setattr("autopilot.pipeline.resume_song", fake_resume_song)

    result = cards.apply_selection(store, run_id, 1)

    assert result == {"status": "awaiting_publish_approval"}
    assert captured["run_id"] == run_id
    assert captured["answer"] == {"selected_index": 1}
    # concept 가 작사 step input_json 에서 복원되어 전달됨
    assert captured["concept"]["title"] == concept["title"]


def test_apply_selection_guard_not_awaiting(store, monkeypatch):
    """awaiting_selection 아닌 run → noop, resume_song 호출 안 됨."""
    run_id, _ = _seed_awaiting_selection(store)
    store.update_run_status(run_id, "done")

    called = {"resume": False}

    def fake_resume_song(*a, **k):
        called["resume"] = True
        return {"status": "done"}

    monkeypatch.setattr("autopilot.pipeline.resume_song", fake_resume_song)

    result = cards.apply_selection(store, run_id, 0)
    assert result["status"] == "noop"
    assert called["resume"] is False


def test_apply_selection_unknown_run(store):
    result = cards.apply_selection(store, "nonexistent", 0)
    assert result["status"] == "noop"


# ---------------------------------------------------------------------------
# _load_concept — '기획'(canonical) 우선 + '작사' 폴백
# ---------------------------------------------------------------------------

def test_load_concept_prefers_planning_step(store):
    """run_album이 영속화하는 '기획' step의 input_json에서 concept을 우선 복원한다.

    @step은 input_data를 저장하지 않으므로 실제 운영에서 '작사' step의
    input_json은 NULL이다. '기획' step이 canonical 소스가 되어야 한다.
    """
    concept = {"title": "무색무취", "mood": "차분한", "theme": "도시", "style": "indie jazz"}
    run_id = store.create_run("2026-앨범")

    # 운영 재현: '기획'에는 concept, '작사'에는 input 없음(@step 미저장)
    store.start_step(run_id, "기획", input_data=concept)
    store.finish_step(run_id, "기획", {"recorded": True})
    store.start_step(run_id, "작사")  # input_data=None → input_json NULL
    store.finish_step(run_id, "작사", {"lyrics_path": "/tmp/l.md"})

    loaded = cards._load_concept(store, run_id)
    assert loaded["title"] == "무색무취"
    assert loaded == concept

    # build_selection_card 도 '무제'가 아닌 실제 제목을 보여줘야 함
    store.start_step(run_id, "프리필터")
    store.finish_step(
        run_id, "프리필터",
        {"passed": [{"path": "/tmp/v1.wav", "metrics": {"lufs": -14.0, "duration_sec": 120.0}}],
         "rejected": []},
    )
    card = cards.build_selection_card(store, run_id)
    assert "무색무취" in card["text"]
    assert "무제" not in card["text"]


def test_load_concept_falls_back_to_lyrics_step(store):
    """'기획' step이 없으면 '작사' step input_json으로 폴백한다 (구버전 호환)."""
    concept = {"title": "옛날 곡", "mood": "잔잔한"}
    run_id = store.create_run("앨범")
    store.start_step(run_id, "작사", input_data=concept)
    store.finish_step(run_id, "작사", {"lyrics_path": "/tmp/l.md"})

    loaded = cards._load_concept(store, run_id)
    assert loaded == concept


def test_load_concept_empty_when_both_missing(store):
    """'기획'/'작사' 둘 다 없거나 비어있으면 빈 dict (크래시 없음)."""
    run_id = store.create_run("앨범")
    assert cards._load_concept(store, run_id) == {}

    # input_json NULL인 step만 있어도 빈 dict
    store.start_step(run_id, "기획")
    store.finish_step(run_id, "기획", {"recorded": True})
    assert cards._load_concept(store, run_id) == {}
