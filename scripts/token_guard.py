#!/usr/bin/env python3
"""YouTube OAuth 토큰 만료 감지 + 경고 (PIPE-F10).

- check_health()    : 실시간 토큰 refresh 시도 + 상태 기록
- pre_upload_guard(): 업로드 직전 호출. 토큰 불량이면 TokenExpiredError 발생
- daily_check()     : cron 진입점. 7일 이상 미확인이면 경고 전송
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests as _requests
except ImportError:
    _requests = None  # type: ignore[assignment]

PROJECT_ROOT = Path(__file__).parent.parent
TOKEN_PATH = PROJECT_ROOT / "token.json"
STATE_PATH = PROJECT_ROOT / "data" / ".token_guard_state.json"

WARN_DAYS = 7  # 마지막 성공 검증 후 N일 이상이면 경고

# 재인증 안내 (WSL/서버 환경 포함)
REAUTH_STEPS = (
    "📋 재인증 방법 (WSL/서버 환경):\n"
    "1. music-lab 서버에서 실행:\n"
    "   cd ~/music-lab\n"
    "   python3 scripts/youtube_upload.py songs/14_geuriumi/ --skip-upload\n\n"
    "2. 출력된 URL을 Windows 브라우저에서 열어 Google 계정 인증\n"
    "   (WSL2: localhost URL은 Windows 브라우저에서 직접 접속 가능합니다)\n\n"
    "3. 인증 완료 후 터미널에 코드 붙여넣기 → token.json 자동 갱신\n\n"
    "4. 갱신 확인:\n"
    "   python3 scripts/token_guard.py --status"
)


class TokenExpiredError(Exception):
    """토큰 만료 또는 무효 시 발생. 업로드를 차단합니다."""


# ---------------------------------------------------------------------------
# 내부 유틸
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def _load_state() -> dict:
    if STATE_PATH.is_file():
        try:
            return json.loads(STATE_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {"last_ok_utc": None, "last_check_utc": None, "last_error": None, "last_error_class": None}


def _save_state(ok: bool, error: str | None = None, error_class: str | None = None) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    state = _load_state()
    now_s = _now().isoformat()
    state["last_check_utc"] = now_s
    if ok:
        state["last_ok_utc"] = now_s
        state["last_error"] = None
        state["last_error_class"] = None
    else:
        state["last_error"] = error
        state["last_error_class"] = error_class
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def _write_token_secure(path: Path, json_str: str) -> None:
    """토큰 파일을 600 권한으로 저장합니다."""
    path.write_text(json_str, encoding="utf-8")
    os.chmod(path, 0o600)


def _send_alert(text: str) -> bool:
    """텔레그램 알림을 전송합니다."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("ADMIN_CHAT_ID", "")
    if not bot_token or not chat_id:
        print(f"[token-guard] 텔레그램 설정 없음 (ADMIN_CHAT_ID 미설정). 경고 출력:\n{text}")
        return False
    if _requests is None:
        print(f"[token-guard] requests 미설치. 경고 출력:\n{text}")
        return False
    try:
        resp = _requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
        return resp.ok
    except Exception as e:
        print(f"[token-guard] 텔레그램 전송 실패: {e}")
        return False


def _build_alert(
    emoji: str,
    title: str,
    error: str,
    error_class: str,
    last_ok: datetime | None,
    include_reauth: bool = True,
) -> str:
    """error_class에 따라 차별화된 알림 메시지를 생성합니다."""
    last_ok_str = (
        f"{last_ok.strftime('%Y-%m-%d %H:%M')} UTC"
        if last_ok else "기록 없음"
    )
    lines = [
        f"{emoji} <b>{title}</b>",
        f"오류: {error}",
        f"마지막 정상: {last_ok_str}",
    ]

    if error_class == "network_error":
        lines += [
            "",
            "ℹ️ 네트워크 일시 오류입니다. 재인증이 필요하지 않습니다.",
            "잠시 후 자동으로 재시도됩니다.",
        ]
    elif error_class == "quota_exceeded":
        lines += [
            "",
            "ℹ️ YouTube API 할당량 초과입니다.",
            "24시간 후 자동으로 초기화됩니다.",
        ]
    elif include_reauth:
        lines += ["", REAUTH_STEPS]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 핵심 함수
# ---------------------------------------------------------------------------

