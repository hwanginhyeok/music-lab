"""
autopilot/nodes/generate.py — 음악 생성 노드 (Phase 3).

실제 SunoClient 래핑 + 멱등성(D-004) + v1/v2 페어 수집(D-005/D-007).

SunoClient 인터페이스:
    __init__(display=None, keep_browser=True)
    generate(lyrics, style, title="", model="v5.5", instrumental=False) -> list[str]
        → 생성된 곡 URL 리스트 반환 (보통 2개, "https://suno.com/song/<id>" 형태)
    download(song_url, output_path=None) -> Path
        → 오디오 파일 다운로드 후 로컬 Path 반환
    captcha 처리: SunoClient 내부에서 텔레그램 알림 + noVNC 수동풀이 + 자동재개.
        generate 노드는 캡차를 재구현하지 않음.

멱등성: idempotency_key(run_id, "생성", prompt_slug) → run_once 로 중복 생성 차단.
v1/v2 페어: generate() 가 반환하는 URL 전부를 download()로 수집 (Suno는 기본 2곡 동시 생성).
"""
from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path
from typing import Any

from autopilot import trace as _trace
from autopilot.engine import Ctx, step
from autopilot.idempotency import idempotency_key, run_once

logger = logging.getLogger("autopilot.nodes.generate")


# ---------------------------------------------------------------------------
# 노드
# ---------------------------------------------------------------------------

@step("생성", max_attempts=2)
def generate_node(ctx: Ctx, prompt_path: str, n: int = 2) -> dict:
    """Suno AI로 음악을 생성하고 오디오 후보 목록을 반환한다.

    prompt_path: suno_prompt_node 가 저장한 프롬프트 파일 경로.
    n:           요청할 후보 수 (현재 Suno가 항상 2곡 동시 생성).

    returns: {"candidates": [{"path": str, "sha256": str}, ...]}

    캡차 처리: SunoClient 내부에서 텔레그램 알림 → noVNC 수동풀이 → 자동재개.
               이 노드는 캡차를 재구현하지 않는다. SunoError("캡차 해결 실패")가
               발생하면 @step 재시도 로직이 처리한다.
    """
    # 1. 프롬프트 파일 파싱
    prompt_text = Path(prompt_path).read_text(encoding="utf-8")
    style, lyrics = _parse_suno_prompt(prompt_text)

    # 2. 멱등성 키 — 프롬프트 내용 hash 기반
    prompt_slug = hashlib.sha256(prompt_text.encode()).hexdigest()[:16]
    idem_key = idempotency_key(ctx.run_id, "생성", prompt_slug)

    # 3. 실제 생성 (run_once가 중복 차단)
    def _do_generate() -> dict:
        return _generate_and_download(ctx, style, lyrics, prompt_slug)

    result = run_once(ctx.store, idem_key, _do_generate)

    # 4. trace 기록
    _trace.emit({
        "event": "generate_done",
        "run_id": ctx.run_id,
        "candidate_count": len(result.get("candidates", [])),
        "idempotency_key": idem_key,
    })

    return result


# ---------------------------------------------------------------------------
# 내부: 생성 + 다운로드 로직 (run_once 내부에서 1회만 실행)
# ---------------------------------------------------------------------------

def _generate_and_download(ctx: Ctx, style: str, lyrics: str, prompt_slug: str) -> dict:
    """SunoClient.generate() 호출 → URL 수집 → 다운로드 → artifact 등록."""
    from suno_client import SunoClient  # 지연 import (테스트 시 mock 주입)

    run_dir = _run_artifact_dir(ctx)
    run_dir.mkdir(parents=True, exist_ok=True)

    client = SunoClient()
    # title은 prompt_slug 앞 8자로 단순 식별용
    title = f"autopilot-{prompt_slug[:8]}"

    # 생성 — Suno는 기본적으로 2곡 동시 생성, URL 리스트 반환
    urls = client.generate(lyrics=lyrics, style=style, title=title)

    # v1/v2 페어 수집: 반환된 URL 전부 다운로드 (D-005/D-007 pair-harvest)
    candidates = []
    for i, url in enumerate(urls):
        audio_path = run_dir / f"candidate_{i:02d}.mp3"
        try:
            downloaded = client.download(url, output_path=str(audio_path))
            raw = Path(downloaded).read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            ctx.store.add_artifact(
                run_id=ctx.run_id,
                step_name="생성",
                kind="audio_candidate",
                path=str(downloaded),
                sha256=digest,
                meta={"url": url, "index": i},
            )
            candidates.append({"path": str(downloaded), "sha256": digest})
        except Exception as e:
            logger.warning("후보 %d 다운로드 실패 (url=%s): %s", i, url, e)

    if not candidates:
        from suno_client import SunoError
        raise SunoError("생성된 곡 다운로드 실패 — 후보 없음")

    return {"candidates": candidates}


# ---------------------------------------------------------------------------
# 헬퍼
# ---------------------------------------------------------------------------

def _parse_suno_prompt(prompt_text: str) -> tuple[str, str]:
    """Suno 프롬프트 텍스트에서 Style of Music 태그와 가사를 분리한다.

    형식:
        ## Style of Music
        ```
        (style tags)
        ```
        ## Lyrics (Suno format)
        ```
        (lyrics)
        ```

    파싱 실패 시 전체 텍스트를 lyrics로, style=""으로 반환.
    """
    import re

    style = ""
    lyrics = prompt_text  # fallback

    # Style of Music 블록 추출
    style_match = re.search(
        r"## Style of Music\s*```[^\n]*\n(.*?)```",
        prompt_text,
        re.DOTALL,
    )
    if style_match:
        style = style_match.group(1).strip()

    # Lyrics 블록 추출
    lyrics_match = re.search(
        r"## Lyrics.*?\s*```[^\n]*\n(.*?)```",
        prompt_text,
        re.DOTALL,
    )
    if lyrics_match:
        lyrics = lyrics_match.group(1).strip()

    return style, lyrics


def _run_artifact_dir(ctx: Ctx) -> Path:
    """run_id 기반 아티팩트 디렉토리 경로를 반환한다."""
    base = os.environ.get("AUTOPILOT_DATA_DIR", "data/autopilot")
    return Path(base) / ctx.run_id
