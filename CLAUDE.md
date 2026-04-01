# Music Lab

> AI 작사/작곡/MIDI 생성 + Suno 연동 + YouTube 게시 프로젝트. 텔레그램 봇으로 Claude와 대화하며 음악을 배우고 만든다.

---

## Commands

```bash
# 봇 실행 (개발용 — 운영은 systemd)
python3 bot.py

# 테스트
python3 -m pytest tests/ -v

# Suno 다운로드
python3 suno_download.py --list                        # 내 곡 목록
python3 suno_download.py --all                         # 전체 다운로드
python3 suno_download.py --song-id UUID                # 개별 다운로드
python3 suno_download.py --all --upload-youtube         # 다운로드 + YouTube 업로드

# Suno 곡 생성 (undetected-chromedriver 기반, 불안정)
python3 suno_pipeline.py --title "제목" --style "장르" --lyrics "[Verse] 가사"
python3 suno_pipeline.py --title "제목" --prompt-file songs/01_봄이라고_부를게/suno_prompt_final.md

# YouTube 게시 파이프라인
python3 scripts/publish.py                             # YouTube 게시 오케스트레이터
python3 scripts/drive_to_youtube.py --latest --title "제목"  # Drive → YouTube

# CLI 유틸
python3 bridge.py recent          # 텔레그램 대화 최근 20건 조회
python3 bridge.py ideas           # 아이디어 라이브러리
python3 bridge.py search 재즈     # 키워드 검색
```

## Tech Stack

- **Python 3.12** — 메인 언어
- **python-telegram-bot 22.7** — 텔레그램 봇 프레임워크
- **Claude CLI (npx @anthropic-ai/claude-code)** — AI 백엔드 (OAuth, API 키 불필요)
- **midiutil** — MIDI 파일 생성
- **python-dotenv** — 환경변수 관리
- **requests** — Suno API 직접 호출 (Clerk JWT 인증)
- **google-api-python-client / google-auth** — YouTube Data API v3 + Google Drive API
- **undetected-chromedriver / selenium** — Suno 웹 자동화 (Cloudflare Turnstile 우회)

## Architecture

```
music-lab/
├── CLAUDE.md              ← 이 파일
├── bot.py                 ← 텔레그램 봇 (핸들러 15개)
├── db.py                  ← SQLite 대화 히스토리 + 아이디어 + Suno 곡 메타데이터
├── audio.py               ← MIDI → OGG 오디오 변환 (FluidSynth)
├── midi_utils.py          ← 피아노롤 텍스트 시각화
├── bridge.py              ← DB 브릿지 — 텔레그램 대화/아이디어를 CLI에서 조회
├── suno_client.py         ← Suno 웹 자동화 클라이언트 (undetected-chromedriver)
├── suno_pipeline.py       ← Suno 곡 생성 파이프라인 CLI
├── suno_download.py       ← Suno 다운로드 파이프라인 (Clerk JWT → API 직접 호출)
├── drive_uploader.py      ← Google Drive 업로더 (서비스 계정 인증)
├── .env                   ← 환경변수 (TELEGRAM_BOT_TOKEN, SUNO_COOKIE 등)
├── client_secrets.json    ← YouTube OAuth 클라이언트 시크릿 (.gitignore)
├── token.json             ← YouTube OAuth 토큰 (.gitignore)
├── data/                  ← SQLite DB + MIDI + Suno 다운로드 (.gitignore)
├── songs/                 ← 곡별 디렉토리 (컨셉, 가사, Suno 프롬프트)
│   ├── 01_봄이라고_부를게/
│   ├── 02_너를_다시/
│   └── template/          ← 워크플로우 템플릿
├── scripts/
│   ├── publish.py         ← YouTube 게시 오케스트레이터
│   ├── youtube_upload.py  ← YouTube Data API v3 업로드
│   ├── drive_to_youtube.py ← Google Drive → YouTube 파이프라인
│   ├── create_video.py    ← 커버 이미지 + 오디오 → MP4 영상 (ffmpeg)
│   ├── generate_thumbnail.py ← YouTube 썸네일 자동 생성 (Pillow)
│   ├── jazz_pipeline.py   ← 재즈 곡 자동 생성 파이프라인
│   └── lyrics_to_srt.py   ← 가사 → SRT 자막 변환
├── docs/
│   ├── suno_guide.md      ← Suno 프롬프트 가이드
│   ├── 작사가/            ← 작사법 분석 (김이나)
│   └── 프로젝트/
│       └── TASK.md        ← 태스크 관리
├── tests/                 ← pytest 테스트
└── logs/                  ← 실행 로그
```

### 데이터 흐름

**텔레그램 봇 (실시간 대화)**
```
텔레그램 메시지
    ↓
bot.py (핸들러 + per-user lock + global semaphore)
    ↓
db.py → 세션 조회 + 히스토리 로딩 (최근 10쌍)
    ↓
claude -p --system-prompt --tools "" --no-session-persistence
    ↓
응답 텍스트 파싱
    ├── 텍스트 → 텔레그램 전송
    ├── ```midi-json``` 블록 → midiutil → .mid → 텔레그램
    ├── audio.py → FluidSynth → .ogg → 텔레그램 인라인 재생
    ├── midi_utils.py → 피아노롤 텍스트 시각화
    └── db.py → 메시지 저장 (midi_json 포함)
```

