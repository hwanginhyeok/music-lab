#!/usr/bin/env python3
"""
Electric Feelings 앨범 — 배치 생성 준비 스크립트
"""
import re
import stat
from pathlib import Path

SRC = Path("docs/albums/electric_feelings_suno.md")
ALBUM_DIR = Path("songs/20_electric_feelings")
BATCH_SCRIPT = Path("scripts/batch_electric_feelings.sh")

TRACK_SLUGS = {
    1:  "01_sunburn",
    2:  "02_chase",
    3:  "03_gasoline",
    4:  "04_neon_city",
    5:  "05_right_now",
    6:  "06_crash_into_me",
    7:  "07_electric",
    8:  "08_drive_fast",
    9:  "09_running_out",
    10: "10_satellite",
    11: "11_alive",
    12: "12_wildfire",
    13: "13_up_all_night",
    14: "14_frequency",
    15: "15_last_summer",
}

content = SRC.read_text(encoding="utf-8")
track_blocks = re.split(r'\n(?=## Track \d+)', content)

parsed = []
for block in track_blocks:
    m = re.match(r'## Track (\d+) — (.+)', block)
    if not m:
        continue

    num = int(m.group(1))
    title = m.group(2).split('(')[0].strip()  # "(서프 록 팝)" 같은 괄호 제거

    style_m = re.search(r'\*\*Style[^:]*:\*\*\s*```\s*\n(.*?)\n```', block, re.DOTALL)
    style = style_m.group(1).strip() if style_m else ""

    lyrics_m = re.search(r'\*\*Lyrics:\*\*\s*```\s*\n(.*?)\n```', block, re.DOTALL)
    lyrics = lyrics_m.group(1).strip() if lyrics_m else ""

    slug = TRACK_SLUGS.get(num, f"{num:02d}_unknown")
    parsed.append({"num": num, "title": title, "slug": slug, "style": style, "lyrics": lyrics})

print(f"파싱 완료: {len(parsed)}곡")

for t in parsed:
    track_dir = ALBUM_DIR / "tracks" / t["slug"]
    track_dir.mkdir(parents=True, exist_ok=True)
    (track_dir / "raw").mkdir(exist_ok=True)

    prompt = f"## Style of Music\n```\n{t['style']}\n```\n\n## Lyrics\n{t['lyrics']}\n"
    (track_dir / "suno_prompt.md").write_text(prompt, encoding="utf-8")
    print(f"  ✅ Track {t['num']:02d} {t['slug']}: {t['title']}")

lines = [
    "#!/bin/bash",
    "# Electric Feelings — 15곡 시리얼 Suno 생성",
    "set -u",
    "cd /home/window11/music-lab",
    "",
    'LOG="/tmp/suno_electric_feelings.log"',
    'echo "=== Electric Feelings 배치 생성 시작 $(date +%T) ===" > "$LOG"',
    "",
]

for t in parsed:
    slug = t["slug"]
    num = t["num"]
    title = t["title"]
    prompt_file = f"songs/20_electric_feelings/tracks/{slug}/suno_prompt.md"
    dest = f"songs/20_electric_feelings/tracks/{slug}/raw"

    lines += [
        f'echo "" >> "$LOG"',
        f'echo "=== Track {num:02d}: {title} ===" >> "$LOG"',
        "",
        f'python3 suno_pipeline.py \\',
        f'    --title "{title}" \\',
        f'    --prompt-file "{prompt_file}" \\',
        f'    --skip-drive \\',
        f'    --model v5.5 >> "$LOG" 2>&1',
        "",
        "LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)",
        'if [ -n "$LATEST_MP3" ]; then',
        f'    mkdir -p "{dest}"',
        f'    mv "$LATEST_MP3" "{dest}/v1.mp3"',
        '    UUID=$(basename "$LATEST_MP3" .mp3)',
        f'    [ -f "data/suno/${{UUID}}_cover.jpeg" ] && mv "data/suno/${{UUID}}_cover.jpeg" "{dest}/v1_cover.jpeg"',
        f'    echo "  -> {dest}/v1.mp3" >> "$LOG"',
        "else",
        '    echo "  ⚠️ mp3 없음" >> "$LOG"',
        "fi",
        "",
        'echo "  완료: $(date +%T)" >> "$LOG"',
        "",
    ]

lines += [
    'echo "" >> "$LOG"',
    'echo "=== 전체 완료 $(date +%T) ===" >> "$LOG"',
    'cat "$LOG"',
]

BATCH_SCRIPT.write_text("\n".join(lines), encoding="utf-8")
BATCH_SCRIPT.chmod(BATCH_SCRIPT.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
print(f"\n배치 스크립트: {BATCH_SCRIPT}")
