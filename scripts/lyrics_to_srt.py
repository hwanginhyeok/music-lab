#!/usr/bin/env python3
"""
가사 텍스트 → SRT 자막 파일 변환.

Suno 곡의 가사를 균등 분할하여 자막 타이밍 생성.
[Verse], [Chorus] 등 섹션 태그는 자막에서 제거.

사용법:
  python3 scripts/lyrics_to_srt.py --lyrics "가사 텍스트" --duration 180 --output lyrics.srt
  python3 scripts/lyrics_to_srt.py --lyrics-file songs/01_봄이라고_부를게/lyrics_v1.md --duration 180
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def lyrics_to_lines(lyrics: str) -> list[str]:
    """가사 텍스트에서 자막 줄 추출. 섹션 태그 제거."""
    lines = []
    for line in lyrics.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        # [Verse], [Chorus], [Bridge] 등 섹션 태그 제거
        if re.match(r"^\[.*\]$", line):
            continue
        # ## 마크다운 헤더 제거
        if line.startswith("#"):
            continue
        # > 인용 제거
        if line.startswith(">"):
            continue
        # --- 구분선 제거
        if line == "---":
            continue
        lines.append(line)
    return lines


def format_srt_time(seconds: float) -> str:
    """초 → SRT 타임스탬프 (HH:MM:SS,mmm)."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def generate_srt(lyrics: str, duration: float, output_path: Path | None = None) -> str:
    """가사 → SRT 자막 생성.

    각 줄을 곡 길이에 맞게 균등 분배.
    빈 줄/섹션 태그 사이에 짧은 간격 추가.
    """
    lines = lyrics_to_lines(lyrics)
    if not lines:
        return ""

    # 각 줄에 균등 시간 분배 (앞뒤 여백 포함)
    margin = min(3.0, duration * 0.05)  # 앞뒤 5% 또는 3초
    available = duration - (margin * 2)
    per_line = available / len(lines)

    srt_entries = []
    for i, line in enumerate(lines):
        start = margin + (i * per_line)
        end = start + per_line - 0.3  # 줄 사이 0.3초 간격
        srt_entries.append(
            f"{i + 1}\n"
            f"{format_srt_time(start)} --> {format_srt_time(end)}\n"
            f"{line}\n"
        )

    srt_content = "\n".join(srt_entries)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(srt_content, encoding="utf-8")
        print(f"  📝 SRT 생성: {output_path} ({len(lines)}줄, {duration:.0f}초)")

    return srt_content


def main():
    parser = argparse.ArgumentParser(description="가사 → SRT 자막 변환")
    parser.add_argument("--lyrics", help="가사 텍스트 (직접 입력)")
    parser.add_argument("--lyrics-file", help="가사 파일 경로")
    parser.add_argument("--duration", type=float, required=True, help="곡 길이 (초)")
    parser.add_argument("--output", "-o", help="출력 SRT 경로")
    args = parser.parse_args()

    if args.lyrics_file:
        lyrics = Path(args.lyrics_file).read_text(encoding="utf-8")
    elif args.lyrics:
        lyrics = args.lyrics
    else:
        print("❌ --lyrics 또는 --lyrics-file 필요")
        sys.exit(1)

    output = Path(args.output) if args.output else Path("output.srt")
    generate_srt(lyrics, args.duration, output)


if __name__ == "__main__":
    main()
