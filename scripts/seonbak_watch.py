"""선 밖 Track01 큐 진입 감지 + 자동 다운로드 워처.
형님이 noVNC에서 Create를 직접 누르면 → 크레딧 차감/신규곡으로 큐 진입 감지 →
complete 될 때까지 폴링 → suno_download.py로 자동 다운로드.

D-001 안티봇으로 자동 클릭은 불가하므로 '사람의 Create 클릭'만 사람이 하고,
그 이후 단계(감지·대기·다운로드)를 자동화한다.

ENV: SUNO_COOKIE 필요. WATCH_MINUTES(기본 180)로 감시 시간 조정.
"""
import os
import sys
import time
import subprocess

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJ)

# systemd 등 비대화 환경에서도 .env 자동 로드 (시크릿 커맨드라인 노출 방지)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(PROJ, ".env"))
except Exception:
    pass

from suno_download import SunoAPI

BASE_CREDITS = 2650
WATCH_MIN = int(os.getenv("WATCH_MINUTES", "360"))

api = SunoAPI()
base_ids = {s["id"] for s in api.get_songs(0) if s.get("id")}
try:
    BASE_CREDITS = api.get_credits()
except Exception:
    pass
print(
    f"[워처 시작] baseline 크레딧={BASE_CREDITS} 곡={len(base_ids)} / "
    f"감시 {WATCH_MIN}분 / 큐 진입 대기...",
    flush=True,
)

deadline = time.time() + WATCH_MIN * 60
new_ids = set()
queued = False

while time.time() < deadline:
    time.sleep(15)
    try:
        api.refresh_jwt()
        cr = api.get_credits()
        songs = api.get_songs(0)
    except Exception as e:
        print(f"[poll] API 오류 {type(e).__name__}", flush=True)
        continue
    cur_ids = {s["id"] for s in songs if s.get("id")}
    fresh = cur_ids - base_ids
    if not queued and (cr < BASE_CREDITS or fresh):
        queued = True
        new_ids = set(fresh)
        print(
            f"[🎉 큐 진입 감지] 크레딧 {BASE_CREDITS}→{cr} / "
            f"신규곡 {len(fresh)}개 {list(fresh)[:4]}",
            flush=True,
        )
    if queued:
        new_ids |= fresh
        statuses = {
            s.get("id"): s.get("status") for s in songs if s.get("id") in new_ids
        }
        print(f"[대기] 크레딧={cr} 신규곡상태={statuses}", flush=True)
        done = [
            s for s in songs
            if s.get("id") in new_ids and s.get("status") == "complete"
        ]
        if statuses and all(st == "complete" for st in statuses.values()):
            print(f"[✅ 완성] {len(done)}곡 complete → 다운로드 시작", flush=True)
            for s in done:
                sid = s["id"]
                print(
                    f"  다운로드: {s.get('title', '')[:30]} ({sid[:8]})",
                    flush=True,
                )
                subprocess.run(
                    ["python3", "suno_download.py", "--song-id", sid],
                    cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                )
            print("[워처 종료] 다운로드 완료", flush=True)
            sys.exit(0)

print(f"[워처 종료] {WATCH_MIN}분 타임아웃 — 큐 진입/완성 미감지", flush=True)
