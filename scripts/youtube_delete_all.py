#!/usr/bin/env python3
"""
YouTube에 업로드된 모든 곡 일괄 삭제.

YouTube Data API v3로 채널의 업로드 목록을 가져와서 전체 삭제.

사용법:
  python3 scripts/youtube_delete_all.py --dry-run  # 삭제 목록만 확인
  python3 scripts/youtube_delete_all.py --force    # 실제 삭제
"""

import sys
from pathlib import Path

try:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
except ImportError:
    print("[오류] Google API 패키지가 설치되어 있지 않습니다.")
    print("  pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
    sys.exit(1)

PROJECT_ROOT = Path(__file__).parent.parent
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def get_credentials():
    """OAuth2 인증 처리."""
    token_path = PROJECT_ROOT / "token.json"

    if not token_path.is_file():
        print("❌ YouTube 인증 토큰이 없습니다.")
        print("  먼저 youtube_upload.py를 한 번 실행해서 인증하세요.")
        sys.exit(1)

    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    # 토큰 갱신
    if creds.expired and creds.refresh_token:
        from google.auth.transport.requests import Request
        creds.refresh(Request())

    return creds


def list_uploaded_videos(youtube):
    """채널에 업로드된 모든 동영상 목록 가져오기."""
    videos = []

    # 업로드 플레이리스트 ID 가져오기
    channels_resp = youtube.channels().list(
        part="contentDetails",
        mine=True
    ).execute()

    if not channels_resp.get("items"):
        print("❌ 채널을 찾을 수 없습니다.")
        return videos

    uploads_playlist_id = channels_resp["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    # 플레이리스트 아이템 가져오기 (페이지네이션)
    next_page_token = None
    while True:
        playlist_resp = youtube.playlistItems().list(
            part="snippet",
            playlistId=uploads_playlist_id,
            maxResults=50,
            pageToken=next_page_token
        ).execute()

        for item in playlist_resp.get("items", []):
            video_id = item["snippet"]["resourceId"]["videoId"]
            title = item["snippet"]["title"]
            videos.append({
                "video_id": video_id,
                "title": title,
            })

        next_page_token = playlist_resp.get("nextPageToken")
        if not next_page_token:
            break

    return videos


def delete_videos(youtube, videos):
    """동영상 일괄 삭제."""
    deleted = []
    failed = []

    for i, video in enumerate(videos, 1):
        video_id = video["video_id"]
        title = video["title"]

        try:
            youtube.videos().delete(id=video_id).execute()
            deleted.append(video)
            print(f"✅ [{i}/{len(videos)}] 삭제 완료: {title}")
        except Exception as e:
            failed.append({"video": video, "error": str(e)})
            print(f"❌ [{i}/{len(videos)}] 삭제 실패: {title} - {e}")

    return deleted, failed


def main():
    import argparse

    parser = argparse.ArgumentParser(description="YouTube 곡 일괄 삭제")
    parser.add_argument("--dry-run", action="store_true", help="삭제 목록만 확인")
    parser.add_argument("--force", action="store_true", help="실제 삭제 실행")
    args = parser.parse_args()

    if not args.dry_run and not args.force:
        print("사용법:")
        print("  python3 scripts/youtube_delete_all.py --dry-run  # 삭제 목록만 확인")
        print("  python3 scripts/youtube_delete_all.py --force    # 실제 삭제")
        sys.exit(1)

    # 인증
    print("YouTube 인증 중...")
    creds = get_credentials()
    youtube = build("youtube", "v3", credentials=creds)
    print("✅ 인증 완료\n")

    # 업로드된 동영상 목록 가져오기
    print("업로드된 동영상 목록 가져오는 중...")
    videos = list_uploaded_videos(youtube)

    if not videos:
        print("업로드된 동영상이 없습니다.")
        return

    print(f"\n총 {len(videos)}개의 동영상을 찾았습니다:\n")

    for i, video in enumerate(videos, 1):
        print(f"{i}. {video['title']}")
        print(f"   ID: {video['video_id']}")
        print(f"   https://www.youtube.com/watch?v={video['video_id']}")
        print()

    if args.dry_run:
        print("--dry-run 모드: 삭제하지 않았습니다.")
        print("--force로 실제 삭제를 실행하세요.")
        return

    # 실제 삭제
    if not args.force:
        return

    print(f"\n{len(videos)}개의 동영상을 삭제합니다...")
    confirm = input("정말 삭제하시겠습니까? (yes/no): ")

    if confirm.lower() != "yes":
        print("취소되었습니다.")
        return

    deleted, failed = delete_videos(youtube, videos)

    print(f"\n=== 삭제 완료 ===")
    print(f"✅ 삭제 성공: {len(deleted)}개")
    print(f"❌ 삭제 실패: {len(failed)}개")

    if failed:
        print("\n실패한 동영상:")
        for item in failed:
            print(f"  - {item['video']['title']}: {item['error']}")


if __name__ == "__main__":
    main()
