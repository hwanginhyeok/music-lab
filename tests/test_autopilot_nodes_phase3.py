"""
autopilot/nodes Phase 3 테스트.

전부 mock 기반 — 실제 VNC/Suno/Claude CLI/오디오 없음.
"""
import json
import os
import sys
import unittest.mock as mock
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from autopilot.store import Store
from autopilot.engine import Ctx
from autopilot.claude_cli import CliResult


# ---------------------------------------------------------------------------
# 공용 픽스처
# ---------------------------------------------------------------------------

@pytest.fixture
def store(tmp_path):
    return Store(str(tmp_path / "nodes_test.db"))


@pytest.fixture
def ctx(store):
    run_id = store.create_run("test-album")
    store.update_run_status(run_id, "running")
    return Ctx(run_id=run_id, store=store)


def _fake_cli_result(text: str) -> CliResult:
    return CliResult(stdout=text, stderr="", exit_code=0, elapsed=0.1)


# ---------------------------------------------------------------------------
# 1. lyrics_node
# ---------------------------------------------------------------------------

class TestLyricsNode:
    def test_가사_파일_생성_및_artifact_등록(self, ctx, tmp_path, monkeypatch):
        """mock call_claude → 가사 파일 저장 + artifact SHA256 등록."""
        monkeypatch.setenv("AUTOPILOT_DATA_DIR", str(tmp_path / "data"))

        fake_lyrics = "[Verse 1]\n자꾸 그쪽 길로 돌아와\n\n[Chorus]\n택시 두 대가 반대로 꺾어진 골목"

        # lyrics.py가 'from autopilot.claude_cli import call_claude'로 로컬 바인딩하므로
        # 해당 모듈의 네임스페이스에서 직접 패치한다.
        import autopilot.nodes.lyrics as lyrics_mod
        monkeypatch.setattr(lyrics_mod, "call_claude", lambda *a, **kw: _fake_cli_result(fake_lyrics))

        from autopilot.nodes.lyrics import lyrics_node

        concept = {"title": "봄의 잔상", "mood": "bittersweet", "theme": "이별", "style": "indie jazz"}
        result = lyrics_node(ctx, concept)

        # 반환값 형태 확인
        assert "lyrics_path" in result
        assert "sha256" in result
        assert len(result["sha256"]) == 64

        # 파일 실제 존재
        lyrics_path = Path(result["lyrics_path"])
        assert lyrics_path.exists()
        assert fake_lyrics in lyrics_path.read_text(encoding="utf-8")

    def test_artifact_store에_등록됨(self, ctx, tmp_path, monkeypatch):
        """artifact 테이블에 lyrics kind 로 등록되는지 확인."""
        monkeypatch.setenv("AUTOPILOT_DATA_DIR", str(tmp_path / "data"))

        import autopilot.nodes.lyrics as lyrics_mod
        monkeypatch.setattr(lyrics_mod, "call_claude", lambda *a, **kw: _fake_cli_result("가사"))

        from autopilot.nodes.lyrics import lyrics_node

        lyrics_node(ctx, {"title": "테스트곡"})

        arts = ctx.store.conn.execute(
            "SELECT * FROM artifacts WHERE run_id=? AND kind='lyrics'",
            (ctx.run_id,)
        ).fetchall()
        assert len(arts) == 1
        assert arts[0]["sha256"] != ""

    def test_trace_이벤트_기록됨(self, ctx, tmp_path, monkeypatch):
        """emit이 호출되어 trace.jsonl에 lyrics_done 이벤트가 기록된다."""
        monkeypatch.setenv("AUTOPILOT_DATA_DIR", str(tmp_path / "data"))

        import autopilot.nodes.lyrics as lyrics_mod
        monkeypatch.setattr(lyrics_mod, "call_claude", lambda *a, **kw: _fake_cli_result("가사"))

        trace_file = str(tmp_path / "trace.jsonl")

        import autopilot.trace as trace_mod
        emitted = []
        original_emit = trace_mod.emit

        def capture_emit(event, trace_path=None, **kw):
            emitted.append(event)
            original_emit(event, trace_path=trace_file)

        monkeypatch.setattr(trace_mod, "emit", capture_emit)

        from autopilot.nodes.lyrics import lyrics_node
        lyrics_node(ctx, {"title": "추적 테스트"})

        events = [e["event"] for e in emitted if "event" in e]
        assert "lyrics_done" in events

    def test_step_done_기록됨(self, ctx, tmp_path, monkeypatch):
        """@step 데코레이터가 step을 done으로 기록한다."""
        monkeypatch.setenv("AUTOPILOT_DATA_DIR", str(tmp_path / "data"))

        import autopilot.nodes.lyrics as lyrics_mod
        monkeypatch.setattr(lyrics_mod, "call_claude", lambda *a, **kw: _fake_cli_result("가사"))

        from autopilot.nodes.lyrics import lyrics_node
        lyrics_node(ctx, {"title": "step 테스트"})

        step_rec = ctx.store.get_step(ctx.run_id, "작사")
        assert step_rec is not None
        assert step_rec["status"] == "done"


