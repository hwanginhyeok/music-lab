"""token_guard.py 단위 테스트 (PIPE-F10)."""
from __future__ import annotations

import json
import os
import stat
import sys
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
# check_health() — 기본 동작
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
        mock_creds.refresh.return_value = None

        with patch.object(Credentials, "from_authorized_user_file", return_value=mock_creds):
            result = token_guard.check_health()

        assert result["ok"] is True
        assert result["error"] is None
        assert result["error_class"] is None

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
# check_health() — error_class 분류
# ---------------------------------------------------------------------------

class TestErrorClassification:
    """RefreshError / 네트워크 오류 분류 검증."""

    def _make_creds(self, side_effect):
        """mock Credentials 반환."""
        try:
            from google.oauth2.credentials import Credentials
        except ImportError:
            pytest.skip("google-auth 미설치")
        mock = MagicMock(spec=Credentials)
        mock.refresh_token = "some_refresh"
        mock.refresh.side_effect = side_effect
        return mock

    def test_invalid_grant_classified(self, isolated_paths):
        """invalid_grant 포함 RefreshError → error_class='invalid_grant'."""
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.exceptions import RefreshError
        except ImportError:
            pytest.skip("google-auth 미설치")

        _write_token(isolated_paths["token"])
        mock_creds = self._make_creds(RefreshError("invalid_grant: Token has been expired or revoked."))

        with patch.object(Credentials, "from_authorized_user_file", return_value=mock_creds):
            result = token_guard.check_health()

        assert result["ok"] is False
        assert result["error_class"] == "invalid_grant"

    def test_quota_exceeded_classified(self, isolated_paths):
        """quota 포함 RefreshError → error_class='quota_exceeded'."""
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.exceptions import RefreshError
        except ImportError:
            pytest.skip("google-auth 미설치")

        _write_token(isolated_paths["token"])
        mock_creds = self._make_creds(RefreshError("quota_exceeded: API quota exceeded"))

        with patch.object(Credentials, "from_authorized_user_file", return_value=mock_creds):
            result = token_guard.check_health()

        assert result["ok"] is False
        assert result["error_class"] == "quota_exceeded"

    def test_rate_limit_camel_case_classified(self, isolated_paths):
        """rateLimitExceeded(camelCase) RefreshError → error_class='quota_exceeded'."""
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.exceptions import RefreshError
        except ImportError:
            pytest.skip("google-auth 미설치")

        _write_token(isolated_paths["token"])
        mock_creds = self._make_creds(RefreshError("rateLimitExceeded: quota exceeded"))

        with patch.object(Credentials, "from_authorized_user_file", return_value=mock_creds):
            result = token_guard.check_health()

        assert result["ok"] is False
        assert result["error_class"] == "quota_exceeded"

    def test_transport_error_classified(self, isolated_paths):
        """TransportError → error_class='network_error'."""
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.exceptions import TransportError
        except ImportError:
            pytest.skip("google-auth 미설치")

        _write_token(isolated_paths["token"])
        mock_creds = self._make_creds(TransportError("Connection reset by peer"))

        with patch.object(Credentials, "from_authorized_user_file", return_value=mock_creds):
            result = token_guard.check_health()

        assert result["ok"] is False
        assert result["error_class"] == "network_error"

    def test_connection_error_classified(self, isolated_paths):
        """Python ConnectionError → error_class='network_error'."""
        try:
            from google.oauth2.credentials import Credentials
        except ImportError:
            pytest.skip("google-auth 미설치")

        _write_token(isolated_paths["token"])
        mock_creds = self._make_creds(ConnectionError("Connection refused"))

        with patch.object(Credentials, "from_authorized_user_file", return_value=mock_creds):
            result = token_guard.check_health()

        assert result["ok"] is False
        assert result["error_class"] == "network_error"

    def test_network_error_alert_no_reauth(self, isolated_paths):
        """네트워크 오류 알림에는 재인증 안내가 포함되지 않아야 함."""
        alerts = []
        with patch.object(token_guard, "check_health", return_value={
            "ok": False,
            "days_since_ok": None,
            "error": "네트워크 연결 실패",
            "error_class": "network_error",
        }), patch.object(token_guard, "_send_alert", side_effect=lambda t: alerts.append(t)):
            with pytest.raises(token_guard.TokenExpiredError):
                token_guard.pre_upload_guard()

        assert len(alerts) == 1
        msg = alerts[0]
        # 네트워크 오류 → 재인증 안내 없어야 함
        assert "재인증 방법" not in msg
        assert "일시 오류" in msg or "네트워크" in msg

    def test_invalid_grant_alert_includes_reauth(self, isolated_paths):
        """invalid_grant 알림에는 재인증 안내가 포함되어야 함."""
        alerts = []
        with patch.object(token_guard, "check_health", return_value={
            "ok": False,
            "days_since_ok": None,
            "error": "refresh_token 만료됨: invalid_grant",
            "error_class": "invalid_grant",
        }), patch.object(token_guard, "_send_alert", side_effect=lambda t: alerts.append(t)):
            with pytest.raises(token_guard.TokenExpiredError):
                token_guard.pre_upload_guard()

        assert len(alerts) == 1
        msg = alerts[0]
        assert "재인증 방법" in msg

    def test_quota_exceeded_alert_no_reauth(self, isolated_paths):
        """quota_exceeded 알림에는 재인증 안내가 없어야 함."""
        alerts = []
        with patch.object(token_guard, "check_health", return_value={
            "ok": False,
            "days_since_ok": None,
            "error": "API 할당량 초과",
            "error_class": "quota_exceeded",
        }), patch.object(token_guard, "_send_alert", side_effect=lambda t: alerts.append(t)):
            with pytest.raises(token_guard.TokenExpiredError):
                token_guard.pre_upload_guard()

        assert len(alerts) == 1
        msg = alerts[0]
        assert "재인증 방법" not in msg
        assert "할당량" in msg or "24시간" in msg

    def test_network_error_daily_check_different_title(self, isolated_paths):
        """network_error는 daily_check에서 다른 타이틀로 알림."""
        with patch.object(token_guard, "check_health", return_value={
            "ok": False,
            "days_since_ok": None,
            "error": "네트워크 오류",
            "error_class": "network_error",
        }):
            alerts = []
            with patch.object(token_guard, "_send_alert", side_effect=lambda t: alerts.append(t)):
                code = token_guard.daily_check()

        assert code == 1
        assert len(alerts) == 1
        # network_error는 🚨이 아닌 ⚠️ 타이틀
        assert "네트워크 오류" in alerts[0]


