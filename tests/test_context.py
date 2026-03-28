"""컨텍스트 포매팅 테스트 — 히스토리 주입 포맷 검증."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from bot import format_context


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
