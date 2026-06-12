# Music Lab Work Rules

## MIDI Generation Rules
- Parse the ```midi-json``` block from Claude's response
- pitch: MIDI note number (60=C4)
- Adhere to GM instrument numbers
- On generation failure, send the error message to Telegram (no silent failures)

## Bot Rules
- Never include the .env tokens in logs/commits
- Claude CLI call timeout: 120 seconds
- Before responding, send a "생각하는 중..." message (UX)

## Suno-related
- SUNO_COOKIE expires periodically — edit .env when renewal is needed
- The Clerk JWT in suno_download.py is auto-issued from the session cookie
- The generate API (song generation) is unstable — the manual Suno web generation + automatic download combination is recommended

## Song Directory Rules
- `songs/{번호}_{곡명}/` format
- Required files: `concept.md`, `lyrics_v{N}.md`, `suno_prompt*.md`
- Template: see `songs/template/`

## Service Operations
- After changing bot code: `systemctl --user restart music-bot`
- Check logs: `journalctl --user -u music-bot -f`
- Restart is unnecessary when only the DB is changed without service interruption