# ---------------------------------------------------------------------------
# token.json 파일 권한 (chmod 0600)
# ---------------------------------------------------------------------------

class TestTokenPermissions:
    def test_token_written_with_0600(self, isolated_paths):
        """refresh 성공 후 token.json 권한이 0600이어야 함."""
        try:
            from google.oauth2.credentials import Credentials
        except ImportError:
            pytest.skip("google-auth 미설치")

        _write_token(isolated_paths["token"])
        # 초기 권한을 0644로 설정
        os.chmod(isolated_paths["token"], 0o644)
        assert stat.S_IMODE(isolated_paths["token"].stat().st_mode) == 0o644

        mock_creds = MagicMock(spec=Credentials)
        mock_creds.refresh_token = "valid_refresh"
        mock_creds.to_json.return_value = json.dumps({"refreshed": True})
        mock_creds.refresh.return_value = None

        with patch.object(Credentials, "from_authorized_user_file", return_value=mock_creds):
            result = token_guard.check_health()

        assert result["ok"] is True
        # 갱신 후 권한이 0600으로 변경되어야 함
        actual_perm = stat.S_IMODE(isolated_paths["token"].stat().st_mode)
        assert actual_perm == 0o600, f"권한이 0600이어야 하지만 {oct(actual_perm)}임"

    def test_write_token_secure_sets_0600(self, isolated_paths):
        """_write_token_secure() 직접 호출 시 0600 권한 설정 확인."""
        target = isolated_paths["tmp"] / "new_token.json"
        token_guard._write_token_secure(target, '{"test": true}')

        actual_perm = stat.S_IMODE(target.stat().st_mode)
        assert actual_perm == 0o600


