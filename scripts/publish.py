#!/usr/bin/env python3
"""
YouTube 게시 오케스트레이터.

곡 디렉토리 또는 임의 오디오 파일을 받아 전체 파이프라인 실행:
  1. 오디오 파일 확인 (release/final.wav 또는 --audio 경로)
  2. generate_thumbnail.py -> thumbnail.jpg 생성
  3. create_video.py -> output.mp4 생성
  4. youtube_upload.py -> YouTube 업로드
  5. 결과 요약 출력

사용법:
  # 곡 디렉토리 (release/final.wav 기준)
  python3 scripts/publish.py songs/01_봄이라고_부를게/

  # 임의 오디오 파일 직접 지정 (Suno MP3 등)
  python3 scripts/publish.py --audio data/suno/Song_abc12345.mp3 --title "곡 제목"

  # 영상까지만 (업로드 스킵)
  python3 scripts/publish.py --audio data/suno/song.mp3 --title "제목" --skip-upload

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
import tempfile
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


def detect_audio_format(audio_path: Path) -> str:
    """오디오 파일 확장자로 형식 감지."""
    suffix = audio_path.suffix.lower()
    if suffix in (".wav", ".mp3", ".ogg", ".flac", ".m4a", ".aac"):
        return suffix.lstrip(".")
    return "unknown"


def find_cover_image(audio_path: Path, song_dir: Path | None = None) -> Path | None:
    """커버 이미지 탐색. Suno 다운로드 커버 또는 곡 디렉토리 커버."""
    candidates = []

    # Suno 패턴: 같은 디렉토리에 *_cover.jpeg
    stem = audio_path.stem
    suno_cover = audio_path.parent / f"{stem}_cover.jpeg"
    candidates.append(suno_cover)

    # 곡 디렉토리 패턴
    if song_dir:
        candidates.extend([
            song_dir / "cover.jpg",
            song_dir / "cover.jpeg",
            song_dir / "cover.png",
        ])

    # 같은 디렉토리 내 이미지 파일
    for ext in (".jpeg", ".jpg", ".png"):
        for p in audio_path.parent.glob(f"*{ext}"):
            candidates.append(p)

    for c in candidates:
        if c.is_file():
            return c
    return None


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
    song_dir: Path | None = None,
    audio_path: Path | None = None,
    title: str = "",
    subtitle: str = "",
    tags: str = "",
    cover_image: Path | None = None,
    skip_upload: bool = False,
    public: bool = False,
    output_dir: Path | None = None,
) -> dict:
    """전체 게시 파이프라인 실행.

    Args:
        song_dir: 곡 디렉토리 (기존 방식)
        audio_path: 오디오 파일 직접 경로 (Suno MP3 등)
        title: 곡 제목
        subtitle: 영문 서브타이틀
        tags: 태그 (쉼표 구분)
        cover_image: 커버 이미지 경로
        skip_upload: True면 영상까지만 만들고 업로드 스킵
        public: True면 공개
        output_dir: 출력 디렉토리 (기본: song_dir/video 또는 audio_path 옆 video/)

    Returns:
        결과 딕셔너리 {success, video_path, youtube_url, ...}
    """
    start_time = time.time()
    result = {
        "success": False,
        "video_path": None,
        "thumbnail_path": None,
        "youtube_url": None,
        "youtube_id": None,
        "duration": 0.0,
        "steps": {"thumbnail": False, "video": False, "upload": False},
    }

    # ---- 오디오 파일 결정 ----
    if audio_path:
        # --audio 로 직접 지정된 경우
        if not audio_path.is_file():
            print(f"  [오류] 오디오 파일 없음: {audio_path}")
            return result
        fmt = detect_audio_format(audio_path)
        if fmt == "unknown":
            print(f"  [오류] 지원하지 않는 오디오 형식: {audio_path.suffix}")
            return result
    elif song_dir:
        # 곡 디렉토리에서 오디오 탐색
        # 우선순위: release/final.wav > release/final.mp3 > data/suno/*.mp3
        for candidate in [
            song_dir / "release" / "final.wav",
            song_dir / "release" / "final.mp3",
        ]:
            if candidate.is_file():
                audio_path = candidate
                break
        if not audio_path:
            print(f"  [오류] 오디오 파일 없음: {song_dir}/release/final.wav")
            print("  --audio 옵션으로 오디오 파일을 직접 지정하세요.")
            return result
    else:
        print("  [오류] song_dir 또는 audio_path 중 하나는 필요합니다.")
        return result

    duration = get_audio_duration(audio_path)
    result["duration"] = duration
    print(f"  오디오: {audio_path.name} ({duration:.0f}초 / {duration/60:.1f}분)")

    # ---- 출력 디렉토리 결정 ----
    if output_dir:
        work_dir = output_dir
    elif song_dir:
        work_dir = song_dir / "video"
    else:
        work_dir = audio_path.parent / "video"
    work_dir.mkdir(parents=True, exist_ok=True)

    video_path = work_dir / "output.mp4"
    thumb_path = work_dir / "thumbnail.jpg"

    # ---- 커버 이미지 탐색 ----
    if not cover_image:
        cover_image = find_cover_image(audio_path, song_dir)

    # ---- 1. 썸네일 생성 ----
    print("\n" + "-" * 40)
    print("  [1/3] 썸네일 생성")
    print("-" * 40)

    if song_dir:
        thumb_args = [str(song_dir)]
        if title:
            thumb_args += ["--title", title]
        if subtitle:
            thumb_args += ["--subtitle", subtitle]
        if tags:
            thumb_args += ["--tags", tags]
        result["steps"]["thumbnail"] = run_script("generate_thumbnail.py", thumb_args)
    elif cover_image and cover_image.is_file():
        # 커버 이미지가 있으면 썸네일로 복사
        import shutil
        shutil.copy2(str(cover_image), str(thumb_path))
        print(f"  커버 이미지를 썸네일로 사용: {cover_image}")
        result["steps"]["thumbnail"] = True
    else:
        print("  [정보] 커버 이미지 없음 -> 썸네일 스킵")
        result["steps"]["thumbnail"] = True  # 필수 아님

    result["thumbnail_path"] = str(thumb_path) if thumb_path.is_file() else None

    if not result["steps"]["thumbnail"]:
        print("  [경고] 썸네일 생성 실패 -> 영상은 계속 진행")

    # ---- 2. 영상 생성 ----
    print("\n" + "-" * 40)
    print("  [2/3] 영상 생성")
    print("-" * 40)

    if song_dir:
        # 곡 디렉토리 기반: create_video.py가 알아서 탐색
        video_args = [str(song_dir)]
        if title:
            video_args += ["--title", title]
        if audio_path and audio_path != song_dir / "release" / "final.wav":
            video_args += ["--audio", str(audio_path)]
        result["steps"]["video"] = run_script("create_video.py", video_args)
    else:
        # 직접 모드: create_video.py에 모든 경로 전달
        image_arg = str(cover_image) if cover_image and cover_image.is_file() else "nonexistent"
        video_args = [
            "--image", image_arg,
            "--audio", str(audio_path),
            "--output", str(video_path),
        ]
        if title:
            video_args += ["--title", title]

        # create_video.py는 song_dir를 첫 인자로 받지만 직접 모드에서는 임시 디렉토리 사용
        temp_dir = work_dir.parent
        result["steps"]["video"] = run_script("create_video.py", [str(temp_dir)] + video_args)

    if not result["steps"]["video"]:
        print("  [오류] 영상 생성 실패 -> 중단")
        return result

    result["video_path"] = str(video_path) if video_path.is_file() else None

    # manifest 상태 업데이트
    if song_dir:
        update_manifest_status(song_dir, "video_ready")

    # ---- 3. YouTube 업로드 ----
    if skip_upload:
        print("\n" + "-" * 40)
        print("  [3/3] 업로드 스킵 (--skip-upload)")
        print("-" * 40)
        result["steps"]["upload"] = True
    else:
        print("\n" + "-" * 40)
        print("  [3/3] YouTube 업로드")
        print("-" * 40)

        if song_dir:
            upload_args = [str(song_dir)]
            if title:
                upload_args += ["--title", title]
            if tags:
                upload_args += ["--tags", tags]
            if public:
                upload_args.append("--public")
            result["steps"]["upload"] = run_script("youtube_upload.py", upload_args)
        else:
            # 직접 모드: youtube_upload.py 호출 대신 직접 업로드
            result["steps"]["upload"] = _direct_youtube_upload(
                video_path=video_path,
                title=title or audio_path.stem,
                tags=tags,
                thumbnail_path=thumb_path if thumb_path.is_file() else None,
                public=public,
                result=result,
            )

    elapsed = time.time() - start_time

    # ---- 4. 결과 요약 ----
    print("\n" + "=" * 60)
    print("  게시 결과 요약")
    print("=" * 60)
    print(f"  곡: {title or (song_dir.name if song_dir else audio_path.stem)}")
    print(f"  소요 시간: {elapsed:.0f}초")
    print()

    if video_path.is_file():
        video_size = video_path.stat().st_size / (1024 * 1024)
        print(f"  영상: {video_path} ({video_size:.1f} MB)")
    if thumb_path.is_file():
        thumb_size = thumb_path.stat().st_size / 1024
        print(f"  썸네일: {thumb_path} ({thumb_size:.0f} KB)")

    print(f"  오디오 길이: {duration:.0f}초 ({duration/60:.1f}분)")
    print()

    for step, success in result["steps"].items():
        status = "성공" if success else "실패"
        print(f"  {step:<12} {status}")

    # YouTube URL
    if song_dir:
        manifest = load_manifest(song_dir)
        youtube_id = manifest.get("youtube_id")
        if youtube_id:
            result["youtube_id"] = youtube_id
            result["youtube_url"] = f"https://www.youtube.com/watch?v={youtube_id}"

    if result["youtube_url"]:
        print(f"\n  YouTube: {result['youtube_url']}")

    print("=" * 60)

    result["success"] = all(result["steps"].values())
    return result


def _direct_youtube_upload(
    video_path: Path,
    title: str,
    tags: str = "",
    thumbnail_path: Path | None = None,
    public: bool = False,
    result: dict | None = None,
) -> bool:
    """곡 디렉토리 없이 직접 YouTube 업로드."""
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from youtube_upload import get_credentials, upload_video

        creds = get_credentials()
        if not creds:
            print("  [오류] Google 인증 실패 — token.json 확인 필요")
            return False

        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
        tag_list.extend(["AI Music", "Suno", "AI Generated"])

        display_title = f"{title} | AI Music by Suno"
        description = (
            f"Made with Suno AI\n\n"
            "---\n"
            "이 곡은 AI 도구(Suno, Claude)를 활용하여 제작되었습니다.\n"
            "작사, 작곡 컨셉 설계는 사람이, 음원 생성은 AI가 담당했습니다."
        )

        video_id = upload_video(
            video_path=video_path,
            title=display_title[:100],
            description=description,
            tags=tag_list[:30],
            thumbnail_path=thumbnail_path,
            public=public,
        )

        if video_id and result is not None:
            result["youtube_id"] = video_id
            result["youtube_url"] = f"https://www.youtube.com/watch?v={video_id}"

        return video_id is not None

    except ImportError as e:
        print(f"  [오류] YouTube 업로드 모듈 임포트 실패: {e}")
        return False
    except Exception as e:
        print(f"  [오류] YouTube 업로드 실패: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="YouTube 게시 오케스트레이터",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="예시:\n"
               "  python3 scripts/publish.py songs/01_봄이라고_부를게/\n"
               "  python3 scripts/publish.py --audio data/suno/song.mp3 --title \"곡 제목\"\n"
               "  python3 scripts/publish.py songs/01_봄이라고_부를게/ --skip-upload\n"
               "  python3 scripts/publish.py songs/01_봄이라고_부를게/ --public\n",
    )
    parser.add_argument("song_dir", nargs="?", help="곡 디렉토리 경로 (선택)")
    parser.add_argument("--audio", help="오디오 파일 경로 (WAV/MP3 직접 지정)")
    parser.add_argument("--title", help="곡 제목")
    parser.add_argument("--subtitle", help="영문 서브타이틀", default="")
    parser.add_argument("--tags", help="태그 (쉼표 구분)", default="")
    parser.add_argument("--cover", help="커버 이미지 경로")
    parser.add_argument("--skip-upload", action="store_true", help="영상까지만 생성, 업로드 스킵")
    parser.add_argument("--public", action="store_true", help="바로 공개 (기본: unlisted)")
    args = parser.parse_args()

    # song_dir 또는 --audio 중 하나는 필요
    if not args.song_dir and not args.audio:
        parser.error("song_dir 또는 --audio 중 하나는 필요합니다.")

    song_dir = None
    audio_path = None

    if args.song_dir:
        song_dir = Path(args.song_dir).resolve()
        if not song_dir.is_dir():
            print(f"[오류] 곡 디렉토리 없음: {song_dir}")
            sys.exit(1)

    if args.audio:
        audio_path = Path(args.audio).resolve()
        if not audio_path.is_file():
            print(f"[오류] 오디오 파일 없음: {audio_path}")
            sys.exit(1)

    cover_image = Path(args.cover).resolve() if args.cover else None

    # 메타데이터 결정
    if song_dir:
        manifest = load_manifest(song_dir)
        concept_info = extract_info_from_concept(song_dir)
        title = args.title or manifest.get("title") or concept_info["title"] or song_dir.name
        subtitle = args.subtitle or manifest.get("subgenre", "").title()
        tags = args.tags
        if not tags and concept_info["tags"]:
            tags = ",".join(concept_info["tags"])
    else:
        title = args.title or (audio_path.stem if audio_path else "Untitled")
        subtitle = args.subtitle
        tags = args.tags

    print("=" * 60)
    print("  YouTube 게시 파이프라인")
    print(f"  곡: {title}")
    if song_dir:
        print(f"  디렉토리: {song_dir}")
    if audio_path:
        print(f"  오디오: {audio_path}")
    if args.skip_upload:
        print("  모드: 영상 생성만 (업로드 스킵)")
    else:
        print(f"  공개: {'공개(public)' if args.public else '미등록(unlisted)'}")
    print("=" * 60)

    result = publish(
        song_dir=song_dir,
        audio_path=audio_path,
        title=title,
        subtitle=subtitle,
        tags=tags,
        cover_image=cover_image,
        skip_upload=args.skip_upload,
        public=args.public,
    )

    if result["success"]:
        print("\n  파이프라인 완료!")
    else:
        print("\n  파이프라인 일부 실패.")
        sys.exit(1)


if __name__ == "__main__":
    main()
