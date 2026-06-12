# Difficulties & Know-how

## D-001: Suno hCaptcha — cannot generate songs via the generate API

- **Date**: 2026-03-29 ~ present
- **Situation**: Tried to automate song generation via the Suno API. Succeeded in bypassing Cloudflare Turnstile with undetected-chromedriver in suno_client.py.
- **Problem**: When calling the generate API, an additional hCaptcha verification appears. Turnstile was bypassed, but hCaptcha cannot be bypassed.
- **Trial and error**:
  - Bypass Turnstile with undetected-chromedriver → success
  - Direct call to the generate API → blocked by hCaptcha
  - Attach Chrome in the VNC environment → tried to solve only the captcha manually
- **Solution**: Switched to a **combination of manual Suno web generation + automated download**. `suno_download.py` works reliably with the Clerk JWT.
- **Know-how**: **Suno song generation cannot be automated (as of 2026-03)**. Download/metadata lookup is possible with the Clerk JWT. Generation is done manually on the web + remote access via noVNC.
- **Related files**: `suno_client.py`, `suno_download.py`, `suno_pipeline.py`

---

## D-002: Clerk JWT auth — short session-cookie expiry cycle

- **Date**: 2026-03-31 ~ 2026-04-02
- **Situation**: suno_download.py calls the Suno API with the Clerk JWT. It worked at first but failed authentication after a few days.
- **Problem**: Suno's Clerk session cookie (`__client`) expires on a short cycle (a few days). The SUNO_COOKIE in .env must be refreshed.
- **Trial and error**:
  - Kept retrying with the expired JWT → 403
  - Searched for a refresh endpoint → Clerk is browser-session-based, so server-side refresh is impossible
- **Solution**: **Log in to Suno in the browser → copy `__client` from DevTools > Application > Cookies → update .env**. Periodic manual refresh required.
- **Know-how**: **The Clerk JWT cannot be auto-refreshed server-side**. It depends on the browser session. Implement it so that a clear error message is logged when the cookie expires.
- **Related files**: `suno_download.py`, `.env` (SUNO_COOKIE)

---

## D-003: Claude CLI silent breaking change

- **Date**: 2026-04-03
- **Situation**: The Telegram bot calls the Claude CLI via npx. From a certain point the response format changed or errors occurred.
- **Problem**: As npx auto-installs the latest version, the Claude CLI's output format or flags changed without notice.
- **Trial and error**:
  - Modified the bot code based only on the error log → the cause was a CLI version difference
  - Tried the `--bare` flag → OAuth got disabled, so it was unusable
- **Solution**: **Pin the version with `npx @anthropic-ai/claude-code@2.1.91`**. Upgrade manually after testing.
- **Know-how**: **Always pin the version when calling the CLI via npx**. Auto-installing the latest is a cause of silent outages in production. Upgrade the version in the order: local test → apply to the bot.
- **Related files**: `bot.py` (the CLI call section)
- **Related commit**: `ca2cec2`


---

## D-004: VNC main domain dropped to tailnet only — external access impossible

- **Date**: 2026-05-05
- **Situation**: While working on the 5-18 album, the user tried to connect via VNC from a laptop. The SSH tunnel method stored in memory (`ssh -N -L 6080:...`) didn't get them in, and the URL seen in the music-lab memory (`http://localhost:6080/vnc.html`) didn't work either.
- **Problem**: In `tailscale funnel status`, the main domain / mapping was shown as `(tailnet only)` — not accessible from the external internet. The memory was a 5-day-old state (the SSH tunnel era) → stale.
- **Trial and error**:
  - Guided with the SSH tunnel command → the user couldn't get in
  - Brought up a separate Funnel on port 8444 → verified, but it wasn't the user's usual URL → they couldn't get in
  - **Checked PM memory reference_vnc_setup.md / reference_tailscale_funnel_pattern.md** → found the exact URL and recovery command
- **Solution**: `echo "0055" | sudo -S tailscale funnel --bg --set-path=/ http://127.0.0.1:6080` — brought the main / mapping back to Funnel on. URL: `https://desktop-plq9e0i.tailec5aa6.ts.net`
- **Know-how**:
  1. **The VNC URL SSOT is the PM `reference_vnc_setup.md`** — fix the project memory to point to it
  2. **The main / sometimes drops to tailnet only** (on PC restart / Tailscale restart) → memorize the set-path recovery pattern
  3. **Actively reference other projects' memory** — if it's the same user/same PC, the PM memory likely has the SSOT. Looking only at the music-lab memory and throwing the SSH tunnel command wastes time
- **Related files**: `~/.claude/projects/-home-window11-project-manager/memory/reference/reference_vnc_setup.md`, `reference_tailscale_funnel_pattern.md`, `~/.claude/skills/hih-vnc/SKILL.md`
- **Related commit**: `ace764c` (memory update)

---

## D-005: suno_pipeline.py polling catches only v1 and exits