# ---------------------------------------------------------------------------
# 2. suno_prompt_node
# ---------------------------------------------------------------------------

class TestSunoPromptNode:
    def test_프롬프트_파일_생성_및_artifact_등록(self, ctx, tmp_path, monkeypatch):
        """mock call_claude → 프롬프트 파일 저장 + artifact 등록."""
        monkeypatch.setenv("AUTOPILOT_DATA_DIR", str(tmp_path / "data"))

        fake_prompt = (
            "## Style of Music\n```\nKorean indie jazz, emotional dreamy, 92bpm\n```\n\n"
            "## Lyrics (Suno format)\n```\n[Verse 1]\n자꾸 그쪽 길로 돌아와\n```"
        )

        # suno_prompt.py 모듈의 로컬 call_claude 바인딩을 직접 패치한다.
        import autopilot.nodes.suno_prompt as sp_mod
        monkeypatch.setattr(sp_mod, "call_claude", lambda *a, **kw: _fake_cli_result(fake_prompt))

        # 가사 파일 준비
        lyrics_file = tmp_path / "lyrics.txt"
        lyrics_file.write_text("가사 내용", encoding="utf-8")

        from autopilot.nodes.suno_prompt import suno_prompt_node

        concept = {"title": "봄의 잔상", "mood": "bittersweet", "style": "indie jazz"}
        result = suno_prompt_node(ctx, concept, str(lyrics_file))

        assert "prompt_path" in result
        assert "sha256" in result
        assert len(result["sha256"]) == 64
        assert Path(result["prompt_path"]).exists()

    def test_전체_프롬프트_trace에_기록됨(self, ctx, tmp_path, monkeypatch):
        """trace에 'suno_prompt' event가 기록되고 prompt 필드를 포함한다."""
        monkeypatch.setenv("AUTOPILOT_DATA_DIR", str(tmp_path / "data"))

        fake_prompt = "## Style of Music\n```\nKorean jazz\n```\n\n## Lyrics (Suno format)\n```\n[Verse 1]\n테스트\n```"

        # suno_prompt.py가 'from autopilot.claude_cli import call_claude'로 로컬 바인딩하므로
        # 해당 모듈의 네임스페이스에서 직접 패치해야 한다.
        import autopilot.nodes.suno_prompt as sp_mod
        monkeypatch.setattr(sp_mod, "call_claude", lambda *a, **kw: _fake_cli_result(fake_prompt))

        lyrics_file = tmp_path / "lyrics.txt"
        lyrics_file.write_text("테스트 가사", encoding="utf-8")

        import autopilot.trace as trace_mod
        emitted = []
        original_emit = trace_mod.emit
        trace_file = str(tmp_path / "trace.jsonl")

        def capture_emit(event, trace_path=None, **kw):
            emitted.append(event)
            original_emit(event, trace_path=trace_file)

        monkeypatch.setattr(trace_mod, "emit", capture_emit)

        from autopilot.nodes.suno_prompt import suno_prompt_node
        suno_prompt_node(ctx, {"title": "테스트"}, str(lyrics_file))

        # suno_prompt 이벤트 찾기
        suno_events = [e for e in emitted if e.get("event") == "suno_prompt"]
        assert len(suno_events) >= 1

        suno_event = suno_events[0]
        # prompt 필드 존재 확인 (짧은 텍스트면 인라인, 길면 사이드카 dict)
        assert "prompt" in suno_event
        prompt_val = suno_event["prompt"]
        # 짧은 텍스트면 직접 문자열, 길면 {"__sidecar__": True, ...}
        if isinstance(prompt_val, dict):
            assert prompt_val.get("__sidecar__") is True
            assert "path" in prompt_val
            assert "sha256" in prompt_val
            # 사이드카 파일에 실제 내용이 있는지
            sidecar = Path(prompt_val["path"])
            assert sidecar.exists()
            assert "Korean jazz" in sidecar.read_text(encoding="utf-8")
        else:
            assert "Korean jazz" in prompt_val

    def test_artifact_store_등록됨(self, ctx, tmp_path, monkeypatch):
        monkeypatch.setenv("AUTOPILOT_DATA_DIR", str(tmp_path / "data"))

        import autopilot.nodes.suno_prompt as sp_mod
        monkeypatch.setattr(sp_mod, "call_claude", lambda *a, **kw: _fake_cli_result("프롬프트"))

        lyrics_file = tmp_path / "lyrics.txt"
        lyrics_file.write_text("가사", encoding="utf-8")

        from autopilot.nodes.suno_prompt import suno_prompt_node
        suno_prompt_node(ctx, {"title": "아티팩트 테스트"}, str(lyrics_file))

        arts = ctx.store.conn.execute(
            "SELECT * FROM artifacts WHERE run_id=? AND kind='suno_prompt'",
            (ctx.run_id,)
        ).fetchall()
        assert len(arts) == 1

    def test_step_done_기록됨(self, ctx, tmp_path, monkeypatch):
        monkeypatch.setenv("AUTOPILOT_DATA_DIR", str(tmp_path / "data"))

        import autopilot.nodes.suno_prompt as sp_mod
        monkeypatch.setattr(sp_mod, "call_claude", lambda *a, **kw: _fake_cli_result("프롬프트"))

        lyrics_file = tmp_path / "lyrics.txt"
        lyrics_file.write_text("가사", encoding="utf-8")

        from autopilot.nodes.suno_prompt import suno_prompt_node
        suno_prompt_node(ctx, {"title": "step 테스트"}, str(lyrics_file))

        step_rec = ctx.store.get_step(ctx.run_id, "Suno프롬프트")
        assert step_rec is not None
        assert step_rec["status"] == "done"


