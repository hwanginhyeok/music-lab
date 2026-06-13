"""
autopilot/nodes/upload.py — YouTube unlisted 업로드 노드 (Phase 2: stub).

실제 구현은 Phase 4에서 YouTube Data API v3 unlisted 업로드.
publish-gate 원칙: unlisted 업로드 자동 OK, public 전환은 사용자 승인 필요.
"""
from __future__ import annotations


def upload(video_path: str, title: str = "", description: str = "") -> str:
    """영상 파일을 YouTube unlisted로 업로드하고 video URL을 반환한다.

    video_path:  업로드할 MP4 파일 경로.
    title:       YouTube 영상 제목.
    description: YouTube 영상 설명.

    returns: YouTube video URL (https://youtu.be/...).

    raises NotImplementedError: Phase 4 구현 전.
    """
    raise NotImplementedError("Phase 4에서 YouTube Data API v3 unlisted 업로드 구현 예정")
