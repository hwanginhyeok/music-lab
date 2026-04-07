#!/usr/bin/env python3
"""
메이킹 영상 생성 — 스크린샷 슬라이드쇼 + TTS 나레이션 + 배경음악.

스크린샷을 순서대로 보여주면서 edge-tts 나레이션을 입히고,
배경음악을 깔아 YouTube용 메이킹 영상을 만든다.

사용법:
  # JSON 스크립트로 실행
  python3 scripts/create_making_video.py --script making_script.json

  # 간단 모드: 이미지 디렉토리 + 나레이션 텍스트
  python3 scripts/create_making_video.py --images screenshots/ --narration narration.txt

  # 배경음악 + 출력 지정
  python3 scripts/create_making_video.py --script making_script.json \\
      --bgm "data/suno/song.mp3" --output making.mp4

출력:
  1920x1080, H.264 (yuv420p), AAC 192k

나레이션 스크립트 JSON 형식:
  {
    "title": "메이킹 영상 제목",
    "voice": "ko-KR-InJoonNeural",
    "bgm": "path/to/bgm.mp3",
    "bgm_volume": 0.15,
    "slides": [
      {"image": "01.png", "text": "나레이션 텍스트", "rate": "+5%"},
      {"image": "02.png", "text": "다음 장면 설명"}
    ]
  }
"""
from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


# ── 유틸 ─────────────────────────────────────────────

