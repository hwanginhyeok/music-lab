#!/usr/bin/env python3
"""
YouTube 썸네일 자동 생성 (Pillow).

어두운 배경 그라데이션 + 큰 한글 제목 + 영문 서브타이틀 + 장르 태그.
배경 이미지가 있으면 어두운 오버레이를 입혀서 사용.

사용법:
  # 곡 디렉토리만 지정 (manifest.json에서 정보 추출)
  python3 scripts/generate_thumbnail.py songs/01_봄이라고_부를게/

  # 옵션 직접 지정
  python3 scripts/generate_thumbnail.py songs/01_봄이라고_부를게/ \\
      --title "봄이라고 부를게" --subtitle "Korean Indie Pop"

  # 배경 이미지 + 장르 태그
  python3 scripts/generate_thumbnail.py songs/01_봄이라고_부를게/ \\
      --background cover.jpg --tags "Jazz,Ballad,Korean"

출력:
  video/thumbnail.jpg (1280x720, JPEG)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Pillow 임포트 (미설치 시 안내)
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("[오류] Pillow가 설치되어 있지 않습니다.")
    print("  pip install Pillow")
    sys.exit(1)


# 썸네일 크기 (YouTube 권장)
WIDTH = 1280
HEIGHT = 720


def find_font(bold: bool = False) -> ImageFont.FreeTypeFont | None:
    """시스템 한글 폰트 탐색. 없으면 기본 폰트 사용."""
    if bold:
        candidates = [
            "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
            "/usr/share/fonts/nanum/NanumGothicBold.ttf",
            "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
            "/usr/share/fonts/nanum/NanumGothic.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]

    for path in candidates:
        if Path(path).is_file():
            return path
    return None


def load_info_from_manifest(song_dir: Path) -> dict:
    """manifest.json에서 곡 정보 추출."""
    manifest_path = song_dir / "manifest.json"
    info = {"title": "", "subgenre": "", "theme": ""}
    if manifest_path.is_file():
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            info["title"] = data.get("title", "")
            info["subgenre"] = data.get("subgenre", "")
            info["theme"] = data.get("theme", "")
        except (json.JSONDecodeError, KeyError):
            pass
    return info


def create_gradient_background() -> Image.Image:
    """어두운 그라데이션 배경 생성 (상단 진한 남색 -> 하단 검정)."""
    img = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(img)

    # 상단: 진한 남색 (25, 25, 60) -> 하단: 거의 검정 (10, 10, 20)
    for y in range(HEIGHT):
        ratio = y / HEIGHT
        r = int(25 * (1 - ratio) + 10 * ratio)
        g = int(25 * (1 - ratio) + 10 * ratio)
        b = int(60 * (1 - ratio) + 20 * ratio)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))

    return img


def darken_image(img: Image.Image, factor: float = 0.4) -> Image.Image:
    """이미지에 어두운 오버레이 적용."""
    img = img.convert("RGB")
    overlay = Image.new("RGB", img.size, (0, 0, 0))
    return Image.blend(img, overlay, 1 - factor)


def draw_text_with_shadow(
    draw: ImageDraw.Draw,
    position: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int],
    shadow_offset: int = 3,
) -> None:
    """그림자 효과로 텍스트 그리기."""
    x, y = position
    # 그림자
    draw.text((x + shadow_offset, y + shadow_offset), text, font=font, fill=(0, 0, 0))
    # 본 텍스트
    draw.text((x, y), text, font=font, fill=fill)


def generate_thumbnail(
    song_dir: Path,
    title: str,
    subtitle: str = "",
    tags: str = "",
    background_path: Path | None = None,
    output_path: Path | None = None,
) -> Path:
    """YouTube 썸네일 생성.

    Args:
        song_dir: 곡 디렉토리
        title: 메인 제목 (한글)
        subtitle: 서브타이틀 (영문)
        tags: 장르 태그 (쉼표 구분)
        background_path: 배경 이미지 경로 (None이면 그라데이션)
        output_path: 출력 경로 (None이면 song_dir/video/thumbnail.jpg)

    Returns:
        생성된 썸네일 경로
    """
    # 배경 준비
    if background_path and background_path.is_file():
        img = Image.open(background_path)
        img = img.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
        img = darken_image(img, factor=0.4)
        print(f"  배경: {background_path.name} (어두운 오버레이 적용)")
    else:
        img = create_gradient_background()
        print(f"  배경: 기본 그라데이션")

    draw = ImageDraw.Draw(img)

    # 폰트 로드
    bold_font_path = find_font(bold=True)
    regular_font_path = find_font(bold=False)

    # 메인 제목 (큰 글씨)
    if bold_font_path:
        title_font = ImageFont.truetype(bold_font_path, 72)
    else:
        title_font = ImageFont.load_default()

    # 서브타이틀 (중간 글씨)
    if regular_font_path:
        subtitle_font = ImageFont.truetype(regular_font_path, 36)
    else:
        subtitle_font = ImageFont.load_default()

    # 태그 (작은 글씨)
    if regular_font_path:
        tag_font = ImageFont.truetype(regular_font_path, 28)
    else:
        tag_font = ImageFont.load_default()

    # 제목이 너무 길면 줄바꿈 처리
    title_lines = []
    if len(title) > 12:
        # 중간점에서 나누기
        mid = len(title) // 2
        # 공백 기준으로 가장 가까운 분할점 찾기
        split_point = title.rfind(" ", 0, mid + 3)
        if split_point == -1:
            split_point = mid
        title_lines = [title[:split_point].strip(), title[split_point:].strip()]
        title_lines = [line for line in title_lines if line]
    else:
        title_lines = [title]

    # 레이아웃 계산 (수직 중앙 정렬)
    total_height = 0
    title_bboxes = []
    for line in title_lines:
        bbox = draw.textbbox((0, 0), line, font=title_font)
        h = bbox[3] - bbox[1]
        title_bboxes.append((bbox, h))
        total_height += h + 10  # 줄 간격

    if subtitle:
        sub_bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
        sub_h = sub_bbox[3] - sub_bbox[1]
        total_height += sub_h + 30  # 제목-서브타이틀 간격
    else:
        sub_h = 0

    if tags:
        tag_text = "  |  ".join(t.strip() for t in tags.split(","))
        tag_bbox = draw.textbbox((0, 0), tag_text, font=tag_font)
        tag_h = tag_bbox[3] - tag_bbox[1]
        total_height += tag_h + 20
    else:
        tag_h = 0

    # 시작 y 좌표 (수직 중앙)
    start_y = (HEIGHT - total_height) // 2

    # 제목 그리기
    y = start_y
    for i, line in enumerate(title_lines):
        bbox, h = title_bboxes[i]
        text_w = bbox[2] - bbox[0]
        x = (WIDTH - text_w) // 2
        draw_text_with_shadow(draw, (x, y), line, title_font, fill=(255, 255, 255), shadow_offset=4)
        y += h + 10

    # 구분선
    y += 15
    line_width = min(400, WIDTH // 3)
    draw.line(
        [(WIDTH // 2 - line_width // 2, y), (WIDTH // 2 + line_width // 2, y)],
        fill=(200, 180, 120),  # 골드색 구분선
        width=2,
    )
    y += 15

    # 서브타이틀 그리기
    if subtitle:
        sub_bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
        text_w = sub_bbox[2] - sub_bbox[0]
        x = (WIDTH - text_w) // 2
        draw_text_with_shadow(draw, (x, y), subtitle, subtitle_font, fill=(200, 200, 200), shadow_offset=2)
        y += sub_h + 20

    # 태그 그리기
    if tags:
        tag_text = "  |  ".join(t.strip() for t in tags.split(","))
        tag_bbox = draw.textbbox((0, 0), tag_text, font=tag_font)
        text_w = tag_bbox[2] - tag_bbox[0]
        x = (WIDTH - text_w) // 2
        draw_text_with_shadow(draw, (x, y), tag_text, tag_font, fill=(150, 150, 180), shadow_offset=2)

    # 저장
    if output_path is None:
        output_path = song_dir / "video" / "thumbnail.jpg"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    img.save(str(output_path), "JPEG", quality=95)
    size_kb = output_path.stat().st_size / 1024
    print(f"  출력: {output_path}")
    print(f"  크기: {size_kb:.0f} KB")
    print(f"  해상도: {WIDTH}x{HEIGHT}")

    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="YouTube 썸네일 자동 생성 (Pillow)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="예시:\n"
               '  python3 scripts/generate_thumbnail.py songs/01_봄이라고_부를게/\n'
               '  python3 scripts/generate_thumbnail.py songs/01_봄이라고_부를게/ '
               '--title "봄이라고 부를게" --subtitle "Korean Indie Pop"\n',
    )
    parser.add_argument("song_dir", help="곡 디렉토리 경로")
    parser.add_argument("--title", help="메인 제목 (한글)")
    parser.add_argument("--subtitle", help="영문 서브타이틀", default="")
    parser.add_argument("--tags", help="장르 태그 (쉼표 구분)", default="")
    parser.add_argument("--background", help="배경 이미지 경로")
    parser.add_argument("--output", help="출력 경로 (기본: video/thumbnail.jpg)")
    args = parser.parse_args()

    song_dir = Path(args.song_dir).resolve()
    if not song_dir.is_dir():
        print(f"[오류] 곡 디렉토리 없음: {song_dir}")
        sys.exit(1)

    # manifest.json에서 기본값 로드
    info = load_info_from_manifest(song_dir)
    title = args.title or info["title"] or song_dir.name
    subtitle = args.subtitle or info.get("subgenre", "").title()
    tags = args.tags

    background_path = Path(args.background) if args.background else song_dir / "cover.jpg"
    if not background_path.is_file():
        background_path = None

    output_path = Path(args.output) if args.output else None

    print("=" * 60)
    print("  YouTube 썸네일 생성")
    print(f"  제목: {title}")
    if subtitle:
        print(f"  서브타이틀: {subtitle}")
    if tags:
        print(f"  태그: {tags}")
    print("=" * 60)

    generate_thumbnail(
        song_dir=song_dir,
        title=title,
        subtitle=subtitle,
        tags=tags,
        background_path=background_path,
        output_path=output_path,
    )

    print("\n  썸네일 생성 완료!")


if __name__ == "__main__":
    main()
