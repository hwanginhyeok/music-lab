"""컨텍스트 포매팅 테스트 — 히스토리 주입 포맷 검증."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from bot import format_context, _get_timeout_error_message, _get_thinking_message


class TestFormatContext:
    def test_히스토리_없음(self):
        """히스토리가 없으면 현재 메시지만 반환."""
        result = format_context([], "안녕하세요")
        assert result == "안녕하세요"

    def test_정상_히스토리(self):
        history = [
            {"role": "user", "content": "코드 추천해줘"},
            {"role": "assistant", "content": "C - G - Am - F를 추천합니다."},
        ]
        result = format_context(history, "세 번째 코드 바꿔줘")
        assert "[이전 대화]" in result
        assert "USER: 코드 추천해줘" in result
        assert "ASSISTANT: C - G - Am - F를 추천합니다." in result
        assert "[현재 요청]" in result
        assert "USER: 세 번째 코드 바꿔줘" in result

    def test_midi_json_요약(self):
        """히스토리에 midi-json 블록이 있으면 [MIDI 데이터 생성됨]으로 대체."""
        history = [
            {"role": "user", "content": "MIDI 만들어줘"},
            {"role": "assistant", "content": "생성했습니다!\n```midi-json\n{\"title\": \"test\"}\n```\n좋아요!"},
        ]
        result = format_context(history, "다음 질문")
        assert "midi-json" not in result
        assert "[MIDI 데이터 생성됨]" in result
        assert "좋아요!" in result

    def test_다중_턴_순서(self):
        """여러 턴이 올바른 순서로 포맷되는지 확인."""
        history = [
            {"role": "user", "content": "1번 질문"},
            {"role": "assistant", "content": "1번 답변"},
            {"role": "user", "content": "2번 질문"},
            {"role": "assistant", "content": "2번 답변"},
        ]
        result = format_context(history, "3번 질문")
        # 순서 확인: 1번 → 2번 → 3번
        idx1 = result.index("1번 질문")
        idx2 = result.index("2번 질문")
        idx3 = result.index("3번 질문")
        assert idx1 < idx2 < idx3

    def test_히스토리_압축_5쌍_이하(self):
        """5쌍 이하면 요약 없이 원문 유지."""
        history = [
            {"role": "user", "content": f"질문 {i}"}
            if i % 2 == 0 else {"role": "assistant", "content": f"답변 {i}"}
            for i in range(10)  # 5쌍 = 10메시지
        ]
        result = format_context(history, "현재 질문")
        assert "[이전 대화 요약" not in result
        assert "질문 0" in result

    def test_히스토리_압축_5쌍_초과(self):
        """5쌍 초과 시 오래된 대화 요약 + 최근 5쌍 원문."""
        history = []
        for i in range(8):  # 8쌍 = 16메시지
            history.append({"role": "user", "content": f"질문 {i}"})
            history.append({"role": "assistant", "content": f"답변 {i}"})
        result = format_context(history, "현재 질문")
        # 요약 포함
        assert "[이전 대화 요약" in result
        # 오래된 대화(0~2번)는 없어야 함
        assert "질문 0" not in result
        assert "질문 1" not in result
        assert "질문 2" not in result
        # 최근 5쌍(3~7번)은 유지
        assert "질문 3" in result
        assert "질문 7" in result


class TestTimeoutErrorMessage:
    """U-5: 상황별 타임아웃 에러 메시지 테스트."""

    def test_midi_관련_요청(self):
        msg = _get_timeout_error_message("멀티트랙 MIDI 만들어줘", [])
        assert "MIDI" in msg
        assert "트랙" in msg

    def test_히스토리_긴_경우(self):
        # 12개 메시지 = 6쌍 (> 10 기준 충족을 위해 12개 이상)
        long_history = [{"role": "user", "content": f"q{i}"} for i in range(12)]
        msg = _get_timeout_error_message("안녕", long_history)
        assert "/new" in msg
        assert "대화가 길어" in msg

    def test_일반_타임아웃(self):
        msg = _get_timeout_error_message("안녕하세요", [])
        assert "시간 초과" in msg

    def test_코드진행_midi_키워드(self):
        msg = _get_timeout_error_message("코드 진행 추천해줘", None)
        assert "MIDI" in msg


class TestThinkingMessage:
    """U-6: 요청 복잡도 사전 안내 테스트."""

    def test_멀티트랙_안내(self):
        msg = _get_thinking_message("멀티트랙 피아노 + 베이스 만들어줘", "🎼")
        assert "멀티트랙" in msg
        assert "1-3분" in msg

    def test_풀트랙_안내(self):
        msg = _get_thinking_message("풀트랙 편곡해줘", "🎼")
        assert "멀티트랙" in msg

    def test_작사_안내(self):
        msg = _get_thinking_message("가사 써줘 벌스 2개", "✍️")
        assert "작사" in msg

    def test_midi_이모지_기본(self):
        msg = _get_thinking_message("C장조 멜로디", "🎼")
        assert "생성 중" in msg

    def test_chord_이모지_기본(self):
        msg = _get_thinking_message("슬픈 분위기", "🎹")
        assert "생성 중" in msg

    def test_일반_대화(self):
        msg = _get_thinking_message("안녕하세요", "💭")
        assert "생각하는 중" in msg
