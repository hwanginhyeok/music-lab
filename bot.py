#!/usr/bin/env python3
"""
Music Lab 텔레그램 봇 — Claude CLI 로컬 연동 (API 키 불필요)

Claude Code CLI의 OAuth 인증을 그대로 사용.
메시지 → claude -p → 응답 → MIDI 파싱 → 텔레그램 전송.

명령어:
  /start          — 소개
  /lyrics [주제]  — AI 작사
  /chord [분위기] — 코드 진행 + MIDI
  /midi [설명]    — 멜로디 MIDI 생성
  /theory [질문]  — 음악 이론 질문
  /save [곡이름]  — 대화의 가사/코드를 songs/에 저장
  /help           — 도움말
"""
from __future__ import annotations

import asyncio
import io
import json
import logging
import os
import re
import subprocess
from collections import defaultdict
from pathlib import Path

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

import db

# ---------------------------------------------------------------------------
# 설정
# ---------------------------------------------------------------------------
load_dotenv()
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("music-lab")

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

항상 한국어로 대화. 음악 용어는 영어 병기.
초보자에게 설명하듯이 쉽게, 하지만 정확하게.

코드 진행을 추천할 때는 아래 형식으로 시각화해줘:
```
| C  | G  | Am7 | F  |
분석: I - V - vi7 - IV
분위기: 밝음 → 안정 → 섬세함 → 편안
```"""

# ---------------------------------------------------------------------------
# 동시성 제어
# ---------------------------------------------------------------------------
# 글로벌 동시 Claude 프로세스 제한 (OOM 방지)
_claude_semaphore = asyncio.Semaphore(2)
# Suno 곡 생성 동시 실행 제한 (Chrome 자동화 — 1개만 허용)
_suno_semaphore = asyncio.Semaphore(1)
# per-user 락 (한 사용자의 중복 요청 방지)
_user_locks: dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)


# ---------------------------------------------------------------------------
# 컨텍스트 포매팅
# ---------------------------------------------------------------------------
def format_context(history: list[dict], current_message: str) -> str:
    """대화 히스토리 + 현재 메시지를 프롬프트로 포맷."""
    if not history:
        return current_message

    lines = ["[이전 대화]"]
    for msg in history:
        role_label = "USER" if msg["role"] == "user" else "ASSISTANT"
        # 히스토리에 midi-json 블록이 있으면 요약 (프롬프트 비대화 방지)
        content = msg["content"]
        if "```midi-json" in content:
            content = re.sub(
                r"```midi-json\s*\n.*?\n```",
                "[MIDI 데이터 생성됨]",
                content,
                flags=re.DOTALL,
            )
        lines.append(f"{role_label}: {content}")

    lines.append("")
    lines.append(f"[현재 요청]")
    lines.append(f"USER: {current_message}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Claude CLI 호출 (API 키 불필요, OAuth 사용)
# ---------------------------------------------------------------------------
async def ask_claude(message: str, history: list[dict] | None = None) -> str:
    """Claude CLI로 음악 대화. 로컬 OAuth 인증 사용."""
    prompt_text = format_context(history or [], message)

    try:
        async with _claude_semaphore:
            proc = await asyncio.create_subprocess_exec(
                "npx", "-y", "@anthropic-ai/claude-code@2.1.91",
                "-p", prompt_text,
                "--system-prompt", SYSTEM_PROMPT,
                "--tools", "",
                "--no-session-persistence",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(Path.home() / "music-lab"),
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        response = stdout.decode("utf-8").strip()

        if not response:
            err = stderr.decode("utf-8").strip()
            logger.error("Claude CLI stderr: %s", err[:200])
            return "⚠️ 응답이 비어있습니다. 다시 시도해주세요."

        return response
    except asyncio.TimeoutError:
        return "⚠️ 응답 시간 초과 (2분). 더 짧은 요청으로 다시 시도해주세요."
    except Exception as e:
        logger.error("Claude CLI 오류: %s", e)
        return f"⚠️ 오류: {e}"


# ---------------------------------------------------------------------------
# MIDI 생성
# ---------------------------------------------------------------------------
def parse_midi_json(text: str) -> dict | None:
    """응답에서 ```midi-json ... ``` 블록을 파싱."""
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
        # midiutil은 ISO-8859-1만 지원 — 한국어 트랙 이름은 ASCII로 폴백
        raw_name = track.get("name", f"Track {i}")
        try:
            raw_name.encode("ISO-8859-1")
            track_name = raw_name
        except UnicodeEncodeError:
            track_name = f"Track {i}"
        midi.addTrackName(i, 0, track_name)
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
# 텔레그램 핸들러
# ---------------------------------------------------------------------------
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🎵 Music Lab 에 오신 걸 환영합니다!\n\n"
        "AI와 함께 작사/작곡을 배우고 만들어보세요.\n\n"
        "📝 /lyrics 이별 발라드 — 가사 생성\n"
        "🎹 /chord 슬픈 분위기 — 코드 진행 + MIDI\n"
        "🎼 /midi C장조 밝은 멜로디 — MIDI 파일 생성\n"
        "📖 /theory 코드란 뭐야? — 음악 이론 질문\n"
        "💬 그냥 말 걸어도 됩니다!\n\n"
        "만든 MIDI는 Suno나 DAW에서 바로 활용 가능 🎧",
    )


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🎵 Music Lab 명령어\n\n"
        "/lyrics [주제/장르/분위기]\n"
        "  예: /lyrics 비오는 날 카페 재즈\n\n"
        "/chord [분위기/장르]\n"
        "  예: /chord 밝은 팝\n"
        "  → 코드 진행 추천 + MIDI 파일\n\n"
        "/midi [설명]\n"
        "  예: /midi C장조 4마디 피아노 멜로디\n"
        "  → MIDI 파일 생성해서 전송\n\n"
        "/theory [질문]\n"
        "  예: /theory 마이너 스케일이 뭐야?\n\n"
        "/new — 새 대화 시작 (이전 맥락 초기화)\n\n"
        "💡 영감 노트\n"
        "/idea [설명] — 아이디어를 즉시 MIDI로 기록\n"
        "/library — 저장된 아이디어 모아보기\n"
        "/export [번호] — MIDI 파일 다시 받기\n"
        "/remix [번호] [스타일] — 아이디어 변형\n\n"
        "💾 /save [곡이름] — 대화의 가사/코드를 songs/에 저장\n\n"
        "📝 /quiz — 음악 이론 퀴즈\n\n"
        "🎬 YouTube 게시\n"
        "/publish — Suno 곡 목록 + YouTube 업로드\n"
        "/publish [song_id] — 해당 곡 YouTube 게시\n\n"
        "💬 명령어 없이 자유롭게 대화해도 OK\n"
        "💡 대화 맥락을 기억해서 \"아까 그 코드 바꿔줘\" 가능!",
    )


async def cmd_new(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """새 대화 시작 — 이전 맥락 초기화."""
    if not update.effective_user:
        return
    session_id = db.new_session(update.effective_user.id)
    await update.message.reply_text(
        f"🔄 새 대화를 시작합니다! (세션: {session_id})\n"
        "이전 대화 맥락이 초기화되었어요.",
    )


async def _respond_with_midi(update: Update, response: str, session_id: str | None = None) -> None:
    """응답 텍스트 + MIDI JSON이 있으면 파일도 전송. 피아노롤 시각화 포함."""
    midi_data = parse_midi_json(response)

    # 텍스트 응답 (midi-json 블록 제거)
    clean_text = re.sub(r"```midi-json\s*\n.*?\n```", "", response, flags=re.DOTALL).strip()

    if len(clean_text) > 4000:
        for i in range(0, len(clean_text), 4000):
            await update.message.reply_text(clean_text[i:i+4000])
    elif clean_text:
        await update.message.reply_text(clean_text)

    if midi_data:
        try:
            midi_bytes = generate_midi(midi_data)
            title = midi_data.get("title", "music-lab")
            # 파일명에서 위험 문자 제거 (커맨드 인젝션 방지)
            safe_title = re.sub(r'[^\w가-힣\s-]', '', title).replace(' ', '_') or "music-lab"
            filename = f"{safe_title}.mid"

            # MIDI 파일 전송
            await update.message.reply_document(
                document=io.BytesIO(midi_bytes),
                filename=filename,
                caption=f"🎹 {title} ({midi_data.get('bpm', 120)} BPM)",
            )

            # 오디오 변환 시도 (FluidSynth)
            try:
                from audio import midi_to_audio
                ogg_bytes = midi_to_audio(midi_bytes)
                if ogg_bytes:
                    await update.message.reply_voice(
                        voice=io.BytesIO(ogg_bytes),
                        caption=f"🎧 {title}",
                    )
            except ImportError:
                pass  # audio.py 없으면 스킵
            except Exception as e:
                logger.error("오디오 변환 오류: %s", e)

            # 피아노롤 시각화
            try:
                from midi_utils import render_piano_roll
                piano_roll = render_piano_roll(midi_data)
                if piano_roll:
                    await update.message.reply_text(piano_roll)
            except ImportError:
                pass  # midi_utils.py 없으면 스킵
            except Exception as e:
                logger.error("피아노롤 렌더링 오류: %s", e)

            # DB에 assistant 응답 저장 (midi_json 포함)
            if session_id and update.effective_user:
                midi_json_str = json.dumps(midi_data, ensure_ascii=False)
                db.save_message(
                    update.effective_user.id, session_id,
                    "assistant", response,
                    midi_json=midi_json_str,
                )
                # MIDI 파일을 디스크에 저장
                user_id = update.effective_user.id
                midi_dir = Path(f"data/midi/{user_id}")
                midi_dir.mkdir(parents=True, exist_ok=True)
                midi_file_path = midi_dir / filename
                midi_file_path.write_bytes(midi_bytes)

        except Exception as e:
            logger.error("MIDI 생성 오류: %s", e)
            await update.message.reply_text(f"⚠️ MIDI 파일 생성 실패: {e}")
    else:
        # MIDI 없는 응답도 DB에 저장
        if session_id and update.effective_user:
            db.save_message(
                update.effective_user.id, session_id,
                "assistant", response,
            )


async def _handle_with_memory(
    update: Update, user_message: str, thinking_emoji: str = "💭"
) -> None:
    """대화 기억이 있는 공통 핸들러. per-user lock + DB 저장/조회."""
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id

    # per-user lock: 이미 처리 중이면 안내 메시지
    lock = _user_locks[user_id]
    if lock.locked():
        await update.message.reply_text("⏳ 이전 요청을 처리 중이에요. 잠시만 기다려주세요!")
        return

    async with lock:
        await update.message.reply_text(f"{thinking_emoji} 생각하는 중...")

        # 세션 + 히스토리 조회
        session_id = db.get_or_create_session(user_id)
        history = db.get_history(session_id)

        # 사용자 메시지 저장
        db.save_message(user_id, session_id, "user", user_message)

        # Claude 호출 (히스토리 포함)
        response = await ask_claude(user_message, history)

        # 응답 전송 + assistant 메시지 저장 (MIDI 포함 시 _respond_with_midi에서 처리)
        await _respond_with_midi(update, response, session_id)


async def cmd_lyrics(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    topic = " ".join(ctx.args) if ctx.args else "자유 주제"
    await _handle_with_memory(
        update,
        f"작사 요청: '{topic}'\n\n벌스 2개, 코러스, 브릿지 포함해서 가사를 써줘. "
        "각 파트가 왜 이렇게 구성되는지 작사 기법도 간단히 설명해줘.",
        thinking_emoji="✍️",
    )


async def cmd_chord(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    mood = " ".join(ctx.args) if ctx.args else "자연스럽고 편안한"
    await _handle_with_memory(
        update,
        f"코드 진행 요청: '{mood}' 분위기\n\n"
        "8마디 코드 진행을 추천해줘. 각 코드가 왜 그 위치에 있는지 설명하고, "
        "MIDI로도 생성해줘 (피아노, 코드당 2비트씩). midi-json 블록으로 포함해.",
        thinking_emoji="🎹",
    )


async def cmd_midi(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    desc = " ".join(ctx.args) if ctx.args else "C장조 4마디 밝은 피아노 멜로디"
    await _handle_with_memory(
        update,
        f"MIDI 생성 요청: '{desc}'\n\n"
        "설명에 맞는 멜로디/코드를 midi-json 블록으로 생성해줘. "
        "음악적으로 왜 이런 선택을 했는지 간단히 설명도 해줘.",
        thinking_emoji="🎼",
    )


async def cmd_theory(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    question = " ".join(ctx.args) if ctx.args else "음악 이론의 기초를 알려줘"
    await _handle_with_memory(
        update,
        f"음악 이론 질문: {question}",
        thinking_emoji="📖",
    )


async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """일반 메시지 — 자유 대화."""
    if not update.message or not update.message.text:
        return
    await _handle_with_memory(update, update.message.text)


# ---------------------------------------------------------------------------
# Stage 2: 영감 노트 (/idea, /library, /export, /remix)
# ---------------------------------------------------------------------------
async def cmd_idea(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """짧은 음악 아이디어를 즉시 MIDI 스니펫으로 기록."""
    if not update.effective_user or not update.message:
        return
    desc = " ".join(ctx.args) if ctx.args else ""
    if not desc:
        await update.message.reply_text(
            "💡 사용법: /idea [설명]\n예: /idea 비오는 날 피아노 루프"
        )
        return

    user_id = update.effective_user.id
    lock = _user_locks[user_id]
    if lock.locked():
        await update.message.reply_text("⏳ 이전 요청을 처리 중이에요.")
        return

    async with lock:
        await update.message.reply_text("💡 아이디어를 MIDI로 변환 중...")

        # Claude에게 짧은 MIDI 스니펫 + 태그 요청
        response = await ask_claude(
            f"음악 아이디어: '{desc}'\n\n"
            "이 아이디어를 4마디 이내의 짧은 MIDI 스니펫으로 만들어줘. midi-json 블록으로 포함해.\n"
            "그리고 응답 마지막에 이 아이디어에 어울리는 태그를 아래 형식으로 달아줘:\n"
            "태그: #장르 #감정 #악기\n"
            "예: 태그: #재즈 #몽환적 #피아노"
        )

        # 태그 추출
        tags = _extract_tags(response)
        midi_data = parse_midi_json(response)
        midi_json_str = json.dumps(midi_data, ensure_ascii=False) if midi_data else None

        # MIDI 파일 저장
        midi_path = None
        if midi_data:
            try:
                midi_bytes = generate_midi(midi_data)
                midi_dir = Path(f"data/midi/{user_id}/ideas")
                midi_dir.mkdir(parents=True, exist_ok=True)
                safe_desc = re.sub(r'[^\w가-힣\s-]', '', desc)[:30].replace(' ', '_') or "idea"
                midi_path = str(midi_dir / f"{safe_desc}.mid")
                Path(midi_path).write_bytes(midi_bytes)
            except Exception as e:
                logger.error("아이디어 MIDI 저장 오류: %s", e)

        # DB 저장
        idea_id = db.save_idea(user_id, desc, tags=tags, midi_json=midi_json_str, midi_path=midi_path)

        # 응답 전송
        await _respond_with_midi(update, response)

        if idea_id:
            tag_str = " ".join(f"#{t}" for t in tags) if tags else "(태그 없음)"
            await update.message.reply_text(
                f"💾 아이디어 #{idea_id} 저장 완료!\n{tag_str}\n"
                f"/library 로 모아보기 | /remix {idea_id} [스타일] 로 변형"
            )


def _extract_tags(text: str) -> list[str]:
    """Claude 응답에서 '태그: #xxx #yyy' 형식의 태그를 추출."""
    m = re.search(r"태그:\s*((?:#\S+\s*)+)", text)
    if not m:
        return ["미분류"]
    raw = m.group(1)
    tags = [t.lstrip("#").strip() for t in raw.split("#") if t.strip()]
    return tags or ["미분류"]


async def cmd_library(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """저장된 아이디어 목록 조회."""
    if not update.effective_user:
        return

    ideas = db.get_ideas(update.effective_user.id, limit=20)
    if not ideas:
        await update.message.reply_text(
            "📚 아직 저장된 아이디어가 없어요.\n/idea 비오는 날 피아노 루프 — 로 첫 영감을 기록해보세요!"
        )
        return

    lines = ["📚 내 아이디어 라이브러리\n"]
    for idea in ideas:
        tags = " ".join(f"#{t}" for t in idea["tags"]) if idea["tags"] else ""
        lines.append(f"  #{idea['id']}  {idea['description']}")
        if tags:
            lines.append(f"      {tags}")

    lines.append(f"\n총 {len(ideas)}개 | /export [번호] 로 MIDI 다운 | /remix [번호] [스타일]")
    await update.message.reply_text("\n".join(lines))


async def cmd_export(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """저장된 아이디어의 MIDI 파일 재전송."""
    if not update.effective_user or not update.message:
        return

    if not ctx.args:
        await update.message.reply_text("사용법: /export [아이디어 번호]\n예: /export 1")
        return

    try:
        idea_id = int(ctx.args[0])
    except ValueError:
        await update.message.reply_text("⚠️ 번호를 입력해주세요. 예: /export 1")
        return

    idea = db.get_idea_by_id(idea_id)
    if not idea:
        await update.message.reply_text(f"⚠️ #{idea_id} 아이디어를 찾을 수 없어요.")
        return

    # midi_path에서 파일 전송 시도
    if idea["midi_path"] and Path(idea["midi_path"]).is_file():
        midi_bytes = Path(idea["midi_path"]).read_bytes()
        await update.message.reply_document(
            document=io.BytesIO(midi_bytes),
            filename=f"idea_{idea_id}.mid",
            caption=f"💡 #{idea_id}: {idea['description']}",
        )
        # 오디오도 전송
        try:
            from audio import midi_to_audio
            ogg = midi_to_audio(midi_bytes)
            if ogg:
                await update.message.reply_voice(voice=io.BytesIO(ogg))
        except (ImportError, Exception):
            pass
    elif idea["midi_json"]:
        # 파일이 없으면 midi_json에서 재생성
        try:
            data = json.loads(idea["midi_json"])
            midi_bytes = generate_midi(data)
            await update.message.reply_document(
                document=io.BytesIO(midi_bytes),
                filename=f"idea_{idea_id}.mid",
                caption=f"💡 #{idea_id}: {idea['description']}",
            )
        except Exception as e:
            await update.message.reply_text(f"⚠️ MIDI 생성 실패: {e}")
    else:
        await update.message.reply_text(f"⚠️ #{idea_id}에 MIDI 데이터가 없어요.")


async def cmd_remix(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """기존 아이디어를 다른 스타일로 변형."""
    if not update.effective_user or not update.message:
        return

    if not ctx.args or len(ctx.args) < 2:
        await update.message.reply_text(
            "🔄 사용법: /remix [번호] [스타일]\n"
            "예: /remix 1 재즈 스타일로\n"
            "예: /remix 3 빠른 템포의 록"
        )
        return

    try:
        idea_id = int(ctx.args[0])
    except ValueError:
        await update.message.reply_text("⚠️ 첫 번째 인자는 아이디어 번호여야 해요.")
        return

    style = " ".join(ctx.args[1:])
    idea = db.get_idea_by_id(idea_id)

    if not idea:
        await update.message.reply_text(f"⚠️ #{idea_id} 아이디어를 찾을 수 없어요.")
        return

    if not idea["midi_json"]:
        await update.message.reply_text(f"⚠️ #{idea_id}에 MIDI 데이터가 없어서 리믹스할 수 없어요.")
        return

    user_id = update.effective_user.id
    lock = _user_locks[user_id]
    if lock.locked():
        await update.message.reply_text("⏳ 이전 요청을 처리 중이에요.")
        return

    async with lock:
        await update.message.reply_text(f"🔄 #{idea_id} 아이디어를 '{style}' 스타일로 변형 중...")

        response = await ask_claude(
            f"기존 MIDI 아이디어를 리믹스해줘.\n\n"
            f"원본 설명: {idea['description']}\n"
            f"원본 MIDI JSON:\n```midi-json\n{idea['midi_json']}\n```\n\n"
            f"요청: 이 아이디어를 '{style}' 스타일로 변형해줘.\n"
            "변형된 결과를 midi-json 블록으로 포함하고, 뭘 어떻게 바꿨는지 설명해줘."
        )

        # 리믹스 결과도 아이디어로 저장
        midi_data = parse_midi_json(response)
        if midi_data:
            tags = _extract_tags(response)
            tags.append("리믹스")
            midi_json_str = json.dumps(midi_data, ensure_ascii=False)

            midi_path = None
            try:
                midi_bytes = generate_midi(midi_data)
                midi_dir = Path(f"data/midi/{user_id}/ideas")
                midi_dir.mkdir(parents=True, exist_ok=True)
                safe_style = re.sub(r'[^\w가-힣\s-]', '', style)[:20].replace(' ', '_') or "remix"
                midi_path = str(midi_dir / f"remix_{idea_id}_{safe_style}.mid")
                Path(midi_path).write_bytes(midi_bytes)
            except Exception as e:
                logger.error("리믹스 MIDI 저장 오류: %s", e)

            new_id = db.save_idea(
                user_id, f"리믹스 #{idea_id}: {style}",
                tags=tags, midi_json=midi_json_str, midi_path=midi_path,
            )
            await _respond_with_midi(update, response)
            if new_id:
                await update.message.reply_text(f"💾 리믹스 결과가 아이디어 #{new_id}로 저장됨!")
        else:
            await _respond_with_midi(update, response)


# ---------------------------------------------------------------------------
# /save — 대화 내용을 songs/ 디렉토리에 파일로 저장
# ---------------------------------------------------------------------------
SONGS_DIR = Path("songs")


def _next_song_number() -> int:
    """songs/ 디렉토리에서 다음 곡 번호 계산. 예: 01, 02 → 다음은 03."""
    if not SONGS_DIR.exists():
        return 1
    max_num = 0
    for d in SONGS_DIR.iterdir():
        if d.is_dir():
            m = re.match(r"^(\d+)_", d.name)
            if m:
                max_num = max(max_num, int(m.group(1)))
    return max_num + 1


def _extract_lyrics(messages: list[dict]) -> str | None:
    """대화 메시지에서 가사 블록 추출. [Verse], [Chorus] 등 섹션 마커 기반."""
    # assistant 메시지를 역순 탐색 (최근 가사 우선)
    for msg in reversed(messages):
        if msg["role"] != "assistant":
            continue
        content = msg["content"]
        # 섹션 마커 패턴: [Verse], [Chorus], [Bridge], [Pre-Chorus], [Outro], [Intro] 등
        if re.search(r"\[(?:Verse|Chorus|Bridge|Pre-Chorus|Outro|Intro|Hook|Final)", content, re.IGNORECASE):
            # 가사 영역 추출: 첫 섹션 마커부터 마지막 가사 라인까지
            lines = content.split("\n")
            lyrics_lines: list[str] = []
            in_lyrics = False
            for line in lines:
                if re.match(r"\s*\[(?:Verse|Chorus|Bridge|Pre-Chorus|Outro|Intro|Hook|Final)", line, re.IGNORECASE):
                    in_lyrics = True
                if in_lyrics:
                    # midi-json 블록이나 코드 블록은 제외
                    if line.strip().startswith("```midi-json") or line.strip().startswith("```"):
                        if "midi-json" in line:
                            in_lyrics = False
                            continue
                    if not in_lyrics:
                        # midi-json 블록 끝나면 다시 탐색
                        if line.strip() == "```":
                            in_lyrics = True
                        continue
                    lyrics_lines.append(line)
            if lyrics_lines:
                return "\n".join(lyrics_lines).strip()
    return None


def _extract_chords(messages: list[dict]) -> str | None:
    """대화 메시지에서 코드 진행 추출. | C | G | Am | 또는 C → G → Am 형식 탐색."""
    # 코드 진행 패턴들 (메시지 필터링용)
    chord_pipe_pattern = re.compile(r"\|[^|]*[A-G][^|]*\|")
    analysis_pattern = re.compile(r"(분석|Analysis|분위기|Mood|키|Key)\s*:")
    chord_arrow_pattern = re.compile(r"[A-G][#b]?(?:m(?:aj)?|dim|aug|sus|add|[0-9])*\s*[→\-–]\s*[A-G]")

    for msg in reversed(messages):
        if msg["role"] != "assistant":
            continue
        content = msg["content"]

        if chord_pipe_pattern.search(content) or analysis_pattern.search(content) or chord_arrow_pattern.search(content):
            lines = content.split("\n")
            chord_lines: list[str] = []
            for line in lines:
                stripped = line.strip()
                # 코드 진행 라인 (| 포함)
                if "|" in stripped and re.search(r"\|.*[A-G]", stripped):
                    chord_lines.append(line)
                # 분석/분위기 라인
                elif analysis_pattern.match(stripped):
                    chord_lines.append(line)
                # 코드명 나열 (C → G → Am)
                elif re.search(r"[A-G][#b]?(?:m(?:aj)?|dim|aug|sus|add|[0-9])*\s*[→\-–]\s*[A-G]", stripped):
                    chord_lines.append(line)
                # 빈 줄 (섹션 구분)
                elif not stripped and chord_lines:
                    chord_lines.append(line)
            if chord_lines:
                return "\n".join(chord_lines).strip()
    return None


def _build_concept(song_name: str, messages: list[dict], has_lyrics: bool, has_chords: bool) -> str:
    """대화 내용 기반 concept.md 생성. Claude에 보내지 않고 대화에서 직접 추출."""
    # 사용자 요청에서 장르/분위기 키워드 추출
    user_requests: list[str] = []
    for msg in messages:
        if msg["role"] == "user":
            user_requests.append(msg["content"])

    # 요청 내용 요약 (최대 3개)
    request_summary = "\n".join(f"- {req[:100]}" for req in user_requests[:3])

    concept = f"""# {song_name} — 곡 컨셉

