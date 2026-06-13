"""
autopilot/nodes/suno_prompt.py — Suno 프롬프트 생성 노드 (Phase 3).

가사 파일 + 컨셉 → Suno Style of Music 태그 + 섹션 마커 포함 프롬프트 생성.
전체 프롬프트 텍스트는 trace에 기록 (사이드카로 자동 오프로드).
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

from autopilot import trace as _trace
from autopilot.claude_cli import call_claude
from autopilot.engine import Ctx, step

# ---------------------------------------------------------------------------
# 시스템 프롬프트 (Suno Prompt Engineer 핵심 요약)
# ---------------------------------------------------------------------------

_SUNO_PE_SYSTEM_PROMPT = """\
당신은 Suno AI 프롬프트 엔지니어링 전문가입니다.
가사와 컨셉을 받아 Suno에서 최적의 결과를 내는 프롬프트를 생성합니다.

출력 형식 (반드시 준수):
## Style of Music
```
(스타일 태그 — 200자 이내, 영어 소문자 콤마 구분)
```

## Lyrics (Suno format)
```
(섹션 마커 + 가사 전문)
```

스타일 태그 우선순위: 장르 > 보컬 > 주요 악기 > 텍스처/분위기 > BPM.
섹션 마커: [Intro] [Verse 1] [Pre-Chorus] [Chorus] [Verse 2] [Bridge] [Outro] 등.
분위기 서브태그: [Soft, Intimate] [Build] [Emotional Vocal] 등 감정 변곡점에 추가.

금지 태그: 'professional studio', 'high quality' (의미없음).
악기는 3~4개 이하로 제한 (과다하면 혼탁).

재즈 채널 유의사항: 모든 장르 제안은 재즈 서브장르 안에서.
lo-fi 금지. indie band + emotional dreamy / contemporary pop 검증됨.
"""


# ---------------------------------------------------------------------------
# 노드
# ---------------------------------------------------------------------------

@step("Suno프롬프트")
def suno_prompt_node(ctx: Ctx, concept: dict, lyrics_path: str) -> dict:
    """가사 + 컨셉 → Suno 프롬프트 파일 생성.

    concept:      앨범/곡 컨셉 dict (title, mood, theme, style 등).
    lyrics_path:  lyrics_node 가 반환한 가사 파일 경로.

    returns: {"prompt_path": str, "sha256": str}
    """
    # 1. 가사 파일 읽기
    lyrics_text = Path(lyrics_path).read_text(encoding="utf-8")

    # 2. 프롬프트 구성
    title = concept.get("title", "무제")
    mood = concept.get("mood", "")
    theme = concept.get("theme", "")
    style_hint = concept.get("style", "")

    prompt = (
        f"다음 가사와 컨셉으로 Suno AI 최적 프롬프트를 생성해 주세요.\n\n"
        f"곡 제목: {title}\n"
        f"분위기: {mood}\n"
        f"주제: {theme}\n"
        f"스타일 힌트: {style_hint}\n\n"
        f"## 가사\n{lyrics_text}\n\n"
        f"위 지침에 따라 Style of Music 태그와 섹션 마커가 포함된 Lyrics를 출력하세요."
    )

    # 3. Claude CLI 호출
    cli_result = call_claude(prompt=prompt, system_prompt=_SUNO_PE_SYSTEM_PROMPT)
    prompt_text = cli_result.stdout.strip()

    # 4. 파일 저장
    run_dir = _run_artifact_dir(ctx)
    run_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = run_dir / "suno_prompt.txt"
    prompt_path.write_text(prompt_text, encoding="utf-8")

    # 5. sha256 계산
    digest = hashlib.sha256(prompt_text.encode()).hexdigest()

    # 6. artifact 등록
    ctx.store.add_artifact(
        run_id=ctx.run_id,
        step_name="Suno프롬프트",
        kind="suno_prompt",
        path=str(prompt_path),
        sha256=digest,
    )

    # 7. trace 기록 — 전체 프롬프트 텍스트 포함 (2048자 초과 시 자동 사이드카 오프로드)
    _trace.emit({
        "event": "suno_prompt",
        "run_id": ctx.run_id,
        "prompt": prompt_text,          # 대용량 시 trace.py가 자동으로 사이드카로 오프로드
        "prompt_path": str(prompt_path),
        "sha256": digest,
        "exit_code": cli_result.exit_code,
        "elapsed": cli_result.elapsed,
    })

    return {"prompt_path": str(prompt_path), "sha256": digest}


# ---------------------------------------------------------------------------
# 헬퍼
# ---------------------------------------------------------------------------

def _run_artifact_dir(ctx: Ctx) -> Path:
    """run_id 기반 아티팩트 디렉토리 경로를 반환한다."""
    base = os.environ.get("AUTOPILOT_DATA_DIR", "data/autopilot")
    return Path(base) / ctx.run_id
