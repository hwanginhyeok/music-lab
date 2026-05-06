"""크레딧 차감 + workspace 최근 곡 추적."""
from __future__ import annotations
import sys, time, json
from pathlib import Path
sys.path.insert(0, '.')
from suno_download import SunoAPI

api = SunoAPI()

# 크레딧
try:
    credits = api.get_credits()
    print(f"현재 크레딧: {credits}")
except Exception as e:
    print(f"크레딧 조회 실패: {e}")

# 최근 곡 (workspace)
api.refresh_jwt()
songs = api.get_songs(page=0)
print(f"\n최근 곡 {len(songs)}개")

# 오늘 13:00 이후 또는 'Theme Statement' 제목 / 인스트루멘탈
import datetime as dt
target_after = dt.datetime(2026, 4, 30, 13, 0).timestamp()
matches = []
for s in songs[:30]:
    title = s.get("title") or ""
    sid = s.get("id")
    status = s.get("status")
    created_at = s.get("created_at")
    audio_url = s.get("audio_url")
    metadata = s.get("metadata") or {}
    is_inst = metadata.get("is_instrumental") if isinstance(metadata, dict) else None
    # 시간 파싱
    ts = None
    if created_at:
        try:
            ts = dt.datetime.fromisoformat(created_at.replace("Z", "+00:00")).timestamp()
        except Exception:
            pass
    recent = ts and ts > (target_after - 3600 * 9)  # KST 보정
    title_match = "theme statement" in title.lower() or "그날" in title or "그 날" in title
    if recent or title_match or is_inst:
        matches.append({
            "id": sid, "title": title, "status": status,
            "created_at": created_at, "is_instrumental": is_inst,
            "audio_url_len": len(audio_url) if audio_url else 0,
        })

print(f"\n매칭 곡 {len(matches)}개:")
for m in matches[:15]:
    print(f"  {m}")

# 전체 30개 요약
print(f"\n전체 30개 요약:")
for s in songs[:15]:
    print(f"  id={s.get('id')[:8]} status={s.get('status')!r:<12} created={s.get('created_at')!r:<28} title={(s.get('title') or '')[:40]!r}")
