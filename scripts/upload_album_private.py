"""5-14 EP final_video.mp4 비공개(private) 업로드 + 썸네일."""
from __future__ import annotations
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

ROOT = Path(__file__).resolve().parent.parent
TOKEN = ROOT / "token.json"
SECRETS = ROOT / "client_secrets.json"

VIDEO = ROOT / "songs/14_geuriumi/final_video.mp4"
THUMB = Path("/mnt/c/Users/window11/Downloads/cover_a_final.jpg")
DESC = (ROOT / "songs/14_geuriumi/youtube_description.txt").read_text(encoding="utf-8")
TITLE = "왜 그리 울고만 있어요? 그리움만 쌓이게"

scopes = ["https://www.googleapis.com/auth/youtube.upload"]
creds = Credentials.from_authorized_user_file(str(TOKEN), scopes=scopes)
if not creds.valid:
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN.write_text(creds.to_json())
        print("[token] refreshed")
    else:
        raise RuntimeError("토큰 만료 — OAuth 재인증 필요")

yt = build("youtube", "v3", credentials=creds)

body = {
    "snippet": {
        "title": TITLE,
        "description": DESC,
        "categoryId": "10",  # Music
        "defaultLanguage": "ko",
    },
    "status": {
        "privacyStatus": "private",
        "selfDeclaredMadeForKids": False,
    },
}

print(f"[upload] {VIDEO}  ({VIDEO.stat().st_size/1024/1024:.1f} MB)")
media = MediaFileUpload(str(VIDEO), mimetype="video/mp4", resumable=True, chunksize=8*1024*1024)
req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
resp = None
last = -1
while resp is None:
    status, resp = req.next_chunk()
    if status:
        prog = int(status.progress() * 100)
        if prog >= last + 5:
            print(f"  ... {prog}%")
            last = prog

video_id = resp["id"]
print(f"[ok] video_id={video_id}")
print(f"     URL: https://youtu.be/{video_id}")
print(f"     Studio: https://studio.youtube.com/video/{video_id}/edit")

# 썸네일
print(f"[thumb] {THUMB}")
yt.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(str(THUMB), mimetype="image/jpeg")).execute()
print("[thumb] uploaded")

# 결과 저장
out = ROOT / "songs/14_geuriumi/youtube_upload.json"
out.write_text(json.dumps({
    "video_id": video_id,
    "url": f"https://youtu.be/{video_id}",
    "title": TITLE,
    "privacy": "private",
    "thumbnail": str(THUMB),
}, ensure_ascii=False, indent=2))
print(f"[meta] {out}")
