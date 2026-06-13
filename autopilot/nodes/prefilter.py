"""
autopilot/nodes/prefilter.py — 자동 프리필터 노드 (Phase 2: stub).

실제 구현은 Phase 3에서 후보 오디오 자동 품질 선별 (LUFS, 길이, 음정 검사).
DIFFICULTY D-005/D-007: Suno 길이 제어 불가 → 노드 구현 시 반영.
"""
from __future__ import annotations


def prefilter(candidates: list[str]) -> list[str]:
    """생성된 오디오 후보 목록을 자동 선별하고 통과한 경로 목록을 반환한다.

    candidates: 오디오 파일 경로 목록.

    returns: 품질 기준을 통과한 경로 목록 (부분집합).

    raises NotImplementedError: Phase 3 구현 전.
    """
    raise NotImplementedError("Phase 3에서 LUFS/길이 기반 자동 선별 구현 예정")
