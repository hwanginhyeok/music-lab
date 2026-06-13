"""
autopilot/nodes/upload.py — YouTube unlisted 업로드 노드 (Phase 4).

Publish-Gate 규칙 (publish-gate.md):
- unlisted 포함 모든 YouTube 게시는 사용자 명시적 승인("올려") 필수.
- 승인 없으면 PublishGateBlocked 발생 (API 호출 전에 차단).
- 멱등성: 같은 (run_id, video_sha) 조합은 1회만 업로드 (D-004 dup-upload 방지).

youtube 파라미터:
- 기본 None → 실제 환경에서 scripts/youtube_upload.get_credentials()로 빌드.
- 테스트 시 mock 객체를 주입해 실제 API 호출 없이 검증 가능.
"""
from __future__ import annotations

import hashlib
import logging
import time
from pathlib import Path
from typing import Any

from autopilot import trace as _trace
from autopilot.engine import Ctx, step
from autopilot.gate import PublishGateBlocked, publish_gate_check
from autopilot.idempotency import idempotency_key, run_once

logger = logging.getLogger("autopilot.nodes.upload")

# YouTube 카테고리: 10 = Music
_YT_CATEGORY_MUSIC: str = "10"


# ---------------------------------------------------------------------------
# 노드
# ---------------------------------------------------------------------------

@step("업로드")
def upload_node(
    ctx: Ctx,
    video_path: str,
    title: str,
    description: str = "",
    youtube: Any = None,
) -> dict:
    """영상을 YouTube unlisted로 업로드하고 결과를 반환한다.

    순서:
    1. Publish-Gate 체크 (미승인 시 PublishGateBlocked, API 호출 없음)
    2. 멱등성 체크 (같은 video_sha → 중복 업로드 차단)
    3. YouTube Data API v3 videos().insert() (privacyStatus='unlisted')

    video_path: 업로드할 MP4 파일 경로.
    title:      YouTube 영상 제목.
    description: YouTube 영상 설명.
    youtube:    YouTube 서비스 클라이언트. None이면 실제 OAuth 빌드.
                테스트 시 mock 주입.

    returns: {"video_id": str, "url": str, "privacy": "unlisted"}

    raises:
        PublishGateBlocked: 게시 승인이 없을 때.
        RuntimeError:       업로드 실패 또는 video_id 없을 때.
    """
    # ── 1. Publish-Gate ──────────────────────────────────────────────────────
    publish_gate_check(ctx)

    # ── 2. 파일 SHA-256 (멱등성 키 재료) ────────────────────────────────────
    vid_path = Path(video_path)
    if vid_path.exists():
        video_sha = hashlib.sha256(vid_path.read_bytes()).hexdigest()
    else:
        video_sha = hashlib.sha256(video_path.encode()).hexdigest()

    idem_key = idempotency_key(ctx.run_id, "업로드", video_sha)

    # ── 3. 업로드 (run_once로 중복 차단) ─────────────────────────────────────
    def _do_upload() -> dict:
        yt = youtube if youtube is not None else _build_youtube()
        return _insert_video(yt, video_path, title, description)

    result = run_once(ctx.store, idem_key, _do_upload)

    # ── 4. artifact 등록 ──────────────────────────────────────────────────────
    url = result["url"]
    ctx.store.add_artifact(
        run_id=ctx.run_id,
        step_name="업로드",
        kind="youtube_unlisted",
        path=url,
        sha256=video_sha,
        meta={"video_id": result["video_id"], "privacy": "unlisted"},
    )

    # ── 5. trace ──────────────────────────────────────────────────────────────
    _trace.emit({
        "event": "upload_done",
        "run_id": ctx.run_id,
        "video_id": result["video_id"],
        "url": url,
        "privacy": "unlisted",
        "ts": time.time(),
    })

    logger.info("업로드 완료: %s → %s", video_path, url)

    return {"video_id": result["video_id"], "url": url, "privacy": "unlisted"}


# ---------------------------------------------------------------------------
# 내부: 실제 YouTube API 호출
# ---------------------------------------------------------------------------

def _build_youtube() -> Any:
    """실제 YouTube 서비스 클라이언트를 빌드한다 (OAuth 토큰 사용)."""
    import sys
    from pathlib import Path as _Path
    # scripts/ 경로를 추가해 youtube_upload 임포트
    scripts_dir = str(_Path(__file__).parent.parent.parent / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)

    from youtube_upload import get_credentials  # type: ignore[import]
    from googleapiclient.discovery import build  # type: ignore[import]

    creds = get_credentials()
    if not creds:
        raise RuntimeError("YouTube OAuth 토큰 없음 — 재인증 필요")
    return build("youtube", "v3", credentials=creds)


def _insert_video(youtube: Any, video_path: str, title: str, description: str) -> dict:
    """youtube.videos().insert()를 실행하고 {video_id, url}을 반환한다."""
    from googleapiclient.http import MediaFileUpload  # type: ignore[import]

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "categoryId": _YT_CATEGORY_MUSIC,
            "defaultLanguage": "ko",
        },
        "status": {
            "privacyStatus": "unlisted",
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(
        video_path,
        mimetype="video/mp4",
        resumable=True,
        chunksize=10 * 1024 * 1024,
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None
    while response is None:
        _, response = request.next_chunk()

    video_id = response.get("id")
    if not video_id:
        raise RuntimeError(f"YouTube 업로드 응답에 video_id 없음: {response}")

    url = f"https://youtu.be/{video_id}"
    return {"video_id": video_id, "url": url}


# ---------------------------------------------------------------------------
# 하위 호환성 stub — Phase 2 시그니처 유지
# ---------------------------------------------------------------------------

def upload(video_path: str, title: str = "", description: str = "") -> str:
    """[DEPRECATED] Phase 2 stub. upload_node(ctx, video_path, title)로 교체됨."""
    raise NotImplementedError("Phase 4에서 upload_node(ctx, video_path, title, ...)로 교체됨")
