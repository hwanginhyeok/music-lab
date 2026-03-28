# Music Lab

> AI 작사/작곡/MIDI 생성 학습 프로젝트. 텔레그램 봇으로 Claude와 대화하며 음악을 배우고 만든다.

---

## Commands

```bash
# 봇 실행
python3 bot.py                    # 텔레그램 봇 시작 (Claude CLI OAuth)

# 테스트
python3 -m pytest tests/ -v      # 테스트 실행
```

## Tech Stack

- **Python 3.12** — 메인 언어
- **python-telegram-bot 22.7** — 텔레그램 봇 프레임워크
- **Claude CLI (npx @anthropic-ai/claude-code)** — AI 백엔드 (OAuth, API 키 불필요)
- **midiutil** — MIDI 파일 생성
- **python-dotenv** — 환경변수 관리

## Architecture

```
music-lab/
├── CLAUDE.md              ← 이 파일
├── bot.py                 ← 텔레그램 봇 (메인 핸들러 12개)
├── db.py                  ← SQLite 대화 히스토리 + 아이디어 저장
├── audio.py               ← MIDI → OGG 오디오 변환 (FluidSynth)
├── midi_utils.py          ← 피아노롤 텍스트 시각화
├── .env                   ← TELEGRAM_BOT_TOKEN, SOUNDFONT_PATH(선택)
├── data/                  ← SQLite DB + MIDI 파일 (.gitignore)
├── docs/
│   └── 프로젝트/
│       └── TASK.md        ← 태스크 관리
└── tests/                 ← pytest 테스트 (36개)
```

### 데이터 흐름

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
| 자유 대화 | 음악 관련 아무 질문 (대화 기억) |

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

### 보안
- .env 파일 절대 커밋 금지 (.gitignore에 포함)
- 봇 토큰 노출 금지
- data/ 디렉토리 (DB, MIDI 파일) 커밋 금지
- MIDI 파일명에서 위험 문자 제거 (커맨드 인젝션 방지)
- Claude CLI 툴 비활성화 (사용자 입력이 Bash/Edit 트리거 방지)

## tmux 세션

| 세션 | 내용 |
|------|------|
| `music` | bot.py 실행 |

## gstack

Use /browse from gstack for all web browsing.
