#!/bin/bash
# Electric Feelings — 15곡 시리얼 Suno 생성
set -u
cd /home/window11/music-lab

LOG="/tmp/suno_electric_feelings.log"
echo "=== Electric Feelings 배치 생성 시작 $(date +%T) ===" > "$LOG"

echo "" >> "$LOG"
echo "=== Track 01: Sunburn ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Sunburn" \
    --prompt-file "songs/20_electric_feelings/tracks/01_sunburn/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/20_electric_feelings/tracks/01_sunburn/raw"
    mv "$LATEST_MP3" "songs/20_electric_feelings/tracks/01_sunburn/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/20_electric_feelings/tracks/01_sunburn/raw/v1_cover.jpeg"
    echo "  -> songs/20_electric_feelings/tracks/01_sunburn/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 02: Chase ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Chase" \
    --prompt-file "songs/20_electric_feelings/tracks/02_chase/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/20_electric_feelings/tracks/02_chase/raw"
    mv "$LATEST_MP3" "songs/20_electric_feelings/tracks/02_chase/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/20_electric_feelings/tracks/02_chase/raw/v1_cover.jpeg"
    echo "  -> songs/20_electric_feelings/tracks/02_chase/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 03: Gasoline ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Gasoline" \
    --prompt-file "songs/20_electric_feelings/tracks/03_gasoline/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/20_electric_feelings/tracks/03_gasoline/raw"
    mv "$LATEST_MP3" "songs/20_electric_feelings/tracks/03_gasoline/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/20_electric_feelings/tracks/03_gasoline/raw/v1_cover.jpeg"
    echo "  -> songs/20_electric_feelings/tracks/03_gasoline/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 04: Neon City ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Neon City" \
    --prompt-file "songs/20_electric_feelings/tracks/04_neon_city/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/20_electric_feelings/tracks/04_neon_city/raw"
    mv "$LATEST_MP3" "songs/20_electric_feelings/tracks/04_neon_city/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/20_electric_feelings/tracks/04_neon_city/raw/v1_cover.jpeg"
    echo "  -> songs/20_electric_feelings/tracks/04_neon_city/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 05: Right Now ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Right Now" \
    --prompt-file "songs/20_electric_feelings/tracks/05_right_now/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/20_electric_feelings/tracks/05_right_now/raw"
    mv "$LATEST_MP3" "songs/20_electric_feelings/tracks/05_right_now/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/20_electric_feelings/tracks/05_right_now/raw/v1_cover.jpeg"
    echo "  -> songs/20_electric_feelings/tracks/05_right_now/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 06: Crash Into Me ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Crash Into Me" \
    --prompt-file "songs/20_electric_feelings/tracks/06_crash_into_me/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/20_electric_feelings/tracks/06_crash_into_me/raw"
    mv "$LATEST_MP3" "songs/20_electric_feelings/tracks/06_crash_into_me/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/20_electric_feelings/tracks/06_crash_into_me/raw/v1_cover.jpeg"
    echo "  -> songs/20_electric_feelings/tracks/06_crash_into_me/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 07: Electric ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Electric" \
    --prompt-file "songs/20_electric_feelings/tracks/07_electric/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/20_electric_feelings/tracks/07_electric/raw"
    mv "$LATEST_MP3" "songs/20_electric_feelings/tracks/07_electric/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/20_electric_feelings/tracks/07_electric/raw/v1_cover.jpeg"
    echo "  -> songs/20_electric_feelings/tracks/07_electric/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 08: Drive Fast ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Drive Fast" \
    --prompt-file "songs/20_electric_feelings/tracks/08_drive_fast/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/20_electric_feelings/tracks/08_drive_fast/raw"
    mv "$LATEST_MP3" "songs/20_electric_feelings/tracks/08_drive_fast/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/20_electric_feelings/tracks/08_drive_fast/raw/v1_cover.jpeg"
    echo "  -> songs/20_electric_feelings/tracks/08_drive_fast/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 09: Running Out ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Running Out" \
    --prompt-file "songs/20_electric_feelings/tracks/09_running_out/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/20_electric_feelings/tracks/09_running_out/raw"
    mv "$LATEST_MP3" "songs/20_electric_feelings/tracks/09_running_out/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/20_electric_feelings/tracks/09_running_out/raw/v1_cover.jpeg"
    echo "  -> songs/20_electric_feelings/tracks/09_running_out/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 10: Satellite ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Satellite" \
    --prompt-file "songs/20_electric_feelings/tracks/10_satellite/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/20_electric_feelings/tracks/10_satellite/raw"
    mv "$LATEST_MP3" "songs/20_electric_feelings/tracks/10_satellite/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/20_electric_feelings/tracks/10_satellite/raw/v1_cover.jpeg"
    echo "  -> songs/20_electric_feelings/tracks/10_satellite/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 11: Alive ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Alive" \
    --prompt-file "songs/20_electric_feelings/tracks/11_alive/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/20_electric_feelings/tracks/11_alive/raw"
    mv "$LATEST_MP3" "songs/20_electric_feelings/tracks/11_alive/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/20_electric_feelings/tracks/11_alive/raw/v1_cover.jpeg"
    echo "  -> songs/20_electric_feelings/tracks/11_alive/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 12: Wildfire ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Wildfire" \
    --prompt-file "songs/20_electric_feelings/tracks/12_wildfire/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/20_electric_feelings/tracks/12_wildfire/raw"
    mv "$LATEST_MP3" "songs/20_electric_feelings/tracks/12_wildfire/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/20_electric_feelings/tracks/12_wildfire/raw/v1_cover.jpeg"
    echo "  -> songs/20_electric_feelings/tracks/12_wildfire/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 13: Up All Night ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Up All Night" \
    --prompt-file "songs/20_electric_feelings/tracks/13_up_all_night/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/20_electric_feelings/tracks/13_up_all_night/raw"
    mv "$LATEST_MP3" "songs/20_electric_feelings/tracks/13_up_all_night/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/20_electric_feelings/tracks/13_up_all_night/raw/v1_cover.jpeg"
    echo "  -> songs/20_electric_feelings/tracks/13_up_all_night/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 14: Frequency ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Frequency" \
    --prompt-file "songs/20_electric_feelings/tracks/14_frequency/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/20_electric_feelings/tracks/14_frequency/raw"
    mv "$LATEST_MP3" "songs/20_electric_feelings/tracks/14_frequency/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/20_electric_feelings/tracks/14_frequency/raw/v1_cover.jpeg"
    echo "  -> songs/20_electric_feelings/tracks/14_frequency/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 15: Last Summer ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Last Summer" \
    --prompt-file "songs/20_electric_feelings/tracks/15_last_summer/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/20_electric_feelings/tracks/15_last_summer/raw"
    mv "$LATEST_MP3" "songs/20_electric_feelings/tracks/15_last_summer/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/20_electric_feelings/tracks/15_last_summer/raw/v1_cover.jpeg"
    echo "  -> songs/20_electric_feelings/tracks/15_last_summer/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== 전체 완료 $(date +%T) ===" >> "$LOG"
cat "$LOG"