- **Date**: 2026-05-05
- **Situation**: During the batch generation of 8 songs for 5-18, the suno_pipeline.py log showed `[2/3] 다운로드 (1곡)` — Suno generates two songs simultaneously (v1/v2), but only one was received.
- **Problem**: The polling logic breaks when the first song completes — ignoring Suno's normal behavior (2 songs at once).
- **Trial and error**: Checked whether the paired song landed in data/suno → looking via suno_download.py --list, the second song (the pair) with the same title existed → confirmed it can be downloaded directly via the API.
- **Solution (workaround)**: Added a v2 auto-supplement step to the batch script:
  ```python
  songs = api.get_songs()
  matches = [s for s in songs if s.get("title","").strip() == TITLE.strip()]
  if len(matches) >= 2:
      v2 = matches[1]  # 두 번째(짝) 곡
      api.download(v2, SUNO_DIR)
  ```
- **Know-how**: **The Suno generate API generates two songs (v1/v2) per call** — that's normal. Polling should wait until the baseline credit is deducted by +20 or more (2 songs × 10), or until two songs with the same title appear. The proper fix is PIPE-F11.
- **Related files**: `suno_pipeline.py` (the polling section), `scripts/batch_5-18_remaining.sh` (the workaround)
- **Related commits**: `4e79d4d`, `6f67ee6`


## D-004: Suno batch concurrent-run conflict + Chrome DISPLAY problem

- **Date**: 2026-05-10
- **Situation**: Tried batch generation of 20 tracks for 5-21 시간여행자
- **Problem**: Three problems occurred at once
  1. **Chrome failed to start** — ran the batch with VNC DISPLAY off → all tracks failed
  2. **Fake mp3 moved** — even after Chrome failed, the batch script moved an existing, different mp3 from `data/suno/` into the track folder (the LATEST_MP3 check logic grabs a previous file even after failure)
  3. **Concurrent-run conflict** — 3 retry scripts ran simultaneously, connecting to the same Chrome port 9222 at once → lyrics/style got mixed up during generation
- **Trial and error**: set VNC_DISPLAY=:99, adjusted the DISPLAY env var, repeated pkill, dug through logs
- **Solution**:
  1. Turn VNC on first (`nohup websockify ...`) then confirm Chrome started (`curl http://127.0.0.1:9222/json`)
  2. Fully clean up leftover processes with `pkill -9 -f suno_pipeline` before running the batch
  3. **Always run only ONE batch** — retries also single-run after killing the existing batch
  4. Identifying a fake mp3: suspect if size < 1M (normal is 2.4M~6M)
- **Know-how**:
  - Suno pre-batch checklist: ① confirm VNC is on ② confirm Chrome 9222 responds ③ confirm 0 existing suno_pipeline processes
  - `ps aux | grep suno_pipeline | grep -v grep | wc -l` → must be 0 to start
  - Recommend adding a guard to the batch script: `pgrep -f suno_pipeline && echo "이미 실행 중" && exit 1`
- **Related files**: `scripts/batch_시간여행자.sh`, `suno_client.py`, `suno_pipeline.py`

## D-007: Suno instrumental length cannot be controlled

- **Date**: 2026-05-15
- **Situation**: Generating Tracks 2~8 of the 무색무취의 빈병 album. Target is 2~4 minutes, but they cut off short at 1:40~2:20
- **Problem**: The Suno v5.5 UI has no duration slider. The `[Instrumental]` tag alone is an insufficient length signal
- **Trial and error**:
  - Added section markers (`[Intro][Verse][Bridge][Outro]`) → only stretched up to 2:20
  - mmm...ah...mmm pattern → the user complained "why is there humming?" Humming got generated
  - Oo-oo-ooh hyphenated syllables → similar result
  - Added `3 minute song, long form` to Style → negligible effect
  - Checked the API (`suno_client.py`) → no duration parameter
  - Searched for an Exclude field → couldn't find it in the UI (there's info that it's inside More Options, but unconfirmed)
- **Conclusion**:
  - In Suno, the amount of lyric content = the song length. Instrumentals are structurally short
  - The theoretical max for a single v5.5 generation is 8 minutes, but for instrumentals the realistic limit is the 2-minute range
  - **The only verified method: the Extend feature (manual in the UI)**
  - When vocalise syllables are input, humming is generated and 2 min+ can be reached — use only on tracks that conceptually need humming (#2, #6, #8)
- **Know-how**:
  - For instrumental tracks, accept the current length or stitch with Extend
  - Vocalise tracks (#2, #6, #8): `Oo-oo-ooh Mm-mm` hyphenated syllables + a 6-section structure
  - Specifying `3 minute song` in Style has negligible effect, but include it anyway
  - Pure instrumental: 5~6 `[Instrumental]` section markers + `instrumental only, no vocals`
- **Related files**: `songs/17_무색무취의빈병/tracks/*/suno_prompt.md`, `suno_client.py`
