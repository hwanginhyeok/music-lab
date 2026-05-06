#!/usr/bin/env python3
"""
Music Lab 재즈 EP 앨범 발주 러너

Track 01 PoC #6 검증 완료. 나머지 8곡 자동화 발주.

사용법:
  python3 scripts/generate_album.py
  python3 scripts/generate_album.py --start-from 03
  python3 scripts/generate_album.py --only 06
"""
from __future__ import annotations

import argparse
import json
import random
import re
import shutil
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

# music-lab 루트를 sys.path에 추가 (suno_client/db/suno_download import 가능하게)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

load_dotenv()

from suno_client import SunoClient, SunoError

# 앨범 메타데이터
ALBUM_TITLE = "왜 그리 울고만 있어요? 그리움만 쌓이게"
ALBUM_DIR = Path("songs/14_geuriumi")

# 발주할 트랙 목록 (사용자 지정 순서)
TRACKS_TO_GENERATE = [
    {"track": "02_reflection", "instrumental": True, "has_lyrics": False},
    {"track": "03_quiet_conversation", "instrumental": True, "has_lyrics": False},
    {"track": "05_solitude", "instrumental": True, "has_lyrics": False},
    {"track": "07_after_the_words", "instrumental": True, "has_lyrics": False},
    {"track": "08_late_night", "instrumental": True, "has_lyrics": False},
    {"track": "09_reprise", "instrumental": True, "has_lyrics": False},
    {"track": "04_saxophone", "instrumental": True, "has_lyrics": False},
    {"track": "06_vocal", "instrumental": False, "has_lyrics": True},
]

# 캡차 카운터
captcha_count = 0


@dataclass
class TrackResult:
    """트랙 발주 결과."""
    track: str
    title: str
    success: bool
    error: str | None = None
    song_ids: list[str] | None = None
    suno_urls: list[str] | None = None
    duration: str | None = None
    credits_after: int | None = None
    credits_consumed: int | None = None


def parse_prompt_file(track_folder: Path) -> tuple[str, str]:
    """suno_prompt.md에서 제목과 Style 추출.

    Returns:
        (title, style)
    """
    prompt_file = track_folder / "suno_prompt.md"
    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_file}")

    content = prompt_file.read_text(encoding="utf-8")

    # 제목 추출: "# Track NN — 제목"
    title_match = re.search(r"# Track \d+ — (.+)", content)
    if not title_match:
        raise ValueError(f"Title not found in {prompt_file}")
    title = title_match.group(1).strip()

    # Style 추출: "## Style of Music" 코드블록
    style_match = re.search(r"## Style of Music\s*```\s*\n(.*?)\n\s*```", content, re.DOTALL)
    if not style_match:
        raise ValueError(f"Style not found in {prompt_file}")
    style = style_match.group(1).strip()

    return title, style


def load_lyrics(track_folder: Path) -> str:
    """lyrics_v1_en.md 전체 본문 읽기."""
    lyrics_file = track_folder / "lyrics_v1_en.md"
    if not lyrics_file.exists():
        raise FileNotFoundError(f"Lyrics file not found: {lyrics_file}")
    return lyrics_file.read_text(encoding="utf-8")