def check_health() -> dict:
    """토큰 상태를 실시간으로 검사합니다. refresh를 실제로 시도하고 결과를 기록합니다.

    Returns:
        {
            "ok": bool,
            "days_since_ok": float | None,  # 이번 check 이전 마지막 OK 기준 경과일
            "error": str | None,
            "error_class": str | None,
                # "invalid_grant"  — refresh_token 만료/취소, 재인증 필요
                # "quota_exceeded" — API 할당량 초과, 대기 필요
                # "network_error"  — 일시 네트워크 실패, 재시도 필요
                # "refresh_error"  — 기타 RefreshError
                # "unknown"        — 예상 외 예외
        }
    """
    # 이번 check 전 마지막 OK 시간을 먼저 기록
    state_before = _load_state()
    prev_last_ok = _parse_dt(state_before.get("last_ok_utc"))
    days_since_ok: float | None = None
    if prev_last_ok:
        days_since_ok = (_now() - prev_last_ok).total_seconds() / 86400

    result: dict = {"ok": False, "days_since_ok": days_since_ok, "error": None, "error_class": None}

    if not TOKEN_PATH.is_file():
        result["error"] = "token.json 없음 — 최초 인증이 필요합니다"
        result["error_class"] = "invalid_grant"
        _save_state(False, result["error"], result["error_class"])
        return result

    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from google.auth.exceptions import RefreshError, TransportError
    except ImportError:
        result["error"] = "google-auth 패키지 미설치 (pip install google-auth-oauthlib)"
        result["error_class"] = "unknown"
        _save_state(False, result["error"], result["error_class"])
        return result

    try:
        raw = json.loads(TOKEN_PATH.read_text())
        scopes = raw.get("scopes", ["https://www.googleapis.com/auth/youtube.upload"])
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), scopes)
    except Exception as e:
        result["error"] = f"token.json 파싱 실패: {e}"
        result["error_class"] = "unknown"
        _save_state(False, result["error"], result["error_class"])
        return result

    if not creds.refresh_token:
        result["error"] = "refresh_token 없음 — 재인증이 필요합니다"
        result["error_class"] = "invalid_grant"
        _save_state(False, result["error"], result["error_class"])
        return result

    try:
        creds.refresh(Request())
        _write_token_secure(TOKEN_PATH, creds.to_json())
        _save_state(True)
        result["ok"] = True

    except TransportError as e:
        # 네트워크 계층 오류 — 재인증 불필요
        result["error"] = f"네트워크 연결 실패 (일시 오류): {e}"
        result["error_class"] = "network_error"
        _save_state(False, result["error"], result["error_class"])

    except RefreshError as e:
        err_str = str(e).lower()
        if "invalid_grant" in err_str:
            result["error"] = f"refresh_token 만료 또는 취소됨 (재인증 필요): {e}"
            result["error_class"] = "invalid_grant"
        elif "quota" in err_str or "rate_limit" in err_str or "ratelimit" in err_str:
            result["error"] = f"API 할당량 초과 (24시간 후 초기화): {e}"
            result["error_class"] = "quota_exceeded"
        else:
            result["error"] = f"토큰 갱신 실패 (원인 불명): {e}"
            result["error_class"] = "refresh_error"
        _save_state(False, result["error"], result["error_class"])

    except (ConnectionError, TimeoutError, OSError) as e:
        # Python 표준 네트워크 예외
        result["error"] = f"네트워크 연결 실패 (일시 오류): {e}"
        result["error_class"] = "network_error"
        _save_state(False, result["error"], result["error_class"])

    except Exception as e:
        result["error"] = f"예상치 못한 예외 발생: {e}"
        result["error_class"] = "unknown"
        _save_state(False, result["error"], result["error_class"])

    return result


def pre_upload_guard() -> None:
    """업로드 직전 토큰 상태를 검사합니다.

    토큰이 불량이면 텔레그램으로 알림을 전송하고 TokenExpiredError를 발생시킵니다.
    네트워크 일시 오류와 재인증 필요 오류를 구분하여 알림 내용을 차별화합니다.

    Raises:
        TokenExpiredError: 토큰이 무효이거나 검증에 실패한 경우
    """
    state_before = _load_state()
    prev_last_ok = _parse_dt(state_before.get("last_ok_utc"))

    result = check_health()

    if not result["ok"]:
        error_class = result.get("error_class", "unknown")
        needs_reauth = error_class in ("invalid_grant", "refresh_error", "unknown")

        msg = _build_alert(
            emoji="🚨",
            title="YouTube 업로드 차단됨",
            error=result["error"],
            error_class=error_class,
            last_ok=prev_last_ok,
            include_reauth=needs_reauth,
        )
        _send_alert(msg)
        raise TokenExpiredError(f"YouTube 토큰 무효: {result['error']}")

    # 성공했지만 오랫동안 미검증 상태였으면 경고 (업로드는 허용)
    days = result.get("days_since_ok") or 0
    if days >= WARN_DAYS:
        msg = (
            f"⚠️ YouTube 토큰 경고\n"
            f"마지막 검증: {prev_last_ok.strftime('%Y-%m-%d %H:%M') + ' UTC' if prev_last_ok else '기록 없음'} "
            f"({days:.0f}일 전)\n"
            f"오늘 갱신에는 성공했습니다. cron 점검을 권장합니다.\n\n"
            + REAUTH_STEPS
        )
        _send_alert(msg)


