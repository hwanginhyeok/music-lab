# Finished Tasks

## 2026-05

| # | Task | Completed | Notes |
|---|--------|--------|------|
| 5-21 | '시간여행자' album (Echo × Jinx) | 05-11 | Generated 20 tracks → selected 11 songs → video editing (31min 42sec) → posted to YouTube unlisted. videoId=8ZTFLgUcLPI. Thumbnail: time-reversal swirl cut |
| 5-18 | '술병이 났다' full album, 9 songs (3·3·3 homophone paradox) | 05-10 | 9 tracks v1/v2 done. Late-night smoky jazz, sax-centered. Track 9 English lyrics (Gregory Porter feel) completed. YouTube posting done |
| 5-14 | '그리움만 쌓이게' jazz trio EP, 9 songs | 05-04 | Bill Evans tone. Generated 9 tracks v1/v2 → selected → mastered → video → YouTube posting done. Track 06 Korean female vocal (Norah Jones × Youn Sun Nah) |
| 4-3 | ~~"너를 다시" Suno generation + YouTube posting~~ | 05-05 | **Cancelled / abandoned**. Concept/lyrics/prompt artifacts moved to `songs/archive/02_너를_다시/`. dhruv "double take" reference, bedroom pop. No intent to resume |
| PIPE-F03 | Suno asyncio parallel generation PoC | 05-05 | **PoC hold conclusion**. asyncio 1.5x / multi-tab 1.2x / multi-profile Nx — all unsuitable given ROI vs. risk. YAGNI for 1-2 EPs per month. Prompt optimization + retry is superior. Report `docs/poc/pipe_f03_report.md`. Re-evaluate multi-profile at the 3+ EPs/month point |

## 2026-04

| # | Task | Completed | Notes |
|---|--------|--------|------|
| PIPE-F04 | Post-processing chain pipeline (postprocess_v2.py lightweight) | 04-24 | Implemented postprocess_v2.py lightweight version. Demucs/Matchering left as flag options. Completed the minimal path of the original spec |
| 4-1 | "봄이라고 부를게" YouTube posting | 04-23 | Single (fa7aabee) + album (Suite 9 tracks) video upload done. Description written |
| 5-1 | Jazz Suite per-track Suno generation + selection + album video | 04-08 | Compared 9 tracks v1/v2 quality → selected best → album audio (27:52) + video (89MB) + chapter markers |
| 5-10 | Finalize single master (fa7aabee) | 04-07 | Analyzed quality of 20 versions → chose version with max dynamic range (16.5dB) + having SRT |
| 3-13 | create_video.py/publish.py SRT subtitle support | 04-07 | --srt CLI argument + auto-detection (lyrics.srt) + cover.jpeg/png fallback |
| 3-14 | Create .env.example | 04-08 | 5 key placeholders |
| 5-11 | Write YouTube description (hostless reference) | 04-07 | Emotional prose + chapter markers + credits structure |
| 4-4 | create_making_video.py | 04-07 | Screenshot slideshow + edge-tts narration + BGM compositing script |
| 1-5 | Pin npx version @2.1.91 | 04-03 | Prevent silent breaking changes |
| 5-2 | Track 02 lyrics revision | 04-04 | "다시 만날 수 있으니까" → "떠올릴 수 있으니까" |
| 5-3 | Finalize album title | 04-04 | 봄을 통해 너를 봄 (Seeing You Through Spring) |
| 1-6 | Batch improvement of 6 Telegram bot UX items | 04-04 | |
| 1-7 | Batch fix of 6 security/stability issues | 04-04 | |
| 1-8 | defaultdict(Lock) memory leak prevention | 04-04 | MAX_USER_LOCKS limit |

## 2026-03

| # | Task | Completed | Notes |
|---|--------|--------|------|
| 1-1 | Telegram bot basic operation | 03-28 | CLI OAuth, history, per-user lock, semaphore |
| 1-2 | Claude CLI history injection POC | 03-28 | Multi-turn conversation working via format_context |
| 1-3 | per-user rate limit | 03-28 | _user_locks + "처리 중" message |
| 1-4 | FluidSynth soundfont path management | 03-28 | SOUNDFONT_PATH environment variable + fallback |
| 1-9 | Global concurrency cap (Semaphore) | 03-28 | asyncio.Semaphore(2) |
| 1-10 | midi_json column for /remix | 03-28 | messages + ideas tables |
| 3-6 | manifest.json support | 03-30 | jazz_pipeline.py metadata auto-generation |
| 3-7 | scripts/create_video.py | 03-30 | ffmpeg image+audio → MP4 |
| 3-8 | scripts/generate_thumbnail.py | 03-30 | Pillow YouTube thumbnail auto-generation |
| 3-9 | scripts/youtube_upload.py | 03-30 | YouTube Data API v3 upload |
| 3-10 | scripts/publish.py | 03-30 | YouTube posting orchestrator |
| 5-4 | Add classic jazz presets | 03-30 | jazz bar, bebop, vocal jazz standards |
| 5-5 | Workflow template set | 03-30 | songs/template/ + workflow_guide.md |
| 5-6 | Suno prompt v3 + contemporary pop | 03-30 | lo-fi prohibited, indie band + emotional dreamy |
| 5-7 | English adaptation "I'll Call You Spring" | 03-30 | Wordplay preserved (call/spring dual meaning) |
| 3-11 | Suno download pipeline | 03-31 | Clerk JWT → studio-api-prod.suno.com API |
| 3-12 | YouTube upload end-to-end | 03-31 | Song download → MP4 → YouTube success |
| 5-8 | Delete lyrics_v2.md | 03-31 | lyrics_v1.md is the finalized version |
| 3-1 | Maintain conversation history (per session) | 03-28 | Multi-turn conversation via format_context(). Implemented together with 1-2 |
| 3-2 | Suno integration (lyrics+genre → Suno generation) | 03-31 | /suno command + suno_client.py. Implemented together with 3-11 |
| 3-5 | MIDI playback (inline audio) | 03-28 | audio.py → midi_to_audio() → OGG Telegram send |
| 5-9 | Suno one-stack transition | 03-29 | Removed post-processing pipeline (mix_stems.py, process.py) |
