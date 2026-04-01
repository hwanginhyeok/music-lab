#!/usr/bin/env python3
"""
Google Drive → YouTube 자동 게시 파이프라인.

Google Drive에서 오디오 파일을 다운로드하고,
썸네일 생성 → 영상 생성 → YouTube 업로드까지 한 번에 처리.

사용법:
  # Drive 최근 오디오 파일 목록 보기
  python3 scripts/drive_to_youtube.py --list

  # 특정 파일 ID로 업로드
  python3 scripts/drive_to_youtube.py --file-id FILE_ID --title "곡 제목"

  # 최신 파일 자동 선택
  python3 scripts/drive_to_youtube.py --latest --title "곡 제목"

  # 영상까지만 (업로드 안 함)
  python3 scripts/drive_to_youtube.py --latest --title "곡 제목" --skip-upload

  # Drive 폴더 지정
  python3 scripts/drive_to_youtube.py --folder-id FOLDER_ID --latest --title "곡 제목"
"""
from __future__ import annotations

import argparse
import io
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
except ImportError:
    print("[오류] Google API 패키지 필요: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
    sys.exit(1)

PROJECT_ROOT = Path(__file__).parent.parent
TOKEN_PATH = PROJECT_ROOT / "token.json"
OUTPUT_DIR = PROJECT_ROOT / "output"

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/drive.readonly",
]

# YouTube 카테고리: 10 = Music
YOUTUBE_CATEGORY_MUSIC = "10"

AI_DISCLOSURE = (
    "\n\n---\n"
    "이 곡은 AI 도구(Suno, Claude)를 활용하여 제작되었습니다.\n"
    "컨셉 설계, 프롬프트 엔지니어링은 사람이 담당했습니다.\n"
    "This song was created with AI tools (Suno, Claude).\n"
    "#AIMusic #Jazz #Suno"
)


def get_credentials() -> Credentials:
    """OAuth2 토큰 로드 + 자동 갱신."""
    if not TOKEN_PATH.is_file():
        print("[오류] token.json 없음. youtube_upload.py --auth를 먼저 실행하세요.")
        sys.exit(1)

    creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        print("  토큰 갱신 중...")
        creds.refresh(Request())
        TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
    return creds


def list_audio_files(drive, folder_id: str | None = None, limit: int = 20):
    """Drive에서 오디오 파일 목록 조회."""
    q = "mimeType contains 'audio/'"
    if folder_id:
        q += f" and '{folder_id}' in parents"

    results = drive.files().list(
        q=q,
        pageSize=limit,
        orderBy="modifiedTime desc",
        fields="files(id, name, mimeType, modifiedTime, size)",
    ).execute()
    return results.get("files", [])


def download_file(drive, file_id: str, output_path: Path) -> Path:
    """Drive에서 파일 다운로드."""
    request = drive.files().get_media(fileId=file_id)
    with open(output_path, "wb") as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                print(f"  다운로드: {int(status.progress() * 100)}%")
    print(f"  -> {output_path}")
    return output_path


