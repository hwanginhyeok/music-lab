"""선 밖 생성 성공 디텍터 (다운로드 워처 아님 — 감지 전용).

형님이 noVNC에서 사람손길+Create+hCaptcha 해결로 제출 성공하면,
크레딧 감소 OR 신규곡(기존 baseline에 없는 id) 등장을 감지하고 즉시 종료한다.
다운로드는 하지 않는다 (감지 후 PM/pane1이 별도로 다운로드+검증).

ENV: SUNO_COOKIE 필요(.env 자동 로드). DETECT_MINUTES(기본 120).
"""
import os
import sys
import time

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJ)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(PROJ, ".env"))
except Exception:
    pass
from suno_download import SunoAPI

DETECT_MIN = int(os.getenv("DETECT_MINUTES", "120"))

api = SunoAPI()
deadline = time.time() + DETECT_MIN * 60

# 네트워크 간헐 단절(Errno 101) 대비: baseline 확보까지 재시도.
FALLBACK_CREDITS = int(os.getenv("BASE_CREDITS", "2640"))
base_ids = None
base_credits = None
neterr0 = 0
while time.time() < deadline and base_ids is None:
    try:
        api.refresh_jwt()
        base_ids = {s["id"] for s in api.get_songs(0) if s.get("id")}
        base_credits = api.get_credits()
    except Exception as e:
        neterr0 += 1
        if neterr0 % 5 == 1:
            print(f"[baseline 대기] 네트워크 오류 {type(e).__name__} (누적 {neterr0}) — 재시도", flush=True)
        base_ids = None
        time.sleep(30)
if base_ids is None:
    print("[디텍터 종료] baseline 확보 실패 — 네트워크 계속 불가", flush=True)
    sys.exit(2)
if base_credits is None:
    base_credits = FALLBACK_CREDITS
print(
    f"[디텍터 시작] baseline 크레딧={base_credits} 곡={len(base_ids)} / "
    f"감지 {DETECT_MIN}분 / 성공 신호 대기 (다운로드 안 함)",
    flush=True,
)
neterr = 0
while time.time() < deadline:
    time.sleep(30)
    try:
        api.refresh_jwt()
        cr = api.get_credits()
        songs = api.get_songs(0)
    except Exception as e:
        neterr += 1
        if neterr % 5 == 1:
            print(f"[poll] 네트워크 오류 {type(e).__name__} (누적 {neterr})", flush=True)
        continue
    cur_ids = {s["id"] for s in songs if s.get("id")}
    fresh = [s for s in songs if s.get("id") and s["id"] not in base_ids]
    credit_dropped = (
        base_credits is not None and cr is not None and cr < base_credits
    )
    if credit_dropped or fresh:
        print(
            f"[🎉 성공 감지] 크레딧 {base_credits}→{cr} / 신규곡 {len(fresh)}개",
            flush=True,
        )
        for s in fresh:
            print(
                f"  신규: {s.get('title','')[:28]} | {s.get('status')} | "
                f"{s.get('created_at','')[:19]}UTC | {s.get('id','')[:8]}",
                flush=True,
            )
        print("[디텍터 종료] 성공 — pane1이 다운로드+검증 진행", flush=True)
        sys.exit(0)

print(f"[디텍터 종료] {DETECT_MIN}분 타임아웃 — 성공 신호 미감지", flush=True)
