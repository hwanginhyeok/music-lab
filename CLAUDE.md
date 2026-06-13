# Music Lab

> AI lyric-writing/composition/MIDI generation + Suno integration + YouTube publishing project. Learn and make music by conversing with Claude through a Telegram bot.

## Tasks
- [CURRENT_TASK.md](CURRENT_TASK.md) | [PREPARED_TASK.md](PREPARED_TASK.md) | [FINISHED_TASK.md](FINISHED_TASK.md)

---

## Commands

```bash
# Run bot (for development — production runs via systemd)
python3 bot.py

# Tests
python3 -m pytest tests/ -v

# Suno download
python3 suno_download.py --list                        # my song list
python3 suno_download.py --all                         # download all
python3 suno_download.py --song-id UUID                # individual download
python3 suno_download.py --all --upload-youtube         # download + YouTube upload

# Suno song generation (undetected-chromedriver based, unstable)
python3 suno_pipeline.py --title "제목" --style "장르" --lyrics "[Verse] 가사"
python3 suno_pipeline.py --title "제목" --prompt-file songs/01_봄이라고_부를게/suno_prompt_final.md

# YouTube publishing pipeline
python3 scripts/publish.py                             # YouTube publishing orchestrator
python3 scripts/drive_to_youtube.py --latest --title "제목"  # Drive → YouTube

# CLI utilities
python3 bridge.py recent          # query the 20 most recent Telegram conversations
python3 bridge.py ideas           # idea library
python3 bridge.py search 재즈     # keyword search
```

## Tech Stack

- **Python 3.12** — main language
- **python-telegram-bot 22.7** — Telegram bot framework
- **Claude CLI (npx @anthropic-ai/claude-code)** — AI backend (OAuth, no API key required)
- **midiutil** — MIDI file generation
- **python-dotenv** — environment variable management
- **requests** — direct Suno API calls (Clerk JWT authentication)
- **google-api-python-client / google-auth** — YouTube Data API v3 + Google Drive API
- **undetected-chromedriver / selenium** — Suno web automation (Cloudflare Turnstile bypass)

## Architecture

```
music-lab/
├── CLAUDE.md              ← this file
├── bot.py                 ← Telegram bot (18 handlers)
├── db.py                  ← SQLite conversation history + ideas + Suno song metadata
├── audio.py               ← MIDI → OGG audio conversion (FluidSynth)
├── midi_utils.py          ← piano roll text visualization
├── bridge.py              ← DB bridge — query Telegram conversations/ideas from the CLI
├── suno_client.py         ← Suno web automation client (undetected-chromedriver)
├── suno_pipeline.py       ← Suno song generation pipeline CLI
├── suno_download.py       ← Suno download pipeline (Clerk JWT → direct API calls)
├── drive_uploader.py      ← Google Drive uploader (service account auth)
├── requirements.txt       ← pip dependency list
├── .env                   ← environment variables (TELEGRAM_BOT_TOKEN, SUNO_COOKIE, etc.)
├── client_secrets.json    ← YouTube OAuth client secret (.gitignore)
├── token.json             ← YouTube OAuth token (.gitignore)
├── data/                  ← SQLite DB + MIDI + Suno downloads (.gitignore)
├── CURRENT_TASK.md        ← in-progress tasks
├── PREPARED_TASK.md       ← prepared tasks (P1/P2/P3)
├── FINISHED_TASK.md       ← completed tasks
├── DIFFICULTY.md          ← technical challenges & know-how
├── TASK_ARCHIVE/          ← monthly completed-task archive
├── songs/                 ← per-song directories (concept, lyrics, Suno prompt)
│   ├── 01_봄이라고_부를게/
│   ├── 02_너를_다시/
│   ├── 02_test_jazz/
│   ├── template/          ← workflow template
│   └── workflow_guide.md  ← song workflow guide
├── scripts/
│   ├── publish.py         ← YouTube publishing orchestrator
│   ├── youtube_upload.py  ← YouTube Data API v3 upload
│   ├── drive_to_youtube.py ← Google Drive → YouTube pipeline
│   ├── create_video.py    ← cover image + audio → MP4 video (ffmpeg)
│   ├── create_making_video.py ← making-of video (screenshots + TTS + BGM)
│   ├── generate_thumbnail.py ← YouTube thumbnail auto-generation (Pillow)
│   ├── jazz_pipeline.py   ← jazz song auto-generation pipeline
│   ├── lyrics_to_srt.py   ← lyrics → SRT subtitle conversion
│   └── start_vnc.sh       ← run VNC + Chrome environment (for manual Suno generation)
├── docs/
│   ├── suno_guide.md      ← Suno prompt guide
│   ├── 작사가/            ← lyric-writing analysis (김이나)
│   └── 프로젝트/          ← overnight-work briefings + archive
├── tests/                 ← pytest tests
└── logs/                  ← execution logs
```

### Data Flow

**Telegram bot (real-time conversation)**
```
Telegram message
    ↓
bot.py (handlers + per-user lock + global semaphore)
    ↓
db.py → session lookup + history loading (most recent 10 pairs)
    ↓
claude -p --system-prompt --tools "" --no-session-persistence
    ↓
response text parsing
    ├── text → send to Telegram
    ├── ```midi-json``` block → midiutil → .mid → Telegram
    ├── audio.py → FluidSynth → .ogg → Telegram inline playback
    ├── midi_utils.py → piano roll text visualization
    └── db.py → save message (including midi_json)
```

**Suno download + YouTube upload pipeline**
```
suno_download.py (Clerk JWT → studio-api-prod.suno.com)
    ↓
WAV/MP3 download → data/suno/
    ↓
ffmpeg → MP4 video generation (cover image + audio)
    ↓
YouTube Data API v3 → YouTube upload
    ↓
db.py → save metadata to the suno_songs table
```

