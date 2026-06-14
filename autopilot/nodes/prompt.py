"""
autopilot/nodes/prompt.py — Suno 프롬프트 빌드 노드 (Phase 2: stub).

실제 구현은 Phase 3에서 가사 + 스타일 태그 → Suno Style of Music 포맷 변환.
"""
from __future__ import annotations


def build_prompt(lyrics: str, style_hints: str = "") -> str:
    """가사와 스타일 힌트를 받아 Suno 입력 프롬프트를 생성한다.

    lyrics:       완성된 가사 텍스트.
    style_hints:  장르/분위기 힌트 (예: "indie jazz, emotional").

    returns: Suno Style of Music + 섹션 마커가 포함된 프롬프트 문자열.

    raises NotImplementedError: Phase 3 구현 전.
    """
    raise NotImplementedError("Phase 3에서 Suno 프롬프트 엔지니어링 구현 예정")
