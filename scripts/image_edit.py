"""
music-lab 이미지 편집 파이프라인
Pillow + OpenCV + rembg 기반

사용법:
  python3 scripts/image_edit.py --help

기능:
  --split-ab       : A/B 두 장면을 개별 파일로 분리 (좌/우 절반 크롭)
  --remove-label   : 이미지 상단 A/B 텍스트 레이블 제거 (배경색 채우기)
  --thumbnail      : YouTube 썸네일 최적화 (1280x720, JPG)
  --brightness N   : 밝기 조정 (기본 1.0, 높을수록 밝음)
  --contrast N     : 대비 조정 (기본 1.0)
  --saturation N   : 채도 조정 (기본 1.0)
  --remove-bg      : 배경 제거 (rembg)
  --show-info      : 이미지 정보만 출력
"""

import argparse
import sys
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw


def load_image(path: str) -> Image.Image:
    return Image.open(path).convert("RGB")


def split_ab(img: Image.Image, output_a: str, output_b: str):
    """좌우 반으로 분리해서 A/B 저장"""
    w, h = img.size
    mid = w // 2
    img_a = img.crop((0, 0, mid, h))
    img_b = img.crop((mid, 0, w, h))
    img_a.save(output_a, quality=95)
    img_b.save(output_b, quality=95)
    print(f"✅ A 저장: {output_a} ({img_a.size})")
    print(f"✅ B 저장: {output_b} ({img_b.size})")


def remove_label(img: Image.Image, label_height: int = 60) -> Image.Image:
    """상단 A/B 텍스트 레이블 제거 — 배경색으로 덮기"""
    result = img.copy()
    draw = ImageDraw.Draw(result)
    # 상단 label_height 픽셀의 평균 색상 샘플링 (가장자리 기준)
    sample = img.crop((0, 0, img.width, label_height))
    pixels = list(sample.getdata())
    avg_r = sum(p[0] for p in pixels) // len(pixels)
    avg_g = sum(p[1] for p in pixels) // len(pixels)
    avg_b = sum(p[2] for p in pixels) // len(pixels)
    bg_color = (avg_r, avg_g, avg_b)
    draw.rectangle([(0, 0), (img.width, label_height)], fill=bg_color)
    print(f"✅ 레이블 제거: 상단 {label_height}px → 배경색 {bg_color} 덮기")
    return result


def thumbnail(img: Image.Image, size=(1280, 720)) -> Image.Image:
    """YouTube 썸네일 최적화: 1280×720, letterbox 없이 중앙 크롭"""
    target_w, target_h = size
    target_ratio = target_w / target_h
    src_ratio = img.width / img.height

    if src_ratio > target_ratio:
        # 원본이 더 넓음 → 좌우 자르기
        new_w = int(img.height * target_ratio)
        offset = (img.width - new_w) // 2
        img = img.crop((offset, 0, offset + new_w, img.height))
    else:
        # 원본이 더 좁음 → 상하 자르기
        new_h = int(img.width / target_ratio)
        offset = (img.height - new_h) // 2
        img = img.crop((0, offset, img.width, offset + new_h))

    img = img.resize(size, Image.LANCZOS)
    print(f"✅ 썸네일 최적화: {size}")
    return img


def adjust(img: Image.Image, brightness=1.0, contrast=1.0, saturation=1.0) -> Image.Image:
    if brightness != 1.0:
        img = ImageEnhance.Brightness(img).enhance(brightness)
    if contrast != 1.0:
        img = ImageEnhance.Contrast(img).enhance(contrast)
    if saturation != 1.0:
        img = ImageEnhance.Color(img).enhance(saturation)
    print(f"✅ 보정: 밝기={brightness} 대비={contrast} 채도={saturation}")
    return img


def remove_bg(img: Image.Image) -> Image.Image:
    try:
        from rembg import remove
        import io
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        result = remove(buf.read())
        return Image.open(io.BytesIO(result)).convert("RGBA")
    except ImportError:
        print("❌ rembg 미설치: pip install rembg")
        return img


def show_info(img: Image.Image):
    print(f"크기: {img.size}")
    print(f"모드: {img.mode}")
    print(f"종횡비: {img.width/img.height:.3f}")
    print(f"YouTube 16:9 기준: {img.width}x{int(img.width*9/16)}")


def main():
    parser = argparse.ArgumentParser(description="music-lab 이미지 편집 파이프라인")
    parser.add_argument("--input", "-i", required=True, help="입력 이미지 경로")
    parser.add_argument("--output", "-o", help="출력 이미지 경로 (기본: input_edited.jpg)")
    parser.add_argument("--split-ab", action="store_true", help="A/B 분리")
    parser.add_argument("--output-a", default=None, help="A 출력 경로")
    parser.add_argument("--output-b", default=None, help="B 출력 경로")
    parser.add_argument("--remove-label", action="store_true", help="상단 A/B 레이블 제거")
    parser.add_argument("--label-height", type=int, default=70, help="레이블 높이 px (기본 70)")
    parser.add_argument("--thumbnail", action="store_true", help="YouTube 썸네일 최적화 (1280x720)")
    parser.add_argument("--brightness", type=float, default=1.0)
    parser.add_argument("--contrast", type=float, default=1.0)
    parser.add_argument("--saturation", type=float, default=1.0)
    parser.add_argument("--remove-bg", action="store_true", help="배경 제거")
    parser.add_argument("--show-info", action="store_true", help="이미지 정보만 출력")
    args = parser.parse_args()

    img = load_image(args.input)
    input_path = Path(args.input)

    if args.show_info:
        show_info(img)
        return

    if args.split_ab:
        out_a = args.output_a or str(input_path.parent / "cover_a.jpg")
        out_b = args.output_b or str(input_path.parent / "cover_b.jpg")
        split_ab(img, out_a, out_b)
        return

    if args.remove_label:
        img = remove_label(img, args.label_height)

    if args.brightness != 1.0 or args.contrast != 1.0 or args.saturation != 1.0:
        img = adjust(img, args.brightness, args.contrast, args.saturation)

    if args.remove_bg:
        img = remove_bg(img)

    if args.thumbnail:
        img = thumbnail(img)

    output = args.output or str(input_path.parent / (input_path.stem + "_edited.jpg"))
    img.save(output, quality=95)
    print(f"✅ 저장: {output} ({img.size})")


if __name__ == "__main__":
    main()
