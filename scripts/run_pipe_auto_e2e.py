#!/usr/bin/env python3
"""
scripts/run_pipe_auto_e2e.py — PIPE-AUTO 실 VNC e2e 러너 (residual (c)).

실 파이프라인 1앨범(1곡) 런: 기획→작사→Suno프롬프트→실 SunoClient 생성(VNC:1+Chrome)
→프리필터→selection 게이트(Paused)에서 정지. **업로드까지 절대 진행 안 함**
(publish-gate + selection 게이트 미답변 → 구조적으로 업로드 도달 불가).

가드:
- selection 게이트에서 멈춤 (사람이 텔레그램 /select 로 선택 전까지 대기).
- 생성 실패/캡차 타임아웃은 @step max_attempts=2 + SunoClient CAPTCHA_TIMEOUT=300s로 유한.
- 이 러너는 어떤 게이트도 답변/승인하지 않는다 (실업로드 금지).
"""
from __future__ import annotations

import json
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("pipe_auto_e2e")

from autopilot.store import Store
from autopilot.pipeline import run_album, PipelineDeps

# 재즈 채널 정체성 — 재즈 서브장르 (lo-fi 금지)
CONCEPT = {
    "title": "비 그친 새벽",
    "mood": "melancholy, intimate, late-night",
    "theme": "비가 그친 새벽, 혼자 남은 방의 고요함과 옅은 그리움",
    "style": (
        "smoky late-night jazz ballad, soft brushed drums, upright bass, "
        "warm piano, emotional female vocal, dreamy, intimate"
    ),
}
ALBUM_SLUG = "VNC_E2E_비그친새벽"
DB_PATH = os.environ.get("AUTOPILOT_DB_PATH", "data/autopilot.db")


def main() -> int:
    log.info("=== PIPE-AUTO 실 VNC e2e 시작 ===")
    log.info("앨범: %s | 곡: %s | DB: %s", ALBUM_SLUG, CONCEPT["title"], DB_PATH)
    store = Store(DB_PATH)
    deps = PipelineDeps()  # 실 runner/youtube (단, 게이트에서 멈추므로 후처리/영상/업로드 미도달)

    try:
        results = run_album(store, ALBUM_SLUG, [CONCEPT], deps)
    except Exception as exc:  # noqa: BLE001
        log.error("run_album 예외 — 중단: %s", exc, exc_info=True)
        print(json.dumps({"fatal": str(exc)}, ensure_ascii=False))
        return 2

    # ── 단계별 상태 보고 ───────────────────────────────────────────────────
    report = []
    for r in results:
        rid = r["run_id"]
        entry = {"run_id": rid, "title": r.get("title"), "status": r["status"], "steps": {}}
        for name in ("기획", "작사", "Suno프롬프트", "생성", "프리필터"):
            st = store.get_step(rid, name)
            entry["steps"][name] = st["status"] if st else "—(미실행)"
        # 후보 수
        gen = store.get_step(rid, "생성")
        if gen and gen["output_json"]:
            try:
                entry["candidates_generated"] = len(json.loads(gen["output_json"]).get("candidates", []))
            except Exception:
                entry["candidates_generated"] = "?"
        pf = store.get_step(rid, "프리필터")
        if pf and pf["output_json"]:
            try:
                pfd = json.loads(pf["output_json"])
                entry["prefilter_passed"] = len(pfd.get("passed", []))
                entry["prefilter_rejected"] = len(pfd.get("rejected", []))
            except Exception:
                pass
        report.append(entry)

    print("\n=== E2E 결과 ===")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    log.info("=== 종료 ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