def daily_check() -> int:
    """매일 cron에서 호출합니다. 토큰 상태 점검 + 이상 시 텔레그램 경고.

    Returns:
        0 = 정상, 1 = 경고/오류
    """
    state_before = _load_state()
    prev_last_ok = _parse_dt(state_before.get("last_ok_utc"))

    now_str = _now().strftime("%Y-%m-%d %H:%M UTC")
    print(f"[token-guard] 토큰 검사 시작 ({now_str})")

    result = check_health()

    if not result["ok"]:
        error_class = result.get("error_class", "unknown")
        needs_reauth = error_class in ("invalid_grant", "refresh_error", "unknown")

        if error_class == "network_error":
            emoji, title = "⚠️", "YouTube 토큰 검사 실패 (네트워크 오류)"
        else:
            emoji, title = "🚨", "YouTube OAuth 토큰 이상 감지"

        msg = _build_alert(
            emoji=emoji,
            title=title,
            error=result["error"],
            error_class=error_class,
            last_ok=prev_last_ok,
            include_reauth=needs_reauth,
        )
        _send_alert(msg)
        print(f"[token-guard] ❌ 토큰 이상 [{error_class}]: {result['error']}")
        return 1

    # 이번 check 성공 — 이전 last_ok 기준으로 경과일 계산 (cron 중단 감지)
    if prev_last_ok:
        days_gap = (_now() - prev_last_ok).total_seconds() / 86400
        if days_gap >= WARN_DAYS:
            msg = (
                f"⚠️ YouTube 토큰 경고\n"
                f"마지막 확인: {prev_last_ok.strftime('%Y-%m-%d %H:%M')} UTC ({days_gap:.0f}일 전)\n"
                f"오늘 갱신에는 성공했지만, {days_gap:.0f}일간 미검증 상태였습니다.\n"
                f"cron이 중단되었을 수 있습니다. 점검을 권장합니다.\n\n"
                + REAUTH_STEPS
            )
            _send_alert(msg)
            print(f"[token-guard] ⚠️ {days_gap:.0f}일 만에 검증 성공 — cron 확인 권장")

    print("[token-guard] ✅ 토큰 정상")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def print_status() -> None:
    """현재 토큰 상태를 출력합니다 (--status 옵션)."""
    state = _load_state()
    last_ok = _parse_dt(state.get("last_ok_utc"))
    last_check = _parse_dt(state.get("last_check_utc"))

    print("=" * 52)
    print("  YouTube 토큰 상태")
    print("=" * 52)

    if TOKEN_PATH.is_file():
        try:
            raw = json.loads(TOKEN_PATH.read_text())
            has_refresh = bool(raw.get("refresh_token"))
            expiry_str = raw.get("expiry", "없음")
            expiry = _parse_dt(expiry_str)
            file_perm = oct(TOKEN_PATH.stat().st_mode)[-4:]
            if expiry:
                diff = (expiry - _now()).total_seconds()
                expiry_info = (
                    f"{expiry_str[:19]}Z "
                    f"({'만료됨' if diff < 0 else f'{diff/60:.0f}분 후 만료'})"
                )
            else:
                expiry_info = "없음"
            print(f"  token.json     : 있음 (권한 {file_perm})")
            print(f"  refresh_token  : {'있음' if has_refresh else '없음 ❌'}")
            print(f"  access token   : {expiry_info}")
        except Exception as e:
            print(f"  token.json     : 파싱 실패 ({e})")
    else:
        print("  token.json     : 없음 ❌")

    if last_ok:
        days_ago = (_now() - last_ok).total_seconds() / 86400
        health = "✅" if days_ago < 1 else ("⚠️" if days_ago < WARN_DAYS else "❌")
        print(
            f"  마지막 검증    : {last_ok.strftime('%Y-%m-%d %H:%M')} UTC "
            f"({days_ago:.1f}일 전) {health}"
        )
    else:
        print("  마지막 검증    : 기록 없음 (daily_check 미실행)")

    if last_check:
        print(f"  마지막 점검    : {last_check.strftime('%Y-%m-%d %H:%M')} UTC")

    if state.get("last_error"):
        ec = state.get("last_error_class", "")
        print(f"  최근 오류      : [{ec}] {state['last_error']}")

    print("=" * 52)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="YouTube OAuth 토큰 상태 점검 (PIPE-F10)",
        epilog=(
            "cron 등록 예시:\n"
            "  1 9 * * * cd ~/music-lab && python3 scripts/token_guard.py "
            ">> logs/token_guard.log 2>&1"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--status", action="store_true", help="현재 토큰 상태 표시")
    args = parser.parse_args()

    if args.status:
        print_status()
        return

    sys.exit(daily_check())


if __name__ == "__main__":
    main()
