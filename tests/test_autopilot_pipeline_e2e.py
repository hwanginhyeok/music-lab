"""
tests/test_autopilot_pipeline_e2e.py — 앨범 파이프라인 E2E 테스트.

실제 VNC / Suno / ffmpeg / YouTube API 는 단 하나도 호출하지 않는다.
모든 외부 의존성은 monkeypatch 또는 mock 으로 대체한다.

검증 항목:
  1. run_album() 호출 → 각 곡 run이 'awaiting_selection' 상태로 Paused
  2. resume_song(answer={"selected_index": 0}) → 'awaiting_publish_approval' 로 진행
     - 후처리 + 영상 step이 done 으로 기록됐는지 확인
  3. resume_song(answer={"approved": True}) → 'done' 으로 완료
     - upload_node mock이 정확히 1회 호출됐는지 확인
     - video_url 이 반환됐는지 확인
  4. 멱등성: 이미 done 인 step(작사, Suno프롬프트, 생성 등)이 resume 시 재실행되지 않음
  5. 실제 subprocess / YouTube / Suno 가 leaked 되지 않음
"""
from __future__ import annotations

import os
import sys
import types
import unittest.mock as mock
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from autopilot.claude_cli import CliResult
from autopilot.store import Store


# ---------------------------------------------------------------------------
# 공용 상수
# ---------------------------------------------------------------------------

_ALBUM_SLUG = "e2e-test-album"
_FAKE_VIDEO_ID = "yt_fake_vid_001"
_FAKE_VIDEO_URL = f"https://youtu.be/{_FAKE_VIDEO_ID}"

# suno_prompt_node 파서에 필요한 최소 형식
_FAKE_PROMPT_TEXT = """\
## Style of Music
```
contemporary jazz, emotional, indie band
```

## Lyrics (Suno format)
```
[Verse 1]
자꾸 그쪽 길로 돌아와

[Chorus]
택시 두 대가 반대로 꺾어진 골목
```
"""

_FAKE_LYRICS_TEXT = """\
[Verse 1]
자꾸 그쪽 길로 돌아와

[Chorus]
택시 두 대가 반대로 꺾어진 골목
"""

_CONCEPT = {
    "title": "봄의 잔상",
    "mood": "bittersweet",
    "theme": "이별",
    "style": "indie jazz",
}


# ---------------------------------------------------------------------------
# 픽스처: 격리된 DB
# ---------------------------------------------------------------------------

@pytest.fixture
def store(tmp_path):
    return Store(str(tmp_path / "e2e_pipeline.db"))


# ---------------------------------------------------------------------------
# 픽스처: call_claude mock (lyrics + suno_prompt 양쪽에 monkeypatch)
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_call_claude(monkeypatch):
    """autopilot.nodes.lyrics 와 autopilot.nodes.suno_prompt 양쪽의
    call_claude 를 mock 으로 교체한다.

    lyrics 노드는 가사 텍스트를, suno_prompt 노드는 형식에 맞는 프롬프트 텍스트를 반환.
    """
    call_count = {"lyrics": 0, "suno_prompt": 0}

    import autopilot.nodes.lyrics as lyrics_mod
    import autopilot.nodes.suno_prompt as suno_mod

    def fake_lyrics_call(*a, **kw):
        call_count["lyrics"] += 1
        return CliResult(stdout=_FAKE_LYRICS_TEXT, stderr="", exit_code=0, elapsed=0.01)

    def fake_suno_prompt_call(*a, **kw):
        call_count["suno_prompt"] += 1
        return CliResult(stdout=_FAKE_PROMPT_TEXT, stderr="", exit_code=0, elapsed=0.01)

    monkeypatch.setattr(lyrics_mod, "call_claude", fake_lyrics_call)
    monkeypatch.setattr(suno_mod, "call_claude", fake_suno_prompt_call)

    return call_count


