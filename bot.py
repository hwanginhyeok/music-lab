#!/usr/bin/env python3
"""
Music Lab 텔레그램 봇 — AI 작사/작곡/MIDI 생성

명령어:
  /start          — 소개
  /lyrics [주제]  — AI 작사 (장르/분위기 지정 가능)
  /chord [분위기] — 코드 진행 추천 + MIDI 생성
  /midi [설명]    — 멜로디 MIDI 생성
  /theory [질문]  — 음악 이론 질문
  /help           — 도움말

일반 메시지도 음악 관련 대화로 처리.
"""
from __future__ import annotations

import io
import json
import logging
import os
import tempfile
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from midiutil import MIDIFile
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ---------------------------------------------------------------------------
# 설정
# ---------------------------------------------------------------------------
load_dotenv()
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CLAUDE_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("music-lab")

client = anthropic.Anthropic(api_key=CLAUDE_API_KEY) if CLAUDE_API_KEY else None

# 사용자별 대화 히스토리
conversations: dict[int, list[dict]] = {}

SYSTEM_PROMPT = """너는 Music Lab 봇이다. 음악 작곡/작사/이론을 가르치는 AI 뮤직 튜터.

역할:
- 음악 이론 (스케일, 코드, 리듬, 곡 구조) 을 쉽게 설명
- 작사 요청 시 벌스/코러스/브릿지 구조로 가사 작성 + 기법 설명
- 코드 진행 추천 시 왜 그 진행이 좋은지 감정적/이론적으로 설명
- MIDI 생성 요청 시 JSON 형식으로 노트 데이터 반환

MIDI 생성이 필요할 때는 반드시 아래 JSON 형식으로 응답에 포함:
```midi-json
{
  "title": "곡 제목",
  "bpm": 120,
  "time_signature": [4, 4],
  "tracks": [
    {
      "name": "멜로디",
      "instrument": 0,
      "channel": 0,
      "notes": [
        {"pitch": 60, "start": 0.0, "duration": 1.0, "velocity": 100},
        {"pitch": 62, "start": 1.0, "duration": 1.0, "velocity": 100}
      ]
    }
  ]
}
```

pitch: MIDI 노트 번호 (60=C4, 62=D4, 64=E4 ...)
start: 비트 단위 시작 시점
duration: 비트 단위 길이
velocity: 세기 (0~127)
instrument: GM 악기 번호 (0=피아노, 24=기타, 33=베이스, 48=현악기, 73=플루트)

코드를 MIDI로 줄 때는 화음의 각 음을 같은 start에 배치.
예: C 코드 = pitch 60, 64, 67 동시.

항상 한국어로 대화. 음악 용어는 영어 병기 (예: "으뜸음(Tonic)").
초보자에게 설명하듯이 쉽게, 하지만 정확하게."""


# ---------------------------------------------------------------------------
# MIDI 생성
# ---------------------------------------------------------------------------
def parse_midi_json(text: str) -> dict | None:
    """응답에서 ```midi-json ... ``` 블록을 파싱."""
    import re
    m = re.search(r"```midi-json\s*\n(.*?)\n```", text, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def generate_midi(data: dict) -> bytes:
    """MIDI JSON 데이터 → MIDI 파일 바이트."""
    tracks = data.get("tracks", [])
    midi = MIDIFile(len(tracks))
    bpm = data.get("bpm", 120)

    for i, track in enumerate(tracks):
        midi.addTrackName(i, 0, track.get("name", f"Track {i}"))
        midi.addTempo(i, 0, bpm)

        channel = track.get("channel", 0)
        instrument = track.get("instrument", 0)
        midi.addProgramChange(i, channel, 0, instrument)

        for note in track.get("notes", []):
            midi.addNote(
                track=i,
                channel=channel,
                pitch=note["pitch"],
                time=note["start"],
                duration=note["duration"],
                volume=note.get("velocity", 100),
            )

    buf = io.BytesIO()
    midi.writeFile(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Claude API 호출
# ---------------------------------------------------------------------------
def ask_claude(user_id: int, message: str) -> str:
    """Claude API로 음악 대화."""
    if not client:
        return "⚠️ ANTHROPIC_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요."

    # 대화 히스토리 관리 (최대 20개)
    if user_id not in conversations:
        conversations[user_id] = []

    conversations[user_id].append({"role": "user", "content": message})

    # 최근 20개만 유지
    if len(conversations[user_id]) > 20:
        conversations[user_id] = conversations[user_id][-20:]

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=conversations[user_id],
        )
        assistant_msg = response.content[0].text
        conversations[user_id].append({"role": "assistant", "content": assistant_msg})
        return assistant_msg
    except Exception as e:
        logger.error("Claude API 오류: %s", e)
        return f"⚠️ AI 응답 오류: {e}"


# ---------------------------------------------------------------------------
# 텔레그램 핸들러
# ---------------------------------------------------------------------------
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🎵 *Music Lab* 에 오신 걸 환영합니다!\n\n"
        "AI와 함께 작사/작곡을 배우고 만들어보세요.\n\n"
        "📝 `/lyrics 이별 발라드` — 가사 생성\n"
        "🎹 `/chord 슬픈 분위기` — 코드 진행 + MIDI\n"
        "🎼 `/midi C장조 밝은 멜로디` — MIDI 파일 생성\n"
        "📖 `/theory 코드란 뭐야?` — 음악 이론 질문\n"
        "💬 그냥 말 걸어도 됩니다!\n\n"
        "만든 MIDI는 Suno나 DAW에서 바로 활용 가능 🎧",
        parse_mode="Markdown",
    )


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🎵 *Music Lab 명령어*\n\n"
        "`/lyrics [주제/장르/분위기]`\n"
        "  예: `/lyrics 비오는 날 카페 재즈`\n\n"
        "`/chord [분위기/장르]`\n"
        "  예: `/chord 밝은 팝`\n"
        "  → 코드 진행 추천 + MIDI 파일\n\n"
        "`/midi [설명]`\n"
        "  예: `/midi C장조 4마디 피아노 멜로디`\n"
        "  → MIDI 파일 생성해서 전송\n\n"
        "`/theory [질문]`\n"
        "  예: `/theory 마이너 스케일이 뭐야?`\n\n"
        "💬 명령어 없이 자유롭게 대화해도 OK",
        parse_mode="Markdown",
    )


