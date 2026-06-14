# Finished Tasks

## 2026-06

| # | Task | Completed | Notes |
|---|--------|--------|------|
| PIPE-F12 | PIPE-AUTO FSM 코어 (Phase 2) | 06-13 | `autopilot/` 자체 state machine. SQLite(runs/steps/human_tasks/artifacts) + `@step`/`@human_gate` 데코 + idempotency + claude_cli 래퍼 + trace 레이어 + state_version 마이그레이션 훅. resume done-skip 멱등. pytest 34. commits `4fcf8b4`/`9bfd2b1`. 설계 SSOT `plans/PIPE-AUTO.md` |
| PIPE-AUTO Phase 3 | 노드 구현 — 작사/Suno프롬프트/생성/프리필터 | 06-13 | claude_cli 작사·suno-pe 프롬프트(전문 trace)·기존 `suno_client.SunoClient` 래핑 생성·프리필터. 생성결정 정정(서드파티 API 취소→기존 웹프로그램). pytest +18. commits `58c26d2`/`0d5e553` |
| PIPE-F01 | 프리필터 노드 (역할 재정의) | 06-13 | (구 quality analyzer) pyloudnorm/librosa 지연import, **기술결함만**(클리핑/무음/길이/손상) 필터·취향판단 없음. Phase 3에서 PIPE-AUTO 노드로 편입 |
| PIPE-F11 | suno v1/v2 폴링 정식구현 | 06-13 | 생성 노드(`autopilot/nodes/generate.py`)가 v1/v2 페어 모두 수확 + idempotency(D-004 중복생성 차단). 폴링 버그 정식 해소 |
| PIPE-AUTO Phase 4 | 후처리(-14LUFS)/영상/unlisted 업로드 + human-gate | 06-14 | ffmpeg loudnorm·MP4·YouTube Data API v3 unlisted. **publish-gate**(미승인 시 API 호출 0) + idempotency + `/resume` human-gate 재개. pytest +31. commits `8e64a63`/`0d7c420`/`0503603` |
| PIPE-AUTO 저널 | HTML 프로비넌스 저널 + 샘플 런 | 06-14 | `autopilot/journal.py` 시더+Jinja2 렌더(노드 타임라인·Suno프롬프트 전문·후보 메트릭·선택take·youtube 링크). canonical=SQLite/trace. 샘플 trace 분리(`data/autopilot/sample_trace.jsonl`) + render out_dir 정리. 포트 8897 서빙. commits `4b26153`/`5b91f02`/`57f447a` |
| PIPE-AUTO 조립 | 풀 앨범 파이프라인 | 06-14 | `autopilot/pipeline.py` song_pipeline(작사→…→업로드 전체 체인)/run_album/resume_song. 양쪽 human-gate(선택·승인) resume 메커니즘. concept '기획' step 영속화. e2e 9(2단 게이트+멱등성). commits `4a3f770`/`05c5deb` |
| PIPE-F02 | 텔레그램 후보카드 /select + /resume 라이브 | 06-14 | `autopilot/cards.py`(build_selection_card/apply_selection/parse) + `bot.py` 순수추가(`/select` 인라인카드 + `^pipeauto:` 콜백 → selected_index 주입 resume). `/resume` 핸들러. 봇 라이브 가동 검증. commits `a919db0`/`2a682a6`/`9837401` |
| PIPE-AUTO 실데이터 e2e | generate 우회 풀루프 검증 (게이트~publish-gate) | 06-14 | D-001(Suno 자동생성 차단, hCaptcha 벽 실측 재확인: 형님 캡차 3회 풀어도 제출 미큐잉) 우회 — 실곡 후보 주입 → 프리필터→[형님 후보선택]→후처리(실 -14LUFS)→영상(실 1080p h264/aac)→publish_approval 게이트 정지·업로드 0. suno_client Bug#1(hang)+Bug#2(재제출) 수정 포함. 좀비 bot.py(PID365) 업데이트 가로채기 사고 발견·제거. commits `127cf2b`/`a063e7e` 등 |
| PIPE-F13 | postprocess 2-pass loudnorm — LUFS 정밀도 ±0.0 | 06-14 | 1-pass→2-pass(pass1 측정 → pass2 measured_*+offset+linear=true)+`-b:a 320k`(저비트레이트 라우드니스 시프트 차단)+devnull sink. 실측: 원본 -14.10 → 1-pass -13.52(오차0.48) → **2-pass -14.00(오차0.00)**. 측정실패 1-pass 폴백. pytest 201. commits `43e015e`/`5e3c224` |
| PIPE-F14 | 좀비 bot.py 재발방지 — 단일 인스턴스 가드 | 06-14 | `bot.py` 순수추가: `_acquire_single_instance_lock`(flock LOCK_EX·NB on `data/.music-bot.lock`) main() 최상단 호출 → 중복 인스턴스 경고+SystemExit(1). flock 자동해제(stale 없음). 2026-06-14 좀비(PID365) 토큰 가로채기 사고 재발방지. systemd-only 문서화. 실 subprocess 검증(2번째 exit1, 사망 후 3번째 획득). pytest 202. commit `a45288d`. ⚠️ 가드 활성화는 봇 재시작 후(형님 승인 대기) |

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
