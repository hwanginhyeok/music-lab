"""workspace에 살아있는 18곡 회수 → tracks/{NN}/raw/v1.mp3, v2.mp3 + meta.json.

Track 01은 PoC #6에서 이미 다운로드됨 (raw/v1, v2 존재) → 스킵.
Track 02~09: workspace 매칭(제목+생성시각)으로 v1/v2 다운로드.
"""
from __future__ import annotations
import sys, json, requests
from pathlib import Path
from datetime import datetime, timezone
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from suno_download import SunoAPI

ALBUM_DIR = Path("songs/14_geuriumi")

# 트랙 → (폴더명, Suno 제목, instrumental, style 키워드, KST 시각 윈도우)
# 발주 순서대로 시각 매칭 (workspace 정렬 기준)
TRACK_MATCH = [
    # (folder, suno_title, instrumental)
    ("02_reflection", "Reflection", True),
    ("03_quiet_conversation", "Quiet Conversation", True),
    ("05_solitude", "Solitude", True),
    ("07_after_the_words", "After the Words", True),
    ("08_late_night", "Late Night", True),
    ("09_reprise", "Reprise (Theme Returns)", True),
    ("04_saxophone", "Saxophone (Her Answer)", True),
    ("06_vocal", "그리움", False),
]

def parse_style(folder: Path) -> str:
    txt = (folder / "suno_prompt.md").read_text(encoding="utf-8")
    import re
    m = re.search(r"## Style of Music\s*```\s*\n(.*?)\n\s*```", txt, re.DOTALL)
    return m.group(1).strip() if m else ""

api = SunoAPI()
api.refresh_jwt()
songs = api.get_songs(page=0)
# 오늘 14:00 KST = 05:00 UTC 이후만
threshold = datetime(2026, 4, 30, 5, 0, 0, tzinfo=timezone.utc)
recent = []
for s in songs:
    ca = s.get("created_at")
    if not ca: continue
    try:
        ts = datetime.fromisoformat(ca.replace("Z", "+00:00"))
    except: continue
    if ts > threshold and s.get("status") == "complete":
        recent.append(s)

# 제목별 그룹핑 (가장 빠른 발주 페어 사용 — 1차 결과 우선)
by_title = {}
for s in sorted(recent, key=lambda x: x.get("created_at")):
    t = s.get("title") or ""
    by_title.setdefault(t, []).append(s)

print(f"workspace 신곡: {len(recent)}, 제목 그룹: {len(by_title)}")
for t, lst in by_title.items():
    print(f"  {t!r}: {len(lst)} 곡")

results = []
total_credits = api.get_credits()

for folder_name, suno_title, instrumental in TRACK_MATCH:
    folder = ALBUM_DIR / "tracks" / folder_name
    raw = folder / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    v1_path = raw / "v1.mp3"
    v2_path = raw / "v2.mp3"

    if v1_path.exists() and v2_path.exists():
        print(f"⏭️  {folder_name}: v1+v2 이미 존재")
        continue

    matches = by_title.get(suno_title, [])
    if len(matches) < 2:
        print(f"❌ {folder_name}: 매칭 곡 {len(matches)}/2 — 스킵")
        results.append({"track": folder_name, "status": "no-match", "found": len(matches)})
        continue

    # 가장 빠른 페어 (첫 2개)
    pair = matches[:2]
    versions = {}
    ok = True
    for idx, song in enumerate(pair, start=1):
        sid = song["id"]
        full = api.get_song(sid)
        url = full.get("audio_url") if full else None
        if not url:
            ok = False; break
        try:
            r = requests.get(url, timeout=120); r.raise_for_status()
        except Exception as e:
            print(f"  download fail: {e}"); ok = False; break
        out = v1_path if idx == 1 else v2_path
        out.write_bytes(r.content)
        versions[f"v{idx}"] = {
            "song_id": sid,
            "suno_url": f"https://suno.com/song/{sid}",
            "size_bytes": len(r.content),
            "created_at": song.get("created_at"),
        }

    if ok:
        meta = {
            "track": folder_name,
            "title": suno_title,
            "album": "왜 그리 울고만 있어요? 그리움만 쌓이게",
            "generated_at": pair[0].get("created_at"),
            "method": "suno_pipeline.py + (C) Advanced 모드 + 빈 lyrics input event"
                      if instrumental else "suno_pipeline.py + Advanced 보컬 경로",
            "model": "v5.5",
            "instrumental": instrumental,
            "style": parse_style(folder),
            "versions": versions,
            "recovered_from_workspace": True,
            "notes": "generate_album.py 검증 버그로 자동 다운로드 실패. workspace에서 회수.",
        }
        (raw / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        sz1 = versions["v1"]["size_bytes"] / 1024 / 1024
        sz2 = versions["v2"]["size_bytes"] / 1024 / 1024
        print(f"✅ {folder_name}: v1 {sz1:.1f}MB / v2 {sz2:.1f}MB")
        results.append({"track": folder_name, "status": "ok"})
    else:
        results.append({"track": folder_name, "status": "download-fail"})

print("\n=== 회수 종합 ===")
ok_count = sum(1 for r in results if r["status"] == "ok")
print(f"성공: {ok_count}/{len(TRACK_MATCH)}")
for r in results:
    print(f"  {r['track']:<28} {r['status']}")
print(f"\n현재 크레딧: {total_credits}")
