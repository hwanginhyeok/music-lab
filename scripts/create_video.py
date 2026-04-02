#!/usr/bin/env python3
"""
커버 이미지 + 오디오 -> YouTube용 MP4 영상 생성.

ffmpeg subprocess로 정지 이미지에 오디오를 입혀 영상을 만든다.
이미지가 없으면 검정 배경 + 곡 제목 텍스트(drawtext)로 대체.

사용법:
  # 곡 디렉토리 지정 (자동 탐색)
  python3 scripts/create_video.py songs/01_봄이라고_부를게/

  # 옵션 직접 지정
  python3 scripts/create_video.py songs/01_봄이라고_부를게/ \\
      --image cover.jpg --audio release/final.wav --output video/output.mp4

  # 제목 지정 (이미지 없을 때 텍스트 표시)
  python3 scripts/create_video.py songs/01_봄이라고_부를게/ --title "봄이라고 부를게"

출력:
  1920x1080, H.264 (yuv420p), AAC 192k
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def check_ffmpeg() -> bool:
    """ffmpeg 설치 확인."""
    return shutil.which("ffmpeg") is not None


def get_audio_duration(audio_path: Path) -> float:
    """ffprobe로 오디오 길이(초) 조회."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio_path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return float(result.stdout.strip())
    except (subprocess.TimeoutExpired, ValueError):
        return 0.0


def load_title_from_manifest(song_dir: Path) -> str:
    """manifest.json에서 곡 제목 추출."""
    manifest_path = song_dir / "manifest.json"
    if manifest_path.is_file():
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            return data.get("title", "")
        except (json.JSONDecodeError, KeyError):
            pass
    return ""


def create_black_background(title: str, output_path: Path) -> Path:
    """검정 배경 + 곡 제목 텍스트 이미지 생성 (ffmpeg drawtext)."""
    # ffmpeg로 검정 1920x1080 이미지 생성
    # 한글 폰트 경로 탐색
    font_candidates = [
        "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/usr/share/fonts/nanum/NanumGothicBold.ttf",
        "/usr/share/fonts/nanum/NanumGothic.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    font_path = ""
    for f in font_candidates:
        if Path(f).is_file():
            font_path = f
            break

    bg_path = output_path.parent / "temp_bg.png"

    if title and font_path:
        # 검정 배경 + 텍스트
        # ffmpeg drawtext 필터에서 특수문자 이스케이프
        escaped_title = title.replace("'", "'\\''").replace(":", "\\:")
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "color=c=black:s=1920x1080:d=1",
            "-vframes", "1",
            "-vf", f"drawtext=fontfile={font_path}:text='{escaped_title}'"
                  f":fontcolor=white:fontsize=72:x=(w-text_w)/2:y=(h-text_h)/2",
            str(bg_path),
        ]
    else:
        # 텍스트 없이 검정 배경만
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "color=c=black:s=1920x1080:d=1",
            "-vframes", "1",
            str(bg_path),
        ]

    subprocess.run(cmd, capture_output=True, timeout=30)
    return bg_path