def check_ffmpeg() -> bool:
    """ffmpeg/ffprobe 설치 확인."""
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def get_duration(path: Path) -> float:
    """ffprobe로 오디오/영상 길이(초) 조회."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return float(result.stdout.strip())
    except (subprocess.TimeoutExpired, ValueError):
        return 0.0


# ── TTS 생성 ──────────────────────────────────────────

async def generate_tts(
    slides: list[dict],
    voice: str,
    tmp_dir: Path,
) -> list[dict]:
    """edge-tts로 각 슬라이드의 나레이션 MP3 생성.

    Returns:
        slides에 tts_path, tts_duration 필드가 추가된 리스트
    """
    from edge_tts import Communicate

    for i, slide in enumerate(slides):
        text = slide.get("text", "").strip()
        if not text:
            slide["tts_path"] = None
            slide["tts_duration"] = 0.0
            continue

        # 짧은 텍스트는 TTS가 불안정 — 마침표 추가
        tts_text = f"{text}." if len(text) < 5 else text
        rate = slide.get("rate", "+0%")
        out_path = tmp_dir / f"nar-{i:02d}.mp3"

        try:
            communicate = Communicate(text=tts_text, voice=voice, rate=rate)
            await communicate.save(str(out_path))
            duration = get_duration(out_path)
            slide["tts_path"] = str(out_path)
            slide["tts_duration"] = duration
            print(f"  TTS [{i+1}/{len(slides)}] {text[:30]}... ({duration:.1f}초)")
        except Exception as e:
            print(f"  TTS [{i+1}/{len(slides)}] 실패: {e}")
            slide["tts_path"] = None
            slide["tts_duration"] = 0.0

    return slides


# ── 타이밍 계산 ───────────────────────────────────────

def calculate_timing(
    slides: list[dict],
    padding: float = 1.5,
    min_duration: float = 3.0,
    transition: float = 0.5,
) -> list[dict]:
    """각 슬라이드의 표시 시간과 나레이션 시작 오프셋 계산.

    각 슬라이드 표시 시간 = max(TTS길이 + padding, min_duration)
    나레이션은 슬라이드 시작 0.5초 후 재생.
    """
    offset = 0.0
    for slide in slides:
        tts_dur = slide.get("tts_duration", 0.0)
        slide_dur = max(tts_dur + padding, min_duration)

        slide["slide_duration"] = slide_dur
        slide["slide_start"] = offset
        slide["narration_start"] = offset + 0.5  # 나레이션은 약간 딜레이
        offset += slide_dur - transition  # 전환 효과 겹침 보정

    return slides


# ── 슬라이드쇼 생성 ───────────────────────────────────

def create_slideshow(
    slides: list[dict],
    output_path: Path,
    transition_sec: float = 0.5,
) -> bool:
    """ffmpeg xfade 필터 체인으로 슬라이드쇼 MP4 생성 (무음).

    각 이미지를 지정된 시간만큼 표시하고 fade 전환으로 연결.
    """
    n = len(slides)
    if n == 0:
        return False

    # 각 이미지를 개별 비디오 스트림으로 입력
    inputs: list[str] = []
    for i, slide in enumerate(slides):
        dur = slide["slide_duration"]
        inputs.extend([
            "-loop", "1",
            "-t", f"{dur:.2f}",
            "-i", slide["image"],
        ])

    # 비디오 필터: scale+pad → xfade 체인
    filters: list[str] = []
    scale_pad = "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p"

    for i in range(n):
        filters.append(f"[{i}:v]{scale_pad},fps=30[v{i}]")

    if n == 1:
        # 이미지 1장: xfade 불필요
        filters.append(f"[v0]null[out]")
    else:
        # xfade 체인 빌드
        cumulative = 0.0
        prev = "v0"
        for i in range(1, n):
            cumulative += slides[i - 1]["slide_duration"] - transition_sec
            out_label = "out" if i == n - 1 else f"x{i}"
            filters.append(
                f"[{prev}][v{i}]xfade=transition=fade"
                f":duration={transition_sec}"
                f":offset={cumulative:.2f}[{out_label}]"
            )
            prev = out_label

    filter_str = ";\n".join(filters)

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_str,
        "-map", "[out]",
        "-c:v", "libx264",
        "-preset", "medium",
        "-pix_fmt", "yuv420p",
        "-an",  # 무음 — 오디오는 나중에 합성
        str(output_path),
    ]

    print(f"  슬라이드쇼 생성 중 ({n}장, 전환: fade {transition_sec}초)...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        print(f"  [오류] 슬라이드쇼 생성 실패:\n{result.stderr[-500:]}")
        return False

    total_dur = get_duration(output_path)
    print(f"  슬라이드쇼 완료: {total_dur:.1f}초")
    return True


# ── 오디오 합성 ───────────────────────────────────────

def mix_audio(
    slideshow_path: Path,
    slides: list[dict],
    output_path: Path,
    bgm_path: Path | None = None,
    bgm_volume: float = 0.15,
) -> bool:
    """나레이션 + 배경음악을 슬라이드쇼에 합성.

    generate-reel.mjs의 adelay + amix 패턴을 Python으로 구현.
    """
    # 나레이션 TTS 파일 수집
    narrations = [
        (slide["tts_path"], slide["narration_start"])
        for slide in slides
        if slide.get("tts_path")
    ]

    if not narrations and not bgm_path:
        # 오디오 없음 — 슬라이드쇼 그대로 복사
        shutil.copy2(slideshow_path, output_path)
        return True

    video_duration = get_duration(slideshow_path)

    # ffmpeg 입력 구성
    inputs = ["-i", str(slideshow_path)]  # [0] = 슬라이드쇼
    filters: list[str] = []
    audio_count = 0

    # 나레이션 클립: adelay로 시간 배치
    for tts_path, start_sec in narrations:
        inputs.extend(["-i", tts_path])
        delay_ms = int(start_sec * 1000)
        idx = audio_count + 1  # [0]은 비디오
        filters.append(f"[{idx}:a]adelay={delay_ms}|{delay_ms},volume=1.0[a{audio_count}]")
        audio_count += 1

    # BGM 추가
    bgm_idx = None
    if bgm_path and bgm_path.is_file():
        inputs.extend(["-i", str(bgm_path)])
        bgm_input = audio_count + 1
        # BGM: 볼륨 조절 + 페이드인/아웃
        fade_out_start = max(0, video_duration - 3)
        filters.append(
            f"[{bgm_input}:a]volume={bgm_volume}"
            f",afade=t=in:d=2"
            f",afade=t=out:d=3:st={fade_out_start:.1f}"
            f"[bgm]"
        )
        bgm_idx = "bgm"
        audio_count += 1

    # 전체 오디오 믹스
    if audio_count == 0:
        shutil.copy2(slideshow_path, output_path)
        return True

    # 나레이션 믹스
    nar_count = len(narrations)
    if nar_count > 0 and bgm_idx:
        # 나레이션끼리 먼저 믹스 → BGM과 합성
        if nar_count == 1:
            filters.append(f"[a0][{bgm_idx}]amix=inputs=2:duration=first:dropout_transition=2[mixed]")
        else:
            nar_labels = "".join(f"[a{i}]" for i in range(nar_count))
            filters.append(f"{nar_labels}amix=inputs={nar_count}:duration=first:dropout_transition=2[narmix]")
            filters.append(f"[narmix][{bgm_idx}]amix=inputs=2:duration=first:dropout_transition=2[mixed]")
    elif nar_count > 0:
        # 나레이션만
        if nar_count == 1:
            filters.append("[a0]anull[mixed]")
        else:
            nar_labels = "".join(f"[a{i}]" for i in range(nar_count))
            filters.append(f"{nar_labels}amix=inputs={nar_count}:duration=first:dropout_transition=2[mixed]")
    elif bgm_idx:
        # BGM만
        filters.append(f"[{bgm_idx}]anull[mixed]")

    filter_str = ";\n".join(filters)

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_str,
        "-map", "0:v",
        "-map", "[mixed]",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(output_path),
    ]

    print(f"  오디오 합성 중 (나레이션 {nar_count}개 + BGM {'있음' if bgm_idx else '없음'})...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        print(f"  [오류] 오디오 합성 실패:\n{result.stderr[-500:]}")
        return False

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"  최종 영상: {output_path} ({size_mb:.1f} MB)")
    return True


# ── 메인 파이프라인 ───────────────────────────────────

def load_script(script_path: Path) -> dict:
    """JSON 스크립트 파일 로드."""
    data = json.loads(script_path.read_text(encoding="utf-8"))
    base_dir = script_path.parent

    # 이미지 경로를 절대경로로 변환
    for slide in data.get("slides", []):
        img = slide.get("image", "")
        if img and not Path(img).is_absolute():
            slide["image"] = str((base_dir / img).resolve())

    # BGM 경로도 절대경로로
    bgm = data.get("bgm", "")
    if bgm and not Path(bgm).is_absolute():
        data["bgm"] = str((base_dir / bgm).resolve())

    return data


def load_simple_mode(
    images_dir: Path,
    narration_file: Path | None,
) -> dict:
    """간단 모드: 이미지 디렉토리 + 나레이션 텍스트 파일 → 스크립트 생성."""
    # 이미지 파일 수집 (정렬)
    image_exts = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
    images = sorted(
        [f for f in images_dir.iterdir() if f.suffix.lower() in image_exts],
        key=lambda f: f.name,
    )

    if not images:
        print(f"[오류] 이미지 없음: {images_dir}")
        sys.exit(1)

    # 나레이션 텍스트 파일 (한 줄 = 한 슬라이드)
    texts: list[str] = []
    if narration_file and narration_file.is_file():
        texts = [
            line.strip()
            for line in narration_file.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    slides = []
    for i, img in enumerate(images):
        text = texts[i] if i < len(texts) else ""
        slides.append({"image": str(img), "text": text})

    return {"slides": slides, "voice": "ko-KR-InJoonNeural"}


def create_making_video(
    script_data: dict,
    output_path: Path,
    bgm_override: Path | None = None,
) -> bool:
    """메이킹 영상 생성 메인 함수."""
    slides = script_data.get("slides", [])
    voice = script_data.get("voice", "ko-KR-InJoonNeural")
    bgm_path = bgm_override or (Path(script_data["bgm"]) if script_data.get("bgm") else None)
    bgm_volume = script_data.get("bgm_volume", 0.15)

    if not slides:
        print("[오류] 슬라이드가 없습니다.")
        return False

    # 이미지 존재 확인
    for slide in slides:
        img = Path(slide["image"])
        if not img.is_file():
            print(f"[오류] 이미지 없음: {img}")
            return False

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="making_") as tmp:
        tmp_dir = Path(tmp)

        # [1] TTS 생성
        print("\n[1/4] TTS 나레이션 생성")
        slides = asyncio.run(generate_tts(slides, voice, tmp_dir))

        # [2] 타이밍 계산
        print("\n[2/4] 타이밍 계산")
        slides = calculate_timing(slides)
        total = sum(s["slide_duration"] for s in slides)
        for s in slides:
            dur = s["slide_duration"]
            text = s.get("text", "") or "(무음)"
            print(f"  {Path(s['image']).name}: {dur:.1f}초 — {text[:40]}")
        print(f"  총 길이: {total:.1f}초 ({total/60:.1f}분)")

        # [3] 슬라이드쇼 생성
        print("\n[3/4] 슬라이드쇼 생성")
        slideshow_path = tmp_dir / "slideshow.mp4"
        if not create_slideshow(slides, slideshow_path):
            return False

        # [4] 오디오 합성
        print("\n[4/4] 오디오 합성")
        if not mix_audio(slideshow_path, slides, output_path, bgm_path, bgm_volume):
            return False

    total_dur = get_duration(output_path)
    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"\n{'='*60}")
    print(f"  메이킹 영상 완료!")
    print(f"  출력: {output_path}")
    print(f"  길이: {total_dur:.0f}초 ({total_dur/60:.1f}분)")
    print(f"  크기: {size_mb:.1f} MB")
    print(f"  해상도: 1920x1080, H.264, AAC 192k")
    print(f"{'='*60}")
    return True


# ── CLI ───────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="메이킹 영상 생성 — 스크린샷 슬라이드쇼 + TTS 나레이션 + 배경음악",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "예시:\n"
            '  python3 scripts/create_making_video.py --script making_script.json\n'
            '  python3 scripts/create_making_video.py --images screenshots/ --narration narration.txt\n'
            '  python3 scripts/create_making_video.py --script script.json --bgm song.mp3 -o making.mp4\n'
        ),
    )

    # 스크립트 모드
    parser.add_argument("--script", "-s", help="나레이션 스크립트 JSON 파일")

    # 간단 모드
    parser.add_argument("--images", "-i", help="스크린샷 이미지 디렉토리")
    parser.add_argument("--narration", "-n", help="나레이션 텍스트 파일 (한 줄 = 한 슬라이드)")

    # 공통
    parser.add_argument("--bgm", "-b", help="배경음악 파일 (MP3/WAV)")
    parser.add_argument("--bgm-volume", type=float, default=0.15, help="배경음악 볼륨 (기본: 0.15)")
    parser.add_argument("--voice", default="ko-KR-InJoonNeural", help="TTS 음성 (기본: ko-KR-InJoonNeural)")
    parser.add_argument("--output", "-o", default="making.mp4", help="출력 MP4 경로 (기본: making.mp4)")

    args = parser.parse_args()

    # ffmpeg 확인
    if not check_ffmpeg():
        print("[오류] ffmpeg/ffprobe가 설치되어 있지 않습니다.")
        sys.exit(1)

    # 스크립트 로드
    if args.script:
        script_path = Path(args.script).resolve()
        if not script_path.is_file():
            print(f"[오류] 스크립트 파일 없음: {script_path}")
            sys.exit(1)
        script_data = load_script(script_path)
    elif args.images:
        images_dir = Path(args.images).resolve()
        if not images_dir.is_dir():
            print(f"[오류] 이미지 디렉토리 없음: {images_dir}")
            sys.exit(1)
        narration_file = Path(args.narration).resolve() if args.narration else None
        script_data = load_simple_mode(images_dir, narration_file)
    else:
        parser.error("--script 또는 --images 중 하나를 지정하세요.")

    # CLI 인자로 오버라이드
    if args.voice:
        script_data["voice"] = args.voice
    if args.bgm_volume != 0.15:
        script_data["bgm_volume"] = args.bgm_volume

    bgm_override = Path(args.bgm).resolve() if args.bgm else None
    output_path = Path(args.output).resolve()

    print("=" * 60)
    print("  메이킹 영상 생성")
    print(f"  슬라이드: {len(script_data.get('slides', []))}장")
    print(f"  음성: {script_data.get('voice', 'ko-KR-InJoonNeural')}")
    print(f"  BGM: {bgm_override or script_data.get('bgm', '없음')}")
    print(f"  출력: {output_path}")
    print("=" * 60)

    success = create_making_video(script_data, output_path, bgm_override)

    if not success:
        print("\n  메이킹 영상 생성 실패.")
        sys.exit(1)


if __name__ == "__main__":
    main()
