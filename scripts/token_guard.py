#!/usr/bin/env python3
"""YouTube OAuth 토큰 만료 감지 + 경고 (PIPE-F10).

- check_health()   : 실시간 토큰 refresh 시도 + 상태 기록
- pre_upload_guard(): 업로드 직전 호출. 토큰 불량이면 TokenExpiredError 발생
- daily_check()    : cron 진입점. 7일 이상 미확인이면 경고 전송
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

WARN_DAYS = 7    # 마지막 성공 검증 후 N일 이상이면 경고
BLOCK_HOURS = 24  # 마지막 성공 검증 후 N시간 이상이면 업로드 차단 (live check 실패 시 적용)

REAUTH_STEPS = (
    "📋 재인증 방법:\n"
    "1. music-lab 서버에서 실행:\n"
    "   cd ~/music-lab && python3 scripts/youtube_upload.py songs/14_geuriumi/ --skip-upload\n"
    "   (--skip-upload: 영상 생성 없이 인증만 진행)\n"
    "2. 콘솔에 출력되는 URL을 브라우저에서 열어 Google 계정 인증\n"
    "3. 인증 코드 붙여넣기 → token.json 자동 갱신"
)


class TokenExpiredError(Exception):
    """토큰 만료 또는 무효 시 발생. 업로드를 차단한다."""


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
    return {"last_ok_utc": None, "last_check_utc": None, "last_error": None}


def _save_state(ok: bool, error: str | None = None) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    state = _load_state()
    now_s = _now().isoformat()
    state["last_check_utc"] = now_s
    if ok:
        state["last_ok_utc"] = now_s
        state["last_error"] = None
    else:
        state["last_error"] = error
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def _send_alert(text: str) -> bool:
    """텔레그램 알림 전송."""
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


def check_health() -> dict:
    """토큰 상태 실시간 검사. refresh 시도 후 결과 기록.

    Returns:
        {
            "ok": bool,
            "days_since_ok": float | None,  # 마지막 OK 이후 경과일 (이번 check 전 기준)
            "error": str | None,
        }
    """
    # 이번 check 전 마지막 OK 시간을 먼저 기록
    state_before = _load_state()
    prev_last_ok = _parse_dt(state_before.get("last_ok_utc"))
    days_since_ok: float | None = None
    if prev_last_ok:
        days_since_ok = (_now() - prev_last_ok).total_seconds() / 86400

    result: dict = {"ok": False, "days_since_ok": days_since_ok, "error": None}

    if not TOKEN_PATH.is_file():
        result["error"] = "token.json 없음 — 최초 인증이 필요합니다"
        _save_state(False, result["error"])
        return result

    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from google.auth.exceptions import RefreshError
    except ImportError:
        result["error"] = "google-auth 패키지 미설치 (pip install google-auth-oauthlib)"
        _save_state(False, result["error"])
        return result

    try:
        raw = json.loads(TOKEN_PATH.read_text())
        scopes = raw.get("scopes", ["https://www.googleapis.com/auth/youtube.upload"])
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), scopes)
    except Exception as e:
        result["error"] = f"token.json 파싱 실패: {e}"
        _save_state(False, result["error"])
        return result

    if not creds.refresh_token:
        result["error"] = "refresh_token 없음 — 재인증 필요"
        _save_state(False, result["error"])
        return result

    try:
        creds.refresh(Request())
        # 갱신된 access token 저장
        TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
        _save_state(True)
        result["ok"] = True
    except RefreshError as e:
        result["error"] = f"refresh_token 만료 또는 취소됨: {e}"
        _save_state(False, result["error"])
    except Exception as e:
        result["error"] = f"토큰 갱신 중 예외: {e}"
        _save_state(False, result["error"])

    return result


def pre_upload_guard() -> None:
    """업로드 직전 토큰 상태 검사. 불량이면 텔레그램 알림 + TokenExpiredError 발생.

    사용법:
        from token_guard import pre_upload_guard, TokenExpiredError
        pre_upload_guard()  # 업로드 직전에 호출
    """
    result = check_health()

    if not result["ok"]:
        msg = (
            "🚨 <b>YouTube 업로드 차단됨</b>\n"
            f"원인: {result['error']}\n\n"
            + REAUTH_STEPS
        )
        _send_alert(msg)
        raise TokenExpiredError(f"YouTube 토큰 무효: {result['error']}")

    # 성공했지만 오랫동안 미검증 상태였으면 경고 (업로드는 허용)
    days = result.get("days_since_ok") or 0
    if days >= WARN_DAYS:
        msg = (
            f"⚠️ YouTube 토큰 경고\n"
            f"마지막 검증: {days:.0f}일 전 (오늘 갱신 성공)\n"
            f"cron 점검을 권장합니다.\n\n"
            + REAUTH_STEPS
        )
        _send_alert(msg)


def daily_check() -> int:
    """매일 cron에서 호출. 토큰 상태 점검 + 이상 시 텔레그램 경고.

    Returns:
        0 = 정상, 1 = 경고/오류
    """
    state_before = _load_state()
    prev_last_ok = _parse_dt(state_before.get("last_ok_utc"))

    now_str = _now().strftime("%Y-%m-%d %H:%M UTC")
    print(f"[token-guard] 토큰 검사 시작 ({now_str})")

    result = check_health()

    if not result["ok"]:
        last_ok_str = prev_last_ok.strftime("%Y-%m-%d") if prev_last_ok else "기록 없음"
        msg = (
            "🚨 <b>YouTube OAuth 토큰 이상 감지</b>\n"
            f"오류: {result['error']}\n"
            f"마지막 정상: {last_ok_str}\n\n"
            + REAUTH_STEPS
        )
        _send_alert(msg)
        print(f"[token-guard] ❌ 토큰 이상: {result['error']}")
        return 1

    # 이번 check는 성공 — 이전 last_ok 기준으로 경과일 계산
    if prev_last_ok:
        days_gap = (_now() - prev_last_ok).total_seconds() / 86400
        if days_gap >= WARN_DAYS:
            msg = (
                f"⚠️ YouTube 토큰 경고\n"
                f"마지막 확인: {days_gap:.0f}일 전\n"
                f"오늘 갱신은 성공했지만, 중간 {days_gap:.0f}일간 미검증 상태였습니다.\n"
                f"cron이 중단되었거나 수동 점검이 필요합니다.\n\n"
                + REAUTH_STEPS
            )
            _send_alert(msg)
            print(f"[token-guard] ⚠️ {days_gap:.0f}일 만에 검증 성공 — cron 확인 권장")

    print("[token-guard] ✅ 토큰 정상")
    return 0


def print_status() -> None:
    """현재 토큰 상태 출력 (CLI --status용)."""
    state = _load_state()
    last_ok = _parse_dt(state.get("last_ok_utc"))
    last_check = _parse_dt(state.get("last_check_utc"))

    print("=" * 50)
    print("  YouTube 토큰 상태")
    print("=" * 50)

    if TOKEN_PATH.is_file():
        try:
            raw = json.loads(TOKEN_PATH.read_text())
            has_refresh = bool(raw.get("refresh_token"))
            expiry_str = raw.get("expiry", "없음")
            expiry = _parse_dt(expiry_str)
            now = _now()
            if expiry:
                diff = (expiry - now).total_seconds()
                expiry_info = f"{expiry_str[:19]}Z ({'만료됨' if diff < 0 else f'{diff/60:.0f}분 후 만료'})"
            else:
                expiry_info = "없음"
            print(f"  token.json     : 있음")
            print(f"  refresh_token  : {'있음' if has_refresh else '없음 ❌'}")
            print(f"  access token   : {expiry_info}")
        except Exception as e:
            print(f"  token.json     : 파싱 실패 ({e})")
    else:
        print("  token.json     : 없음 ❌")

    if last_ok:
        days_ago = (_now() - last_ok).total_seconds() / 86400
        status = "✅" if days_ago < 1 else ("⚠️" if days_ago < WARN_DAYS else "❌")
        print(f"  마지막 검증    : {last_ok.strftime('%Y-%m-%d %H:%M')} UTC ({days_ago:.1f}일 전) {status}")
    else:
        print("  마지막 검증    : 기록 없음 (daily_check 미실행)")

    if last_check:
        print(f"  마지막 점검    : {last_check.strftime('%Y-%m-%d %H:%M')} UTC")

    if state.get("last_error"):
        print(f"  최근 오류      : {state['last_error']}")

    print("=" * 50)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="YouTube OAuth 토큰 상태 점검 (PIPE-F10)",
        epilog=(
            "cron 등록 예시:\n"
            "  0 9 * * * cd ~/music-lab && python3 scripts/token_guard.py "
            ">> logs/token_guard.log 2>&1"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--status", action="store_true", help="현재 토큰 상태 표시")
    parser.add_argument("--check", action="store_true", help="토큰 검사 (daily_check 실행)")
    args = parser.parse_args()

    if args.status:
        print_status()
        return

    # 기본 동작 (--check 포함): daily_check 실행
    sys.exit(daily_check())


if __name__ == "__main__":
    main()
