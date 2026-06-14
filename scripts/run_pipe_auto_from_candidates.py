#!/usr/bin/env python3
"""
scripts/run_pipe_auto_from_candidates.py — PIPE-AUTO 검증 (generate 노드 우회).

D-001(Suno 자동생성 차단) 회피: 실 생성 대신 기존 검증된 실곡 mp3를 후보로 주입.
기획/작사/Suno프롬프트/생성 step을 done으로 시드(생성 output=실 mp3 후보) →
song_pipeline 실행 → 작사~생성은 @step done-skip → **프리필터(실파일)→selection 게이트(정지)**.

게이트 도달 후: 형님이 텔레그램 /select 로 선택 → 후처리(-14LUFS 실ffmpeg)→영상(실ffmpeg)
→ publish_approval 게이트 정지(업로드는 '올려' 전까지 publish-gate 유지).
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("pipe_from_cands")

from autopilot.store import Store
from autopilot.engine import Ctx, run_pipeline
from autopilot.pipeline import song_pipeline, PipelineDeps

DB_PATH = os.environ.get("AUTOPILOT_DB_PATH", "data/autopilot.db")
ALBUM_SLUG = "VNC_E2E_프리필터검증"

# 기존 검증된 실 Suno mp3 3개를 후보(v1/v2/v3 take)로 주입
CAND_PATHS = [
    "data/suno/4b3b0278-a850-4b87-81ef-02a211c258d0.mp3",
    "data/suno/6bf985d1-022e-4d62-af60-9301e00053b7.mp3",
    "data/suno/72fe2e54-de04-41a7-a644-11edea042652.mp3",
]
CONCEPT = {
    "title": "비 그친 새벽",
    "mood": "melancholy, intimate, late-night",
    "theme": "비가 그친 새벽, 혼자 남은 방의 고요함",
    "style": "smoky late-night jazz ballad, warm piano, emotional vocal",
}


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    abs_cands = [os.path.abspath(p) for p in CAND_PATHS]
    for p in abs_cands:
        if not os.path.exists(p):
            log.error("후보 파일 없음: %s", p)
            return 2
    candidates = [{"path": p, "sha256": _sha256(p)} for p in abs_cands]
    log.info("주입 후보 %d개 (실 Suno mp3)", len(candidates))

    store = Store(DB_PATH)
    rid = store.create_run(ALBUM_SLUG)
    log.info("run 생성: %s (album=%s)", rid, ALBUM_SLUG)

    # 상류 step 시드 (done) — song_pipeline이 @step done-skip으로 건너뜀
    store.start_step(rid, "기획", input_data=CONCEPT)
    store.finish_step(rid, "기획", {"recorded": True})
    store.start_step(rid, "작사", input_data=CONCEPT)
    store.finish_step(rid, "작사", {"lyrics_path": f"data/autopilot/{rid}/lyrics.txt", "sha256": "seed"})
    store.start_step(rid, "Suno프롬프트")
    store.finish_step(rid, "Suno프롬프트", {"prompt_path": f"data/autopilot/{rid}/suno_prompt.txt", "sha256": "seed"})
    store.start_step(rid, "생성")
    store.finish_step(rid, "생성", {"candidates": candidates})  # ← 실 mp3 후보 주입
    for c in candidates:
        store.add_artifact(rid, "생성", "audio_candidate", c["path"], c["sha256"], meta={"injected": True})
    log.info("상류 step 시드 완료 (기획/작사/Suno프롬프트/생성=done)")

    # 파이프라인 실행 — 작사~생성 skip → 프리필터(실파일) → selection 게이트
    ctx = Ctx(run_id=rid, store=store)
    deps = PipelineDeps()  # 실 ffmpeg/youtube (게이트에서 멈추므로 후처리 이후 미도달)
    result = run_pipeline(ctx, lambda c: song_pipeline(c, CONCEPT, deps))

    # 보고
    print("\n=== 결과 ===")
    print("run_id:", rid)
    print("status:", result.get("status"))
    pf = store.get_step(rid, "프리필터")
    if pf and pf["output_json"]:
        pfd = json.loads(pf["output_json"])
        print(f"프리필터: 통과 {len(pfd.get('passed', []))} / 제외 {len(pfd.get('rejected', []))}")
        for i, p in enumerate(pfd.get("passed", [])):
            print(f"  [통과 {i}] {os.path.basename(p['path'])}  metrics={p.get('metrics')}")
        for r in pfd.get("rejected", []):
            print(f"  [제외] {os.path.basename(r['path'])}  reason={r.get('reason')}")
    # 게이트 상태
    runrow = store.get_run(rid)
    print("run status(DB):", runrow["status"] if runrow else "?")
    from autopilot import resume as R
    awaiting = [w for w in R.list_awaiting(store) if w["run_id"] == rid]
    print("awaiting 게이트:", awaiting)
    print(json.dumps({"run_id": rid, "status": result.get("status")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
