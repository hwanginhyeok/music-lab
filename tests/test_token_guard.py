"""token_guard.py 단위 테스트 (PIPE-F10)."""
from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# scripts/ 디렉토리를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import token_guard


# ---------------------------------------------------------------------------
# 픽스처
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def isolated_paths(tmp_path, monkeypatch):
    """token.json / state 파일을 임시 디렉토리로 격리."""
    token_path = tmp_path / "token.json"
    state_path = tmp_path / "data" / ".token_guard_state.json"
    monkeypatch.setattr(token_guard, "TOKEN_PATH", token_path)
    monkeypatch.setattr(token_guard, "STATE_PATH", state_path)
    return {"token": token_path, "state": state_path, "tmp": tmp_path}


def _write_token(token_path: Path, refresh_token: str = "valid_refresh",
                 expiry_offset_hours: float = 1.0):
    """테스트용 token.json 생성."""
    expiry = (datetime.now(timezone.utc) + timedelta(hours=expiry_offset_hours)).isoformat()
    data = {
        "token": "access_token_value",
        "refresh_token": refresh_token,
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": "test_client_id",
        "client_secret": "test_client_secret",
        "scopes": ["https://www.googleapis.com/auth/youtube.upload"],
        "expiry": expiry,
    }
    token_path.write_text(json.dumps(data))


# ---------------------------------------------------------------------------
# check_health() 테스트
# ---------------------------------------------------------------------------

class TestCheckHealth:
    def test_token_missing(self, isolated_paths):
        """token.json 없을 때 False 반환."""
        result = token_guard.check_health()
        assert result["ok"] is False
        assert "없음" in result["error"]

    def test_refresh_success(self, isolated_paths):
        """refresh 성공 시 OK + 토큰 저장."""
        try:
            from google.oauth2.credentials import Credentials
        except ImportError:
            pytest.skip("google-auth 미설치")

        _write_token(isolated_paths["token"])

        mock_creds = MagicMock(spec=Credentials)
        mock_creds.refresh_token = "valid_refresh"
        mock_creds.to_json.return_value = json.dumps({"ok": True})
        mock_creds.refresh.return_value = None  # 성공

        with patch.object(Credentials, "from_authorized_user_file", return_value=mock_creds):
            result = token_guard.check_health()

        assert result["ok"] is True
        assert result["error"] is None

    def test_refresh_failure_blocks(self, isolated_paths):
        """RefreshError 발생 시 ok=False."""
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.exceptions import RefreshError
        except ImportError:
            pytest.skip("google-auth 미설치")

        _write_token(isolated_paths["token"])

        mock_creds = MagicMock(spec=Credentials)
        mock_creds.refresh_token = "invalid_refresh"
        mock_creds.refresh.side_effect = RefreshError("token expired")

        with patch.object(Credentials, "from_authorized_user_file", return_value=mock_creds):
            result = token_guard.check_health()

        assert result["ok"] is False
        assert result["error"] is not None

    def test_no_refresh_token(self, isolated_paths):
        """refresh_token 없을 때 False."""
        _write_token(isolated_paths["token"])
        raw = json.loads(isolated_paths["token"].read_text())
        raw.pop("refresh_token", None)
        isolated_paths["token"].write_text(json.dumps(raw))

        try:
            from google.oauth2.credentials import Credentials
        except ImportError:
            pytest.skip("google-auth 미설치")

        with patch.object(Credentials, "from_authorized_user_file") as mock_load:
            mock_creds = MagicMock(spec=Credentials)
            mock_creds.refresh_token = None
            mock_load.return_value = mock_creds

            result = token_guard.check_health()

        assert result["ok"] is False
        assert "refresh_token" in result["error"]


# ---------------------------------------------------------------------------
# pre_upload_guard() 테스트
# ---------------------------------------------------------------------------

class TestPreUploadGuard:
    def test_healthy_token_passes(self, isolated_paths):
        """토큰 정상 → guard 통과 (예외 없음)."""
        with patch.object(token_guard, "check_health", return_value={"ok": True, "days_since_ok": 0.1, "error": None}):
            token_guard.pre_upload_guard()  # 예외 없어야 함

    def test_bad_token_raises(self, isolated_paths):
        """토큰 불량 → TokenExpiredError 발생."""
        with patch.object(token_guard, "check_health", return_value={
            "ok": False, "days_since_ok": None, "error": "refresh_token 만료됨"
        }), patch.object(token_guard, "_send_alert", return_value=True):
            with pytest.raises(token_guard.TokenExpiredError):
                token_guard.pre_upload_guard()

    def test_sends_alert_on_failure(self, isolated_paths):
        """토큰 불량 시 _send_alert 호출됨."""
        with patch.object(token_guard, "check_health", return_value={
            "ok": False, "days_since_ok": None, "error": "test error"
        }):
            alert_calls = []
            with patch.object(token_guard, "_send_alert", side_effect=lambda t: alert_calls.append(t)):
                with pytest.raises(token_guard.TokenExpiredError):
                    token_guard.pre_upload_guard()

        assert len(alert_calls) == 1
        assert "차단" in alert_calls[0] or "blocked" in alert_calls[0].lower()

    def test_stale_token_warns_but_allows(self, isolated_paths):
        """7일 이상 미검증이지만 오늘 refresh 성공 → 경고 전송 후 통과."""
        with patch.object(token_guard, "check_health", return_value={
            "ok": True, "days_since_ok": 8.0, "error": None
        }):
            alert_calls = []
            with patch.object(token_guard, "_send_alert", side_effect=lambda t: alert_calls.append(t)):
                token_guard.pre_upload_guard()  # 예외 없이 통과

        assert len(alert_calls) == 1
        assert "경고" in alert_calls[0]