def generate_track(
    client: SunoClient,
    track_info: dict,
    start_credits: int,
) -> TrackResult:
    """단일 트랙 발주.

    Args:
        client: SunoClient 인스턴스
        track_info: 트랙 정보 dict
        start_credits: 발주 전 크레딧 (차감량 계산용)

    Returns:
        TrackResult
    """
    track = track_info["track"]
    instrumental = track_info["instrumental"]
    has_lyrics = track_info["has_lyrics"]

    track_folder = ALBUM_DIR / "tracks" / track
    track_num = track.split("_")[0]

    try:
        # 1. 프롬프트 파싱
        title, style = parse_prompt_file(track_folder)
        print(f"\n{'='*60}", flush=True)
        print(f"Track {track_num} — {title}", flush=True)
        print(f"{'='*60}", flush=True)
        print(f"Folder: {track_folder}", flush=True)
        print(f"Style: {style[:100]}...", flush=True)

        # 2. 가사 로드 (보컬 트랙만)
        lyrics = ""
        if has_lyrics:
            lyrics = load_lyrics(track_folder)
            print(f"Lyrics: {len(lyrics)} chars (first 100: {lyrics[:100]}...)", flush=True)
        else:
            print("Mode: Instrumental", flush=True)

        # 3. Suno 발주 (시간 측정으로 캡차 추정)
        gen_start = time.time()
        song_urls = client.generate(
            lyrics=lyrics,
            style=style,
            title=title,
            model="v5.5",
            instrumental=instrumental,
        )
        gen_duration = time.time() - gen_start

        # 5분 이상 소요 시 캡차로 추정
        global captcha_count
        if gen_duration > 300:
            captcha_count += 1
            print(f"⚠️  Generation took {gen_duration:.0f}s — possible captcha", flush=True)

        print(f"✅ Generated {len(song_urls)} songs", flush=True)
        for url in song_urls:
            print(f"   → {url}", flush=True)

        # 4. 크레딧 확인
        credits_after = client.get_credits()
        credits_consumed = start_credits - credits_after
        print(f"💰 Credits: {start_credits} → {credits_after} (consumed: {credits_consumed})", flush=True)

        # 5. 다운로드
        print("\n📥 Downloading...", flush=True)
        downloaded_paths = []
        song_ids = []
        for url in song_urls:
            try:
                path = client.download(url)
                downloaded_paths.append(path)
                song_id = url.rstrip("/").split("/")[-1]
                song_ids.append(song_id)
                size_mb = path.stat().st_size / 1024 / 1024
                print(f"   → {path.name} ({size_mb:.1f}MB)", flush=True)
            except SunoError as e:
                print(f"   ⚠️  Download failed: {e}", flush=True)

        if len(downloaded_paths) < 2:
            raise SunoError(f"Expected 2 downloads, got {len(downloaded_paths)}")

        # 6. 파일 복사 (raw/v1.mp3, raw/v2.mp3)
        raw_dir = track_folder / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)

        v1_path = raw_dir / "v1.mp3"
        v2_path = raw_dir / "v2.mp3"

        shutil.copy2(downloaded_paths[0], v1_path)
        shutil.copy2(downloaded_paths[1], v2_path)
        print(f"\n📁 Copied to:", flush=True)
        print(f"   → {v1_path}", flush=True)
        print(f"   → {v2_path}", flush=True)

        # 7. meta.json 작성
        meta = {
            "track": track,
            "title": title,
            "album": ALBUM_TITLE,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "method": "suno_pipeline.py + (C) Advanced 모드 + 빈 lyrics input event"
            if instrumental
            else "suno_pipeline.py + (C) Advanced 보컬 경로",
            "model": "v5.5",
            "instrumental": instrumental,
            "style": style,
            "credits_consumed": credits_consumed,
            "credits_after": credits_after,
            "versions": {
                "v1": {
                    "song_id": song_ids[0],
                    "suno_url": song_urls[0],
                    "size_bytes": downloaded_paths[0].stat().st_size,
                },
                "v2": {
                    "song_id": song_ids[1],
                    "suno_url": song_urls[1],
                    "size_bytes": downloaded_paths[1].stat().st_size,
                },
            },
        }

        meta_file = raw_dir / "meta.json"
        meta_file.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"📄 Meta: {meta_file}", flush=True)

        # 8. 진행 보고
        # 곡 길이 추정 (파일 크기로 대체)
        duration_est = f"{downloaded_paths[0].stat().st_size / 1024 / 1024:.1f}MB"
        print(
            f"\n✅ Track {track_num} {title} — v1/v2 / Credits {credits_after} / Duration ~{duration_est}",
            flush=True
        )

        return TrackResult(
            track=track,
            title=title,
            success=True,
            song_ids=song_ids,
            suno_urls=song_urls,
            duration=duration_est,
            credits_after=credits_after,
            credits_consumed=credits_consumed,
        )

    except Exception as e:
        print(f"\n❌ Track {track_num} failed: {e}", flush=True)
        return TrackResult(
            track=track,
            title=title if 'title' in locals() else track,
            success=False,
            error=str(e),
        )


def print_final_report(
    results: list[TrackResult],
    initial_credits: int,
    final_credits: int,
):
    """종합 보고 출력."""
    print("\n" + "=" * 60)
    print("🎵 재즈 EP 9곡 발주 결과")
    print("=" * 60)

    # Track 01 (PoC 완료)
    print("✅ Track 01 Theme Statement (PoC #6 검증 완료, 기존)", flush=True)

    # 발주한 8곡
    success_count = 0
    failed_tracks = []
    for r in results:
        track_num = r.track.split("_")[0]
        if r.success:
            song_id_short = r.song_ids[0][:8] if r.song_ids else "N/A"
            print(f"✅ Track {track_num} {r.title} — {r.duration} / {song_id_short}", flush=True)
            success_count += 1
        else:
            print(f"❌ Track {track_num} {r.title} — {r.error}", flush=True)
            failed_tracks.append(track_num)

    print("=" * 60)
    total_consumed = initial_credits - final_credits
    print(f"- 캡차 발생: 총 {captcha_count}회", flush=True)
    print(f"- 크레딧: {initial_credits} → {final_credits} (총 {total_consumed} 차감)", flush=True)
    if failed_tracks:
        print(f"- 실패 트랙: {failed_tracks}", flush=True)
    print(f"- 결과 디렉토리: {ALBUM_DIR}/tracks/{{NN}}/raw/", flush=True)
    print("=" * 60, flush=True)

    # 성공 여부 반환
    return len(failed_tracks) == 0


