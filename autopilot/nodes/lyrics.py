"""
autopilot/nodes/lyrics.py — 작사 노드 (Phase 3).

김이나 작사법 기반 한국어 가사 생성 노드.
Claude CLI 호출 → 가사 파일 저장 → artifact 등록 → trace 기록.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

from autopilot import trace as _trace
from autopilot.claude_cli import call_claude
from autopilot.engine import Ctx, step

# ---------------------------------------------------------------------------
# 시스템 프롬프트 (김이나 작사법 핵심 요약)
# ---------------------------------------------------------------------------

_LYRICIST_SYSTEM_PROMPT = """\
당신은 김이나 작사법을 내재화한 한국어 작사 전문가입니다.

핵심 원칙:
1. 캐릭터 먼저 — 화자의 나이대, 상황, 감정 표출 방식을 먼저 정립한다.
2. 발음 설계 — 발라드는 파열음(ㅂ,ㄷ,ㄱ) 최소화, 긴 음표에는 개모음 음절(아,어,오,우) 배치.
3. 간접 표현 — 감정을 직접 명명하지 않는다. "슬프다" 대신 "자꾸 그쪽 길로 돌아와".
4. 디테일 — 추상 감정 대신 구체 장면. "이별이 아팠다" → "택시 두 대가 반대로 꺾어진 골목".
5. 구조 — [Verse 1] / [Pre-Chorus] / [Chorus] / [Verse 2] / [Bridge] / [Outro] 순서로 작성.

금지:
- "봄이 왔어요" 같은 진부한 계절 묘사
- "정말 많이 보고 싶어" 같은 감정 직접 명명
- 억지 라임 (운율보다 내용 우선)
- 과도한 영어 (훅 1~2줄은 허용)
"""


# ---------------------------------------------------------------------------
# 노드
# ---------------------------------------------------------------------------

@step("작사")
def lyrics_node(ctx: Ctx, concept: dict) -> dict:
    """앨범 컨셉을 바탕으로 가사를 생성하고 파일로 저장한다.

    concept: 앨범/곡 컨셉 정보 (title, mood, theme 등 포함 dict).

    returns: {"lyrics_path": str, "sha256": str}
    """
    # 1. 컨셉 → 프롬프트 구성
    title = concept.get("title", "무제")
    mood = concept.get("mood", "")
    theme = concept.get("theme", "")
    style = concept.get("style", "")

    prompt = (
        f"다음 앨범 컨셉으로 완성도 높은 한국어 가사를 작성해 주세요.\n\n"
        f"곡 제목: {title}\n"
        f"분위기: {mood}\n"
        f"주제: {theme}\n"
        f"스타일: {style}\n\n"
        f"[Verse 1] / [Pre-Chorus] / [Chorus] / [Verse 2] / [Bridge] / [Outro] 구조로 작성하세요.\n"
        f"각 섹션 앞에 분위기 서브태그(예: [Soft, Intimate])를 추가하세요.\n"
        f"가사만 출력하고 설명은 생략하세요."
    )

    # 2. Claude CLI 호출
    cli_result = call_claude(prompt=prompt, system_prompt=_LYRICIST_SYSTEM_PROMPT)
    lyrics_text = cli_result.stdout.strip()

    # 3. 파일 저장
    run_dir = _run_artifact_dir(ctx)
    run_dir.mkdir(parents=True, exist_ok=True)
    lyrics_path = run_dir / "lyrics.txt"
    lyrics_path.write_text(lyrics_text, encoding="utf-8")

    # 4. sha256 계산
    digest = hashlib.sha256(lyrics_text.encode()).hexdigest()

    # 5. artifact 등록
    ctx.store.add_artifact(
        run_id=ctx.run_id,
        step_name="작사",
        kind="lyrics",
        path=str(lyrics_path),
        sha256=digest,
    )

    # 6. trace 기록
    _trace.emit({
        "event": "lyrics_done",
        "run_id": ctx.run_id,
        "lyrics_path": str(lyrics_path),
        "sha256": digest,
        "exit_code": cli_result.exit_code,
        "elapsed": cli_result.elapsed,
    })

    return {"lyrics_path": str(lyrics_path), "sha256": digest}


# ---------------------------------------------------------------------------
# 헬퍼
# ---------------------------------------------------------------------------

def _run_artifact_dir(ctx: Ctx) -> Path:
    """run_id 기반 아티팩트 디렉토리 경로를 반환한다."""
    base = os.environ.get("AUTOPILOT_DATA_DIR", "data/autopilot")
    return Path(base) / ctx.run_id


# 하위 호환성 stub (Phase 2 tests) — 사용하지 말 것, 제거 예정
def write_lyrics(concept: str) -> str:
    """[DEPRECATED] Phase 2 stub. 사용하지 마세요."""
    raise NotImplementedError("Phase 3에서 lyrics_node(ctx, concept)로 교체됨")
