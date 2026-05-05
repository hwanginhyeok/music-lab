#!/usr/bin/env python3
"""
앨범 YouTube 업로드 스크립트.

songs/01_봄이라고_부를게/suite/release/album.mp3를 YouTube에 업로드.

사용법:
  python3 scripts/youtube_upload_album.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
except ImportError:
    print("[오류] Google API 패키지가 설치되어 있지 않습니다.")
    print("  pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
    sys.exit(1)

sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
from description_utils import compose_description, AI_DISCLOSURE  # noqa: E402

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
YOUTUBE_CATEGORY_MUSIC = "10"

ALBUM_DIR = PROJECT_ROOT / "songs/01_봄이라고_부를게"
ALBUM_PATH = ALBUM_DIR / "suite/release/album_video.mp4"
THUMBNAIL_PATH = ALBUM_DIR / "suite/video/thumbnail.jpg"


def get_credentials():
    """OAuth2 인증 처리."""
    token_path = PROJECT_ROOT / "token.json"
    secrets_path = PROJECT_ROOT / "client_secrets.json"

    creds = None

    if token_path.is_file():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("  토큰 갱신 중...")
            creds.refresh(Request())
        else:
            if not secrets_path.is_file():
                print("❌ client_secrets.json을 찾을 수 없습니다.")
                print("  Google Cloud Console에서 OAuth 2.0 클라이언트 ID를 만드세요.")
                return None

            flow = InstalledAppFlow.from_client_secrets_file(str(secrets_path), SCOPES)
            creds = flow.run_local_server(port=0)

        token_path.write_text(creds.to_json(), encoding="utf-8")
        print(f"  토큰 저장: {token_path}")

    return creds


def get_video_metadata():
    """앨범 메타데이터 생성. description은 description_utils로 통일."""
    return {
        "title": "봄이라고 부를게 (Album Suite) - AI 인디 팝",
        "description": compose_description(ALBUM_DIR),
        "tags": "인디팝,Indie Pop,팝송,K-POP,감성,보컬,앨범,Suno AI,AI음악,Korean Pop",
        "category_id": YOUTUBE_CATEGORY_MUSIC,
        "privacy_status": "public",  # 바로 공개
    }


def upload_album(youtube, metadata):
    """앨범 업로드."""
    if not ALBUM_PATH.is_file():
        print(f"❌ 앨범 파일을 찾을 수 없습니다: {ALBUM_PATH}")
        return None

    print(f"\n앨범 업로드 시작: {ALBUM_PATH.name}")
    print(f"파일 크기: {ALBUM_PATH.stat().st_size / 1024 / 1024:.1f} MB\n")

    body = {
        "snippet": {
            "title": metadata["title"],
            "description": metadata["description"],
            "tags": metadata["tags"].split(","),
            "categoryId": metadata["category_id"],
        },
        "status": {
            "privacyStatus": metadata["privacy_status"],
            "selfDeclaredMadeForKids": False,
        },
    }

    media_body = MediaFileUpload(
        str(ALBUM_PATH),
        mimetype="video/mp4",
        resumable=True
    )

    insert_request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media_body
    )

    print("업로드 중... (시간이 걸릴 수 있습니다)")

    try:
        response = insert_request.execute()

        video_id = response["id"]
        youtube_url = f"https://www.youtube.com/watch?v={video_id}"

        print(f"\n✅ 업로드 완료!")
        print(f"🔗 {youtube_url}")
        print(f"ID: {video_id}")

        # 썸네일 업로드
        if THUMBNAIL_PATH.is_file():
            try:
                youtube.thumbnails().set(
                    videoId=video_id,
                    media_body=MediaFileUpload(str(THUMBNAIL_PATH))
                ).execute()
                print("✅ 썸네일 업로드 완료")
            except Exception as e:
                print(f"⚠️ 썸네일 업로드 실패: {e}")

        return {
            "video_id": video_id,
            "url": youtube_url,
        }

    except Exception as e:
        print(f"❌ 업로드 실패: {e}")
        return None


def main():
    print("봄이라고 부를게 앨범 YouTube 업로드\n")

    # 인증
    print("YouTube 인증 중...")
    creds = get_credentials()
    if not creds:
        sys.exit(1)

    youtube = build("youtube", "v3", credentials=creds)
    print("✅ 인증 완료\n")

    # 메타데이터
    metadata = get_video_metadata()

    print(f"제목: {metadata['title']}")
    print(f"설명: {metadata['description'][:100]}...")
    print()

    # 업로드
    result = upload_album(youtube, metadata)

    if result:
        print(f"\n🎉 앨범 업로드 성공!")
        print(f"🔗 {result['url']}")


if __name__ == "__main__":
    main()
