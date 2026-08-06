---
contract_layer: project
inherits: hih-agent-core-v1
project_id: music
---

# Music Lab

AI lyric/composition/MIDI Telegram bot + Suno song pipeline + YouTube publishing. Python 3.12.

## Architecture / entry points
- `bot.py` — Telegram bot (python-telegram-bot). Calls Claude CLI (`claude -p --system-prompt --tools "" --no-session-persistence`, OAuth, no API key). Parses ` ```midi-json``` ` blocks → midiutil → .mid; `audio.py` (FluidSynth) → .ogg.
- `db.py` — SQLite (conversations, ideas, suno_songs) in `data/` (gitignored). `bridge.py` — CLI query of that DB.
- `suno_download.py` — Clerk JWT → direct `studio-api-prod.suno.com` calls; `--upload-youtube` chains upload.
- `suno_client.py` / `suno_pipeline.py` — undetected-chromedriver web automation; the generate API is unstable (hcaptcha). `scripts/start_vnc.sh` for manual generation.
- `scripts/publish.py` — YouTube orchestrator (thumbnail → ffmpeg MP4 → YouTube Data API v3 upload). `scripts/drive_to_youtube.py` — Drive → YouTube. `drive_uploader.py` — Google Drive service-account upload (`GOOGLE_CREDENTIALS_PATH`, `GOOGLE_DRIVE_FOLDER_ID`).
- Song assets live in `songs/{NN}_{name}/` (concept, lyrics, `suno_prompt*.md`).
- `.claude/agents/`: lyricist, composer, mixing-engineer, vocalist, suno-prompt-engineer.

## Run / test
```bash
python3 -m pytest tests/ -v
systemctl --user restart music-bot    # production bot (systemd user unit)
journalctl --user -u music-bot -f
```

## Boundaries
- Never run `python3 bot.py` while the `music-bot` systemd unit is active — a duplicate poller steals Telegram updates. Stop the unit first for dev runs (`data/.music-bot.lock` guards, but stop anyway).
- YouTube publication is external publication: user approval required.
- Secrets stay out of git: `.env` (bot token, `SUNO_COOKIE`), `client_secrets.json`, `token.json`, `data/`.
- Claude CLI is invoked with all tools disabled; keep it that way (untrusted Telegram input).
- Sanitize MIDI filenames (command-injection surface).