### Telegram Bot Commands

| Command | Description |
|--------|------|
| `/start` | introduction |
| `/help` | full command guide |
| `/lyrics [topic]` | AI lyric-writing (verse/chorus/bridge) |
| `/chord [mood]` | chord progression recommendation + MIDI + visualization |
| `/midi [description]` | melody MIDI generation + piano roll |
| `/theory [question]` | music theory Q&A |
| `/new` | start a new conversation (reset context) |
| `/idea [description]` | instantly record an inspiration as a MIDI snippet |
| `/library` | view saved ideas |
| `/export [number]` | resend MIDI file |
| `/remix [number] [style]` | style variation of an existing idea |
| `/quiz` | music theory quiz |
| `/daily` | daily quiz subscription (in preparation) |
| `/save` | save conversation content as a song file |
| `/suno [prompt-filename]` | generate a song with Suno AI |
| `/suno_list` | list of generated Suno songs |
| `/publish` | publish a Suno song to YouTube |
| free conversation | any music-related question (remembers conversation) |

## Service Operations

> SSOT: see `/home/window11/project-manager/projects.yaml` (music-lab → services: music-bot)

```bash
systemctl --user restart music-bot   # restart after bot code changes
journalctl --user -u music-bot -f    # check logs
```

> **Run only via systemd `music-bot`.** Do NOT manually run `python3 bot.py` — a duplicate poller steals Telegram updates (the /select-click interception incident, PIPE-F14). A single-instance lock (`data/.music-bot.lock`) makes any duplicate exit immediately, but for dev testing still stop systemd first (`systemctl --user stop music-bot`) before running standalone.

## Agents (`.claude/agents/`)

| Agent | Role | Model |
|---------|------|------|
| `lyricist` | Korean lyric-writing (based on 김이나's lyric-writing method) | opus |
| `composer` | chord progression + melody + MIDI JSON generation | sonnet |
| `mixing-engineer` | stem mix balance/tone adjustment | sonnet |
| `vocalist` | vocal style analysis + Suno vocal tag optimization | sonnet |
| `suno-prompt-engineer` | Suno Style of Music tag + section marker optimization | sonnet |

## Core Rules

### Code Conventions
- Variable/function names in English, comments/commit messages in Korean
- Use Python 3.12+ type hints
- Minimize external dependencies

### MIDI Generation
- Claude returns note data as a `midi-json` code block
- bot.py parses it → generates .mid via midiutil → sends to Telegram
- Use GM instrument numbers (0=piano, 24=guitar, 33=bass, 48=strings)
- Korean track names are not ISO-8859-1 compatible, so fall back to "Track N"

### Claude CLI Invocation
- `--system-prompt`: pass the system prompt separately (prevents CLAUDE.md auto-loading)
- `--tools ""`: disable all tools (security)
- `--no-session-persistence`: prevent session file accumulation

### Suno Integration
- **Download**: `suno_download.py` — Clerk JWT authentication → direct API calls to `studio-api-prod.suno.com`
- **Generation**: `suno_client.py` — undetected-chromedriver based (Turnstile bypass). The generate API is unstable due to additional hcaptcha verification
- **Prompts**: managed in the format `songs/{song-number}_{song-name}/suno_prompt*.md`

### YouTube Upload
- Uses YouTube Data API v3 (OAuth: `client_secrets.json` + `token.json`)
- `suno_download.py --upload-youtube`: auto-upload after download
- `scripts/publish.py`: orchestrator (thumbnail generation → MP4 conversion → upload)
- `scripts/drive_to_youtube.py`: fetch from Google Drive and upload to YouTube

### Google Drive Integration
- `drive_uploader.py` — upload WAV/MP3 with service account auth + generate share links
- Environment variables: `GOOGLE_CREDENTIALS_PATH`, `GOOGLE_DRIVE_FOLDER_ID`

### Security
- Never commit the .env file (included in .gitignore)
- Do not expose the bot token
- Do not commit the data/ directory (DB, MIDI, Suno downloads)
- Do not commit client_secrets.json, token.json
- Remove dangerous characters from MIDI filenames (command injection prevention)
- Disable Claude CLI tools (prevents user input from triggering Bash/Edit)

## gstack

Use /browse from gstack for all web browsing.

---

## Superpowers 활성화

> 모든 Claude Code 세션 시작 시 `using-superpowers` 스킬을 **반드시 먼저** Skill 도구로 호출할 것.

### 작업 유형별 필수 프로세스

| 작업 유형 | 필수 프로세스 |
|-----------|--------------|
| 새 기능 / 기능 수정 | `brainstorming` → `writing-plans` → `matt-tdd` → `verification-before-completion` |
| 버그 수정 | `systematic-debugging` (재현 → 원인 파악 → 수정 → 검증) → `verification-before-completion` |
| 계획 수립 | `brainstorming` → `writing-plans` → `executing-plans` |

### 스킬 호출 규칙

1. **Skill 도구 사용**: Read 도구로 직접 읽지 않고 항상 Skill 도구로 호출
2. **관련 스킬 필수 호출**: 1% 가능성이라도 관련 스킬이 있으면 반드시 호출
3. **순서 준수**: 프로세스 스킬 먼저 (brainstorming, debugging), 구현 스킬 나중에 (TDD)
4. **체크리스트 추적**: 체크리스트가 있으면 TodoWrite로 각 항목 추적

### 언어 규칙

- **한국어로 응답** (로그, 코멘트, 메시지 모두 한국어)
- **코드 변수명/함수명은 영어** 유지
