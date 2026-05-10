#!/bin/bash
# 시간여행자 — 20곡 시리얼 Suno 생성
set -u
cd /home/window11/music-lab

LOG="/tmp/suno_시간여행자.log"
echo "=== 시간여행자 배치 생성 시작 $(date +%T) ===" > "$LOG"

echo "" >> "$LOG"
echo "=== Track 01: Pressed and Ready ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Pressed and Ready" \
    --prompt-file "songs/21_시간여행자/tracks/01_pressed_and_ready/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/21_시간여행자/tracks/01_pressed_and_ready/raw"
    mv "$LATEST_MP3" "songs/21_시간여행자/tracks/01_pressed_and_ready/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/21_시간여행자/tracks/01_pressed_and_ready/raw/v1_cover.jpeg"
    echo "  -> songs/21_시간여행자/tracks/01_pressed_and_ready/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 02: A Little at a Time ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "A Little at a Time" \
    --prompt-file "songs/21_시간여행자/tracks/02_a_little_at_a_time/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/21_시간여행자/tracks/02_a_little_at_a_time/raw"
    mv "$LATEST_MP3" "songs/21_시간여행자/tracks/02_a_little_at_a_time/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/21_시간여행자/tracks/02_a_little_at_a_time/raw/v1_cover.jpeg"
    echo "  -> songs/21_시간여행자/tracks/02_a_little_at_a_time/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 03: Already Know the End ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Already Know the End" \
    --prompt-file "songs/21_시간여행자/tracks/03_already_know_the_end/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/21_시간여행자/tracks/03_already_know_the_end/raw"
    mv "$LATEST_MP3" "songs/21_시간여행자/tracks/03_already_know_the_end/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/21_시간여행자/tracks/03_already_know_the_end/raw/v1_cover.jpeg"
    echo "  -> songs/21_시간여행자/tracks/03_already_know_the_end/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 04: Swear on the Z-Drive ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Swear on the Z-Drive" \
    --prompt-file "songs/21_시간여행자/tracks/04_swear_on_the_z_drive/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/21_시간여행자/tracks/04_swear_on_the_z_drive/raw"
    mv "$LATEST_MP3" "songs/21_시간여행자/tracks/04_swear_on_the_z_drive/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/21_시간여행자/tracks/04_swear_on_the_z_drive/raw/v1_cover.jpeg"
    echo "  -> songs/21_시간여행자/tracks/04_swear_on_the_z_drive/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 05: There You Are ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "There You Are" \
    --prompt-file "songs/21_시간여행자/tracks/05_there_you_are/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/21_시간여행자/tracks/05_there_you_are/raw"
    mv "$LATEST_MP3" "songs/21_시간여행자/tracks/05_there_you_are/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/21_시간여행자/tracks/05_there_you_are/raw/v1_cover.jpeg"
    echo "  -> songs/21_시간여행자/tracks/05_there_you_are/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 06: Tape from the Alley ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Tape from the Alley" \
    --prompt-file "songs/21_시간여행자/tracks/06_tape_from_the_alley/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/21_시간여행자/tracks/06_tape_from_the_alley/raw"
    mv "$LATEST_MP3" "songs/21_시간여행자/tracks/06_tape_from_the_alley/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/21_시간여행자/tracks/06_tape_from_the_alley/raw/v1_cover.jpeg"
    echo "  -> songs/21_시간여행자/tracks/06_tape_from_the_alley/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 07: Come With Me ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Come With Me" \
    --prompt-file "songs/21_시간여행자/tracks/07_come_with_me/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/21_시간여행자/tracks/07_come_with_me/raw"
    mv "$LATEST_MP3" "songs/21_시간여행자/tracks/07_come_with_me/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/21_시간여행자/tracks/07_come_with_me/raw/v1_cover.jpeg"
    echo "  -> songs/21_시간여행자/tracks/07_come_with_me/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 08: Bottom to the Top ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Bottom to the Top" \
    --prompt-file "songs/21_시간여행자/tracks/08_bottom_to_the_top/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/21_시간여행자/tracks/08_bottom_to_the_top/raw"
    mv "$LATEST_MP3" "songs/21_시간여행자/tracks/08_bottom_to_the_top/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/21_시간여행자/tracks/08_bottom_to_the_top/raw/v1_cover.jpeg"
    echo "  -> songs/21_시간여행자/tracks/08_bottom_to_the_top/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 09: Underdog Entrance ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Underdog Entrance" \
    --prompt-file "songs/21_시간여행자/tracks/09_underdog_entrance/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/21_시간여행자/tracks/09_underdog_entrance/raw"
    mv "$LATEST_MP3" "songs/21_시간여행자/tracks/09_underdog_entrance/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/21_시간여행자/tracks/09_underdog_entrance/raw/v1_cover.jpeg"
    echo "  -> songs/21_시간여행자/tracks/09_underdog_entrance/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 10: Carolina Rush ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Carolina Rush" \
    --prompt-file "songs/21_시간여행자/tracks/10_carolina_rush/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/21_시간여행자/tracks/10_carolina_rush/raw"
    mv "$LATEST_MP3" "songs/21_시간여행자/tracks/10_carolina_rush/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/21_시간여행자/tracks/10_carolina_rush/raw/v1_cover.jpeg"
    echo "  -> songs/21_시간여행자/tracks/10_carolina_rush/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 11: No Interruption Z ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "No Interruption Z" \
    --prompt-file "songs/21_시간여행자/tracks/11_no_interruption_z/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/21_시간여행자/tracks/11_no_interruption_z/raw"
    mv "$LATEST_MP3" "songs/21_시간여행자/tracks/11_no_interruption_z/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/21_시간여행자/tracks/11_no_interruption_z/raw/v1_cover.jpeg"
    echo "  -> songs/21_시간여행자/tracks/11_no_interruption_z/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 12: UPS DOWNS Z ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "UPS DOWNS Z" \
    --prompt-file "songs/21_시간여행자/tracks/12_ups_downs_z/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/21_시간여행자/tracks/12_ups_downs_z/raw"
    mv "$LATEST_MP3" "songs/21_시간여행자/tracks/12_ups_downs_z/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/21_시간여행자/tracks/12_ups_downs_z/raw/v1_cover.jpeg"
    echo "  -> songs/21_시간여행자/tracks/12_ups_downs_z/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 13: Wrong Timeline Goodbye ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Wrong Timeline Goodbye" \
    --prompt-file "songs/21_시간여행자/tracks/13_wrong_timeline_goodbye/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/21_시간여행자/tracks/13_wrong_timeline_goodbye/raw"
    mv "$LATEST_MP3" "songs/21_시간여행자/tracks/13_wrong_timeline_goodbye/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/21_시간여행자/tracks/13_wrong_timeline_goodbye/raw/v1_cover.jpeg"
    echo "  -> songs/21_시간여행자/tracks/13_wrong_timeline_goodbye/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 14: Coolest Kid in Zaun ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Coolest Kid in Zaun" \
    --prompt-file "songs/21_시간여행자/tracks/14_coolest_kid_in_zaun/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/21_시간여행자/tracks/14_coolest_kid_in_zaun/raw"
    mv "$LATEST_MP3" "songs/21_시간여행자/tracks/14_coolest_kid_in_zaun/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/21_시간여행자/tracks/14_coolest_kid_in_zaun/raw/v1_cover.jpeg"
    echo "  -> songs/21_시간여행자/tracks/14_coolest_kid_in_zaun/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 15: Get Out of My Way ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Get Out of My Way" \
    --prompt-file "songs/21_시간여행자/tracks/15_get_out_of_my_way/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/21_시간여행자/tracks/15_get_out_of_my_way/raw"
    mv "$LATEST_MP3" "songs/21_시간여행자/tracks/15_get_out_of_my_way/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/21_시간여행자/tracks/15_get_out_of_my_way/raw/v1_cover.jpeg"
    echo "  -> songs/21_시간여행자/tracks/15_get_out_of_my_way/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 16: Look What You Make Me Do ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Look What You Make Me Do" \
    --prompt-file "songs/21_시간여행자/tracks/16_look_what_you_make_me_do/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/21_시간여행자/tracks/16_look_what_you_make_me_do/raw"
    mv "$LATEST_MP3" "songs/21_시간여행자/tracks/16_look_what_you_make_me_do/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/21_시간여행자/tracks/16_look_what_you_make_me_do/raw/v1_cover.jpeg"
    echo "  -> songs/21_시간여행자/tracks/16_look_what_you_make_me_do/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 17: Running ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Running" \
    --prompt-file "songs/21_시간여행자/tracks/17_running/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/21_시간여행자/tracks/17_running/raw"
    mv "$LATEST_MP3" "songs/21_시간여행자/tracks/17_running/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/21_시간여행자/tracks/17_running/raw/v1_cover.jpeg"
    echo "  -> songs/21_시간여행자/tracks/17_running/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 18: Still Here With You ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Still Here With You" \
    --prompt-file "songs/21_시간여행자/tracks/18_still_here_with_you/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/21_시간여행자/tracks/18_still_here_with_you/raw"
    mv "$LATEST_MP3" "songs/21_시간여행자/tracks/18_still_here_with_you/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/21_시간여행자/tracks/18_still_here_with_you/raw/v1_cover.jpeg"
    echo "  -> songs/21_시간여행자/tracks/18_still_here_with_you/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 19: Look Twice ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Look Twice" \
    --prompt-file "songs/21_시간여행자/tracks/19_look_twice/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/21_시간여행자/tracks/19_look_twice/raw"
    mv "$LATEST_MP3" "songs/21_시간여행자/tracks/19_look_twice/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/21_시간여행자/tracks/19_look_twice/raw/v1_cover.jpeg"
    echo "  -> songs/21_시간여행자/tracks/19_look_twice/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== Track 20: Tease Me, Time ===" >> "$LOG"

