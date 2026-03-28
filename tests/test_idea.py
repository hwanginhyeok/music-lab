"""영감 노트 관련 테스트 — 태그 추출, 아이디어 CRUD 통합."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from bot import _extract_tags


class TestExtractTags:
    def test_정상_태그(self):
        text = "멜로디입니다.\n태그: #재즈 #몽환적 #피아노"
        tags = _extract_tags(text)
        assert tags == ["재즈", "몽환적", "피아노"]

    def test_태그_없음(self):
        text = "태그 없는 응답입니다."
        tags = _extract_tags(text)
        assert tags == ["미분류"]

    def test_태그_공백_포함(self):
        text = "태그: #밝은 #팝 #기타"
        tags = _extract_tags(text)
        assert "밝은" in tags
        assert "팝" in tags

    def test_태그_하나(self):
        text = "태그: #피아노"
        tags = _extract_tags(text)
        assert tags == ["피아노"]

    def test_영어_태그(self):
        text = "태그: #jazz #chill #piano"
        tags = _extract_tags(text)
        assert "jazz" in tags
        assert "chill" in tags