def main():
    parser = argparse.ArgumentParser(description="Music Lab 재즈 EP 앨범 발주 러너")
    parser.add_argument(
        "--start-from",
        type=str,
        help="시작 트랙 번호 (예: 03)",
    )
    parser.add_argument(
        "--only",
        type=str,
        help="단일 트랙만 발주 (예: 06)",
    )
    args = parser.parse_args()

    # 트랙 필터링
    tracks = TRACKS_TO_GENERATE.copy()

    if args.only:
        only_track = f"{args.only}_"
        tracks = [t for t in tracks if t["track"].startswith(only_track)]
        if not tracks:
            print(f"❌ Track {args.only} not found in track list", flush=True)
            sys.exit(1)
        print(f"🎯 Only track {args.only} will be generated", flush=True)
    elif args.start_from:
        start_track = f"{args.start_from}_"
        start_idx = next(
            (i for i, t in enumerate(tracks) if t["track"].startswith(start_track)),
            None,
        )
        if start_idx is None:
            print(f"❌ Track {args.start_from} not found in track list", flush=True)
            sys.exit(1)
        tracks = tracks[start_idx:]
        print(f"🎯 Starting from track {args.start_from}", flush=True)

    print(f"\n🎵 재즈 EP 발주 시작: {len(tracks)} tracks", flush=True)
    print(f"Album: {ALBUM_TITLE}", flush=True)
    print(f"Base directory: {ALBUM_DIR}", flush=True)

    # SunoClient 초기화 (전체 과정에서 단일 인스턴스 재사용)
    client = None
    results = []
    retry_queue = []

    try:
        client = SunoClient()
        initial_credits = client.get_credits()
        print(f"\n💰 Initial credits: {initial_credits}", flush=True)

        for i, track_info in enumerate(tracks, 1):
            track = track_info["track"]
            track_num = track.split("_")[0]

            print(f"\n[{i}/{len(tracks)}] Generating Track {track_num}...", flush=True)

            # 트랙 발주
            result = generate_track(client, track_info, initial_credits)
            results.append(result)

            # 실패 시 재시도 큐에 추가
            if not result.success:
                retry_queue.append(track_info)
                print(f"⚠️  Track {track_num} added to retry queue", flush=True)

            # 트랙 간 sleep (30~60초 랜덤)
            if i < len(tracks):
                sleep_time = random.randint(30, 60)
                print(f"\n⏸️  Sleeping {sleep_time}s before next track...", flush=True)
                time.sleep(sleep_time)

            # 크레딧 업데이트
            initial_credits = result.credits_after or initial_credits

        # 재시도 큐 처리
        if retry_queue:
            print(f"\n\n{'='*60}", flush=True)
            print(f"🔄 Retrying {len(retry_queue)} failed tracks...", flush=True)
            print(f"{'='*60}", flush=True)

            # SunoClient 재초기화
            print("\n🔄 Reinitializing SunoClient...", flush=True)
            client.close()
            time.sleep(5)
            client = SunoClient()

            for i, track_info in enumerate(retry_queue, 1):
                track = track_info["track"]
                track_num = track.split("_")[0]
                print(f"\n[Retry {i}/{len(retry_queue)}] Track {track_num}...", flush=True)

                result = generate_track(client, track_info, initial_credits)
                # 기존 결과 업데이트
                for j, r in enumerate(results):
                    if r.track == track:
                        results[j] = result
                        break

                if result.success:
                    print(f"✅ Retry succeeded for Track {track_num}", flush=True)
                else:
                    print(f"❌ Retry failed for Track {track_num}: {result.error}", flush=True)

                if i < len(retry_queue):
                    sleep_time = random.randint(30, 60)
                    print(f"\n⏸️  Sleeping {sleep_time}s...", flush=True)
                    time.sleep(sleep_time)

                initial_credits = result.credits_after or initial_credits

        # 최종 크레딧 확인
        final_credits = client.get_credits() if client else 0

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user", flush=True)
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if client:
            client.close()

    # 종합 보고
    all_success = print_final_report(results, initial_credits if 'initial_credits' in locals() else client.get_credits() if client else 0, final_credits)

    sys.exit(0 if all_success else 1)


if __name__ == "__main__":
    main()