"""
autopilot/nodes/postprocess.py — 후처리 노드 (Phase 2: stub).

실제 구현은 Phase 4에서 -14 LUFS 라우드니스 정규화 + 포맷 변환.
"""
from __future__ import annotations


def postprocess(audio_path: str) -> str:
    """오디오 파일을 -14 LUFS 기준으로 정규화하고 결과 경로를 반환한다.

    audio_path: 원본 오디오 파일 경로.

    returns: 후처리된 오디오 파일 경로.

    raises NotImplementedError: Phase 4 구현 전.
    """
    raise NotImplementedError("Phase 4에서 -14 LUFS 라우드니스 정규화 구현 예정")
