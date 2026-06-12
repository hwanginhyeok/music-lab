# Prepared Tasks

## P1

| # | Task | Priority | depends | Notes |
|---|--------|----------|---------|------|
| PIPE-F05 | Fix Drive service account JSON (bug) | P1 | user: GCP issuance | `client_secrets.json` is OAuth format. GCP console `music-lab-491900` → IAM → create service account → key JSON → save to `credentials/drive-sa.json` + update `.env GOOGLE_CREDENTIALS_PATH` |
| PIPE-F10 | Auto-refresh YouTube OAuth refresh_token | P1 | — | Prevent recurrence of the token expiry hit in 4-1. Telegram warning 7 days before expiry + re-auth link |
| PIPE-F01 | Automatic quality analysis (quality analyzer) | P1 | — | pyloudnorm + librosa + essentia + Claude multimodal. Outputs score to `quality/{song_id}.json` |
| PIPE-F02 | Telegram bot /review inline | P1 | PIPE-F01 | 6-song cards + inline buttons (pick/extend/reject/edit). On pick, auto-enters the F-04 queue |
| 2-1 | Phase 1: Understand chord progressions (1 week) | P1 | — | Suno-linked learning curriculum |
| 5-12 | Jazz Suite post-processing (loudness normalization) | P1 | 4-1 done | Correct volume deviation across tracks (-14 LUFS) — can reuse the PIPE-F04 lightweight path |
| 5-17b | 무색무취의 빈병 — post-processing + YouTube release | P1 | 5-17 selection done | After best-take selection, -14 LUFS post-processing → album video → YouTube publish |
| PIPE-F11 | Fix suno_pipeline polling v2 missing bug | P1 | — | Suno generates two songs (v1/v2) per generate call, but suno_pipeline.py polling terminates at the moment the first song completes. v2 is currently supplemented after the fact via suno_download.py. Workaround pattern verified in the batch script — a formal fix is needed |

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
