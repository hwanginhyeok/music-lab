#!/bin/bash
# Daylight Hours — 15곡 시리얼 Suno 생성
set -u
cd /home/window11/music-lab

LOG="/tmp/suno_daylight_hours.log"
echo "=== Daylight Hours 배치 생성 시작 $(date +%T) ===" > "$LOG"

echo "" >> "$LOG"
echo "=== Track 01: First Light ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "First Light" \
    --prompt-file "songs/19_daylight_hours/tracks/01_first_light/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/19_daylight_hours/tracks/01_first_light/raw"
    mv "$LATEST_MP3" "songs/19_daylight_hours/tracks/01_first_light/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/19_daylight_hours/tracks/01_first_light/raw/v1_cover.jpeg"
    echo "  -> songs/19_daylight_hours/tracks/01_first_light/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 02: Knock It ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Knock It" \
    --prompt-file "songs/19_daylight_hours/tracks/02_knock_it/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/19_daylight_hours/tracks/02_knock_it/raw"
    mv "$LATEST_MP3" "songs/19_daylight_hours/tracks/02_knock_it/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/19_daylight_hours/tracks/02_knock_it/raw/v1_cover.jpeg"
    echo "  -> songs/19_daylight_hours/tracks/02_knock_it/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 03: Wrong Number ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Wrong Number" \
    --prompt-file "songs/19_daylight_hours/tracks/03_wrong_number/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/19_daylight_hours/tracks/03_wrong_number/raw"
    mv "$LATEST_MP3" "songs/19_daylight_hours/tracks/03_wrong_number/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/19_daylight_hours/tracks/03_wrong_number/raw/v1_cover.jpeg"
    echo "  -> songs/19_daylight_hours/tracks/03_wrong_number/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 04: Midday ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Midday" \
    --prompt-file "songs/19_daylight_hours/tracks/04_midday/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/19_daylight_hours/tracks/04_midday/raw"
    mv "$LATEST_MP3" "songs/19_daylight_hours/tracks/04_midday/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/19_daylight_hours/tracks/04_midday/raw/v1_cover.jpeg"
    echo "  -> songs/19_daylight_hours/tracks/04_midday/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 05: That Girl ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "That Girl" \
    --prompt-file "songs/19_daylight_hours/tracks/05_that_girl/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/19_daylight_hours/tracks/05_that_girl/raw"
    mv "$LATEST_MP3" "songs/19_daylight_hours/tracks/05_that_girl/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/19_daylight_hours/tracks/05_that_girl/raw/v1_cover.jpeg"
    echo "  -> songs/19_daylight_hours/tracks/05_that_girl/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 06: Say It Now ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Say It Now" \
    --prompt-file "songs/19_daylight_hours/tracks/06_say_it_now/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/19_daylight_hours/tracks/06_say_it_now/raw"
    mv "$LATEST_MP3" "songs/19_daylight_hours/tracks/06_say_it_now/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/19_daylight_hours/tracks/06_say_it_now/raw/v1_cover.jpeg"
    echo "  -> songs/19_daylight_hours/tracks/06_say_it_now/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 07: Burn Down ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Burn Down" \
    --prompt-file "songs/19_daylight_hours/tracks/07_burn_down/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/19_daylight_hours/tracks/07_burn_down/raw"
    mv "$LATEST_MP3" "songs/19_daylight_hours/tracks/07_burn_down/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/19_daylight_hours/tracks/07_burn_down/raw/v1_cover.jpeg"
    echo "  -> songs/19_daylight_hours/tracks/07_burn_down/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 08: Coffee Date ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Coffee Date" \
    --prompt-file "songs/19_daylight_hours/tracks/08_coffee_date/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/19_daylight_hours/tracks/08_coffee_date/raw"
    mv "$LATEST_MP3" "songs/19_daylight_hours/tracks/08_coffee_date/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/19_daylight_hours/tracks/08_coffee_date/raw/v1_cover.jpeg"
    echo "  -> songs/19_daylight_hours/tracks/08_coffee_date/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 09: Golden Hour ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Golden Hour" \
    --prompt-file "songs/19_daylight_hours/tracks/09_golden_hour/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/19_daylight_hours/tracks/09_golden_hour/raw"
    mv "$LATEST_MP3" "songs/19_daylight_hours/tracks/09_golden_hour/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/19_daylight_hours/tracks/09_golden_hour/raw/v1_cover.jpeg"
    echo "  -> songs/19_daylight_hours/tracks/09_golden_hour/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 10: Stay Loud ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Stay Loud" \
    --prompt-file "songs/19_daylight_hours/tracks/10_stay_loud/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/19_daylight_hours/tracks/10_stay_loud/raw"
    mv "$LATEST_MP3" "songs/19_daylight_hours/tracks/10_stay_loud/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/19_daylight_hours/tracks/10_stay_loud/raw/v1_cover.jpeg"
    echo "  -> songs/19_daylight_hours/tracks/10_stay_loud/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 11: Overthinking ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Overthinking" \
    --prompt-file "songs/19_daylight_hours/tracks/11_overthinking/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/19_daylight_hours/tracks/11_overthinking/raw"
    mv "$LATEST_MP3" "songs/19_daylight_hours/tracks/11_overthinking/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/19_daylight_hours/tracks/11_overthinking/raw/v1_cover.jpeg"
    echo "  -> songs/19_daylight_hours/tracks/11_overthinking/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 12: Last Text ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Last Text" \
    --prompt-file "songs/19_daylight_hours/tracks/12_last_text/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/19_daylight_hours/tracks/12_last_text/raw"
    mv "$LATEST_MP3" "songs/19_daylight_hours/tracks/12_last_text/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/19_daylight_hours/tracks/12_last_text/raw/v1_cover.jpeg"
    echo "  -> songs/19_daylight_hours/tracks/12_last_text/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 13: Midnight Rain ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Midnight Rain" \
    --prompt-file "songs/19_daylight_hours/tracks/13_midnight_rain/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/19_daylight_hours/tracks/13_midnight_rain/raw"
    mv "$LATEST_MP3" "songs/19_daylight_hours/tracks/13_midnight_rain/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/19_daylight_hours/tracks/13_midnight_rain/raw/v1_cover.jpeg"
    echo "  -> songs/19_daylight_hours/tracks/13_midnight_rain/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 14: Moving On ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Moving On" \
    --prompt-file "songs/19_daylight_hours/tracks/14_moving_on/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/19_daylight_hours/tracks/14_moving_on/raw"
    mv "$LATEST_MP3" "songs/19_daylight_hours/tracks/14_moving_on/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/19_daylight_hours/tracks/14_moving_on/raw/v1_cover.jpeg"
    echo "  -> songs/19_daylight_hours/tracks/14_moving_on/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 15: Settle Down ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Settle Down" \
    --prompt-file "songs/19_daylight_hours/tracks/15_settle_down/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/19_daylight_hours/tracks/15_settle_down/raw"
    mv "$LATEST_MP3" "songs/19_daylight_hours/tracks/15_settle_down/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/19_daylight_hours/tracks/15_settle_down/raw/v1_cover.jpeg"
    echo "  -> songs/19_daylight_hours/tracks/15_settle_down/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== 전체 완료 $(date +%T) ===" >> "$LOG"
cat "$LOG"