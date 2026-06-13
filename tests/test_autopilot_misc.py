"""
autopilot 부속 모듈 테스트 — claude_cli, trace, nodes stubs.
"""
import json
import os
import sys
import unittest.mock as mock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from autopilot.claude_cli import call_claude, CliResult, ClaudeAuthError, CLAUDE_CLI_VERSION
from autopilot.trace import emit, flush, LANGSMITH_AVAILABLE


# ---------------------------------------------------------------------------
# claude_cli: 정상 호출 + auth 에러 감지
# ---------------------------------------------------------------------------
class TestClaudeCli:
    def test_정상_호출_CliResult_반환(self):
        """subprocess를 mock해서 정상 응답을 반환받는다."""
        mock_result = mock.MagicMock()
        mock_result.stdout = "생성된 가사 텍스트"
        mock_result.stderr = ""
        mock_result.returncode = 0

        def mock_runner(cmd, **kwargs):
            return mock_result

        result = call_claude("가사를 써줘", runner=mock_runner)
        assert isinstance(result, CliResult)
        assert result.stdout == "생성된 가사 텍스트"
        assert result.exit_code == 0

    def test_버전_핀_포함_확인(self):
        """CLAUDE_CLI_VERSION 상수가 설정되어 있고, 빌드된 커맨드에 포함된다."""
        captured_cmd = {}

        def capture_runner(cmd, **kwargs):
            captured_cmd["cmd"] = cmd
            r = mock.MagicMock()
            r.stdout = ""
            r.stderr = ""
            r.returncode = 0
            return r

        call_claude("테스트", runner=capture_runner)
        cmd_str = " ".join(captured_cmd["cmd"])
        assert CLAUDE_CLI_VERSION in cmd_str
        assert "--tools" in cmd_str
        assert "--no-session-persistence" in cmd_str

    def test_auth_에러_stderr_ClaudeAuthError(self):
        """stderr에 인증 관련 키워드가 있으면 ClaudeAuthError가 발생한다."""
        for auth_msg in ["OAuth token expired", "Unauthorized", "Please login", "auth failed"]:
            mock_result = mock.MagicMock()
            mock_result.stdout = ""
            mock_result.stderr = auth_msg
            mock_result.returncode = 1

            with pytest.raises(ClaudeAuthError):
                call_claude("테스트", runner=lambda cmd, **kw: mock_result)

    def test_일반_에러는_ClaudeAuthError_아님(self):
        """일반 에러(비인증)는 ClaudeAuthError를 발생시키지 않는다."""
        mock_result = mock.MagicMock()
        mock_result.stdout = ""
        mock_result.stderr = "timeout occurred"
        mock_result.returncode = 1

        # ClaudeAuthError가 아닌 일반 예외나 그냥 CliResult 반환
        # (구현 선택: 비auth 에러는 CliResult로 반환하고 exit_code!=0으로 처리)
        result = call_claude("테스트", runner=lambda cmd, **kw: mock_result)
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# trace: jsonl 기록 + langsmith no-op
# ---------------------------------------------------------------------------
class TestTrace:
    def test_emit_jsonl_기록(self, tmp_path):
        """emit 호출 시 trace.jsonl에 JSON 라인이 추가된다."""
        trace_file = str(tmp_path / "trace.jsonl")
        emit({"event": "step_start", "step": "write_lyrics"}, trace_path=trace_file)
        emit({"event": "step_done", "step": "write_lyrics"}, trace_path=trace_file)
        flush(trace_file)

        lines = (tmp_path / "trace.jsonl").read_text().strip().split("\n")
        assert len(lines) == 2
        parsed = json.loads(lines[0])
        assert parsed["event"] == "step_start"

    def test_langsmith_없으면_noop(self, tmp_path):
        """LangSmith 미설치 환경에서 LANGSMITH_AVAILABLE=False이고 emit은 정상 작동."""
        # LANGSMITH_AVAILABLE 이 False여도 emit이 동작해야 함
        trace_file = str(tmp_path / "trace_noop.jsonl")
        # 에러 없이 실행되면 성공
        emit({"event": "test"}, trace_path=trace_file)
        assert (tmp_path / "trace_noop.jsonl").exists()

    def test_LANGSMITH_AVAILABLE_bool(self):
        """LANGSMITH_AVAILABLE 이 bool이어야 한다."""
        assert isinstance(LANGSMITH_AVAILABLE, bool)


# ---------------------------------------------------------------------------
# nodes stubs — Phase 4 stub 확인 (Phase 3 노드는 구현 완료)
# ---------------------------------------------------------------------------
class TestNodeStubs:
    # Phase 3 구현 완료: generate_node, lyrics_node, suno_prompt_node, prefilter_node
    # → NotImplementedError 테스트 제거. 대신 Phase 3 테스트는 test_autopilot_nodes_phase3.py 참조.

    # 하위 호환성 deprecated stub 함수들은 여전히 NotImplementedError를 발생시킨다.
    def test_generate_deprecated_stub_제거됨(self):
        """generate() 함수는 더 이상 존재하지 않음 — generate_node()로 교체됨."""
        import autopilot.nodes.generate as gen_mod
        assert hasattr(gen_mod, "generate_node"), "generate_node 함수가 없음"

    def test_write_lyrics_deprecated_NotImplementedError(self):
        """write_lyrics()는 deprecated stub으로 NotImplementedError를 발생시킨다."""
        from autopilot.nodes.lyrics import write_lyrics
        with pytest.raises(NotImplementedError):
            write_lyrics("앨범 컨셉")

    def test_build_prompt_NotImplementedError(self):
        """build_prompt()는 Phase 2 stub으로 NotImplementedError를 발생시킨다."""
        from autopilot.nodes.prompt import build_prompt
        with pytest.raises(NotImplementedError):
            build_prompt("가사")

    def test_prefilter_deprecated_NotImplementedError(self):
        """prefilter()는 deprecated stub으로 NotImplementedError를 발생시킨다."""
        from autopilot.nodes.prefilter import prefilter
        with pytest.raises(NotImplementedError):
            prefilter([])

    def test_postprocess_NotImplementedError(self):
        from autopilot.nodes.postprocess import postprocess
        with pytest.raises(NotImplementedError):
            postprocess("track.wav")

    def test_upload_NotImplementedError(self):
        from autopilot.nodes.upload import upload
        with pytest.raises(NotImplementedError):
            upload("track.mp4")