## 기본 정보
- **작업명**: {song_name}
- **장르**: (대화에서 확인)
- **BPM**: (미정)
- **키**: (미정)
- **버전**: v1.0
- **생성 방식**: 텔레그램 봇 /save 명령어로 자동 생성

## 핵심 컨셉
텔레그램 대화에서 추출한 곡 작업물.

## 대화 요청 요약
{request_summary}

## 포함된 파일
- concept.md: 이 파일
{f"- lyrics_v1.md: 가사 초안" if has_lyrics else ""}
{f"- chord_ref.md: 코드 진행 레퍼런스" if has_chords else ""}

## TODO
- [ ] 컨셉 보완
- [ ] 코드 진행 확정
- [ ] Suno 프롬프트 작성
- [ ] Suno 생성 + 피드백
"""
    return concept.strip() + "\n"


async def cmd_save(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """현재 세션의 가사/코드 진행을 songs/ 디렉토리에 저장."""
    if not update.effective_user or not update.message:
        return

    # 곡 이름 파싱
    song_name = " ".join(ctx.args).strip() if ctx.args else ""
    if not song_name:
        await update.message.reply_text(
            "💾 사용법: /save 곡이름\n"
            "예: /save 비오는_카페\n\n"
            "현재 세션의 가사/코드 진행을 songs/ 디렉토리에 저장합니다."
        )
        return

    user_id = update.effective_user.id
    lock = _user_locks[user_id]
    if lock.locked():
        await update.message.reply_text("⏳ 이전 요청을 처리 중이에요.")
        return

    async with lock:
        await update.message.reply_text("💾 대화 내용을 분석하는 중...")

        # 현재 세션 히스토리 조회
        session_id = db.get_or_create_session(user_id)
        messages = db.get_session_messages(session_id, limit=50)

        if not messages:
            await update.message.reply_text("⚠️ 현재 세션에 대화 내용이 없어요. 먼저 /lyrics 나 /chord 로 작업해보세요!")
            return

        # 가사 / 코드 추출
        lyrics = _extract_lyrics(messages)
        chords = _extract_chords(messages)

        if not lyrics and not chords:
            await update.message.reply_text(
                "⚠️ 대화에서 가사나 코드 진행을 찾지 못했어요.\n"
                "/lyrics 로 가사를 생성하거나 /chord 로 코드 진행을 만든 후 다시 시도해주세요."
            )
            return

        # 다음 곡 번호 계산 + 디렉토리 생성
        next_num = _next_song_number()
        # 곡 이름에서 파일시스템 안전 문자만 허용
        safe_name = re.sub(r'[^\w가-힣\s-]', '', song_name).replace(' ', '_') or "untitled"
        song_dir = SONGS_DIR / f"{next_num:02d}_{safe_name}"

        try:
            song_dir.mkdir(parents=True, exist_ok=True)

            # concept.md 저장
            concept_content = _build_concept(song_name, messages, bool(lyrics), bool(chords))
            (song_dir / "concept.md").write_text(concept_content, encoding="utf-8")

            saved_files = ["concept.md"]

            # lyrics_v1.md 저장
            if lyrics:
                lyrics_header = f"# {song_name}\n\n> 텔레그램 /save로 자동 저장\n\n---\n\n"
                (song_dir / "lyrics_v1.md").write_text(lyrics_header + lyrics + "\n", encoding="utf-8")
                saved_files.append("lyrics_v1.md")

            # chord_ref.md 저장
            if chords:
                chord_header = f"# {song_name} — 코드 진행 레퍼런스\n\n"
                (song_dir / "chord_ref.md").write_text(chord_header + chords + "\n", encoding="utf-8")
                saved_files.append("chord_ref.md")

            # 결과 메시지
            files_str = "\n".join(f"  📄 {f}" for f in saved_files)
            await update.message.reply_text(
                f"💾 저장 완료! songs/{song_dir.name}/\n\n"
                f"{files_str}\n\n"
                f"{'🎤 가사 저장됨' if lyrics else '⬜ 가사 없음'}\n"
                f"{'🎹 코드 진행 저장됨' if chords else '⬜ 코드 진행 없음'}\n\n"
                f"다음 단계: concept.md를 보완하고 Suno 프롬프트를 작성해보세요!"
            )
            logger.info("곡 저장 완료: %s (%s)", song_dir.name, ", ".join(saved_files))

        except Exception as e:
            logger.error("곡 저장 오류: %s", e)
            await update.message.reply_text(f"⚠️ 저장 실패: {e}")


# ---------------------------------------------------------------------------
# Stage 2: /daily 음악 퀴즈
# ---------------------------------------------------------------------------
async def cmd_daily(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """매일 음악 퀴즈 구독 토글."""
    if not update.effective_user or not update.message:
        return
    await update.message.reply_text(
        "📝 /quiz 로 바로 음악 퀴즈를 풀 수 있어요!\n"
        "(매일 자동 전송 기능은 준비 중입니다)"
    )


async def cmd_quiz(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """음악 이론 퀴즈 한 문제 출제."""
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id
    lock = _user_locks[user_id]
    if lock.locked():
        await update.message.reply_text("⏳ 이전 요청을 처리 중이에요.")
        return

    async with lock:
        await update.message.reply_text("📝 퀴즈 생성 중...")
        response = await ask_claude(
            "음악 이론 퀴즈 한 문제를 내줘.\n\n"
            "형식:\n"
            "❓ [질문]\n"
            "A) ...\nB) ...\nC) ...\nD) ...\n\n"
            "정답과 해설은 '정답 보기'라고 하면 알려줄게.\n\n"
            "난이도: 초급~중급. 코드, 스케일, 리듬, 음정, 곡 구조 중 랜덤."
        )
        await update.message.reply_text(response)


# ---------------------------------------------------------------------------
# Suno AI 곡 생성
# ---------------------------------------------------------------------------

async def cmd_suno(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Suno AI로 곡 생성. /suno <프롬프트파일명>"""
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id
    text = (update.message.text or "").replace("/suno", "").strip()

    if not text:
        await update.message.reply_text(
            "사용법:\n"
            "/suno <프롬프트 파일명>\n"
            "예: /suno suno_prompt_final\n\n"
            "songs/ 폴더의 프롬프트 파일에서 Style + Lyrics를 읽어 Suno에 전달합니다."
        )
        return

    # Suno semaphore: 이미 생성 중이면 안내
    if _suno_semaphore.locked():
        await update.message.reply_text(
            "⏳ Suno 생성이 진행 중입니다. 완료 후 다시 시도해주세요.\n"
            "(Chrome 자동화는 동시에 1건만 가능)"
        )
        return

    # 프롬프트 파일 찾기
    prompt_path = None
    for song_dir in sorted(Path("songs").iterdir()):
        if not song_dir.is_dir() or song_dir.name == "template":
            continue
        for f in song_dir.iterdir():
            if text in f.stem and f.suffix == ".md":
                prompt_path = f
                break
        if prompt_path:
            break

    if not prompt_path:
        await update.message.reply_text(f"프롬프트 파일을 찾을 수 없습니다: {text}")
        return

    from suno_pipeline import parse_prompt_file
    try:
        style, lyrics = parse_prompt_file(str(prompt_path))
    except Exception as e:
        await update.message.reply_text(f"프롬프트 파싱 실패: {e}")
        return

    if not style or not lyrics:
        await update.message.reply_text("Style 또는 Lyrics가 비어있습니다.")
        return

    title = prompt_path.parent.name.replace("_", " ")
    msg = await update.message.reply_text(
        f"🎵 Suno 곡 생성 중: {title}\n"
        f"Style: {style[:60]}...\n"
        f"⏳ 2~5분 소요됩니다..."
    )

    loop = asyncio.get_event_loop()

    async with _suno_semaphore:
        try:
            from suno_client import SunoClient, SunoError

            def _generate():
                client = SunoClient()
                try:
                    song_urls = client.generate(lyrics=lyrics, style=style, title=title)
                    song_id = song_urls[0].rstrip("/").split("/")[-1]
                    db.save_suno_song(user_id, title, song_id, style, lyrics)

                    path = client.download(song_urls[0])
                    drive_url = ""
                    try:
                        from drive_uploader import DriveUploader
                        uploader = DriveUploader()
                        drive_url = uploader.upload(str(path))
                    except Exception:
                        pass
                    db.update_suno_status(
                        song_id, "complete",
                        local_path=str(path),
                        drive_url=drive_url,
                    )
                    return song_id, path, drive_url, len(song_urls)
                finally:
                    client.close()

            song_id, path, drive_url, num_songs = await loop.run_in_executor(None, _generate)

            result_text = f"✅ 곡 생성 완료!\n🎵 {title} ({num_songs}곡)"
            if drive_url:
                result_text += f"\n☁️ {drive_url}"

            await msg.edit_text(result_text)

            with open(path, "rb") as audio_file:
                await update.message.reply_audio(
                    audio=audio_file,
                    title=title,
                    performer="Suno AI",
                )

        except Exception as e:
            logger.error("Suno 파이프라인 오류: %s", e, exc_info=True)
            await msg.edit_text(f"❌ Suno 생성 실패: {e}")


