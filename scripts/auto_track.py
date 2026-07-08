"""트랙 자동제출 러너 — SunoClient.generate(submit=True) + 멱등 검증 + 다운로드 + 풀길이 검증.

사용: python3 scripts/auto_track.py <track_dir> "<title>"
  예: python3 scripts/auto_track.py songs/cortis_ep_선밖/02_내식대로 "내 식대로"

흐름:
  1. baseline 크레딧 캡처 (멱등키)
  2. suno_prompt.md에서 style/lyrics 추출
  3. SunoClient.generate(submit=True) — 입력+Create+캡차대기(형님 noVNC)+제출감지
  4. 멱등 검증: 크레딧이 정확히 baseline-10 이고 신규곡 2개? (0이면 D-001 미성사 → 종료코드 3)
  5. 신규곡 complete까지 폴링 → 다운로드 → ffprobe 풀길이(>=110초) 검증
  6. 결과 출력 (성공/실패/길이)

종료코드: 0=성공, 3=제출 미성사(D-001), 4=중복의심, 5=다운로드/길이 실패, 2=설정오류
⚠️ Exclude 박스는 generate()가 안 채움(한계).
"""
import os
import re
import sys
import time
import json
import subprocess

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJ)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(PROJ, ".env"))
except Exception:
    pass

from suno_download import SunoAPI


def log(m):
    print(m, flush=True)


def extract(track_dir):
    pf = os.path.join(PROJ, track_dir, "suno_prompt.md")
    src = open(pf, encoding="utf-8").read()
    style = re.search(r"## Style of Music[^\n]*\n+```\s*\n(.*?)\n```", src, re.DOTALL)
    lyr = re.search(r"## Suno 입력용 가사[^\n]*\n+```\s*\n(.*?)\n```", src, re.DOTALL)
    if not style or not lyr:
        raise SystemExit(f"[설정오류] style/lyrics 추출 실패: {pf}")
    return style.group(1).strip(), lyr.group(1).strip()


def main():
    if len(sys.argv) < 3:
        log("usage: auto_track.py <track_dir> <title>")
        sys.exit(2)
    track_dir, title = sys.argv[1], sys.argv[2]
    style, lyrics = extract(track_dir)
    log(f"[추출] title={title} style={len(style)}자 lyrics={len(lyrics)}자")

    api = SunoAPI()
    # 네트워크 간헐 단절(Errno 101) 대비: baseline 확보까지 재시도 (최대 5분)
    base_credits = None
    base_ids = None
    t0 = time.time()
    while time.time() - t0 < 300:
        try:
            api.refresh_jwt()
            base_credits = api.get_credits()
            base_ids = {s["id"] for s in api.get_songs(0) if s.get("id")}
            break
        except Exception as e:
            log(f"[baseline 재시도] 네트워크 {type(e).__name__} — 20초 후 재시도")
            time.sleep(20)
    if base_ids is None or base_credits is None:
        log("[설정오류] baseline 확보 실패 — 네트워크 지속 불가. 중단(제출 안 함).")
        sys.exit(2)
    log(f"[baseline] 크레딧={base_credits} 곡={len(base_ids)}")

    # === 자동 제출 ===
    from suno_client import SunoClient
    g = SunoClient()
    log("[generate] submit=True 시작 — 캡차 뜨면 형님이 noVNC에서 풀어야 함")
    try:
        urls = g.generate(lyrics=lyrics, style=style, title=title,
                          model="v5.5", instrumental=False, submit=True)
        log(f"[generate 반환] urls={urls}")
    except Exception as e:
        log(f"[generate 예외] {type(e).__name__}: {e}")
        urls = None

    # === 멱등 검증: 크레딧/신규곡 ===
    time.sleep(3)
    try:
        api.refresh_jwt()
        now_credits = api.get_credits()
    except Exception:
        now_credits = base_credits
    songs = api.get_songs(0)
    fresh = [s for s in songs if s.get("id") and s["id"] not in base_ids]
    drop = (base_credits - now_credits) if (base_credits and now_credits) else 0
    log(f"[멱등검증] 크레딧 {base_credits}→{now_credits} (드롭 {drop}) / 신규곡 {len(fresh)}개")

    if drop == 0 and not fresh:
        log("[❌ D-001 미성사] 크레딧 무변+신규곡 0 — 자동제출 안티봇 차단. 중단.")
        sys.exit(3)
    if drop > 10 or len(fresh) > 2:
        log(f"[⚠️ 중복의심] 드롭 {drop} / 신규 {len(fresh)} — 정상은 10/2. 중단 후 점검 필요.")
        sys.exit(4)

    # === complete 폴링 + 다운로드 ===
    new_ids = {s["id"] for s in fresh}
    deadline = time.time() + 600
    done = {}
    while time.time() < deadline and len(done) < len(new_ids):
        try:
            api.refresh_jwt()
            songs = api.get_songs(0)
        except Exception:
            time.sleep(20); continue
        for s in songs:
            if s.get("id") in new_ids and s.get("status") == "complete" and s["id"] not in done:
                done[s["id"]] = s
                log(f"[complete] {s.get('title')} {s['id'][:8]}")
        if len(done) < len(new_ids):
            time.sleep(20)

    if not done:
        log("[❌ 타임아웃] complete 0곡 — 다운로드 불가. 중단.")
        sys.exit(5)

    # 다운로드 + ffprobe
    results = []
    import glob
    for sid, s in done.items():
        subprocess.run(["python3", "suno_download.py", "--song-id", sid], cwd=PROJ)
        # Suno 자동제목 방지: 다운로드 파일을 기획 곡명으로 강제 리네임
        sid8 = sid[:8]
        for ext in ("mp3", "jpeg", "jpg", "png"):
            for f in glob.glob(os.path.join(PROJ, "data/suno", f"*{sid8}*.{ext}")):
                base = os.path.basename(f)
                suffix = "_cover" if base.rsplit(".", 1)[0].endswith("_cover") else ""
                newname = f"{title}_{sid8}{suffix}.{ext}"
                newpath = os.path.join(PROJ, "data/suno", newname)
                if f != newpath:
                    os.replace(f, newpath)
        cands = glob.glob(os.path.join(PROJ, "data/suno", f"{title}_{sid8}.mp3"))
        dur = 0.0
        path = cands[0] if cands else None
        if path:
            out = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=nk=1:nw=1", path],
                capture_output=True, text=True)
            try:
                dur = float(out.stdout.strip())
            except Exception:
                dur = 0.0
        results.append({"id": sid[:8], "path": os.path.basename(path) if path else None,
                       "dur": round(dur, 1)})
        log(f"[다운로드+검증] {sid[:8]} {os.path.basename(path) if path else '?'} {dur:.1f}초")

    full_ok = all(r["dur"] >= 110 for r in results)
    log(f"[결과] {json.dumps(results, ensure_ascii=False)}")
    log(f"[풀길이검증] {'PASS' if full_ok else 'FAIL(110초 미만 포함)'}")
    sys.exit(0 if full_ok else 5)


if __name__ == "__main__":
    main()
