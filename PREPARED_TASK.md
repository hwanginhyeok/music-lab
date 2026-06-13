# Prepared Tasks

## P1

| # | Task | Priority | depends | Notes |
|---|--------|----------|---------|------|
| PIPE-F05 | Fix Drive service account JSON (bug) | P1 | user: GCP issuance | `client_secrets.json` is OAuth format. GCP console `music-lab-491900` → IAM → create service account → key JSON → save to `credentials/drive-sa.json` + update `.env GOOGLE_CREDENTIALS_PATH` |
| PIPE-F10 | Auto-refresh YouTube OAuth refresh_token | P1 | — | Prevent recurrence of the token expiry hit in 4-1. Telegram warning 7 days before expiry + re-auth link |
| 2-1 | Phase 1: Understand chord progressions (1 week) | P1 | — | Suno-linked learning curriculum |
| 5-12 | Jazz Suite post-processing (loudness normalization) | P1 | 4-1 done | Correct volume deviation across tracks (-14 LUFS) — can reuse the PIPE-F04 lightweight path. **PIPE-AUTO 후처리 노드(`autopilot/nodes/postprocess.py`)로 재사용 가능** |
| 5-17b | 무색무취의 빈병 — post-processing + YouTube release | P1 | 5-17 selection done | After best-take selection, -14 LUFS post-processing → album video → YouTube publish |

> ✅ PIPE-F12/F01/F02/F11 → FINISHED 이동 (2026-06-13~14, PIPE-AUTO Phase 2~4 + F02 완료)

## P2

| # | Task | Priority | depends | Notes |
|---|--------|----------|---------|------|
| PIPE-F10b | PIPE-F10 remainder (GLM 5.1 + 4.6 review integration) | P2 | PIPE-F10 (done 91046ab + d4b05e4) | (a) `_write_token_secure` TOCTOU atomic creation (P3) (b) Strengthen the BLOCK_HOURS 24 deletion commit message (c) Make `(ConnectionError,TimeoutError,OSError)` scope explicit (d) ~~rate_limit camelCase matching~~ → **fixed in d4b05e4** (e) Add 1 test for the `refresh_error` notification needs_reauth (f) `_save_state` 0600 consistency (g) **youtube_upload.py token write 0600 not applied** — reverts to 0644 on refresh (h) **whitespace-separated "rate limit" pattern may be missed** — need to empirically verify the actual google-auth format (i) **mock message format** — verify the google-auth RefreshError message generation logic (j) **rate_limit vs quota classification split** — fine from an operational standpoint but the message may be confusing. All LOW priority. Verification: discovered over 2 cycles with `/hih-glm review` (GLM 5.1) + `/hih-dual` (Sonnet+GLM 4.6) |

| # | Task | Priority | depends | Notes |
|---|--------|----------|---------|------|
| PIPE-F13 | postprocess 2-pass loudnorm — LUFS 정밀도↑ | P2 | — | 현재 `autopilot/nodes/postprocess.py`는 ffmpeg **1-pass** `loudnorm=I=-14`. 실 e2e(run 86494cf1d566, 후보 6bf985d1) 측정: 원본 -14.10 → 후처리 **-13.52**(타겟 -14, ~0.48 LU 오차, 1-pass 오버슈트). **2-pass**(1차 측정 `print_format=json` → measured_I/LRA/TP/thresh를 2차 인자로 주입)로 ±0.1 LU 정밀도 확보. 스트리밍 허용(-14±1) 내지만 앨범 릴리즈 품질용 개선 |
| 2-2 | Phase 2: Writing melodies (1~2 weeks) | P2 | 2-1 done | |
| 2-3 | Phase 3: Designing song structure (1~2 weeks) | P2 | 2-2 done | |
| 3-3 | Chord progression visualization (image generation) | P2 | — | |

## P3

| # | Task | Priority | depends | Notes |
|---|--------|----------|---------|------|
| 2-4 | Phase 4: Intro to DAW production (2~4 weeks) | P3 | 2-3 done | |
| 3-4 | Voice message input → humming analysis | P3 | — | |
| 6-1 | Build YouTube management pipeline | P3 | — | Implement /youtube_list (list), /youtube_delete (delete), and stats features. Re-evaluate once channel content is sufficiently accumulated |
| PIPE-F14 | 좀비 bot.py 재발방지 — systemd-only 가드 | P3 | — | 2026-06-14 사고: 6/7부터 떠있던 수동 `python3 bot.py`(PID 365) 좀비가 같은 텔레그램 토큰을 getUpdates 폴링 → 형님 `/select`+버튼클릭이 좀비(구코드)에게 가로채여 증발(systemd 봇은 미수신). 수동 kill로 해결. 재발방지: (a) `bot.py` 시작 시 기존 인스턴스 감지하면 경고+종료(pidfile/flock 또는 `getUpdates` 충돌 감지) (b) 운영은 systemd `music-bot`만 — 수동 실행 금지 문서화/가드. 텔레그램 단일 폴러 보장 |
