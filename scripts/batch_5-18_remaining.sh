#!/bin/bash
# 5-18 트랙 02~09 시리얼 생성 + v1/v2 정리
set -u
cd /home/window11/music-lab

# 트랙별 (slug, title, style)
declare -a TRACKS=(
    "02_table_without_you|너 없는 술상 (Table Without You)|late-night smoky jazz, tenor saxophone ballad, BPM 66, D minor to G minor modulation, instrumental, melodic warm soft sax, sax + piano + double bass trio, no drums, Stan Getz Early Autumn style, Lester Young, intimate room mic, acoustic, restrained vibrato"
    "03_last_drink|마지막 한 잔 (Last Drink)|late-night smoky jazz, tenor saxophone ballad, BPM 72, G minor, instrumental, breathy sax tone, sax + piano + double bass + subtle brush drums entering, Ben Webster My One and Only Love style, fade ending, intimate room mic"
    "04_hangover|숙취 (Hangover)|late-night smoky jazz hard bop, BPM 84, F minor, instrumental, dirty pinched tenor saxophone, sax + piano + bass + brush drums + subtle horn pad quartet, slightly off-beat swing groove, Dexter Gordon Cheese Cake style, Hank Mobley"
    "05_3am|새벽 세 시 (3 AM)|late-night smoky jazz, BPM 88, B-flat minor, instrumental, dirty fragmented tenor saxophone with broken phrases, full band sax + piano + bass + brush drums + horn section, dark obsessive mood, Coltrane Ballads dark style, Joe Henderson Inner Urge"
    "06_tie_on_head|머리에 넥타이 (Tie on Head)|late-night smoky jazz hard bop climax, BPM 100, B-flat minor to F minor modulation, instrumental, raw out-side blow tenor saxophone, sax + trumpet counter-solo + piano + bass + drums quintet, peak intensity, Dexter Gordon Body and Soul late solo style, Roland Kirk"
    "07_haejangguk|해장국 (Haejangguk)|late-night smoky jazz, tenor saxophone ballad, BPM 76, F minor to F major parallel modulation, instrumental, warming breathy to clean sax, sax + piano + double bass trio, no drums, Stan Getz Misty style, Coleman Hawkins late ballads"
    "08_glass_down|잔을 엎어놓다 (Glass Down)|late-night smoky jazz duo, tenor saxophone, BPM 78, D major, instrumental, round deliberate decision-tone sax, sax + piano duo only, no bass no drums, Stan Getz Once Upon a Summertime duo style, minimal"
    "09_healed|술병이 다 나았다 (Healed)|late-night smoky jazz, tenor saxophone ballad, BPM 70, D major, instrumental, warm clean sax returning to track 1 tone, sax + piano + double bass trio, Stan Getz Misty style, cyclic resolution, intimate room mic"
)

LOG="/tmp/suno_5-18_batch.log"
echo "=== 5-18 트랙 02~09 시리얼 생성 시작 $(date +%T) ===" > "$LOG"

for entry in "${TRACKS[@]}"; do
    IFS='|' read -r SLUG TITLE STYLE <<< "$entry"
    echo "" >> "$LOG"
    echo "============================================================" >> "$LOG"
    echo "▶ $SLUG | $TITLE" >> "$LOG"
    echo "============================================================" >> "$LOG"

    python3 suno_pipeline.py \
        --title "$TITLE" \
        --style "$STYLE" \
        --instrumental \
        --skip-drive \
        --model v5.5 >> "$LOG" 2>&1

    # 생성된 mp3 찾아서 raw/v1.mp3로 이동
    LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
    if [ -n "$LATEST_MP3" ]; then
        DEST_DIR="songs/18_sulbyeong_natda/tracks/$SLUG/raw"
        mkdir -p "$DEST_DIR"
        mv "$LATEST_MP3" "$DEST_DIR/v1.mp3"
        # 커버도 이동 (있으면)
        UUID=$(basename "$LATEST_MP3" .mp3)
        [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "$DEST_DIR/v1_cover.jpeg"
        echo "  ✅ v1 → $DEST_DIR/v1.mp3" >> "$LOG"
    fi

    # v2 보충 (Suno API에서 같은 title의 짝 곡 찾아 다운로드)
    python3 - <<PY >> "$LOG" 2>&1
import sys, shutil
sys.path.insert(0, '/home/window11/music-lab')
from suno_download import SunoAPI, SUNO_DIR
from pathlib import Path

api = SunoAPI()
songs = api.get_songs()
target_title = """$TITLE"""
matches = [s for s in songs if s.get('title','').strip() == target_title.strip()]
if len(matches) >= 2:
    # 두 번째(나중에 생성된) 곡이 v2 후보
    v2_song = matches[1]
    p = api.download(v2_song, SUNO_DIR)
    if p:
        dest = Path('songs/18_sulbyeong_natda/tracks/$SLUG/raw/v2.mp3')
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(p), str(dest))
        # 커버도
        cover = p.parent / f"{p.stem}_cover.jpeg"
        if cover.exists():
            shutil.move(str(cover), str(dest.parent / 'v2_cover.jpeg'))
        print(f"  ✅ v2 → {dest}")
    else:
        print(f"  ⚠️ v2 다운로드 실패")
else:
    print(f"  ⚠️ v2 짝 곡 못찾음 (matches={len(matches)})")
PY

    echo "  완료: $(date +%T)" >> "$LOG"
done

echo "" >> "$LOG"
echo "=== 전체 완료 $(date +%T) ===" >> "$LOG"
ls -lh songs/18_sulbyeong_natda/tracks/0[2-9]_*/raw/ 2>&1 | tail -40 >> "$LOG"