def generate_thumbnail(title: str, subtitle: str, output_path: Path) -> Path:
    """썸네일 생성 (generate_thumbnail.py 호출)."""
    # Pillow 직접 사용
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("  [경고] Pillow 없음. 썸네일 생성 건너뜀.")
        return None

    width, height = 1280, 720
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)

    # 어두운 그라데이션 배경
    for y in range(height):
        r = int(15 + (25 - 15) * y / height)
        g = int(15 + (20 - 15) * y / height)
        b = int(30 + (45 - 30) * y / height)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # 폰트 로드
    font_large = None
    font_small = None
    font_paths = [
        "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for fp in font_paths:
        if Path(fp).exists():
            try:
                font_large = ImageFont.truetype(fp, 64)
                font_small = ImageFont.truetype(fp, 32)
                break
            except Exception:
                continue

    if not font_large:
        font_large = ImageFont.load_default()
        font_small = font_large

    # 제목 (중앙)
    bbox = draw.textbbox((0, 0), title, font=font_large)
    tw = bbox[2] - bbox[0]
    draw.text(((width - tw) / 2, height / 2 - 60), title, fill=(255, 255, 255), font=font_large)

    # 서브타이틀
    bbox2 = draw.textbbox((0, 0), subtitle, font=font_small)
    tw2 = bbox2[2] - bbox2[0]
    draw.text(((width - tw2) / 2, height / 2 + 30), subtitle, fill=(180, 180, 200), font=font_small)

    img.save(str(output_path), "JPEG", quality=90)
    print(f"  썸네일: {output_path}")
    return output_path


def create_video(audio_path: Path, thumbnail_path: Path, output_path: Path) -> Path:
    """ffmpeg로 이미지+오디오 → MP4."""
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(thumbnail_path),
        "-i", str(audio_path),
        "-c:v", "libx264", "-tune", "stillimage",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:-1:-1:color=black",
        str(output_path),
    ]
    print("  영상 생성 중...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        print(f"  [오류] ffmpeg 실패: {result.stderr[:300]}")
        return None
    print(f"  -> {output_path}")
    return output_path


def upload_to_youtube(creds, video_path: Path, title: str, description: str, tags: list[str], public: bool = False):
    """YouTube 업로드."""
    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": title,
            "description": description + AI_DISCLOSURE,
            "tags": tags,
            "categoryId": YOUTUBE_CATEGORY_MUSIC,
        },
        "status": {
            "privacyStatus": "public" if public else "unlisted",
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(str(video_path), mimetype="video/mp4", resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    print("  YouTube 업로드 중...")
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"  업로드: {int(status.progress() * 100)}%")

    video_id = response["id"]
    url = f"https://youtu.be/{video_id}"
    print(f"  업로드 완료: {url}")
    return url


def main():
    parser = argparse.ArgumentParser(description="Google Drive → YouTube 자동 게시")
    parser.add_argument("--list", action="store_true", help="Drive 오디오 파일 목록")
    parser.add_argument("--file-id", help="Drive 파일 ID")
    parser.add_argument("--latest", action="store_true", help="최신 오디오 파일 자동 선택")
    parser.add_argument("--folder-id", help="Drive 폴더 ID")
    parser.add_argument("--title", help="곡 제목", default="Jazz")
    parser.add_argument("--subtitle", help="영문 서브타이틀", default="AI Jazz")
    parser.add_argument("--tags", help="태그 (쉼표 구분)", default="jazz,AI,music,suno")
    parser.add_argument("--description", help="영상 설명", default="")
    parser.add_argument("--public", action="store_true", help="바로 공개 (기본: unlisted)")
    parser.add_argument("--skip-upload", action="store_true", help="영상까지만, 업로드 스킵")
    args = parser.parse_args()

    creds = get_credentials()
    drive = build("drive", "v3", credentials=creds)

    # 목록 모드
    if args.list:
        files = list_audio_files(drive, args.folder_id)
        if not files:
            print("오디오 파일 없음")
        else:
            print(f"\n{'이름':<40} {'수정일':<12} {'ID'}")
            print("-" * 80)
            for f in files:
                size_mb = int(f.get("size", 0)) / 1024 / 1024
                print(f"{f['name']:<40} {f['modifiedTime'][:10]:<12} {f['id']}")
        return

    # 파일 선택
    file_id = args.file_id
    file_name = "audio"
    if args.latest:
        files = list_audio_files(drive, args.folder_id, limit=1)
        if not files:
            print("[오류] Drive에 오디오 파일 없음")
            sys.exit(1)
        file_id = files[0]["id"]
        file_name = files[0]["name"]
        print(f"  최신 파일: {file_name}")

    if not file_id:
        print("[오류] --file-id 또는 --latest를 지정하세요. --list로 목록 확인.")
        sys.exit(1)

    # 출력 디렉토리
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 파일 확장자 추출
    ext = Path(file_name).suffix or ".wav"
    audio_path = OUTPUT_DIR / f"audio{ext}"
    thumbnail_path = OUTPUT_DIR / "thumbnail.jpg"
    video_path = OUTPUT_DIR / "output.mp4"

    print("=" * 60)
    print(f"  Drive → YouTube 파이프라인")
    print(f"  제목: {args.title}")
    print(f"  파일: {file_name}")
    print("=" * 60)

    # 1. 다운로드
    print("\n[1/4] Drive에서 다운로드...")
    download_file(drive, file_id, audio_path)

    # 2. 썸네일
    print("\n[2/4] 썸네일 생성...")
    thumb = generate_thumbnail(args.title, args.subtitle, thumbnail_path)

    # 3. 영상 생성
    print("\n[3/4] 영상 생성...")
    if thumb:
        video = create_video(audio_path, thumbnail_path, video_path)
    else:
        print("  [오류] 썸네일 없어서 영상 생성 불가")
        sys.exit(1)

    if not video:
        sys.exit(1)

    # 4. YouTube 업로드
    if args.skip_upload:
        print("\n[4/4] 업로드 스킵 (--skip-upload)")
    else:
        print("\n[4/4] YouTube 업로드...")
        desc = args.description or f"{args.title} - {args.subtitle}"
        tags = [t.strip() for t in args.tags.split(",")]
        url = upload_to_youtube(creds, video_path, args.title, desc, tags, args.public)

    print("\n" + "=" * 60)
    print("  완료!")
    print(f"  오디오: {audio_path}")
    print(f"  영상: {video_path}")
    if not args.skip_upload:
        print(f"  YouTube: {url}")
    print("=" * 60)


if __name__ == "__main__":
    main()
