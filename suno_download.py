#!/usr/bin/env python3
"""
Suno 곡 다운로드 파이프라인 — API 직접 호출 방식

Clerk JWT 인증 → studio-api-prod.suno.com API로 곡 목록 조회 → WAV/MP3 다운로드.

사용법:
  python3 suno_download.py --list                    # 내 곡 목록
  python3 suno_download.py --all                     # 전체 다운로드
  python3 suno_download.py --song-id UUID            # 개별 다운로드
  python3 suno_download.py --all --upload-youtube     # 다운로드 + YouTube 업로드
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

import requests

logger = logging.getLogger("suno-download")

# .env 로드
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

import db

SUNO_DIR = Path("data/suno")
SUNO_DIR.mkdir(parents=True, exist_ok=True)


class SunoAuthError(Exception):
    """Suno 인증 실패 예외. 쿠키 만료, JWT 갱신 실패 등."""


class SunoAPI:
    """Clerk JWT 인증 기반 Suno API 클라이언트."""

    BASE_URL = "https://studio-api-prod.suno.com"
    CLERK_URL = "https://clerk.suno.com"

    def __init__(self):
        self.cookie = os.getenv("SUNO_COOKIE", "")
        if not self.cookie:
            logger.error("SUNO_COOKIE 환경변수 필요")
            raise SunoAuthError("SUNO_COOKIE 환경변수가 설정되지 않았습니다")
        self._jwt = None
        self._session = requests.Session()

    def _get_jwt(self) -> str:
        """Clerk에서 JWT 토큰 갱신."""
        if self._jwt:
            return self._jwt

        s = requests.Session()
        s.headers["Cookie"] = self.cookie
        s.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

        resp = s.get(f"{self.CLERK_URL}/v1/client?_clerk_js_version=5.117.0")
        data = resp.json()["response"]
        sessions = data.get("sessions", [])
        if not sessions:
            logger.error("Suno 세션 없음 — 쿠키 만료. 브라우저에서 재로그인 필요.")
            raise SunoAuthError("Suno 세션 없음 — 쿠키 만료. 브라우저에서 재로그인 필요")

        sid = sessions[0]["id"]
        token_resp = s.post(f"{self.CLERK_URL}/v1/client/sessions/{sid}/tokens?_clerk_js_version=5.117.0")
        self._jwt = token_resp.json().get("jwt", "")
        if not self._jwt:
            logger.error("JWT 토큰 갱신 실패")
            raise SunoAuthError("JWT 토큰 갱신 실패")

        self._session.headers.update({
            "Authorization": f"Bearer {self._jwt}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Origin": "https://suno.com",
            "Referer": "https://suno.com/",
        })
        return self._jwt

    def get_credits(self) -> int:
        """남은 크레딧."""
        self._get_jwt()
        r = self._session.get(f"{self.BASE_URL}/api/billing/info/")
        if r.status_code == 200:
            return r.json().get("total_credits_left", r.json().get("credits", -1))
        return -1

    def get_songs(self, page: int = 0) -> list[dict]:
        """내 곡 목록."""
        self._get_jwt()
        r = self._session.post(f"{self.BASE_URL}/api/feed/v3", json={"page": page})
        if r.status_code != 200:
            print(f"❌ 곡 목록 조회 실패: {r.status_code}")
            return []
        data = r.json()
        return data if isinstance(data, list) else data.get("clips", [])

    def get_song(self, song_id: str) -> dict | None:
        """개별 곡 정보."""
        self._get_jwt()
        r = self._session.get(f"{self.BASE_URL}/api/clip/{song_id}")
        if r.status_code == 200:
            return r.json()
        return None

    def download(self, song: dict, output_dir: Path = SUNO_DIR) -> Path | None:
        """곡 다운로드. WAV 우선, 없으면 MP3."""
        audio_url = song.get("audio_url")
        if not audio_url:
            print(f"  ⚠️  오디오 URL 없음: {song.get('id', '?')}")
            return None

        song_id = song.get("id", "unknown")
        title = song.get("title", "").strip() or song_id
        safe_title = "".join(c for c in title if c.isalnum() or c in " ._-").strip()

        ext = "mp3"
        if ".wav" in audio_url:
            ext = "wav"

        filename = f"{safe_title}_{song_id[:8]}.{ext}"
        path = output_dir / filename

        if path.exists():
            print(f"  ⏭️  이미 존재: {path}")
            return path

        resp = requests.get(audio_url, timeout=60)
        resp.raise_for_status()
        path.write_bytes(resp.content)
        print(f"  ✅ {path} ({len(resp.content) / 1024 / 1024:.1f}MB)")

        # 커버 이미지 다운로드
        self.download_cover(song, output_dir)

        return path

    def download_cover(self, song: dict, output_dir: Path = SUNO_DIR) -> Path | None:
        """Suno AI 생성 커버 이미지 다운로드."""
        image_url = song.get("image_large_url") or song.get("image_url")
        if not image_url:
            return None

        song_id = song.get("id", "unknown")
        title = song.get("title", "").strip() or song_id
        safe_title = "".join(c for c in title if c.isalnum() or c in " ._-").strip()
        cover_path = output_dir / f"{safe_title}_{song_id[:8]}_cover.jpeg"

        if cover_path.exists():
            return cover_path

        resp = requests.get(image_url, timeout=30)
        if resp.status_code == 200:
            cover_path.write_bytes(resp.content)
            print(f"  🎨 커버: {cover_path}")
            return cover_path
        return None


def cmd_list(api: SunoAPI):
    """곡 목록 출력."""
    credits = api.get_credits()
    print(f"크레딧: {credits}\n")

    songs = api.get_songs()
    print(f"곡 수: {len(songs)}\n")
    for i, s in enumerate(songs):
        title = s.get("title", "무제")
        status = s.get("status", "?")
        sid = s.get("id", "?")[:8]
        duration = s.get("duration", 0) or 0
        icon = "✅" if status == "complete" else "⏳"
        print(f"  {icon} [{i+1}] {title} ({duration:.0f}초) — {sid}...")


def cmd_download(api: SunoAPI, song_id: str | None = None, all_songs: bool = False, upload_youtube: bool = False):
    """곡 다운로드 (+ 선택적 YouTube 업로드)."""
    db.init_db()

    if song_id:
        song = api.get_song(song_id)
        if not song:
            print(f"❌ 곡을 찾을 수 없습니다: {song_id}")
            return
        songs = [song]
    elif all_songs:
        songs = [s for s in api.get_songs() if s.get("status") == "complete"]
    else:
        print("❌ --song-id 또는 --all 필요")
        return

    print(f"다운로드할 곡: {len(songs)}개\n")

    downloaded = []
    for s in songs:
        title = s.get("title", "무제")
        print(f"📥 {title}...")
        path = api.download(s)
        if path:
            downloaded.append((s, path))
            # DB 저장
            db.save_suno_song(
                user_id=0,
                title=title,
                song_id=s.get("id", ""),
                style=s.get("metadata", {}).get("tags", ""),
                lyrics=s.get("metadata", {}).get("prompt", ""),
            )
            db.update_suno_status(
                s.get("id", ""),
                "complete",
                local_path=str(path),
            )

    print(f"\n{'='*60}")
    print(f"✅ {len(downloaded)}/{len(songs)}곡 다운로드 완료")
    for s, p in downloaded:
        print(f"  📁 {p}")

    # YouTube 업로드
    if upload_youtube and downloaded:
        print(f"\n🎬 YouTube 업로드...")
        for s, p in downloaded:
            try:
                upload_to_youtube(s, p)
            except Exception as e:
                print(f"  ⚠️  YouTube 업로드 실패: {e}")


def upload_to_youtube(song: dict, audio_path: Path):
    """YouTube에 곡 업로드."""
    sys.path.insert(0, str(Path(__file__).parent / "scripts"))
    from youtube_upload import get_credentials

    creds = get_credentials()
    if not creds:
        print("  ❌ Google 인증 실패 — token.json 확인 필요")
        return

    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    youtube = build("youtube", "v3", credentials=creds)

    title = song.get("title", "Untitled") + " | AI Music by Suno"
    lyrics = song.get("metadata", {}).get("prompt", "")
    tags_str = song.get("metadata", {}).get("tags", "")
    description = (
        f"{lyrics}\n\n"
        f"🎵 Made with Suno AI\n🏷️ {tags_str}\n\n"
        "---\n"
        "이 곡은 AI 도구(Suno, Claude)를 활용하여 제작되었습니다.\n"
        "작사, 작곡 컨셉 설계는 사람이, 음원 생성은 AI가 담당했습니다."
    )
    tags = [t.strip() for t in tags_str.split(",") if t.strip()]
    tags.extend(["AI Music", "Suno", "AI Generated"])

    # 영상 생성 (Ken Burns 효과 + 가사 자막)
    mp4_path = audio_path.with_suffix(".mp4")
    if not mp4_path.exists():
        cover_path = audio_path.with_name(audio_path.stem + "_cover.jpeg")
        lyrics_text = song.get("metadata", {}).get("prompt", "")

        # 가사 → SRT 자막 생성
        srt_path = None
        if lyrics_text:
            scripts_dir = str(Path(__file__).parent / "scripts")
            if scripts_dir not in sys.path:
                sys.path.insert(0, scripts_dir)
            from lyrics_to_srt import generate_srt
            from create_video import get_audio_duration
            duration = get_audio_duration(audio_path)
            if duration > 0:
                srt_path = audio_path.with_suffix(".srt")
                generate_srt(lyrics_text, duration, srt_path)

        # create_video로 영상 생성
        scripts_dir = str(Path(__file__).parent / "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        from create_video import create_video
        song_title = song.get("title", "Untitled")
        print("  🎬 영상 생성 (Ken Burns + 자막)...")
        create_video(
            image_path=cover_path if cover_path.exists() else Path("nonexistent"),
            audio_path=audio_path,
            output_path=mp4_path,
            title=song_title,
            ken_burns=cover_path.exists(),
            lyrics_srt=srt_path,
        )

    media = MediaFileUpload(str(mp4_path), mimetype="video/mp4", resumable=True)

    print(f"  📤 {title[:60]}...")
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title[:100],
                "description": description[:5000],
                "tags": tags[:30],
                "categoryId": "10",
                "defaultLanguage": "ko",
            },
            "status": {
                "privacyStatus": "unlisted",
                "selfDeclaredMadeForKids": False,
            },
        },
        media_body=media,
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"  진행: {int(status.progress() * 100)}%")

    video_id = response.get("id")
    if video_id:
        url = f"https://youtube.com/watch?v={video_id}"
        print(f"  ✅ {url}")
        db.update_suno_status(song.get("id", ""), "complete", drive_url=url)

        # 썸네일 설정
        cover_path = audio_path.with_name(audio_path.stem + "_cover.jpeg")
        if cover_path.exists():
            try:
                youtube.thumbnails().set(
                    videoId=video_id,
                    media_body=MediaFileUpload(str(cover_path), mimetype="image/jpeg"),
                ).execute()
                print(f"  🎨 썸네일 설정 완료")
            except Exception as e:
                print(f"  ⚠️  썸네일 설정 실패: {e}")
    else:
        print("  ❌ 업로드 실패")


def main():
    parser = argparse.ArgumentParser(description="Suno 곡 다운로드")
    parser.add_argument("--list", action="store_true", help="내 곡 목록")
    parser.add_argument("--all", action="store_true", help="전체 다운로드")
    parser.add_argument("--song-id", help="개별 곡 ID")
    parser.add_argument("--upload-youtube", action="store_true", help="YouTube 업로드")
    args = parser.parse_args()

    api = SunoAPI()

    if args.list:
        cmd_list(api)
    elif args.all or args.song_id:
        cmd_download(api, song_id=args.song_id, all_songs=args.all, upload_youtube=args.upload_youtube)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