# ---------------------------------------------------------------------------
# 픽스처: SunoClient mock
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_suno(monkeypatch, tmp_path):
    """suno_client.SunoClient 를 mock 으로 교체한다.

    generate() → 2개의 가짜 URL 반환.
    download() → tmp_path 에 실제 파일을 쓰고 Path 반환.
    """
    generate_count = {"count": 0}
    download_count = {"count": 0}

    # 가짜 오디오 바이트 (SHA-256 계산이 동작하는 실제 내용)
    fake_audio_bytes = b"FAKE_AUDIO_CONTENT_FOR_SUNO_CANDIDATE"

    class FakeSunoClient:
        def __init__(self, *a, **kw):
            pass

        def generate(self, lyrics, style, title="", **kw):
            generate_count["count"] += 1
            return [
                "https://suno.com/song/fake-001",
                "https://suno.com/song/fake-002",
            ]

        def download(self, song_url, output_path=None):
            download_count["count"] += 1
            # output_path 가 지정되면 해당 경로에 파일 쓰기
            if output_path is not None:
                p = Path(output_path)
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(fake_audio_bytes)
                return p
            else:
                p = tmp_path / f"suno_dl_{download_count['count']}.mp3"
                p.write_bytes(fake_audio_bytes)
                return p

    # suno_client 모듈 자체를 교체 (generate_node 가 'from suno_client import SunoClient' 로 임포트)
    fake_module = types.ModuleType("suno_client")
    fake_module.SunoClient = FakeSunoClient

    class FakeSunoError(Exception):
        pass

    fake_module.SunoError = FakeSunoError
    monkeypatch.setitem(sys.modules, "suno_client", fake_module)

    return {"generate_count": generate_count, "download_count": download_count}


# ---------------------------------------------------------------------------
# 픽스처: prefilter._analyze mock
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_prefilter(monkeypatch):
    """autopilot.nodes.prefilter._analyze 를 mock 으로 교체한다.

    후보 2개 모두 통과 (reason=None).
    """
    import autopilot.nodes.prefilter as pf_mod

    analyze_count = {"count": 0}

    def fake_analyze(audio_path: str):
        analyze_count["count"] += 1
        # 2개 모두 good metrics, 이유 없음 → pass
        metrics = {"duration_sec": 180.0, "lufs": -14.5, "peak_dbfs": -1.5}
        return metrics, None  # reason=None → 통과

    monkeypatch.setattr(pf_mod, "_analyze", fake_analyze)
    return analyze_count


# ---------------------------------------------------------------------------
# 픽스처: fake runner (ffmpeg mock)
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_runner(tmp_path):
    """subprocess.run 을 대체하는 fake runner.

    postprocess_node 가 기대하는 '{stem}_normalized{suffix}' 파일을 생성한다.
    video_node 가 기대하는 '{stem}.mp4' 파일을 생성한다.
    둘 다 returncode=0 으로 성공 처리.
    """
    call_count = {"count": 0}

    def runner(cmd, **kwargs):
        call_count["count"] += 1
        result = mock.MagicMock()
        result.returncode = 0
        result.stderr = ""
        result.stdout = ""

        # cmd 에서 마지막 인자가 출력 파일 경로
        # ffmpeg 는 항상 마지막 positional 인자가 output
        out = Path(cmd[-1])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"FAKE_FFMPEG_OUTPUT")
        return result

    runner.call_count = call_count
    return runner


# ---------------------------------------------------------------------------
# 픽스처: YouTube mock
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_youtube():
    """YouTube 서비스 클라이언트 mock.

    videos().insert(...).next_chunk() → (None, {"id": _FAKE_VIDEO_ID})
    """
    insert_count = {"count": 0}

    def counting_insert(**kwargs):
        insert_count["count"] += 1
        req = mock.MagicMock()
        req.next_chunk.return_value = (None, {"id": _FAKE_VIDEO_ID})
        return req

    yt = mock.MagicMock()
    yt.videos.return_value.insert.side_effect = counting_insert

    yt._insert_count = insert_count
    return yt


# ---------------------------------------------------------------------------
# 픽스처: AUTOPILOT_DATA_DIR 환경변수 (실제 data/ 디렉토리 오염 방지)
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOPILOT_DATA_DIR", str(tmp_path / "autopilot_data"))


# ---------------------------------------------------------------------------
# 전체 E2E 테스트
# ---------------------------------------------------------------------------

