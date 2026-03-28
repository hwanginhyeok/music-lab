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
├── bot.py                 ← 텔레그램 봇 (메인)
├── .env                   ← TELEGRAM_BOT_TOKEN
├── docs/
│   └── 프로젝트/
│       └── TASK.md        ← 태스크 관리
└── tests/                 ← pytest 테스트
```

### 데이터 흐름

```
텔레그램 메시지
    ↓
bot.py (핸들러)
    ↓
claude -p "시스템프롬프트 + 유저메시지"  (로컬 CLI, OAuth)
    ↓
응답 텍스트 파싱
    ├── 텍스트 → 텔레그램 전송
    └── ```midi-json``` 블록 → MIDIFile 생성 → .mid 파일 텔레그램 전송
```

### 텔레그램 봇 명령어

| 명령어 | 설명 |
|--------|------|
| `/start` | 소개 |
| `/lyrics [주제]` | AI 작사 (벌스/코러스/브릿지) |
| `/chord [분위기]` | 코드 진행 추천 + MIDI |
| `/midi [설명]` | 멜로디 MIDI 생성 |
| `/theory [질문]` | 음악 이론 Q&A |
| 자유 대화 | 음악 관련 아무 질문 |

## 핵심 규칙

### 코드 컨벤션
- 변수/함수명 영어, 주석/커밋 메시지 한국어
- Python 3.12+ type hints 사용
- 외부 의존성 최소화

### MIDI 생성
- Claude가 `midi-json` 코드블록으로 노트 데이터 반환
- bot.py가 파싱 → midiutil로 .mid 생성 → 텔레그램 전송
- GM 악기 번호 사용 (0=피아노, 24=기타, 33=베이스, 48=현악기)

### 보안
- .env 파일 절대 커밋 금지 (.gitignore에 포함)
- 봇 토큰 노출 금지

## tmux 세션

| 세션 | 내용 |
|------|------|
| `music` | bot.py 실행 |

## gstack

Use /browse from gstack for all web browsing.