python3 suno_pipeline.py \
    --title "Tease Me, Time" \
    --prompt-file "songs/21_시간여행자/tracks/20_tease_me_time/suno_prompt.md" \
    --skip-drive \
    --model v5.5 >> "$LOG" 2>&1

LATEST_MP3=$(ls -t data/suno/*.mp3 2>/dev/null | head -1)
if [ -n "$LATEST_MP3" ]; then
    mkdir -p "songs/21_시간여행자/tracks/20_tease_me_time/raw"
    mv "$LATEST_MP3" "songs/21_시간여행자/tracks/20_tease_me_time/raw/v1.mp3"
    UUID=$(basename "$LATEST_MP3" .mp3)
    [ -f "data/suno/${UUID}_cover.jpeg" ] && mv "data/suno/${UUID}_cover.jpeg" "songs/21_시간여행자/tracks/20_tease_me_time/raw/v1_cover.jpeg"
    echo "  -> songs/21_시간여행자/tracks/20_tease_me_time/raw/v1.mp3" >> "$LOG"
else
    echo "  ⚠️ mp3 없음" >> "$LOG"
fi

echo "  완료: $(date +%T)" >> "$LOG"

echo "" >> "$LOG"
echo "=== 전체 완료 $(date +%T) ===" >> "$LOG"
cat "$LOG"