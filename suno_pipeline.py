#!/usr/bin/env python3
"""
Suno AI 곡 생성 파이프라인 (CLI)

undetected-chromedriver 기반. Cloudflare Turnstile 우회.

사용법:
  python3 suno_pipeline.py --title "Bossa Nova Test" --style "bossa nova jazz" --lyrics "[Verse] test"
  python3 suno_pipeline.py --title "봄이라고 부를게" --prompt-file songs/01_봄이라고_부를게/suno_prompt_final.md
  python3 suno_pipeline.py --title "테스트" --style "indie pop" --lyrics "[Verse] hello" --skip-drive
"""
from __future__ import annotations

import argparse
import re
import sys

from dotenv import load_dotenv

load_dotenv()

import db
from suno_client import SunoClient, SunoError


def parse_prompt_file(path: str) -> tuple[str, str]:
    """Suno 프롬프트 md 파일에서 Style + Lyrics 추출."""
    with open(path, encoding="utf-8") as f:
        content = f.read()

    style_match = re.search(
        r"## Style of Music\s*```\s*\n(.*?)\n\s*```", content, re.DOTALL
    )
    style = style_match.group(1).strip() if style_match else ""

    lyrics_match = re.search(
        r"## Lyrics\s*\n(.*?)(?=\n---|\n## |\Z)", content, re.DOTALL
    )
    lyrics = lyrics_match.group(1).strip() if lyrics_match else ""

    return style, lyrics


def run_pipeline(
    title: str,
    style: str,
    lyrics: str,
    user_id: int = 0,
    skip_drive: bool = False,
    model: str = "v5.5",
    instrumental: bool = False,
) -> bool:
    """전체 파이프라인 실행.

    Args:
        instrumental: 인스트루멘털 모드 (가사 없이 곡 생성). 기본 False.
    """
    print("=" * 60)
    print(f"🎵 Suno 곡 생성 파이프라인: {title}")
    print("=" * 60)

    client = None
    try:
        # 1. Suno 곡 생성 (generate 안에서 완료 대기까지 포함)
        print("\n[1/3] Suno 곡 생성 중 (2~5분 소요)...")
        client = SunoClient()

        credits = client.get_credits()
        print(f"  크레딧: {credits}")
        if credits == 0:
            print("  ❌ 크레딧 부족!")
            return False

        song_urls = client.generate(
            lyrics=lyrics, style=style, title=title, model=model, instrumental=instrumental
        )
        print(f"  ✅ {len(song_urls)}곡 생성 완료!")
        for url in song_urls:
            print(f"    → {url}")

        # DB 저장 (첫 번째 곡 기준)
        db.init_db()
        song_id = song_urls[0].rstrip("/").split("/")[-1]
        db.save_suno_song(user_id, title, song_id, style, lyrics)

        # 2. 다운로드
        print(f"\n[2/3] 다운로드 ({len(song_urls)}곡)...")
        paths = []
        for i, url in enumerate(song_urls):
            try:
                path = client.download(url)
                paths.append(path)
                print(f"  → [{i+1}] {path} ({path.stat().st_size / 1024 / 1024:.1f}MB)")
            except SunoError as e:
                print(f"  ⚠️  [{i+1}] 다운로드 실패: {e}")

        if not paths:
            print("  ❌ 다운로드된 곡 없음")
            db.update_suno_status(song_id, "error")
            return False

        # 3. Google Drive 업로드
        drive_url = ""
        if not skip_drive:
            print(f"\n[3/3] Google Drive 업로드...")
            try:
                from drive_uploader import DriveUploader, DriveError
                uploader = DriveUploader()
                drive_url = uploader.upload(str(paths[0]))
                print(f"  → {drive_url}")
            except Exception as e:
                print(f"  ⚠️  Drive 업로드 스킵: {e}")
        else:
            print("\n[3/3] Drive 업로드 스킵 (--skip-drive)")

        # DB 업데이트
        db.update_suno_status(
            song_id, "complete",
            local_path=str(paths[0]),
            drive_url=drive_url,
        )

        # 결과
        print("\n" + "=" * 60)
        print("✅ 파이프라인 완료!")
        for p in paths:
            print(f"  📁 {p}")
        if drive_url:
            print(f"  ☁️  Drive: {drive_url}")
        print("=" * 60)
        return True

    except SunoError as e:
        print(f"\n❌ Suno 오류: {e}")
        return False
    except Exception as e:
        print(f"\n❌ 오류: {e}")
        return False
    finally:
        if client:
            client.close()


def main():
    parser = argparse.ArgumentParser(description="Suno AI 곡 생성 파이프라인")
    parser.add_argument("--title", "-t", required=True, help="곡 제목")
    parser.add_argument("--prompt-file", "-f", help="Suno 프롬프트 md 파일 경로")
    parser.add_argument("--style", "-s", help="Style of Music 태그")
    parser.add_argument("--lyrics", "-l", help="가사 텍스트")
    parser.add_argument("--user-id", type=int, default=0, help="사용자 ID")
    parser.add_argument("--skip-drive", action="store_true", help="Drive 업로드 스킵")
    parser.add_argument(
        "--model",
        choices=["v3.5", "v4", "v4.5", "v5", "v5.5"],
        default="v5.5",
        help="Suno 모델 버전 (기본 v5.5)",
    )
    parser.add_argument(
        "--instrumental",
        action="store_true",
        help="인스트루멘털 모드 (가사 없이 곡 생성)",
    )
    args = parser.parse_args()

    if args.prompt_file:
        style, lyrics = parse_prompt_file(args.prompt_file)
        if args.style:
            style = args.style
        if args.lyrics:
            lyrics = args.lyrics
    elif args.style and args.lyrics:
        style = args.style
        lyrics = args.lyrics
    else:
        # 인스트루멘털 모드: --style만 있어도 OK, --lyrics는 선택사항
        if args.instrumental and args.style:
            style = args.style
            lyrics = args.lyrics or ""
        else:
            print("❌ --prompt-file 또는 --style + --lyrics 필요 (인스트루멘털 모드: --style만 필요)")
            sys.exit(1)

    if not style:
        print("❌ Style of Music 태그가 비어있습니다")
        sys.exit(1)

    # 인스트루멘털 모드가 아닐 때만 가사 검증
    if not args.instrumental and not lyrics:
        print("❌ 가사가 비어있습니다 (--instrumental 플래그 없음)")
        sys.exit(1)

    print(f"Style: {style[:80]}...")
    if args.instrumental:
        print(f"Mode: Instrumental (가사 없음)")
    else:
        print(f"Lyrics: {lyrics[:80]}...")

    success = run_pipeline(
        title=args.title,
        style=style,
        lyrics=lyrics,
        user_id=args.user_id,
        skip_drive=args.skip_drive,
        model=args.model,
        instrumental=args.instrumental,
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
