#!/usr/bin/env python3
"""
YouTube 게시 오케스트레이터.

곡 디렉토리 하나를 받아 전체 파이프라인 실행:
  1. release/final.wav 존재 확인
  2. generate_thumbnail.py -> thumbnail.jpg 생성
  3. create_video.py -> output.mp4 생성
  4. youtube_upload.py -> YouTube 업로드
  5. 결과 요약 출력

사용법:
  # 전체 파이프라인
  python3 scripts/publish.py songs/01_봄이라고_부를게/

  # 영상까지만 (업로드 스킵)
  python3 scripts/publish.py songs/01_봄이라고_부를게/ --skip-upload

  # 바로 공개
  python3 scripts/publish.py songs/01_봄이라고_부를게/ --public

  # 옵션 지정
  python3 scripts/publish.py songs/01_봄이라고_부를게/ \\
      --title "봄이라고 부를게" --subtitle "Korean Indie Pop" --tags "jazz,korean"
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.parent


def load_manifest(song_dir: Path) -> dict:
    """manifest.json 로드."""
    manifest_path = song_dir / "manifest.json"
    if manifest_path.is_file():
        try:
            return json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {}


def update_manifest_status(song_dir: Path, status: str, extra: dict | None = None) -> None:
    """manifest.json status 업데이트."""
    manifest_path = song_dir / "manifest.json"
    if manifest_path.is_file():
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            data["status"] = status
            if extra:
                data.update(extra)
            manifest_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except json.JSONDecodeError:
            pass


def extract_info_from_concept(song_dir: Path) -> dict:
    """concept.md에서 제목/설명/태그 추출."""
    concept_path = song_dir / "concept.md"
    info = {"title": "", "description": "", "tags": []}

    if not concept_path.is_file():
        return info

    text = concept_path.read_text(encoding="utf-8")

    # 제목 추출 (첫 번째 # 줄)
    match = re.search(r"^#\s+(.+?)(?:\s*[-—]|$)", text, re.MULTILINE)
    if match:
        info["title"] = match.group(1).strip()

    # 장르 추출
    match = re.search(r"장르[:\s]*(.+)", text)
    if match:
        genre = match.group(1).strip().strip("*")
        info["tags"].append(genre)

    # 핵심 컨셉 추출 (설명용)
    match = re.search(r"##\s*핵심\s*컨셉\s*\n(.*?)(?=\n##|\Z)", text, re.DOTALL)
    if match:
        desc = match.group(1).strip()
        if len(desc) > 500:
            desc = desc[:500] + "..."
        info["description"] = desc

    return info


def get_audio_duration(audio_path: Path) -> float:
    """오디오 길이(초) 조회."""
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return float(result.stdout.strip())
    except (subprocess.TimeoutExpired, ValueError, FileNotFoundError):
        return 0.0


def run_script(script_name: str, args: list[str]) -> bool:
    """서브 스크립트 실행.

    Args:
        script_name: 스크립트 파일명 (scripts/ 디렉토리 기준)
        args: 추가 인자 목록

    Returns:
        성공 여부
    """
    script_path = PROJECT_ROOT / "scripts" / script_name
    if not script_path.is_file():
        print(f"  [오류] 스크립트 없음: {script_path}")
        return False

    cmd = [sys.executable, str(script_path)] + args
    print(f"\n  실행: {script_name} {' '.join(args)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
            cwd=str(PROJECT_ROOT),
        )

        # 서브 스크립트 출력 전달 (인덴트 추가)
        if result.stdout:
            for line in result.stdout.strip().split("\n"):
                print(f"    {line}")

        if result.returncode != 0:
            if result.stderr:
                for line in result.stderr.strip().split("\n")[-5:]:
                    print(f"    [stderr] {line}")
            return False

        return True

    except subprocess.TimeoutExpired:
        print(f"  [오류] {script_name} 타임아웃 (10분 초과)")
        return False
    except Exception as e:
        print(f"  [오류] {script_name} 실행 실패: {e}")
        return False


def publish(
    song_dir: Path,
    title: str = "",
    subtitle: str = "",
    tags: str = "",
    skip_upload: bool = False,
    public: bool = False,
) -> bool:
    """전체 게시 파이프라인 실행.

    Args:
        song_dir: 곡 디렉토리
        title: 곡 제목
        subtitle: 영문 서브타이틀
        tags: 태그 (쉼표 구분)
        skip_upload: True면 영상까지만 만들고 업로드 스킵
        public: True면 공개

    Returns:
        성공 여부
    """
    start_time = time.time()
    results = {"thumbnail": False, "video": False, "upload": False}

    # 1. release/final.wav 확인
    audio_path = song_dir / "release" / "final.wav"
    if not audio_path.is_file():
        print(f"  [오류] 오디오 파일 없음: {audio_path}")
        print("  mix_stems.py를 먼저 실행하세요.")
        return False

    duration = get_audio_duration(audio_path)
    print(f"  오디오: {audio_path.name} ({duration:.0f}초 / {duration/60:.1f}분)")

    # 2. 썸네일 생성
    print("\n" + "-" * 40)
    print("  [1/3] 썸네일 생성")
    print("-" * 40)

    thumb_args = [str(song_dir)]
    if title:
        thumb_args += ["--title", title]
    if subtitle:
        thumb_args += ["--subtitle", subtitle]
    if tags:
        thumb_args += ["--tags", tags]

    results["thumbnail"] = run_script("generate_thumbnail.py", thumb_args)

    if not results["thumbnail"]:
        print("  [경고] 썸네일 생성 실패 -> 영상은 계속 진행")

    # 3. 영상 생성
    print("\n" + "-" * 40)
    print("  [2/3] 영상 생성")
    print("-" * 40)

    video_args = [str(song_dir)]
    if title:
        video_args += ["--title", title]

    results["video"] = run_script("create_video.py", video_args)

    if not results["video"]:
        print("  [오류] 영상 생성 실패 -> 중단")
        return False

    # manifest 상태 업데이트
    update_manifest_status(song_dir, "video_ready")

    # 4. YouTube 업로드
    if skip_upload:
        print("\n" + "-" * 40)
        print("  [3/3] 업로드 스킵 (--skip-upload)")
        print("-" * 40)
        results["upload"] = True  # 스킵은 성공으로 처리
    else:
        print("\n" + "-" * 40)
        print("  [3/3] YouTube 업로드")
        print("-" * 40)

        upload_args = [str(song_dir)]
        if title:
            upload_args += ["--title", title]
        if tags:
            upload_args += ["--tags", tags]
        if public:
            upload_args.append("--public")

        results["upload"] = run_script("youtube_upload.py", upload_args)

    elapsed = time.time() - start_time

    # 5. 결과 요약
    print("\n" + "=" * 60)
    print("  게시 결과 요약")
    print("=" * 60)
    print(f"  곡: {title or song_dir.name}")
    print(f"  소요 시간: {elapsed:.0f}초")
    print()

    video_path = song_dir / "video" / "output.mp4"
    thumb_path = song_dir / "video" / "thumbnail.jpg"

    # 파일 정보
    if video_path.is_file():
        video_size = video_path.stat().st_size / (1024 * 1024)
        print(f"  영상: {video_path} ({video_size:.1f} MB)")
    if thumb_path.is_file():
        thumb_size = thumb_path.stat().st_size / 1024
        print(f"  썸네일: {thumb_path} ({thumb_size:.0f} KB)")

    print(f"  오디오 길이: {duration:.0f}초 ({duration/60:.1f}분)")
    print()

    # 상태
    for step, success in results.items():
        status = "성공" if success else "실패"
        print(f"  {step:<12} {status}")

    # YouTube URL
    manifest = load_manifest(song_dir)
    youtube_id = manifest.get("youtube_id")
    if youtube_id:
        print(f"\n  YouTube: https://www.youtube.com/watch?v={youtube_id}")

    print("=" * 60)

    return all(results.values())


def main():
    parser = argparse.ArgumentParser(
        description="YouTube 게시 오케스트레이터",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="예시:\n"
               "  python3 scripts/publish.py songs/01_봄이라고_부를게/\n"
               "  python3 scripts/publish.py songs/01_봄이라고_부를게/ --skip-upload\n"
               "  python3 scripts/publish.py songs/01_봄이라고_부를게/ --public\n",
    )
    parser.add_argument("song_dir", help="곡 디렉토리 경로")
    parser.add_argument("--title", help="곡 제목")
    parser.add_argument("--subtitle", help="영문 서브타이틀", default="")
    parser.add_argument("--tags", help="태그 (쉼표 구분)", default="")
    parser.add_argument("--skip-upload", action="store_true", help="영상까지만 생성, 업로드 스킵")
    parser.add_argument("--public", action="store_true", help="바로 공개 (기본: unlisted)")
    args = parser.parse_args()

    song_dir = Path(args.song_dir).resolve()
    if not song_dir.is_dir():
        print(f"[오류] 곡 디렉토리 없음: {song_dir}")
        sys.exit(1)

    # 메타데이터 결정
    manifest = load_manifest(song_dir)
    concept_info = extract_info_from_concept(song_dir)

    title = args.title or manifest.get("title") or concept_info["title"] or song_dir.name
    subtitle = args.subtitle or manifest.get("subgenre", "").title()
    tags = args.tags

    if not tags and concept_info["tags"]:
        tags = ",".join(concept_info["tags"])

    print("=" * 60)
    print("  YouTube 게시 파이프라인")
    print(f"  곡: {title}")
    print(f"  디렉토리: {song_dir}")
    if args.skip_upload:
        print("  모드: 영상 생성만 (업로드 스킵)")
    else:
        print(f"  공개: {'공개(public)' if args.public else '미등록(unlisted)'}")
    print("=" * 60)

    success = publish(
        song_dir=song_dir,
        title=title,
        subtitle=subtitle,
        tags=tags,
        skip_upload=args.skip_upload,
        public=args.public,
    )

    if success:
        print("\n  파이프라인 완료!")
    else:
        print("\n  파이프라인 일부 실패.")
        sys.exit(1)


if __name__ == "__main__":
    main()