async def _respond_with_midi(update: Update, response: str) -> None:
    """응답 텍스트 + MIDI JSON이 있으면 파일도 전송."""
    # MIDI JSON 파싱 시도
    midi_data = parse_midi_json(response)

    # 텍스트 응답 (midi-json 블록 제거해서 보내기)
    import re
    clean_text = re.sub(r"```midi-json\s*\n.*?\n```", "", response, flags=re.DOTALL).strip()

    # 텔레그램 메시지 길이 제한 (4096자)
    if len(clean_text) > 4000:
        for i in range(0, len(clean_text), 4000):
            await update.message.reply_text(clean_text[i:i+4000])
    elif clean_text:
        await update.message.reply_text(clean_text)

    # MIDI 파일 전송
    if midi_data:
        try:
            midi_bytes = generate_midi(midi_data)
            title = midi_data.get("title", "music-lab")
            filename = f"{title.replace(' ', '_')}.mid"
            await update.message.reply_document(
                document=io.BytesIO(midi_bytes),
                filename=filename,
                caption=f"🎹 {title} ({midi_data.get('bpm', 120)} BPM)",
            )
        except Exception as e:
            logger.error("MIDI 생성 오류: %s", e)
            await update.message.reply_text(f"⚠️ MIDI 파일 생성 실패: {e}")


async def cmd_lyrics(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    topic = " ".join(ctx.args) if ctx.args else "자유 주제"
    prompt = f"작사 요청: '{topic}'\n\n벌스 2개, 코러스, 브릿지 포함해서 가사를 써줘. 각 파트가 왜 이렇게 구성되는지 작사 기법도 간단히 설명해줘."
    response = ask_claude(update.effective_user.id, prompt)
    await _respond_with_midi(update, response)


async def cmd_chord(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    mood = " ".join(ctx.args) if ctx.args else "자연스럽고 편안한"
    prompt = (
        f"코드 진행 요청: '{mood}' 분위기\n\n"
        "8마디 코드 진행을 추천해줘. 각 코드가 왜 그 위치에 있는지 감정적/이론적으로 설명하고, "
        "MIDI로도 생성해줘 (피아노, 코드당 2비트씩). midi-json 블록으로 포함해."
    )
    response = ask_claude(update.effective_user.id, prompt)
    await _respond_with_midi(update, response)


async def cmd_midi(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    desc = " ".join(ctx.args) if ctx.args else "C장조 4마디 밝은 피아노 멜로디"
    prompt = (
        f"MIDI 생성 요청: '{desc}'\n\n"
        "설명에 맞는 멜로디/코드를 midi-json 블록으로 생성해줘. "
        "음악적으로 왜 이런 선택을 했는지 간단히 설명도 해줘."
    )
    response = ask_claude(update.effective_user.id, prompt)
    await _respond_with_midi(update, response)


async def cmd_theory(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    question = " ".join(ctx.args) if ctx.args else "음악 이론의 기초를 알려줘"
    prompt = f"음악 이론 질문: {question}"
    response = ask_claude(update.effective_user.id, prompt)
    await _respond_with_midi(update, response)


async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """일반 메시지 — 자유 대화."""
    if not update.message or not update.message.text:
        return
    response = ask_claude(update.effective_user.id, update.message.text)
    await _respond_with_midi(update, response)


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------
def main() -> None:
    logger.info("Music Lab 봇 시작")
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("lyrics", cmd_lyrics))
    app.add_handler(CommandHandler("chord", cmd_chord))
    app.add_handler(CommandHandler("midi", cmd_midi))
    app.add_handler(CommandHandler("theory", cmd_theory))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("폴링 시작...")
    app.run_polling()


if __name__ == "__main__":
    main()
