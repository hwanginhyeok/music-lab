# Prepared Tasks

## P1

| # | Task | Priority | depends | Notes |
|---|--------|----------|---------|------|
| PIPE-F05 | Fix Drive service account JSON (bug) | P1 | user: GCP issuance | `client_secrets.json` is OAuth format. GCP console `music-lab-491900` → IAM → create service account → key JSON → save to `credentials/drive-sa.json` + update `.env GOOGLE_CREDENTIALS_PATH` |
| PIPE-F10 | Auto-refresh YouTube OAuth refresh_token | P1 | — | Prevent recurrence of the token expiry hit in 4-1. Telegram warning 7 days before expiry + re-auth link |
| PIPE-F12 | PIPE-AUTO 오케스트레이터 (자체 FSM 코어) | P1 | — | `autopilot/` state machine. runs/steps/human_tasks/artifacts SQLite + @step/@human_gate 데코레이터 + idempotency + claude_cli 래퍼 + trace 레이어. Phase 2 = 코어(키 불필요), 노드는 stub. 설계 SSOT: `plans/PIPE-AUTO.md` |
| PIPE-F01 | 프리필터 (생성 후보 자동 추림) ※역할 재정의 | P1 | PIPE-F12 | (구 quality analyzer) pyloudnorm + librosa + Claude multimodal로 점수화 → 후보 N곡 중 사람 청취 전 자동 컷. PIPE-AUTO 프리필터 노드로 편입. `quality/{song_id}.json` |
| PIPE-F02 | 텔레그램 후보카드 + /resume 핸들러 | P1 | PIPE-F12, PIPE-F01 | 후보 곡 카드 + 인라인 버튼(pick/extend/reject/edit). human_gate `awaiting_selection` 재개 트리거. pick 시 후처리 노드로 진행 |
| 2-1 | Phase 1: Understand chord progressions (1 week) | P1 | — | Suno-linked learning curriculum |
| 5-12 | Jazz Suite post-processing (loudness normalization) | P1 | 4-1 done | Correct volume deviation across tracks (-14 LUFS) — can reuse the PIPE-F04 lightweight path |
| 5-17b | 무색무취의 빈병 — post-processing + YouTube release | P1 | 5-17 selection done | After best-take selection, -14 LUFS post-processing → album video → YouTube publish |
| PIPE-F11 | Fix suno_pipeline polling v2 missing bug | P1 | PIPE-F12 (생성 노드 편입) | Suno generates two songs (v1/v2) per generate call, but suno_pipeline.py polling terminates at the moment the first song completes. v2 is currently supplemented after the fact via suno_download.py. PIPE-AUTO 생성 노드(`autopilot/nodes/generate.py`)에서 v1/v2 모두 수확하도록 정식 구현. Workaround pattern verified in the batch script |

## P2

| # | Task | Priority | depends | Notes |
|---|--------|----------|---------|------|
| PIPE-F10b | PIPE-F10 remainder (GLM 5.1 + 4.6 review integration) | P2 | PIPE-F10 (done 91046ab + d4b05e4) | (a) `_write_token_secure` TOCTOU atomic creation (P3) (b) Strengthen the BLOCK_HOURS 24 deletion commit message (c) Make `(ConnectionError,TimeoutError,OSError)` scope explicit (d) ~~rate_limit camelCase matching~~ → **fixed in d4b05e4** (e) Add 1 test for the `refresh_error` notification needs_reauth (f) `_save_state` 0600 consistency (g) **youtube_upload.py token write 0600 not applied** — reverts to 0644 on refresh (h) **whitespace-separated "rate limit" pattern may be missed** — need to empirically verify the actual google-auth format (i) **mock message format** — verify the google-auth RefreshError message generation logic (j) **rate_limit vs quota classification split** — fine from an operational standpoint but the message may be confusing. All LOW priority. Verification: discovered over 2 cycles with `/hih-glm review` (GLM 5.1) + `/hih-dual` (Sonnet+GLM 4.6) |

| # | Task | Priority | depends | Notes |
|---|--------|----------|---------|------|
| 5-16 | 'Art / Artist' jazz EP — homophone paradox, 9 songs | P2 | — | **On hold (2026-05-05)**. Bill Evans tone Vol.2. Homophone paradox of the object of longing 'Art' (a person's name) + 'artist' (the narrator's self). English lyrics. Concept draft `songs/16_art_artist/concept_draft.md`. Re-evaluate after 5-17 (무색무취) |
| 2-2 | Phase 2: Writing melodies (1~2 weeks) | P2 | 2-1 done | |
| 2-3 | Phase 3: Designing song structure (1~2 weeks) | P2 | 2-2 done | |
| 3-3 | Chord progression visualization (image generation) | P2 | — | |

## P3

| # | Task | Priority | depends | Notes |
|---|--------|----------|---------|------|
| 2-4 | Phase 4: Intro to DAW production (2~4 weeks) | P3 | 2-3 done | |
| 3-4 | Voice message input → humming analysis | P3 | — | |
| 6-1 | Build YouTube management pipeline | P3 | — | Implement /youtube_list (list), /youtube_delete (delete), and stats features. Re-evaluate once channel content is sufficiently accumulated |