# ---------------------------------------------------------------------------
# 3. generate_node
# ---------------------------------------------------------------------------

class TestGenerateNode:
    def _make_prompt_file(self, tmp_path: Path, text: str | None = None) -> Path:
        """테스트용 Suno 프롬프트 파일을 생성한다."""
        content = text or (
            "## Style of Music\n```\nKorean indie jazz\n```\n\n"
            "## Lyrics (Suno format)\n```\n[Verse 1]\n자꾸 그쪽 길로\n```"
        )
        p = tmp_path / "suno_prompt.txt"
        p.write_text(content, encoding="utf-8")
        return p

    def _make_mock_client(self, tmp_path: Path, num_songs: int = 2):
        """가짜 SunoClient — generate() → URL 2개, download() → 임시 mp3 파일."""
        fake_urls = [f"https://suno.com/song/fake-{i}" for i in range(num_songs)]

        class FakeSunoClient:
            def __init__(self, *a, **kw):
                self.generate_call_count = 0
                self.download_call_count = 0

            def generate(self, lyrics, style, title="", **kw):
                self.generate_call_count += 1
                return fake_urls

            def download(self, url, output_path=None):
                self.download_call_count += 1
                idx = fake_urls.index(url)
                p = tmp_path / f"candidate_{idx:02d}.mp3"
                p.write_bytes(b"FAKEMP3DATA" * (idx + 1))
                return p

        return FakeSunoClient

    def test_v1v2_페어_모두_수집됨(self, ctx, tmp_path, monkeypatch):
        """generate() 가 반환하는 URL 2개가 모두 download돼 candidates에 포함된다."""
        monkeypatch.setenv("AUTOPILOT_DATA_DIR", str(tmp_path / "data"))

        FakeSunoClient = self._make_mock_client(tmp_path)
        monkeypatch.setattr("suno_client.SunoClient", FakeSunoClient)

        prompt_file = self._make_prompt_file(tmp_path)
        from autopilot.nodes.generate import generate_node
        result = generate_node(ctx, str(prompt_file))

        assert "candidates" in result
        assert len(result["candidates"]) == 2
        for cand in result["candidates"]:
            assert "path" in cand
            assert "sha256" in cand
            assert len(cand["sha256"]) == 64

    def test_멱등성_두번_호출_생성_한번만(self, ctx, tmp_path, monkeypatch):
        """같은 prompt_path로 두 번 호출해도 실제 generate()는 1회만 호출된다."""
        monkeypatch.setenv("AUTOPILOT_DATA_DIR", str(tmp_path / "data"))

        FakeSunoClient = self._make_mock_client(tmp_path)
        mock_client_instance = None
        original_init = FakeSunoClient.__init__

        # 클라이언트 인스턴스 추적
        instances = []

        class TrackedClient(FakeSunoClient):
            def __init__(self, *a, **kw):
                super().__init__(*a, **kw)
                instances.append(self)

        monkeypatch.setattr("suno_client.SunoClient", TrackedClient)

        prompt_file = self._make_prompt_file(tmp_path)

        from autopilot.nodes.generate import generate_node

        # 1회 호출
        result1 = generate_node(ctx, str(prompt_file))

        # step이 done 상태이므로 @step이 캐시 반환 (generate() 재호출 없음)
        # step 상태를 리셋해서 run_once 레벨 멱등성만 테스트
        # → step done이면 @step 자체가 fn 호출 안 함 (engine.py 설계)
        # → 그러므로 @step done 리셋 후 run_once가 차단하는지 테스트

        # step을 pending으로 돌려서 함수 진입은 허용
        ctx.store.conn.execute(
            "UPDATE steps SET status='pending' WHERE run_id=? AND step_name='생성'",
            (ctx.run_id,)
        )
        ctx.store.conn.commit()

        result2 = generate_node(ctx, str(prompt_file))

        # run_once 덕분에 generate_call_count 합계는 1이어야 함
        total_generate_calls = sum(inst.generate_call_count for inst in instances)
        assert total_generate_calls == 1, f"generate 호출 횟수={total_generate_calls}, 기대=1"

        # 두 결과는 동일해야 함
        assert result1["candidates"][0]["sha256"] == result2["candidates"][0]["sha256"]

    def test_artifact_audio_candidate_등록됨(self, ctx, tmp_path, monkeypatch):
        """각 오디오 후보가 artifact 테이블에 audio_candidate kind로 등록된다."""
        monkeypatch.setenv("AUTOPILOT_DATA_DIR", str(tmp_path / "data"))

        FakeSunoClient = self._make_mock_client(tmp_path)
        monkeypatch.setattr("suno_client.SunoClient", FakeSunoClient)

        prompt_file = self._make_prompt_file(tmp_path)
        from autopilot.nodes.generate import generate_node
        generate_node(ctx, str(prompt_file))

        arts = ctx.store.conn.execute(
            "SELECT * FROM artifacts WHERE run_id=? AND kind='audio_candidate'",
            (ctx.run_id,)
        ).fetchall()
        assert len(arts) == 2

    def test_step_done_기록됨(self, ctx, tmp_path, monkeypatch):
        monkeypatch.setenv("AUTOPILOT_DATA_DIR", str(tmp_path / "data"))

        FakeSunoClient = self._make_mock_client(tmp_path)
        monkeypatch.setattr("suno_client.SunoClient", FakeSunoClient)

        prompt_file = self._make_prompt_file(tmp_path)
        from autopilot.nodes.generate import generate_node
        generate_node(ctx, str(prompt_file))

        step_rec = ctx.store.get_step(ctx.run_id, "생성")
        assert step_rec is not None
        assert step_rec["status"] == "done"