**Suno 다운로드 + YouTube 업로드 파이프라인**
```
suno_download.py (Clerk JWT → studio-api-prod.suno.com)
    ↓
WAV/MP3 다운로드 → data/suno/
    ↓
ffmpeg → MP4 영상 생성 (커버 이미지 + 오디오)
    ↓
YouTube Data API v3 → YouTube 업로드
    ↓
db.py → suno_songs 테이블에 메타데이터 저장
```

### 텔레그램 봇 명령어

| 명령어 | 설명 |
|--------|------|
| `/start` | 소개 |
| `/help` | 전체 명령어 안내 |
| `/lyrics [주제]` | AI 작사 (벌스/코러스/브릿지) |
| `/chord [분위기]` | 코드 진행 추천 + MIDI + 시각화 |
| `/midi [설명]` | 멜로디 MIDI 생성 + 피아노롤 |
| `/theory [질문]` | 음악 이론 Q&A |
| `/new` | 새 대화 시작 (맥락 초기화) |
| `/idea [설명]` | 영감을 MIDI 스니펫으로 즉시 기록 |
| `/library` | 저장된 아이디어 모아보기 |
| `/export [번호]` | MIDI 파일 재전송 |
| `/remix [번호] [스타일]` | 기존 아이디어 스타일 변형 |
| `/quiz` | 음악 이론 퀴즈 |
| `/daily` | 매일 퀴즈 구독 (준비 중) |
| `/suno [프롬프트파일명]` | Suno AI로 곡 생성 |
| `/suno_list` | 생성한 Suno 곡 목록 |
| 자유 대화 | 음악 관련 아무 질문 (대화 기억) |

## 서비스 운영

| 항목 | 설명 |
|------|------|
| 서비스 | `music-bot.service` (systemd user service) |
| 서비스 파일 | `~/.config/systemd/user/music-bot.service` |
| 시작 | `systemctl --user start music-bot` |
| 중지 | `systemctl --user stop music-bot` |
| 재시작 | `systemctl --user restart music-bot` |
| 상태 확인 | `systemctl --user status music-bot` |
| 로그 | `journalctl --user -u music-bot -f` |
| 자동 재시작 | `Restart=always, RestartSec=5` |

## 에이전트 (`.claude/agents/`)

| 에이전트 | 역할 | 모델 |
|---------|------|------|
| `lyricist` | 한국어 작사 (김이나 작사법 기반) | opus |
| `composer` | 코드 진행 + 멜로디 + MIDI JSON 생성 | sonnet |
| `mixing-engineer` | 스템 믹스 밸런스/음색 조정 | sonnet |
| `vocalist` | 보컬 스타일 분석 + Suno 보컬 태그 최적화 | sonnet |
| `suno-prompt-engineer` | Suno Style of Music 태그 + 섹션 마커 최적화 | sonnet |

## 핵심 규칙

### 코드 컨벤션
- 변수/함수명 영어, 주석/커밋 메시지 한국어
- Python 3.12+ type hints 사용
- 외부 의존성 최소화

### MIDI 생성
- Claude가 `midi-json` 코드블록으로 노트 데이터 반환
- bot.py가 파싱 → midiutil로 .mid 생성 → 텔레그램 전송
- GM 악기 번호 사용 (0=피아노, 24=기타, 33=베이스, 48=현악기)
- 한국어 트랙명은 ISO-8859-1 호환 안 되므로 "Track N"으로 폴백

### Claude CLI 호출
- `--system-prompt`: 시스템 프롬프트 별도 전달 (CLAUDE.md 자동로딩 방지)
- `--tools ""`: 모든 툴 비활성화 (보안)
- `--no-session-persistence`: 세션 파일 누적 방지

### Suno 연동
- **다운로드**: `suno_download.py` — Clerk JWT 인증 → `studio-api-prod.suno.com` API 직접 호출
- **생성**: `suno_client.py` — undetected-chromedriver 기반 (Turnstile 우회). generate API는 hcaptcha 추가 검증으로 불안정
- **프롬프트**: `songs/{곡번호}_{곡명}/suno_prompt*.md` 형식으로 관리

### YouTube 업로드
- YouTube Data API v3 사용 (OAuth: `client_secrets.json` + `token.json`)
- `suno_download.py --upload-youtube`: 다운로드 후 자동 업로드
- `scripts/publish.py`: 오케스트레이터 (썸네일 생성 → MP4 변환 → 업로드)
- `scripts/drive_to_youtube.py`: Google Drive에서 가져와 YouTube 업로드

### Google Drive 연동
- `drive_uploader.py` — 서비스 계정 인증으로 WAV/MP3 업로드 + 공유 링크 생성
- 환경변수: `GOOGLE_CREDENTIALS_PATH`, `GOOGLE_DRIVE_FOLDER_ID`

### 보안
- .env 파일 절대 커밋 금지 (.gitignore에 포함)
- 봇 토큰 노출 금지
- data/ 디렉토리 (DB, MIDI, Suno 다운로드) 커밋 금지
- client_secrets.json, token.json 커밋 금지
- MIDI 파일명에서 위험 문자 제거 (커맨드 인젝션 방지)
- Claude CLI 툴 비활성화 (사용자 입력이 Bash/Edit 트리거 방지)

## gstack

Use /browse from gstack for all web browsing.