# ---------------------------------------------------------------------------
# pre_upload_guard() 테스트
# ---------------------------------------------------------------------------

class TestPreUploadGuard:
    def test_healthy_token_passes(self, isolated_paths):
        """토큰 정상 → guard 통과 (예외 없음)."""
        with patch.object(token_guard, "check_health", return_value={
            "ok": True, "days_since_ok": 0.1, "error": None, "error_class": None,
        }):
            token_guard.pre_upload_guard()

    def test_bad_token_raises(self, isolated_paths):
        """토큰 불량 → TokenExpiredError 발생."""
        with patch.object(token_guard, "check_health", return_value={
            "ok": False, "days_since_ok": None,
            "error": "refresh_token 만료됨", "error_class": "invalid_grant",
        }), patch.object(token_guard, "_send_alert", return_value=True):
            with pytest.raises(token_guard.TokenExpiredError):
                token_guard.pre_upload_guard()

    def test_sends_alert_on_failure(self, isolated_paths):
        """토큰 불량 시 _send_alert 호출됨."""
        with patch.object(token_guard, "check_health", return_value={
            "ok": False, "days_since_ok": None,
            "error": "test error", "error_class": "invalid_grant",
        }):
            alert_calls = []
            with patch.object(token_guard, "_send_alert", side_effect=lambda t: alert_calls.append(t)):
                with pytest.raises(token_guard.TokenExpiredError):
                    token_guard.pre_upload_guard()

        assert len(alert_calls) == 1
        assert "차단" in alert_calls[0]

    def test_stale_token_warns_but_allows(self, isolated_paths):
        """7일 이상 미검증이지만 오늘 refresh 성공 → 경고 전송 후 통과."""
        with patch.object(token_guard, "check_health", return_value={
            "ok": True, "days_since_ok": 8.0, "error": None, "error_class": None,
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
        with patch.object(token_guard, "check_health", return_value={
            "ok": True, "days_since_ok": 0.5, "error": None, "error_class": None,
        }):
            assert token_guard.daily_check() == 0

    def test_bad_token_returns_1(self, isolated_paths):
        """토큰 불량 → 종료코드 1 + 알림."""
        with patch.object(token_guard, "check_health", return_value={
            "ok": False, "days_since_ok": None,
            "error": "token revoked", "error_class": "invalid_grant",
        }), patch.object(token_guard, "_send_alert", return_value=True) as mock_alert:
            code = token_guard.daily_check()

        assert code == 1
        mock_alert.assert_called_once()
        msg = mock_alert.call_args[0][0]
        assert "이상" in msg or "오류" in msg

    def test_stale_7days_warns(self, isolated_paths):
        """7일 이상 미검증 후 오늘 성공 → 경고 전송."""
        old_time = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
        token_guard.STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        token_guard.STATE_PATH.write_text(json.dumps({
            "last_ok_utc": old_time,
            "last_check_utc": old_time,
            "last_error": None,
            "last_error_class": None,
        }))

        with patch.object(token_guard, "check_health", return_value={
            "ok": True, "days_since_ok": 0.0, "error": None, "error_class": None,
        }), patch.object(token_guard, "_save_state"):
            alert_calls = []
            with patch.object(token_guard, "_send_alert", side_effect=lambda t: alert_calls.append(t)):
                code = token_guard.daily_check()

        assert code == 0
        assert any("일 만에" in a or "미검증" in a or "경고" in a for a in alert_calls)

    def test_no_stale_no_warn(self, isolated_paths):
        """어제 검증 → 경고 없음."""
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        token_guard.STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        token_guard.STATE_PATH.write_text(json.dumps({
            "last_ok_utc": yesterday,
            "last_check_utc": yesterday,
            "last_error": None,
            "last_error_class": None,
        }))

        with patch.object(token_guard, "check_health", return_value={
            "ok": True, "days_since_ok": 1.0, "error": None, "error_class": None,
        }), patch.object(token_guard, "_save_state"):
            alert_calls = []
            with patch.object(token_guard, "_send_alert", side_effect=lambda t: alert_calls.append(t)):
                code = token_guard.daily_check()

        assert code == 0
        assert len(alert_calls) == 0


# ---------------------------------------------------------------------------
# 시나리오 테스트
# ---------------------------------------------------------------------------

class TestScenarios:
    """만료 14일/7일/refresh 실패 시나리오."""

    def test_scenario_14days_ok(self, isolated_paths):
        """14일 전 마지막 성공, 오늘 refresh 성공 → warning 전송, 업로드 허용."""
        old = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
        token_guard.STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        token_guard.STATE_PATH.write_text(json.dumps({
            "last_ok_utc": old, "last_check_utc": old,
            "last_error": None, "last_error_class": None,
        }))

        with patch.object(token_guard, "check_health", return_value={
            "ok": True, "days_since_ok": 14.0, "error": None, "error_class": None,
        }), patch.object(token_guard, "_save_state"):
            alerts = []
            with patch.object(token_guard, "_send_alert", side_effect=lambda t: alerts.append(t)):
                token_guard.pre_upload_guard()  # 업로드 허용 (예외 없음)
                token_guard.daily_check()

        assert len(alerts) >= 1

    def test_scenario_7days_warning(self, isolated_paths):
        """7일 전 마지막 성공 → daily_check에서 경고 발송."""
        old = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        token_guard.STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        token_guard.STATE_PATH.write_text(json.dumps({
            "last_ok_utc": old, "last_check_utc": old,
            "last_error": None, "last_error_class": None,
        }))

        with patch.object(token_guard, "check_health", return_value={
            "ok": True, "days_since_ok": 7.0, "error": None, "error_class": None,
        }), patch.object(token_guard, "_save_state"):
            alerts = []
            with patch.object(token_guard, "_send_alert", side_effect=lambda t: alerts.append(t)):
                code = token_guard.daily_check()

        assert code == 0
        assert len(alerts) >= 1

    def test_scenario_refresh_fails_blocks(self, isolated_paths):
        """refresh_token 만료 → pre_upload_guard에서 즉시 차단 + 재인증 알림."""
        with patch.object(token_guard, "check_health", return_value={
            "ok": False, "days_since_ok": 30.0,
            "error": "refresh_token 만료됨: invalid_grant",
            "error_class": "invalid_grant",
        }):
            alerts = []
            with patch.object(token_guard, "_send_alert", side_effect=lambda t: alerts.append(t)):
                with pytest.raises(token_guard.TokenExpiredError):
                    token_guard.pre_upload_guard()

        assert len(alerts) == 1
        msg = alerts[0]
        assert "차단" in msg
        assert "재인증" in msg

    def test_scenario_network_error_blocks_no_reauth(self, isolated_paths):
        """네트워크 오류 → 차단되지만 재인증 안내 없음."""
        with patch.object(token_guard, "check_health", return_value={
            "ok": False, "days_since_ok": 0.5,
            "error": "네트워크 연결 실패",
            "error_class": "network_error",
        }):
            alerts = []
            with patch.object(token_guard, "_send_alert", side_effect=lambda t: alerts.append(t)):
                with pytest.raises(token_guard.TokenExpiredError):
                    token_guard.pre_upload_guard()

        assert len(alerts) == 1
        assert "재인증 방법" not in alerts[0]
        assert "일시 오류" in alerts[0] or "네트워크" in alerts[0]
