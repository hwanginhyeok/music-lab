#!/usr/bin/env python3
"""
YouTube Data API v3로 영상 업로드.

OAuth2 인증 (client_secrets.json -> 브라우저 인증 -> token.json 저장 -> 자동 갱신).
메타데이터는 concept.md / manifest.json에서 자동 추출하거나 CLI 옵션으로 직접 지정.

사용법:
  # 곡 디렉토리 지정 (자동 탐색)
  python3 scripts/youtube_upload.py songs/01_봄이라고_부를게/

  # 옵션 직접 지정
  python3 scripts/youtube_upload.py songs/01_봄이라고_부를게/ \\
      --title "봄이라고 부를게" --description "AI로 만든 인디 팝" --tags "jazz,korean"

  # 바로 공개
  python3 scripts/youtube_upload.py songs/01_봄이라고_부를게/ --public

필요 패키지:
  pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Google API 임포트 (미설치 시 안내)
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


PROJECT_ROOT = Path(__file__).parent.parent

# OAuth2 범위
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

# YouTube 카테고리: 10 = Music
YOUTUBE_CATEGORY_MUSIC = "10"

# AI 콘텐츠 공개 문구
AI_DISCLOSURE = (
    "\n\n---\n"
    "이 곡은 AI 도구(Suno, Claude)를 활용하여 제작되었습니다.\n"
    "작사, 작곡 컨셉 설계는 사람이, 음원 생성은 AI가 담당했습니다.\n"
    "This song was created with AI tools (Suno, Claude).\n"
    "Human: concept, lyrics, direction | AI: music generation."
)


def get_credentials() -> Credentials | None:
    """OAuth2 인증 처리. token.json 캐시 사용, 만료 시 자동 갱신."""
    token_path = PROJECT_ROOT / "token.json"
    secrets_path = PROJECT_ROOT / "client_secrets.json"

    creds = None

    # 기존 토큰 로드
    if token_path.is_file():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    # 토큰 없거나 만료 시
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("  토큰 갱신 중...")
            creds.refresh(Request())
        else:
            if not secrets_path.is_file():
                print_setup_guide()
                return None

            print("  브라우저에서 Google 인증을 진행합니다...")
            flow = InstalledAppFlow.from_client_secrets_file(str(secrets_path), SCOPES)
            creds = flow.run_local_server(port=0)

        # 토큰 저장
        token_path.write_text(creds.to_json(), encoding="utf-8")
        print(f"  토큰 저장: {token_path}")

    return creds


def print_setup_guide():
    """YouTube API 설정 안내."""
    print()
    print("=" * 60)
    print("  YouTube API 설정 안내")
    print("=" * 60)
    print()
    print("  1. Google Cloud Console (https://console.cloud.google.com/) 접속")
    print("  2. 프로젝트 생성 또는 선택")
    print("  3. YouTube Data API v3 활성화")
    print("     - API 및 서비스 > 라이브러리 > YouTube Data API v3")
    print("  4. OAuth 2.0 클라이언트 ID 생성")
    print("     - API 및 서비스 > 사용자 인증 정보 > OAuth 2.0 클라이언트 ID")
    print("     - 애플리케이션 유형: 데스크톱 앱")
    print("  5. JSON 다운로드 -> 프로젝트 루트에 client_secrets.json 으로 저장")
    print(f"     - 경로: {PROJECT_ROOT / 'client_secrets.json'}")
    print()
    print("  6. 최초 실행 시 브라우저에서 Google 계정 인증")
    print("     - token.json이 자동 생성되어 이후 자동 갱신")
    print()
    print("  참고: client_secrets.json과 token.json은 .gitignore에 포함되어 있습니다.")
    print("=" * 60)


def load_metadata_from_manifest(song_dir: Path) -> dict:
    """manifest.json에서 메타데이터 추출."""
    manifest_path = song_dir / "manifest.json"
    meta = {"title": "", "subgenre": "", "theme": ""}
    if manifest_path.is_file():
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            meta["title"] = data.get("title", "")
            meta["subgenre"] = data.get("subgenre", "")
            meta["theme"] = data.get("theme", "")
        except (json.JSONDecodeError, KeyError):
            pass
    return meta


def extract_description_from_concept(song_dir: Path) -> str:
    """concept.md에서 곡 설명 추출."""
    concept_path = song_dir / "concept.md"
    if not concept_path.is_file():
        return ""

    text = concept_path.read_text(encoding="utf-8")

    # 핵심 컨셉 섹션 추출
    match = re.search(r"##\s*핵심\s*컨셉\s*\n(.*?)(?=\n##|\Z)", text, re.DOTALL)
    if match:
        desc = match.group(1).strip()
        # 너무 길면 자르기
        if len(desc) > 500:
            desc = desc[:500] + "..."
        return desc

    # 첫 번째 ## 이후 내용
    match = re.search(r"##.*?\n(.*?)(?=\n##|\Z)", text, re.DOTALL)
    if match:
        return match.group(1).strip()[:500]

    return ""


def upload_video(
    video_path: Path,
    title: str,
    description: str,
    tags: list[str],
    thumbnail_path: Path | None = None,
    public: bool = False,
) -> str | None:
    """YouTube에 영상 업로드.

    Args:
        video_path: MP4 영상 파일 경로
        title: 영상 제목
        description: 영상 설명
        tags: 태그 목록
        thumbnail_path: 썸네일 이미지 경로
        public: True면 공개, False면 미등록(unlisted)

    Returns:
        업로드된 영상 ID (실패 시 None)
    """
    creds = get_credentials()
    if not creds:
        return None

    youtube = build("youtube", "v3", credentials=creds)

    # AI 콘텐츠 공개 문구 추가
    full_description = description + AI_DISCLOSURE

    privacy = "public" if public else "unlisted"

    body = {
        "snippet": {
            "title": title,
            "description": full_description,
            "tags": tags,
            "categoryId": YOUTUBE_CATEGORY_MUSIC,
            "defaultLanguage": "ko",
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        resumable=True,
        chunksize=10 * 1024 * 1024,  # 10MB 청크
    )

    print(f"  업로드 중: {video_path.name} ({privacy})...")

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            progress = int(status.progress() * 100)
            print(f"  진행: {progress}%")

    video_id = response.get("id")
    video_url = f"https://www.youtube.com/watch?v={video_id}"

    print(f"  업로드 완료!")
    print(f"  영상 ID: {video_id}")
    print(f"  URL: {video_url}")
    print(f"  상태: {privacy}")

    # 썸네일 설정
    if thumbnail_path and thumbnail_path.is_file():
        try:
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(str(thumbnail_path), mimetype="image/jpeg"),
            ).execute()
            print(f"  썸네일 설정 완료: {thumbnail_path.name}")
        except Exception as e:
            print(f"  [경고] 썸네일 설정 실패: {e}")
            print("  (YouTube 계정 인증이 필요할 수 있습니다)")

    return video_id


def update_manifest(song_dir: Path, video_id: str) -> None:
    """manifest.json에 YouTube ID 기록."""
    manifest_path = song_dir / "manifest.json"
    if manifest_path.is_file():
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            data["youtube_id"] = video_id
            data["status"] = "published"
            manifest_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"  manifest.json 업데이트: status=published, youtube_id={video_id}")
        except (json.JSONDecodeError, KeyError):
            pass


def main():
    parser = argparse.ArgumentParser(
        description="YouTube Data API v3로 영상 업로드",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="예시:\n"
               '  python3 scripts/youtube_upload.py songs/01_봄이라고_부를게/\n'
               '  python3 scripts/youtube_upload.py songs/01_봄이라고_부를게/ '
               '--title "봄이라고 부를게" --public\n',
    )
    parser.add_argument("song_dir", help="곡 디렉토리 경로")
    parser.add_argument("--title", help="영상 제목")
    parser.add_argument("--description", help="영상 설명")
    parser.add_argument("--tags", help="태그 (쉼표 구분)")
    parser.add_argument("--video", help="영상 파일 경로 (기본: video/output.mp4)")
    parser.add_argument("--thumbnail", help="썸네일 경로 (기본: video/thumbnail.jpg)")
    parser.add_argument("--public", action="store_true", help="바로 공개 (기본: unlisted)")
    args = parser.parse_args()

    song_dir = Path(args.song_dir).resolve()
    if not song_dir.is_dir():
        print(f"[오류] 곡 디렉토리 없음: {song_dir}")
        sys.exit(1)

    # client_secrets.json 확인
    if not (PROJECT_ROOT / "client_secrets.json").is_file():
        print_setup_guide()
        sys.exit(1)

    # 경로 결정
    video_path = Path(args.video) if args.video else song_dir / "video" / "output.mp4"
    thumbnail_path = Path(args.thumbnail) if args.thumbnail else song_dir / "video" / "thumbnail.jpg"

    if not video_path.is_file():
        print(f"[오류] 영상 파일 없음: {video_path}")
        print("  create_video.py를 먼저 실행하세요.")
        sys.exit(1)

    # 메타데이터 결정
    meta = load_metadata_from_manifest(song_dir)

    title = args.title or meta["title"] or song_dir.name
    description = args.description or extract_description_from_concept(song_dir) or f"{title} - AI 음악 프로젝트"

    if args.tags:
        tags = [t.strip() for t in args.tags.split(",")]
    else:
        tags = ["AI Music", "AI Generated", "Korean"]
        if meta["subgenre"]:
            tags.append(meta["subgenre"].title())

    if not thumbnail_path.is_file():
        thumbnail_path = None

    print("=" * 60)
    print("  YouTube 업로드")
    print(f"  제목: {title}")
    print(f"  영상: {video_path}")
    print(f"  썸네일: {thumbnail_path or '(없음)'}")
    print(f"  태그: {', '.join(tags)}")
    print(f"  공개: {'공개(public)' if args.public else '미등록(unlisted)'}")
    print("=" * 60)

    video_id = upload_video(
        video_path=video_path,
        title=title,
        description=description,
        tags=tags,
        thumbnail_path=thumbnail_path,
        public=args.public,
    )

    if video_id:
        update_manifest(song_dir, video_id)
        print(f"\n  업로드 완료: https://www.youtube.com/watch?v={video_id}")
    else:
        print("\n  업로드 실패.")
        sys.exit(1)


if __name__ == "__main__":
    main()