async def cmd_suno_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """생성한 Suno 곡 목록."""
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id
    songs = db.get_suno_songs(user_id)

    if not songs:
        await update.message.reply_text("아직 생성한 곡이 없습니다. /suno로 시작해보세요!")
        return

    lines = ["🎵 내 Suno 곡 목록\n"]
    for s in songs:
        status_icon = "✅" if s["status"] == "complete" else "⏳" if s["status"] == "pending" else "❌"
        line = f"{status_icon} {s['title']}"
        if s.get("duration_sec"):
            line += f" ({s['duration_sec']:.0f}초)"
        if s.get("drive_url"):
            line += f"\n   ☁️ {s['drive_url']}"
        lines.append(line)

    await update.message.reply_text("\n".join(lines))


# ---------------------------------------------------------------------------
# Stage 3: /publish — Suno 곡 YouTube 게시
# ---------------------------------------------------------------------------
async def cmd_publish(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Suno 곡 YouTube 게시 파이프라인.

    /publish         → 최근 Suno 곡 목록 표시
    /publish {song_id} → 해당 곡 YouTube 업로드
    """
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id
    arg = " ".join(ctx.args) if ctx.args else ""

    if not arg:
        # 곡 목록 표시
        songs = db.get_suno_songs(user_id, limit=10)
        if not songs:
            await update.message.reply_text(
                "📋 Suno 곡이 없습니다.\n\n"
                "suno_download.py로 곡을 먼저 다운로드하세요:\n"
                "  python3 suno_download.py --all"
            )
            return

        lines = ["🎬 YouTube 게시 가능한 Suno 곡\n"]
        for s in songs:
            title = s.get("title", "무제")
            song_id = s.get("song_id", "?")
            status = s.get("status", "?")
            drive_url = s.get("drive_url", "")
            duration = s.get("duration_sec") or 0
            local_path = s.get("local_path", "")

            # 상태 아이콘
            if drive_url and "youtube" in drive_url:
                icon = "✅"  # 이미 업로드됨
            elif local_path and Path(local_path).is_file():
                icon = "📁"  # 로컬 파일 있음
            else:
                icon = "⏳"  # 다운로드 필요

            duration_str = f"{duration:.0f}초" if duration else ""
            lines.append(f"  {icon} {title} {duration_str}")
            lines.append(f"      /publish {song_id[:8]}")
            if drive_url and "youtube" in drive_url:
                lines.append(f"      {drive_url}")

        lines.append("")
        lines.append("📁 = 게시 가능 | ✅ = 이미 업로드됨 | ⏳ = 파일 없음")
        lines.append("\n사용법: /publish {song_id}")
        await update.message.reply_text("\n".join(lines))
        return

    # song_id로 게시 실행
    song_id = arg.strip()

    # song_id 부분 매칭 지원 (앞 8자만 입력해도 OK)
    song = db.get_suno_song(song_id)
    if not song:
        # 부분 매칭 시도
        songs = db.get_suno_songs(user_id, limit=50)
        matched = [s for s in songs if s.get("song_id", "").startswith(song_id)]
        if len(matched) == 1:
            song = db.get_suno_song(matched[0]["song_id"])
        elif len(matched) > 1:
            await update.message.reply_text(
                f"⚠️ '{song_id}'에 매칭되는 곡이 {len(matched)}개입니다. 더 정확한 ID를 입력하세요."
            )
            return
        else:
            await update.message.reply_text(
                f"⚠️ '{song_id}'에 해당하는 곡을 찾을 수 없습니다.\n"
                "/publish 로 곡 목록을 확인하세요."
            )
            return

    # 로컬 파일 확인
    local_path = song.get("local_path", "")
    if not local_path or not Path(local_path).is_file():
        await update.message.reply_text(
            f"⚠️ 로컬 오디오 파일이 없습니다: {local_path or '(경로 없음)'}\n\n"
            "suno_download.py로 먼저 다운로드하세요:\n"
            f"  python3 suno_download.py --song-id {song.get('song_id', '')}"
        )
        return

    audio_path = Path(local_path)
    title = song.get("title", audio_path.stem)

    # per-user lock: 중복 실행 방지
    lock = _user_locks[user_id]
    if lock.locked():
        await update.message.reply_text("⏳ 이전 요청을 처리 중이에요. 잠시만 기다려주세요!")
        return

    async with lock:
        # 진행 상황 메시지
        status_msg = await update.message.reply_text(
            f"🎬 YouTube 게시 시작: {title}\n\n"
            f"📁 오디오: {audio_path.name}\n"
            "⏳ 준비 중..."
        )

        try:
            # 1단계: 영상 생성 준비
            await status_msg.edit_text(
                f"🎬 YouTube 게시: {title}\n\n"
                "[1/3] 🖼️ 썸네일 준비 중..."
            )

            # publish.py의 publish() 함수를 subprocess로 실행
            # (ffmpeg 등 무거운 작업이므로 별도 프로세스)
            await status_msg.edit_text(
                f"🎬 YouTube 게시: {title}\n\n"
                "[2/3] 🎥 영상 생성 중... (1-2분 소요)"
            )

            # publish.py 실행
            publish_result = await _run_publish_pipeline(
                audio_path=audio_path,
                title=title,
                song=song,
            )

            if not publish_result["success"]:
                failed_steps = [
                    step for step, ok in publish_result.get("steps", {}).items() if not ok
                ]
                await status_msg.edit_text(
                    f"⚠️ 게시 실패: {title}\n\n"
                    f"실패 단계: {', '.join(failed_steps)}\n"
                    "로그를 확인하세요."
                )
                return

            # 성공 결과
            youtube_url = publish_result.get("youtube_url", "")
            video_path = publish_result.get("video_path", "")

            result_text = f"✅ YouTube 게시 완료: {title}\n\n"
            if youtube_url:
                result_text += f"🔗 {youtube_url}\n"
            if publish_result.get("duration"):
                d = publish_result["duration"]
                result_text += f"⏱️ {d:.0f}초 ({d/60:.1f}분)\n"

            await status_msg.edit_text(result_text)

            # DB 업데이트
            if youtube_url:
                db.update_suno_status(
                    song.get("song_id", ""),
                    "published",
                    drive_url=youtube_url,
                )

        except Exception as e:
            logger.error("YouTube 게시 오류: %s", e)
            await status_msg.edit_text(
                f"⚠️ 게시 오류: {title}\n\n{str(e)[:200]}"
            )


async def _run_publish_pipeline(
    audio_path: Path,
    title: str,
    song: dict,
) -> dict:
    """publish.py 파이프라인을 subprocess로 실행. 결과 파싱."""
    project_root = Path(__file__).parent

    cmd = [
        sys.executable,
        str(project_root / "scripts" / "publish.py"),
        "--audio", str(audio_path),
        "--title", title,
    ]

    # Suno 커버 이미지 탐색
    cover_path = audio_path.with_name(audio_path.stem + "_cover.jpeg")
    if cover_path.is_file():
        cmd += ["--cover", str(cover_path)]

    # Suno 스타일 태그
    style = song.get("style", "")
    if style:
        cmd += ["--tags", style]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(project_root),
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=600)
        output = stdout.decode("utf-8")
        err_output = stderr.decode("utf-8")

        if proc.returncode != 0:
            logger.error("publish.py 실패: %s", err_output[:500])

        # 결과 파싱: YouTube URL 추출
        result = {
            "success": proc.returncode == 0,
            "video_path": None,
            "youtube_url": None,
            "youtube_id": None,
            "duration": 0.0,
            "steps": {
                "thumbnail": "썸네일" not in err_output or proc.returncode == 0,
                "video": "영상 생성 실패" not in output,
                "upload": "업로드 실패" not in output,
            },
        }

        # YouTube URL 추출
        import re as _re
        url_match = _re.search(r"https://(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)", output)
        if url_match:
            result["youtube_url"] = url_match.group(0)
            result["youtube_id"] = url_match.group(1)

        # 오디오 길이 추출
        dur_match = _re.search(r"오디오 길이:\s*(\d+)초", output)
        if dur_match:
            result["duration"] = float(dur_match.group(1))

        # 영상 경로 추출
        video_match = _re.search(r"영상:\s*(\S+\.mp4)", output)
        if video_match:
            result["video_path"] = video_match.group(1)

        return result

    except asyncio.TimeoutError:
        logger.error("publish.py 타임아웃 (10분)")
        return {
            "success": False,
            "steps": {"thumbnail": False, "video": False, "upload": False},
        }
    except Exception as e:
        logger.error("publish.py 실행 오류: %s", e)
        return {
            "success": False,
            "steps": {"thumbnail": False, "video": False, "upload": False},
        }


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------
def main() -> None:
    logger.info("Music Lab 봇 시작 (Claude CLI 로컬 모드)")

    # DB 초기화
    db.init_db()
    logger.info("SQLite DB 초기화 완료: %s", db.DB_PATH)

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("new", cmd_new))
    app.add_handler(CommandHandler("lyrics", cmd_lyrics))
    app.add_handler(CommandHandler("chord", cmd_chord))
    app.add_handler(CommandHandler("midi", cmd_midi))
    app.add_handler(CommandHandler("theory", cmd_theory))
    app.add_handler(CommandHandler("idea", cmd_idea))
    app.add_handler(CommandHandler("library", cmd_library))
    app.add_handler(CommandHandler("export", cmd_export))
    app.add_handler(CommandHandler("remix", cmd_remix))
    app.add_handler(CommandHandler("save", cmd_save))
    app.add_handler(CommandHandler("daily", cmd_daily))
    app.add_handler(CommandHandler("quiz", cmd_quiz))
    app.add_handler(CommandHandler("suno", cmd_suno))
    app.add_handler(CommandHandler("suno_list", cmd_suno_list))
    app.add_handler(CommandHandler("publish", cmd_publish))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("폴링 시작... (대화 기억 활성, Claude CLI OAuth 사용)")
    app.run_polling()


if __name__ == "__main__":
    main()
