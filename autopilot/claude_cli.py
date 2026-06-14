"""
autopilot/claude_cli.py — Claude CLI subprocess 래퍼.

원칙:
- CLI 버전 고정 (DIFFICULTY D-003: npx 최신 자동설치 silent outage 방지).
- OAuth 만료 감지: stderr auth 패턴 → ClaudeAuthError raise.
- subprocess.run 주입으로 테스트 시 실제 npx 호출 방지.
"""
from __future__ import annotations

import logging
import re
import subprocess
import time
from dataclasses import dataclass
from typing import Any, Callable

logger = logging.getLogger("autopilot.claude_cli")

# ---------------------------------------------------------------------------
# 상수
# ---------------------------------------------------------------------------

CLAUDE_CLI_VERSION: str = "2.1.91"
"""npx로 설치할 Claude CLI 정확한 버전. 변경 시 DIFFICULTY D-003 참조."""

_AUTH_ERROR_PATTERN = re.compile(
    r"(auth|oauth|unauthorized|login|token expired)", re.IGNORECASE
)
"""stderr에서 인증 관련 에러를 감지하는 정규식."""


# ---------------------------------------------------------------------------
# 결과 타입
# ---------------------------------------------------------------------------


@dataclass
class CliResult:
    """Claude CLI 호출 결과."""
    stdout: str
    stderr: str
    exit_code: int
    elapsed: float


# ---------------------------------------------------------------------------
# 예외
# ---------------------------------------------------------------------------


class ClaudeAuthError(Exception):
    """Claude CLI OAuth 만료 또는 인증 실패."""


# ---------------------------------------------------------------------------
# call_claude
# ---------------------------------------------------------------------------


def call_claude(
    prompt: str,
    system_prompt: str | None = None,
    timeout: int = 120,
    runner: Callable[..., Any] = subprocess.run,
) -> CliResult:
    """Claude CLI를 subprocess로 호출해 CliResult를 반환한다.

    prompt:         사용자 프롬프트.
    system_prompt:  시스템 프롬프트 (선택). None이면 포함 안 함.
    timeout:        subprocess 타임아웃(초). 기본 120.
    runner:         subprocess.run 호환 callable. 테스트에서 mock으로 주입.

    raises ClaudeAuthError: stderr에 인증 에러 패턴이 있고 exit_code != 0일 때.
    """
    cmd = [
        "npx",
        f"@anthropic-ai/claude-code@{CLAUDE_CLI_VERSION}",
        "-p", prompt,
        "--tools", "",
        "--no-session-persistence",
    ]
    if system_prompt is not None:
        cmd += ["--system-prompt", system_prompt]

    start_ts = time.time()
    proc = runner(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    elapsed = time.time() - start_ts

    stdout: str = proc.stdout or ""
    stderr: str = proc.stderr or ""
    exit_code: int = proc.returncode

    logger.debug(
        "Claude CLI 호출 완료: exit_code=%d, elapsed=%.2fs, stderr=%r",
        exit_code, elapsed, stderr[:200],
    )

    # OAuth 만료 감지
    if exit_code != 0 and _AUTH_ERROR_PATTERN.search(stderr):
        raise ClaudeAuthError(
            f"Claude CLI 인증 오류 — OAuth 토큰이 만료됐거나 로그인이 필요합니다. "
            f"exit_code={exit_code}, stderr={stderr!r}"
        )

    return CliResult(stdout=stdout, stderr=stderr, exit_code=exit_code, elapsed=elapsed)
