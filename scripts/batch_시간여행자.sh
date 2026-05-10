#!/bin/bash
# 시간여행자 — 20곡 시리얼 Suno 생성
set -u
cd /home/window11/music-lab

LOG="/tmp/suno_시간여행자.log"
echo "=== 시간여행자 배치 생성 시작 $(date +%T) ===" > "$LOG"

echo "" >> "$LOG"
echo "=== Track 01: Slow Reverse ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Slow Reverse" \
    --prompt-file "songs/21_시간여행자/tracks/01_slow_reverse/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/21_시간여행자/tracks/01_slow_reverse/raw"
    mv "$LATEST_MP3" "songs/21_시간여행자/tracks/01_slow_reverse/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/21_시간여행자/tracks/01_slow_reverse/raw/v1_cover.jpeg"
    echo "  -> songs/21_시간여행자/tracks/01_slow_reverse/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 02: Waterline ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Waterline" \
    --prompt-file "songs/21_시간여행자/tracks/02_waterline/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/21_시간여행자/tracks/02_waterline/raw"
    mv "$LATEST_MP3" "songs/21_시간여행자/tracks/02_waterline/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/21_시간여행자/tracks/02_waterline/raw/v1_cover.jpeg"
    echo "  -> songs/21_시간여행자/tracks/02_waterline/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 03: Don't Rewind ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Don't Rewind" \
    --prompt-file "songs/21_시간여행자/tracks/03_dont_rewind/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/21_시간여행자/tracks/03_dont_rewind/raw"
    mv "$LATEST_MP3" "songs/21_시간여행자/tracks/03_dont_rewind/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/21_시간여행자/tracks/03_dont_rewind/raw/v1_cover.jpeg"
    echo "  -> songs/21_시간여행자/tracks/03_dont_rewind/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 04: Alley Summer ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Alley Summer" \
    --prompt-file "songs/21_시간여행자/tracks/04_alley_summer/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/21_시간여행자/tracks/04_alley_summer/raw"
    mv "$LATEST_MP3" "songs/21_시간여행자/tracks/04_alley_summer/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/21_시간여행자/tracks/04_alley_summer/raw/v1_cover.jpeg"
    echo "  -> songs/21_시간여행자/tracks/04_alley_summer/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 05: VHS of You ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "VHS of You" \
    --prompt-file "songs/21_시간여행자/tracks/05_vhs_of_you/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/21_시간여행자/tracks/05_vhs_of_you/raw"
    mv "$LATEST_MP3" "songs/21_시간여행자/tracks/05_vhs_of_you/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/21_시간여행자/tracks/05_vhs_of_you/raw/v1_cover.jpeg"
    echo "  -> songs/21_시간여행자/tracks/05_vhs_of_you/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 06: Across the Skyline ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Across the Skyline" \
    --prompt-file "songs/21_시간여행자/tracks/06_across_the_skyline/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/21_시간여행자/tracks/06_across_the_skyline/raw"
    mv "$LATEST_MP3" "songs/21_시간여행자/tracks/06_across_the_skyline/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/21_시간여행자/tracks/06_across_the_skyline/raw/v1_cover.jpeg"
    echo "  -> songs/21_시간여행자/tracks/06_across_the_skyline/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 07: What's Your Motive ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "What's Your Motive" \
    --prompt-file "songs/21_시간여행자/tracks/07_whats_your_motive/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/21_시간여행자/tracks/07_whats_your_motive/raw"
    mv "$LATEST_MP3" "songs/21_시간여행자/tracks/07_whats_your_motive/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/21_시간여행자/tracks/07_whats_your_motive/raw/v1_cover.jpeg"
    echo "  -> songs/21_시간여행자/tracks/07_whats_your_motive/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 08: Drive Lights ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Drive Lights" \
    --prompt-file "songs/21_시간여행자/tracks/08_drive_lights/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/21_시간여행자/tracks/08_drive_lights/raw"
    mv "$LATEST_MP3" "songs/21_시간여행자/tracks/08_drive_lights/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/21_시간여행자/tracks/08_drive_lights/raw/v1_cover.jpeg"
    echo "  -> songs/21_시간여행자/tracks/08_drive_lights/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 09: TicToc Zaun ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "TicToc Zaun" \
    --prompt-file "songs/21_시간여행자/tracks/09_tictoc_zaun/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/21_시간여행자/tracks/09_tictoc_zaun/raw"
    mv "$LATEST_MP3" "songs/21_시간여행자/tracks/09_tictoc_zaun/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/21_시간여행자/tracks/09_tictoc_zaun/raw/v1_cover.jpeg"
    echo "  -> songs/21_시간여행자/tracks/09_tictoc_zaun/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 10: Hate You for Forever ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Hate You for Forever" \
    --prompt-file "songs/21_시간여행자/tracks/10_hate_you_for_forever/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/21_시간여행자/tracks/10_hate_you_for_forever/raw"
    mv "$LATEST_MP3" "songs/21_시간여행자/tracks/10_hate_you_for_forever/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/21_시간여행자/tracks/10_hate_you_for_forever/raw/v1_cover.jpeg"
    echo "  -> songs/21_시간여행자/tracks/10_hate_you_for_forever/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 11: Getting Over Jinx ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Getting Over Jinx" \
    --prompt-file "songs/21_시간여행자/tracks/11_getting_over_jinx/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/21_시간여행자/tracks/11_getting_over_jinx/raw"
    mv "$LATEST_MP3" "songs/21_시간여행자/tracks/11_getting_over_jinx/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/21_시간여행자/tracks/11_getting_over_jinx/raw/v1_cover.jpeg"
    echo "  -> songs/21_시간여행자/tracks/11_getting_over_jinx/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 12: Somebody Broke the Clock ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Somebody Broke the Clock" \
    --prompt-file "songs/21_시간여행자/tracks/12_somebody_broke_the_clock/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/21_시간여행자/tracks/12_somebody_broke_the_clock/raw"
    mv "$LATEST_MP3" "songs/21_시간여행자/tracks/12_somebody_broke_the_clock/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/21_시간여행자/tracks/12_somebody_broke_the_clock/raw/v1_cover.jpeg"
    echo "  -> songs/21_시간여행자/tracks/12_somebody_broke_the_clock/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 13: Hallelujah Powder ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Hallelujah Powder" \
    --prompt-file "songs/21_시간여행자/tracks/13_hallelujah_powder/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/21_시간여행자/tracks/13_hallelujah_powder/raw"
    mv "$LATEST_MP3" "songs/21_시간여행자/tracks/13_hallelujah_powder/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/21_시간여행자/tracks/13_hallelujah_powder/raw/v1_cover.jpeg"
    echo "  -> songs/21_시간여행자/tracks/13_hallelujah_powder/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 14: Hate Me Love Me Anyway ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Hate Me Love Me Anyway" \
    --prompt-file "songs/21_시간여행자/tracks/14_hate_me_love_me_anyway/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/21_시간여행자/tracks/14_hate_me_love_me_anyway/raw"
    mv "$LATEST_MP3" "songs/21_시간여행자/tracks/14_hate_me_love_me_anyway/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/21_시간여행자/tracks/14_hate_me_love_me_anyway/raw/v1_cover.jpeg"
    echo "  -> songs/21_시간여행자/tracks/14_hate_me_love_me_anyway/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 15: Burn the Timeline ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Burn the Timeline" \
    --prompt-file "songs/21_시간여행자/tracks/15_burn_the_timeline/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/21_시간여행자/tracks/15_burn_the_timeline/raw"
    mv "$LATEST_MP3" "songs/21_시간여행자/tracks/15_burn_the_timeline/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/21_시간여행자/tracks/15_burn_the_timeline/raw/v1_cover.jpeg"
    echo "  -> songs/21_시간여행자/tracks/15_burn_the_timeline/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 16: No Interruption Tonight ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "No Interruption Tonight" \
    --prompt-file "songs/21_시간여행자/tracks/16_no_interruption_tonight/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/21_시간여행자/tracks/16_no_interruption_tonight/raw"
    mv "$LATEST_MP3" "songs/21_시간여행자/tracks/16_no_interruption_tonight/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/21_시간여행자/tracks/16_no_interruption_tonight/raw/v1_cover.jpeg"
    echo "  -> songs/21_시간여행자/tracks/16_no_interruption_tonight/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 17: Everything She Lost ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Everything She Lost" \
    --prompt-file "songs/21_시간여행자/tracks/17_everything_she_lost/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/21_시간여행자/tracks/17_everything_she_lost/raw"
    mv "$LATEST_MP3" "songs/21_시간여행자/tracks/17_everything_she_lost/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/21_시간여행자/tracks/17_everything_she_lost/raw/v1_cover.jpeg"
    echo "  -> songs/21_시간여행자/tracks/17_everything_she_lost/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 18: Ups and Downs Z ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Ups and Downs Z" \
    --prompt-file "songs/21_시간여행자/tracks/18_ups_and_downs_z/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/21_시간여행자/tracks/18_ups_and_downs_z/raw"
    mv "$LATEST_MP3" "songs/21_시간여행자/tracks/18_ups_and_downs_z/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/21_시간여행자/tracks/18_ups_and_downs_z/raw/v1_cover.jpeg"
    echo "  -> songs/21_시간여행자/tracks/18_ups_and_downs_z/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 19: Up and Find You ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Up and Find You" \
    --prompt-file "songs/21_시간여행자/tracks/19_up_and_find_you/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/21_시간여행자/tracks/19_up_and_find_you/raw"
    mv "$LATEST_MP3" "songs/21_시간여행자/tracks/19_up_and_find_you/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/21_시간여행자/tracks/19_up_and_find_you/raw/v1_cover.jpeg"
    echo "  -> songs/21_시간여행자/tracks/19_up_and_find_you/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 20: Bite Marks on Time ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Bite Marks on Time" \
    --prompt-file "songs/21_시간여행자/tracks/20_bite_marks_on_time/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/21_시간여행자/tracks/20_bite_marks_on_time/raw"
    mv "$LATEST_MP3" "songs/21_시간여행자/tracks/20_bite_marks_on_time/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/21_시간여행자/tracks/20_bite_marks_on_time/raw/v1_cover.jpeg"
    echo "  -> songs/21_시간여행자/tracks/20_bite_marks_on_time/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== 전체 완료 $(date +%T) ===" >> "$LOG"
cat "$LOG"