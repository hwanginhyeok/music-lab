#!/usr/bin/env python3
"""
YouTube description 합성 유틸 (publish.py / youtube_upload.py / youtube_upload_album.py 공용).

규칙:
  1. description.md 본문 그대로 사용 (500자 컷 X). 없으면 concept.md '## 핵심 컨셉' 폴백.
  2. 앨범(tracks/*/raw/master.mp3 2개 이상)이면 'MM:SS Track N' 챕터 자동 합성.
  3. 단일곡은 챕터 생략.
  4. 최종 description = 본문 + 빈줄 + 챕터 + 빈줄 + '---' + AI_DISCLOSURE.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path


AI_DISCLOSURE = (
    "이 곡은 AI 도구(Suno, Claude)를 활용하여 제작되었습니다.\n"
    "작사, 작곡 컨셉 설계는 사람이, 음원 생성은 AI가 담당했습니다.\n"
    "This song was created with AI tools (Suno, Claude).\n"
    "Human: concept, lyrics, direction | AI: music generation."
)


def load_description(song_dir: Path) -> str:
    """description.md 본문 그대로. 없으면 concept.md '## 핵심 컨셉' 폴백."""
    desc_path = song_dir / "description.md"
    if desc_path.is_file():
        return desc_path.read_text(encoding="utf-8").strip()

    concept_path = song_dir / "concept.md"
    if concept_path.is_file():
        text = concept_path.read_text(encoding="utf-8")
        m = re.search(r"##\s*핵심\s*컨셉\s*\n(.*?)(?=\n##|\Z)", text, re.DOTALL)
        if m:
            return m.group(1).strip()
        m = re.search(r"##.*?\n(.*?)(?=\n##|\Z)", text, re.DOTALL)
        if m:
            return m.group(1).strip()
    return ""


def _ffprobe_duration(path: Path) -> float:
    try:
        r = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            capture_output=True, text=True, timeout=30,
        )
        return float(r.stdout.strip())
    except (subprocess.TimeoutExpired, ValueError, FileNotFoundError):
        return 0.0


def _fmt_ts(seconds: float) -> str:
    s = int(round(seconds))
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{m:02d}:{sec:02d}" if h == 0 else f"{h:d}:{m:02d}:{sec:02d}"


def build_chapters(song_dir: Path) -> list[str]:
    """앨범이면 'MM:SS Track N' 라인 리스트, 단일곡이면 빈 리스트."""
    tracks_dir = song_dir / "tracks"
    if not tracks_dir.is_dir():
        return []
    track_dirs = sorted(
        p for p in tracks_dir.iterdir()
        if p.is_dir() and (p / "raw" / "master.mp3").is_file()
    )
    if len(track_dirs) < 2:
        return []

    lines: list[str] = []
    cum = 0.0
    for i, td in enumerate(track_dirs, 1):
        lines.append(f"{_fmt_ts(cum)} Track {i}")
        cum += _ffprobe_duration(td / "raw" / "master.mp3")
    return lines


def compose_description(song_dir: Path) -> str:
    """[본문] + 빈줄 + [챕터 9줄] + 빈줄 + '---' + [AI_DISCLOSURE]."""
    body = load_description(song_dir)
    chapters = build_chapters(song_dir)

    parts: list[str] = []
    if body:
        parts.append(body)
    if chapters:
        parts.append("\n".join(chapters))
    parts.append("---\n" + AI_DISCLOSURE)
    return "\n\n".join(parts)