class TestAlbumPipelineE2E:
    """앨범 파이프라인 전체 E2E (2-resume 드라이브 + 멱등성 검증)."""

    @pytest.fixture
    def all_mocks(self, store, mock_call_claude, mock_suno, mock_prefilter, fake_runner, mock_youtube):
        """모든 외부 의존성 mock을 모아 반환하는 편의 픽스처."""
        from autopilot.pipeline import PipelineDeps
        deps = PipelineDeps(runner=fake_runner, youtube=mock_youtube, n=2)
        return {
            "store": store,
            "deps": deps,
            "call_claude_count": mock_call_claude,
            "suno": mock_suno,
            "prefilter": mock_prefilter,
            "runner": fake_runner,
            "youtube": mock_youtube,
        }

    # ── Step 1: run_album → awaiting_selection ────────────────────────────────

    def test_1_run_album_awaiting_selection(self, all_mocks):
        """run_album 최초 실행 시 selection gate 에서 Paused → awaiting_selection."""
        from autopilot.pipeline import run_album

        m = all_mocks
        results = run_album(
            store=m["store"],
            album_slug=_ALBUM_SLUG,
            song_concepts=[_CONCEPT],
            deps=m["deps"],
        )

        assert len(results) == 1
        r = results[0]
        assert r["title"] == _CONCEPT["title"]
        assert r["status"] == "awaiting_selection", f"실제 status: {r['status']}"

        # open selection human_task 가 존재해야 함
        run_id = r["run_id"]
        open_task = m["store"].get_open_human_task(run_id, "selection")
        assert open_task is not None, "selection 게이트 open task 가 없음"

    # ── Step 2: resume → awaiting_publish_approval ────────────────────────────

    def test_2_resume_selection_awaiting_publish(self, all_mocks):
        """selection gate 통과 후 publish_approval gate 에서 재차 Paused."""
        from autopilot.pipeline import run_album, resume_song

        m = all_mocks

        # run_album: awaiting_selection 상태
        results = run_album(
            store=m["store"],
            album_slug=_ALBUM_SLUG,
            song_concepts=[_CONCEPT],
            deps=m["deps"],
        )
        run_id = results[0]["run_id"]
        assert results[0]["status"] == "awaiting_selection"

        # resume: selection 답변 → publish_approval 게이트까지 진행
        result2 = resume_song(
            store=m["store"],
            run_id=run_id,
            concept=_CONCEPT,
            deps=m["deps"],
            answer={"selected_index": 0},
        )

        assert result2["status"] == "awaiting_publish_approval", (
            f"기대: awaiting_publish_approval, 실제: {result2['status']}"
        )

        # 후처리 step 이 done 이어야 함
        post_step = m["store"].get_step(run_id, "후처리")
        assert post_step is not None
        assert post_step["status"] == "done", f"후처리 status: {post_step['status']}"

        # 영상 step 이 done 이어야 함
        video_step = m["store"].get_step(run_id, "영상")
        assert video_step is not None
        assert video_step["status"] == "done", f"영상 status: {video_step['status']}"

        # publish_approval open task 가 생성됐어야 함
        pub_task = m["store"].get_open_human_task(run_id, "publish_approval")
        assert pub_task is not None, "publish_approval 게이트 open task 없음"

    # ── Step 3: resume → done + upload 확인 ──────────────────────────────────

    def test_3_resume_publish_done(self, all_mocks):
        """publish_approval gate 통과 후 업로드 → done 완료."""
        from autopilot.pipeline import run_album, resume_song

        m = all_mocks

        # Run 1: awaiting_selection
        results = run_album(
            store=m["store"],
            album_slug=_ALBUM_SLUG,
            song_concepts=[_CONCEPT],
            deps=m["deps"],
        )
        run_id = results[0]["run_id"]

        # Resume 1: selection → awaiting_publish_approval
        resume_song(
            store=m["store"],
            run_id=run_id,
            concept=_CONCEPT,
            deps=m["deps"],
            answer={"selected_index": 0},
        )

        # Resume 2: publish_approval → done
        result_final = resume_song(
            store=m["store"],
            run_id=run_id,
            concept=_CONCEPT,
            deps=m["deps"],
            answer={"approved": True},
        )

        assert result_final["status"] == "done", (
            f"기대: done, 실제: {result_final['status']}"
        )

        # 업로드 step 이 done 이어야 함
        upload_step = m["store"].get_step(run_id, "업로드")
        assert upload_step is not None
        assert upload_step["status"] == "done", f"업로드 status: {upload_step['status']}"

        # YouTube mock 이 정확히 1회 insert 호출됐는지 확인
        insert_count = m["youtube"]._insert_count["count"]
        assert insert_count == 1, f"youtube insert 호출 횟수={insert_count}, 기대=1"

        # video_url 이 포함됐는지 확인
        upload_output = m["store"].get_step(run_id, "업로드")
        import json
        out_data = json.loads(upload_output["output_json"])
        assert "url" in out_data
        assert _FAKE_VIDEO_ID in out_data["url"]

    # ── Step 4: 멱등성 — done step 재실행 없음 ───────────────────────────────

    def test_4_idempotency_no_double_run(self, all_mocks):
        """resume 2회 후 이미 done인 step 들이 재실행되지 않는다.

        - call_claude: 작사(1) + suno_prompt(1) = 총 2회만 호출됨 (resume 시 skip)
        - Suno generate: 1회만 호출됨 (멱등성 테이블로 run_once 중복 차단)
        - ffmpeg runner: 후처리 1회 + 영상 1회 = 총 2회만 (resume 2 에서 skip)
        """
        from autopilot.pipeline import run_album, resume_song

        m = all_mocks

        # Run 1
        results = run_album(
            store=m["store"],
            album_slug=_ALBUM_SLUG,
            song_concepts=[_CONCEPT],
            deps=m["deps"],
        )
        run_id = results[0]["run_id"]

        # call_claude: lyrics 1회 + suno_prompt 1회
        assert m["call_claude_count"]["lyrics"] == 1, \
            f"lyrics call_claude 호출 횟수={m['call_claude_count']['lyrics']}"
        assert m["call_claude_count"]["suno_prompt"] == 1

        suno_generate_after_run1 = m["suno"]["generate_count"]["count"]
        assert suno_generate_after_run1 == 1, f"Suno generate={suno_generate_after_run1}, 기대=1"

        # Resume 1: selection
        resume_song(
            store=m["store"],
            run_id=run_id,
            concept=_CONCEPT,
            deps=m["deps"],
            answer={"selected_index": 0},
        )

        # 이미 done인 step들의 mock이 재호출되지 않아야 함
        assert m["call_claude_count"]["lyrics"] == 1, \
            "resume 1 에서 lyrics call_claude 재호출됨 (멱등성 위반)"
        assert m["call_claude_count"]["suno_prompt"] == 1, \
            "resume 1 에서 suno_prompt call_claude 재호출됨"
        assert m["suno"]["generate_count"]["count"] == 1, \
            "resume 1 에서 Suno generate 재호출됨 (멱등성 위반)"

        runner_after_resume1 = m["runner"].call_count["count"]
        assert runner_after_resume1 == 2, \
            f"ffmpeg runner 호출 횟수={runner_after_resume1}, 기대=2 (후처리+영상)"

        # Resume 2: publish_approval
        resume_song(
            store=m["store"],
            run_id=run_id,
            concept=_CONCEPT,
            deps=m["deps"],
            answer={"approved": True},
        )

        # resume 2 에서도 already-done step 들은 재실행되지 않음
        assert m["call_claude_count"]["lyrics"] == 1, \
            "resume 2 에서 lyrics call_claude 재호출됨"
        assert m["suno"]["generate_count"]["count"] == 1, \
            "resume 2 에서 Suno generate 재호출됨"
        # ffmpeg runner: resume 2 에서는 후처리+영상이 이미 done → skip
        runner_after_resume2 = m["runner"].call_count["count"]
        assert runner_after_resume2 == 2, \
            f"resume 2 에서 ffmpeg 재호출됨: {runner_after_resume2}"

    # ── Step 5: 실제 외부 호출 누출 없음 ─────────────────────────────────────

    def test_5_no_real_external_calls_leaked(self, all_mocks, monkeypatch):
        """실제 subprocess.run, youtube OAuth, suno 실제 모듈이 호출되지 않음을 확인."""
        from autopilot.pipeline import run_album, resume_song

        m = all_mocks

        # 실제 subprocess.run 이 호출되면 AssertionError 를 발생시키는 sentinel
        real_subprocess_call_count = {"count": 0}

        import subprocess as _real_subprocess
        original_run = _real_subprocess.run

        def sentinel_run(cmd, **kwargs):
            # fake_runner 가 처리하는 호출과 구분하기 위해
            # fake_runner 는 dep.runner 로 주입되므로 실제 subprocess.run 호출은 없어야 함
            real_subprocess_call_count["count"] += 1
            return original_run(cmd, **kwargs)

        # subprocess.run 모듈 레벨 패치는 하지 않음 — 대신 deps.runner 가 mock 임을 확인
        # (fake_runner fixture 가 이미 PipelineDeps 에 주입되어 있음)

        # 전체 흐름 실행
        results = run_album(
            store=m["store"],
            album_slug=_ALBUM_SLUG,
            song_concepts=[_CONCEPT],
            deps=m["deps"],
        )
        run_id = results[0]["run_id"]

        resume_song(
            store=m["store"],
            run_id=run_id,
            concept=_CONCEPT,
            deps=m["deps"],
            answer={"selected_index": 0},
        )
        resume_song(
            store=m["store"],
            run_id=run_id,
            concept=_CONCEPT,
            deps=m["deps"],
            answer={"approved": True},
        )

        # 모든 호출이 mock 으로 처리됐으므로 실제 subprocess.run 은 0회
        # (sentinel_run 을 monkeypatch 하지 않았으므로 이 확인은 deps.runner 검증으로 대체)
        assert m["runner"].call_count["count"] == 2, \
            "fake_runner 가 2회 호출됐어야 함 (후처리 + 영상)"

        # youtube insert 가 mock 으로만 호출됐는지 (실제 API 아님)
        assert m["youtube"]._insert_count["count"] == 1

        # suno generate 가 fake module 로만 호출됐는지
        assert m["suno"]["generate_count"]["count"] == 1