# ---------------------------------------------------------------------------
# 4. prefilter_node
# ---------------------------------------------------------------------------

class TestPrefilterNode:
    def _mock_analyze_good(self):
        """통과하는 오디오 메트릭 반환."""
        return {"duration_sec": 180.0, "lufs": -16.0, "peak_dbfs": -3.0}, None

    def _mock_analyze_clipping(self):
        return {"duration_sec": 180.0, "lufs": -16.0, "peak_dbfs": -0.05}, "클리핑 (peak=-0.05 dBFS >= -0.1)"

    def _mock_analyze_silence(self):
        return {"duration_sec": 180.0, "lufs": -80.0, "peak_dbfs": -60.0}, "무음/거의 무음 (LUFS=-80.0 < -70.0)"

    def _mock_analyze_too_short(self):
        return {"duration_sec": 10.0}, "길이 너무 짧음 (10.0s < 30.0s)"

    def test_기술적_결함_제외_정상_통과(self, ctx, tmp_path, monkeypatch):
        """클리핑/무음/짧음 후보 제외, 정상 후보 통과 확인."""
        import autopilot.nodes.prefilter as pf_mod

        # 4개 후보 (경로는 없어도 되도록 _analyze를 통째로 mock)
        candidates = [
            {"path": str(tmp_path / "good.mp3"), "sha256": "aaa"},
            {"path": str(tmp_path / "clipping.mp3"), "sha256": "bbb"},
            {"path": str(tmp_path / "silence.mp3"), "sha256": "ccc"},
            {"path": str(tmp_path / "short.mp3"), "sha256": "ddd"},
        ]

        analyze_results = {
            str(tmp_path / "good.mp3"):     self._mock_analyze_good(),
            str(tmp_path / "clipping.mp3"): self._mock_analyze_clipping(),
            str(tmp_path / "silence.mp3"):  self._mock_analyze_silence(),
            str(tmp_path / "short.mp3"):    self._mock_analyze_too_short(),
        }

        # 파일을 실제로 만들어줘야 add_artifact가 통과
        for p in [tmp_path / "good.mp3", tmp_path / "clipping.mp3",
                  tmp_path / "silence.mp3", tmp_path / "short.mp3"]:
            p.write_bytes(b"FAKE")

        monkeypatch.setattr(pf_mod, "_analyze", lambda path: analyze_results[path])

        from autopilot.nodes.prefilter import prefilter_node
        result = prefilter_node(ctx, candidates)

        assert len(result["passed"]) == 1
        assert len(result["rejected"]) == 3
        assert result["passed"][0]["path"] == str(tmp_path / "good.mp3")

    def test_제외_이유는_기술적_원인만(self, ctx, tmp_path, monkeypatch):
        """rejected 항목의 reason이 기술적 결함(클리핑/무음/길이) 중 하나임을 확인.
        취향/컨셉 관련 reason은 없어야 한다."""
        import autopilot.nodes.prefilter as pf_mod

        technical_reasons = ["클리핑", "무음", "길이 너무 짧음", "파일 없음", "파일 손상"]

        bad_path = str(tmp_path / "bad.mp3")
        candidates = [{"path": bad_path, "sha256": "xxx"}]

        # 클리핑 시뮬레이션
        (tmp_path / "bad.mp3").write_bytes(b"FAKE")
        monkeypatch.setattr(pf_mod, "_analyze", lambda p: ({"peak_dbfs": -0.01}, "클리핑 (peak=-0.01 dBFS >= -0.1)"))

        from autopilot.nodes.prefilter import prefilter_node
        result = prefilter_node(ctx, candidates)

        for rej in result["rejected"]:
            reason = rej["reason"]
            # reason이 기술적 원인 중 하나로 시작해야 함
            assert any(r in reason for r in technical_reasons), \
                f"취향/컨셉 판단이 섞인 reason: {reason!r}"

    def test_metrics_trace_및_artifact_meta에_포함됨(self, ctx, tmp_path, monkeypatch):
        """metrics가 trace 이벤트와 artifact meta에 기록된다."""
        import autopilot.nodes.prefilter as pf_mod
        import autopilot.trace as trace_mod

        emitted = []
        original_emit = trace_mod.emit
        trace_file = str(tmp_path / "trace.jsonl")

        def capture_emit(event, trace_path=None, **kw):
            emitted.append(event)
            original_emit(event, trace_path=trace_file)

        monkeypatch.setattr(trace_mod, "emit", capture_emit)

        good_path = str(tmp_path / "good.mp3")
        (tmp_path / "good.mp3").write_bytes(b"FAKE")
        candidates = [{"path": good_path, "sha256": "aaa"}]

        good_metrics = {"duration_sec": 200.0, "lufs": -14.0, "peak_dbfs": -3.0}
        monkeypatch.setattr(pf_mod, "_analyze", lambda p: (good_metrics, None))

        from autopilot.nodes.prefilter import prefilter_node
        prefilter_node(ctx, candidates)

        # trace에 prefilter_candidate 이벤트 + metrics 포함
        cand_events = [e for e in emitted if e.get("event") == "prefilter_candidate"]
        assert len(cand_events) >= 1
        assert "metrics" in cand_events[0]
        assert cand_events[0]["metrics"]["duration_sec"] == 200.0

        # artifact meta에도 metrics 포함
        arts = ctx.store.conn.execute(
            "SELECT meta_json FROM artifacts WHERE run_id=? AND kind='prefilter_metrics'",
            (ctx.run_id,)
        ).fetchall()
        assert len(arts) >= 1
        meta = json.loads(arts[0]["meta_json"])
        assert "metrics" in meta

    def test_step_done_기록됨(self, ctx, tmp_path, monkeypatch):
        import autopilot.nodes.prefilter as pf_mod

        good_path = str(tmp_path / "good.mp3")
        (tmp_path / "good.mp3").write_bytes(b"FAKE")
        candidates = [{"path": good_path, "sha256": "aaa"}]

        monkeypatch.setattr(pf_mod, "_analyze", lambda p: ({"duration_sec": 200.0, "lufs": -14.0, "peak_dbfs": -3.0}, None))

        from autopilot.nodes.prefilter import prefilter_node
        prefilter_node(ctx, candidates)

        step_rec = ctx.store.get_step(ctx.run_id, "프리필터")
        assert step_rec is not None
        assert step_rec["status"] == "done"


# ---------------------------------------------------------------------------
# 5. postprocess + upload — Phase 4 stub 유지 확인
# ---------------------------------------------------------------------------

class TestPhase4Stubs:
    def test_postprocess_NotImplementedError(self):
        from autopilot.nodes.postprocess import postprocess
        with pytest.raises(NotImplementedError):
            postprocess("track.wav")

    def test_upload_NotImplementedError(self):
        from autopilot.nodes.upload import upload
        with pytest.raises(NotImplementedError):
            upload("track.mp4")