def create_video(
    image_path: Path,
    audio_path: Path,
    output_path: Path,
    title: str = "",
    ken_burns: bool = True,
    lyrics_srt: Path | None = None,
) -> bool:
    """정지 이미지 + 오디오 -> MP4 영상 생성.

    Args:
        image_path: 커버 이미지 경로 (없으면 검정 배경 생성)
        audio_path: 오디오 파일 경로 (WAV/MP3)
        output_path: 출력 MP4 경로
        title: 곡 제목 (검정 배경 시 텍스트 표시용)
        ken_burns: Ken Burns 줌 효과 적용 여부
        lyrics_srt: 가사 자막 SRT 파일 경로

    Returns:
        성공 여부
    """
    temp_bg = None
    try:
        # 이미지 없으면 검정 배경 생성
        actual_image = image_path
        if not image_path.is_file():
            print(f"  [정보] 이미지 없음 -> 검정 배경 + 제목 텍스트 사용")
            temp_bg = create_black_background(title, output_path)
            actual_image = temp_bg

        # 출력 디렉토리 생성
        output_path.parent.mkdir(parents=True, exist_ok=True)

        duration = get_audio_duration(audio_path)

        if ken_burns and actual_image != temp_bg:
            # Ken Burns 효과: zoompan 필터로 천천히 줌인
            # 이미지를 먼저 고해상도로 업스케일 (zoompan용)
            total_frames = int(duration * 30) if duration > 0 else 9000  # 30fps

            vf_parts = []
            # zoompan: 천천히 줌인 (1.0 → 1.2, 20% 줌)
            vf_parts.append(
                f"scale=3840:-1,"
                f"zoompan=z='min(zoom+0.0003,1.2)'"
                f":x='iw/2-(iw/zoom/2)'"
                f":y='ih/2-(ih/zoom/2)'"
                f":d={total_frames}"
                f":s=1920x1080"
                f":fps=30"
            )

            # 자막 추가 (있으면)
            if lyrics_srt and lyrics_srt.is_file():
                # subtitles 필터 경로에서 : \ 이스케이프
                srt_escaped = str(lyrics_srt).replace("\\", "/").replace(":", "\\:")
                vf_parts.append(
                    f"subtitles='{srt_escaped}'"
                    f":force_style='FontSize=28,PrimaryColour=&HFFFFFF&"
                    f",OutlineColour=&H000000&,BorderStyle=3,Outline=2"
                    f",Alignment=2,MarginV=60'"
                )

            vf = ",".join(vf_parts)

            cmd = [
                "ffmpeg", "-y",
                "-i", str(actual_image),
                "-i", str(audio_path),
                "-c:v", "libx264",
                "-preset", "medium",
                "-c:a", "aac",
                "-b:a", "192k",
                "-pix_fmt", "yuv420p",
                "-vf", vf,
                "-shortest",
                str(output_path),
            ]
            print(f"  ffmpeg 실행 중 (Ken Burns + 자막)...")
        else:
            # 기존 방식: 정지 이미지
            vf = "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2"

            # 자막 추가 (있으면)
            if lyrics_srt and lyrics_srt.is_file():
                srt_escaped = str(lyrics_srt).replace("\\", "/").replace(":", "\\:")
                vf += (
                    f",subtitles='{srt_escaped}'"
                    f":force_style='FontSize=28,PrimaryColour=&HFFFFFF&"
                    f",OutlineColour=&H000000&,BorderStyle=3,Outline=2"
                    f",Alignment=2,MarginV=60'"
                )

            cmd = [
                "ffmpeg", "-y",
                "-loop", "1",
                "-i", str(actual_image),
                "-i", str(audio_path),
                "-c:v", "libx264",
                "-tune", "stillimage",
                "-c:a", "aac",
                "-b:a", "192k",
                "-pix_fmt", "yuv420p",
                "-vf", vf,
                "-shortest",
                str(output_path),
            ]
            print(f"  ffmpeg 실행 중...")

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

        if result.returncode != 0:
            print(f"  [오류] ffmpeg 실패:\n{result.stderr[-500:]}")
            return False

        # 결과 출력
        duration = get_audio_duration(audio_path)
        size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"  출력: {output_path}")
        print(f"  크기: {size_mb:.1f} MB")
        print(f"  길이: {duration:.0f}초 ({duration/60:.1f}분)")
        print(f"  해상도: 1920x1080, H.264, AAC 192k")
        return True

    except subprocess.TimeoutExpired:
        print("  [오류] ffmpeg 타임아웃 (10분 초과)")
        return False
    except Exception as e:
        print(f"  [오류] 영상 생성 실패: {e}")
        return False
    finally:
        # 임시 배경 이미지 정리
        if temp_bg and temp_bg.is_file():
            temp_bg.unlink()


def main():
    parser = argparse.ArgumentParser(
        description="커버 이미지 + 오디오 -> YouTube용 MP4 영상 생성",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="예시:\n"
               "  python3 scripts/create_video.py songs/01_봄이라고_부를게/\n"
               "  python3 scripts/create_video.py songs/01_봄이라고_부를게/ --title \"봄이라고 부를게\"\n",
    )
    parser.add_argument("song_dir", help="곡 디렉토리 경로")
    parser.add_argument("--image", help="커버 이미지 경로 (기본: cover.jpg)")
    parser.add_argument("--audio", help="오디오 파일 경로 (기본: release/final.wav)")
    parser.add_argument("--output", help="출력 MP4 경로 (기본: video/output.mp4)")
    parser.add_argument("--title", help="곡 제목 (이미지 없을 때 텍스트 표시)")
    args = parser.parse_args()

    # ffmpeg 확인
    if not check_ffmpeg():
        print("[오류] ffmpeg가 설치되어 있지 않습니다.")
        print("  Ubuntu/Debian: sudo apt install ffmpeg")
        print("  macOS: brew install ffmpeg")
        sys.exit(1)

    song_dir = Path(args.song_dir).resolve()
    if not song_dir.is_dir():
        print(f"[오류] 곡 디렉토리 없음: {song_dir}")
        sys.exit(1)

    # 경로 결정
    image_path = Path(args.image) if args.image else song_dir / "cover.jpg"
    audio_path = Path(args.audio) if args.audio else song_dir / "release" / "final.wav"
    output_path = Path(args.output) if args.output else song_dir / "video" / "output.mp4"

    # 제목 결정 (인자 > manifest.json > 디렉토리 이름)
    title = args.title or load_title_from_manifest(song_dir) or song_dir.name

    # 오디오 파일 확인
    if not audio_path.is_file():
        print(f"[오류] 오디오 파일 없음: {audio_path}")
        print("  mix_stems.py를 먼저 실행하세요.")
        sys.exit(1)

    print("=" * 60)
    print("  YouTube 영상 생성")
    print(f"  곡: {title}")
    print(f"  이미지: {image_path}" + (" (없음 -> 검정 배경)" if not image_path.is_file() else ""))
    print(f"  오디오: {audio_path}")
    print(f"  출력: {output_path}")
    print("=" * 60)

    success = create_video(image_path, audio_path, output_path, title)

    if success:
        print("\n  영상 생성 완료!")
    else:
        print("\n  영상 생성 실패.")
        sys.exit(1)


if __name__ == "__main__":
    main()