# ---------------------------------------------------------------------------
# daily_check() 테스트
# ---------------------------------------------------------------------------

class TestDailyCheck:
    def test_healthy_returns_0(self, isolated_paths):
        """토큰 정상 → 종료코드 0."""
        with patch.object(token_guard, "check_health", return_value={"ok": True, "days_since_ok": 0.5, "error": None}):
            assert token_guard.daily_check() == 0

    def test_bad_token_returns_1(self, isolated_paths):
        """토큰 불량 → 종료코드 1 + 알림."""
        with patch.object(token_guard, "check_health", return_value={
            "ok": False, "days_since_ok": None, "error": "token revoked"
        }), patch.object(token_guard, "_send_alert", return_value=True) as mock_alert:
            code = token_guard.daily_check()

        assert code == 1
        mock_alert.assert_called_once()
        msg = mock_alert.call_args[0][0]
        assert "이상" in msg or "오류" in msg

    def test_stale_7days_warns(self, isolated_paths):
        """7일 이상 미검증 후 오늘 성공 → 경고 전송."""
        # 8일 전 last_ok를 state에 기록
        old_time = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
        token_guard.STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        token_guard.STATE_PATH.write_text(json.dumps({
            "last_ok_utc": old_time,
            "last_check_utc": old_time,
            "last_error": None,
        }))

        with patch.object(token_guard, "check_health", return_value={"ok": True, "days_since_ok": 0.0, "error": None}), \
             patch.object(token_guard, "_save_state"):  # state 업데이트 스킵 (이미 설정됨)
            alert_calls = []
            with patch.object(token_guard, "_send_alert", side_effect=lambda t: alert_calls.append(t)):
                code = token_guard.daily_check()

        assert code == 0  # 성공했으므로 0
        # 경고 알림이 한 번 전송됨
        assert any("일 만에" in a or "미검증" in a or "경고" in a for a in alert_calls)

    def test_no_stale_no_warn(self, isolated_paths):
        """어제 검증 → 경고 없음."""
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        token_guard.STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        token_guard.STATE_PATH.write_text(json.dumps({
            "last_ok_utc": yesterday,
            "last_check_utc": yesterday,
            "last_error": None,
        }))

        with patch.object(token_guard, "check_health", return_value={"ok": True, "days_since_ok": 1.0, "error": None}), \
             patch.object(token_guard, "_save_state"):
            alert_calls = []
            with patch.object(token_guard, "_send_alert", side_effect=lambda t: alert_calls.append(t)):
                code = token_guard.daily_check()

        assert code == 0
        assert len(alert_calls) == 0


# ---------------------------------------------------------------------------
# 시나리오 테스트
# ---------------------------------------------------------------------------

class TestScenarios:
    """만료 14일/7일/1일 시나리오."""

    def test_scenario_14days_ok(self, isolated_paths):
        """14일 전 마지막 성공, 오늘 refresh 성공 → warning 전송, 업로드 허용."""
        old = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
        token_guard.STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        token_guard.STATE_PATH.write_text(json.dumps({
            "last_ok_utc": old, "last_check_utc": old, "last_error": None,
        }))

        with patch.object(token_guard, "check_health", return_value={"ok": True, "days_since_ok": 14.0, "error": None}), \
             patch.object(token_guard, "_save_state"):
            alerts = []
            with patch.object(token_guard, "_send_alert", side_effect=lambda t: alerts.append(t)):
                token_guard.pre_upload_guard()  # 업로드 허용 (예외 없음)
                token_guard.daily_check()

        # pre_upload_guard: stale warning 1건
        # daily_check: stale warning 1건 (총 2건)
        assert len(alerts) >= 1

    def test_scenario_7days_warning(self, isolated_paths):
        """7일 전 마지막 성공 → daily_check에서 경고 발송."""
        old = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        token_guard.STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        token_guard.STATE_PATH.write_text(json.dumps({
            "last_ok_utc": old, "last_check_utc": old, "last_error": None,
        }))

        with patch.object(token_guard, "check_health", return_value={"ok": True, "days_since_ok": 7.0, "error": None}), \
             patch.object(token_guard, "_save_state"):
            alerts = []
            with patch.object(token_guard, "_send_alert", side_effect=lambda t: alerts.append(t)):
                code = token_guard.daily_check()

        assert code == 0
        assert len(alerts) >= 1

    def test_scenario_refresh_fails_blocks(self, isolated_paths):
        """refresh_token 만료 → pre_upload_guard에서 즉시 차단 + 알림."""
        with patch.object(token_guard, "check_health", return_value={
            "ok": False, "days_since_ok": 30.0, "error": "refresh_token 만료됨: invalid_grant"
        }):
            alerts = []
            with patch.object(token_guard, "_send_alert", side_effect=lambda t: alerts.append(t)):
                with pytest.raises(token_guard.TokenExpiredError):
                    token_guard.pre_upload_guard()

        assert len(alerts) == 1
        msg = alerts[0]
        assert "차단" in msg
        assert "재인증" in msg
