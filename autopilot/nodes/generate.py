"""
autopilot/nodes/generate.py — 음악 생성 노드 (Phase 2: stub).

실제 구현은 Phase 1 PoC (Suno 서드파티 API 연동) 완료 후 진행.
DIFFICULTY D-001: Suno hCaptcha로 자체 무인생성 불가 → API 키 대기 중.
"""
from __future__ import annotations


def generate(prompt: str, n: int = 2) -> list[str]:
    """Suno API를 통해 음악 후보를 생성하고 로컬 경로 목록을 반환한다.

    prompt: Suno 스타일 태그 + 가사 프롬프트.
    n:      생성할 후보 수 (기본 2).

    returns: 생성된 오디오 파일 경로 목록.

    raises NotImplementedError: Phase 1 PoC에서 서드파티 API 연동 전.
    """
    raise NotImplementedError("Phase 1 PoC에서 서드파티 API 연동")