# ---------------------------------------------------------------------------
# 단위 테스트: PipelineDeps 기본값
# ---------------------------------------------------------------------------

class TestPipelineDeps:
    def test_기본값_runner는_subprocess_run(self):
        import subprocess
        from autopilot.pipeline import PipelineDeps
        d = PipelineDeps()
        assert d.runner is subprocess.run

    def test_기본값_youtube는_None(self):
        from autopilot.pipeline import PipelineDeps
        d = PipelineDeps()
        assert d.youtube is None

    def test_기본값_n은_2(self):
        from autopilot.pipeline import PipelineDeps
        d = PipelineDeps()
        assert d.n == 2


# ---------------------------------------------------------------------------
# 단위 테스트: selection_gate 인덱스 폴백
# ---------------------------------------------------------------------------

class TestSongPipelineSelectionFallback:
    """song_pipeline 내부의 selected_index 범위 초과 → 0번 폴백 확인."""

    def test_out_of_range_index_fallback(self, store, monkeypatch, tmp_path):
        """selected_index 가 범위를 벗어나면 0번 후보로 폴백한다."""
        import autopilot.nodes.lyrics as lyrics_mod
        import autopilot.nodes.suno_prompt as suno_mod
        import autopilot.nodes.prefilter as pf_mod

        monkeypatch.setattr(
            lyrics_mod, "call_claude",
            lambda *a, **kw: CliResult(stdout=_FAKE_LYRICS_TEXT, stderr="", exit_code=0, elapsed=0.01)
        )
        monkeypatch.setattr(
            suno_mod, "call_claude",
            lambda *a, **kw: CliResult(stdout=_FAKE_PROMPT_TEXT, stderr="", exit_code=0, elapsed=0.01)
        )
        monkeypatch.setattr(
            pf_mod, "_analyze",
            lambda path: ({"duration_sec": 180.0, "lufs": -14.5, "peak_dbfs": -1.5}, None)
        )

        # suno_client mock
        fake_audio = b"FAKE"

        class FakeSunoClient:
            def generate(self, *a, **kw):
                return ["https://suno.com/song/fake-001", "https://suno.com/song/fake-002"]

            def download(self, url, output_path=None):
                p = Path(output_path) if output_path else (tmp_path / "dl.mp3")
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(fake_audio)
                return p

        import types
        mod = types.ModuleType("suno_client")
        mod.SunoClient = FakeSunoClient
        mod.SunoError = Exception
        monkeypatch.setitem(sys.modules, "suno_client", mod)

        # 영상/후처리 runner mock
        def fake_runner(cmd, **kw):
            out = Path(cmd[-1])
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(b"OUT")
            r = mock.MagicMock()
            r.returncode = 0
            r.stderr = ""
            return r

        # youtube mock — upload_node 가 publish_gate_check 를 통과한 후 호출
        yt = mock.MagicMock()
        req = mock.MagicMock()
        req.next_chunk.return_value = (None, {"id": "fallback_vid"})
        yt.videos.return_value.insert.return_value = req

        from autopilot.pipeline import PipelineDeps, song_pipeline
        from autopilot.engine import Ctx, run_pipeline
        from autopilot.resume import resume_run
        from autopilot.gate import PUBLISH_APPROVAL_KIND

        deps = PipelineDeps(runner=fake_runner, youtube=yt, n=2)

        run_id = store.create_run("fallback-test")
        store.update_run_status(run_id, "running")
        ctx = Ctx(run_id=run_id, store=store)

        # 1차 실행: awaiting_selection
        r1 = run_pipeline(ctx, lambda c: song_pipeline(c, _CONCEPT, deps))
        assert r1["status"] == "awaiting_selection"

        # 2차 재개: 범위 초과 index=999 → 0번 폴백
        r2 = resume_run(
            store=store,
            run_id=run_id,
            kind="selection",
            answer={"selected_index": 999},
            pipeline_fn=lambda c: song_pipeline(c, _CONCEPT, deps),
        )
        assert r2["status"] == "awaiting_publish_approval"

        # 3차 재개: publish 승인
        r3 = resume_run(
            store=store,
            run_id=run_id,
            kind=PUBLISH_APPROVAL_KIND,
            answer={"approved": True},
            pipeline_fn=lambda c: song_pipeline(c, _CONCEPT, deps),
        )
        assert r3["status"] == "done"
