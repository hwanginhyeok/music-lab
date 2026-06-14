"""
autopilot Phase 4 테스트.

전부 mock 기반 — 실제 ffmpeg, YouTube API, 텔레그램 없음.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
import types
import unittest.mock as mock
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from autopilot.store import Store
from autopilot.engine import Ctx, Paused, run_pipeline, human_gate, step


# ---------------------------------------------------------------------------
# 공용 픽스처
# ---------------------------------------------------------------------------

@pytest.fixture
def store(tmp_path):
    return Store(str(tmp_path / "phase4_test.db"))


@pytest.fixture
def ctx(store):
    run_id = store.create_run("test-album")
    store.update_run_status(run_id, "running")
    return Ctx(run_id=run_id, store=store)


def _fake_runner_ok(cmd, **kwargs):
    """ffmpeg 성공 흉내."""
    result = mock.MagicMock()
    result.returncode = 0
    result.stderr = ""
    result.stdout = ""
    return result


def _fake_runner_fail(cmd, **kwargs):
    """ffmpeg 실패 흉내."""
    result = mock.MagicMock()
    result.returncode = 1
    result.stderr = "ffmpeg error: no such codec"
    result.stdout = ""
    return result


# ---------------------------------------------------------------------------
# 1. postprocess_node
# ---------------------------------------------------------------------------

class TestPostprocessNode:
    """후처리 노드: ffmpeg loudnorm mock 검증."""

    def test_2패스_loudnorm_명령_검증(self, ctx, tmp_path, monkeypatch):
        """2-패스: Pass1=측정(print_format=json), Pass2=측정값 기반 적용(linear)."""
        import autopilot.nodes.postprocess as pp_mod

        # 임시 오디오 파일 생성 (mock runner이므로 내용 무관)
        audio = tmp_path / "track.wav"
        audio.write_bytes(b"FAKEAUDIO")

        captured_cmds: list[list[str]] = []

        # Pass 1 measure JSON (ffmpeg loudnorm 출력 형식 모사).
        loudnorm_json = (
            "[Parsed_loudnorm_0 @ 0x55] \n"
            "{\n"
            '	"input_i" : "-14.10",\n'
            '	"input_tp" : "-1.20",\n'
            '	"input_lra" : "7.50",\n'
            '	"input_thresh" : "-24.30",\n'
            '	"output_i" : "-14.00",\n'
            '	"output_tp" : "-1.50",\n'
            '	"output_lra" : "7.40",\n'
            '	"output_thresh" : "-24.20",\n'
            '	"normalization_type" : "dynamic",\n'
            '	"target_offset" : "0.10"\n'
            "}\n"
        )

        def capturing_runner(cmd, **kwargs):
            captured_cmds.append(list(cmd))
            result = _fake_runner_ok(cmd, **kwargs)
            # Pass 1 (측정)에는 stderr에 JSON 제공.
            if "print_format=json" in " ".join(cmd):
                result.stderr = loudnorm_json
            return result

        # 출력 파일도 생성해 sha256 계산 통과
        normalized = tmp_path / "track_normalized.wav"
        normalized.write_bytes(b"NORMALIZED")

        from autopilot.nodes.postprocess import postprocess_node
        result = postprocess_node(ctx, str(audio), runner=capturing_runner)

        assert len(captured_cmds) == 2
        p1_cmd, p2_cmd = captured_cmds

        # Pass 1: 측정 명령 (print_format=json, null sink)
        p1_af = p1_cmd[p1_cmd.index("-af") + 1]
        assert "loudnorm" in p1_af
        assert "print_format=json" in p1_af
        assert "I=-14" in p1_af
        assert "TP=-1.5" in p1_af
        assert "LRA=11" in p1_af
        assert "null" in p1_cmd  # -f null -

        # Pass 2: 측정값 기반 정밀 적용
        p2_af = p2_cmd[p2_cmd.index("-af") + 1]
        assert "measured_I=-14.10" in p2_af
        assert "measured_TP=-1.20" in p2_af
        assert "measured_LRA=7.50" in p2_af
        assert "measured_thresh=-24.30" in p2_af
        assert "offset=0.10" in p2_af
        assert "linear=true" in p2_af
        assert "-ar" in p2_cmd  # 출력 샘플레이트
        # 고비트레이트 출력: 손실 인코딩 라우드니스 시프트 방지 (-14 LUFS 정밀도)
        assert "-b:a" in p2_cmd
        assert "320k" in p2_cmd

        # 반환값에 measured_i_pre 포함
        assert result["measured_i_pre"] == "-14.10"

    def test_2패스_artifact_trace_측정값_포함(self, ctx, tmp_path, monkeypatch):
        """2-패스 성공 시 artifact/trace에 measured 값이 기록된다."""
        import autopilot.trace as trace_mod

        audio = tmp_path / "track.wav"
        audio.write_bytes(b"FAKEAUDIO")
        normalized = tmp_path / "track_normalized.wav"
        normalized.write_bytes(b"NORMALIZED")

        loudnorm_json = (
            "{\n"
            '	"input_i" : "-14.10",\n'
            '	"input_tp" : "-1.20",\n'
            '	"input_lra" : "7.50",\n'
            '	"input_thresh" : "-24.30",\n'
            '	"target_offset" : "0.10"\n'
            "}\n"
        )

        def runner_2pass(cmd, **kwargs):
            result = _fake_runner_ok(cmd, **kwargs)
            if "print_format=json" in " ".join(cmd):
                result.stderr = loudnorm_json
            return result

        emitted = []
        original_emit = trace_mod.emit
        trace_file = str(tmp_path / "trace.jsonl")

        def capture_emit(event, trace_path=None, **kw):
            emitted.append(event)
            original_emit(event, trace_path=trace_file)

        monkeypatch.setattr(trace_mod, "emit", capture_emit)

        from autopilot.nodes.postprocess import postprocess_node
        postprocess_node(ctx, str(audio), runner=runner_2pass)

        # artifact meta에 측정값
        arts = ctx.store.conn.execute(
            "SELECT * FROM artifacts WHERE run_id=? AND kind='audio_mastered'",
            (ctx.run_id,)
        ).fetchall()
        meta = json.loads(arts[0]["meta_json"])
        assert meta["two_pass"] is True
        assert meta["measured_i"] == "-14.10"
        assert meta["measured_thresh"] == "-24.30"
        assert meta["measured_i_pre"] == "-14.10"

        # trace 이벤트에 measured_i_pre
        done = [e for e in emitted if e.get("event") == "postprocess_done"]
        assert done and done[0]["measured_i_pre"] == "-14.10"

    def test_측정_파싱_실패시_1패스_폴백(self, ctx, tmp_path):
        """Pass1 stderr에 JSON이 없으면 1-패스로 폴백(measured_I 없음), 크래시 없음."""
        audio = tmp_path / "track.wav"
        audio.write_bytes(b"FAKEAUDIO")
        normalized = tmp_path / "track_normalized.wav"
        normalized.write_bytes(b"NORMALIZED")

        captured_cmds: list[list[str]] = []

        def runner_no_json(cmd, **kwargs):
            captured_cmds.append(list(cmd))
            result = _fake_runner_ok(cmd, **kwargs)
            # JSON 없는 stderr (측정 출력 깨짐 모사)
            if "print_format=json" in " ".join(cmd):
                result.stderr = "ffmpeg version 6.0\nNo JSON here at all.\n"
            return result

        from autopilot.nodes.postprocess import postprocess_node
        result = postprocess_node(ctx, str(audio), runner=runner_no_json)

        # Pass1(측정) + Pass2(1-패스 폴백) — 단, 폴백 적용 명령은 measured_I 없음
        # 적용 명령 후보: print_format=json 없는 명령
        apply_cmds = [c for c in captured_cmds if "print_format=json" not in " ".join(c)]
        assert len(apply_cmds) == 1
        apply_cmd = apply_cmds[0]
        af = apply_cmd[apply_cmd.index("-af") + 1]
        assert "loudnorm" in af
        assert "measured_I" not in af  # 1-패스 폴백
        assert "linear=true" not in af

        # 폴백이므로 measured_i_pre는 None
        assert result["measured_i_pre"] is None
        assert result["lufs_target"] == -14

    def test_반환_형태(self, ctx, tmp_path):
        """postprocess_node 반환값에 path, sha256, lufs_target 포함."""
        audio = tmp_path / "track.wav"
        audio.write_bytes(b"FAKEAUDIO")

        normalized = tmp_path / "track_normalized.wav"
        normalized.write_bytes(b"NORMALIZED")

        from autopilot.nodes.postprocess import postprocess_node
        result = postprocess_node(ctx, str(audio), runner=_fake_runner_ok)

        assert "path" in result
        assert "sha256" in result
        assert "lufs_target" in result
        assert result["lufs_target"] == -14

    def test_artifact_audio_mastered_등록됨(self, ctx, tmp_path):
        """artifact 테이블에 audio_mastered kind로 등록된다."""
        audio = tmp_path / "track.wav"
        audio.write_bytes(b"FAKEAUDIO")

        normalized = tmp_path / "track_normalized.wav"
        normalized.write_bytes(b"NORMALIZED")

        from autopilot.nodes.postprocess import postprocess_node
        postprocess_node(ctx, str(audio), runner=_fake_runner_ok)

        arts = ctx.store.conn.execute(
            "SELECT * FROM artifacts WHERE run_id=? AND kind='audio_mastered'",
            (ctx.run_id,)
        ).fetchall()
        assert len(arts) == 1

        meta = json.loads(arts[0]["meta_json"])
        assert meta["target_lufs"] == -14

    def test_trace_이벤트_기록됨(self, ctx, tmp_path, monkeypatch):
        """postprocess_done 이벤트가 trace에 기록된다."""
        import autopilot.trace as trace_mod

        emitted = []
        original_emit = trace_mod.emit
        trace_file = str(tmp_path / "trace.jsonl")

        def capture_emit(event, trace_path=None, **kw):
            emitted.append(event)
            original_emit(event, trace_path=trace_file)

        monkeypatch.setattr(trace_mod, "emit", capture_emit)

        audio = tmp_path / "track.wav"
        audio.write_bytes(b"FAKEAUDIO")

        normalized = tmp_path / "track_normalized.wav"
        normalized.write_bytes(b"NORMALIZED")

        from autopilot.nodes.postprocess import postprocess_node
        postprocess_node(ctx, str(audio), runner=_fake_runner_ok)

        events = [e.get("event") for e in emitted]
        assert "postprocess_done" in events

    def test_step_done_기록됨(self, ctx, tmp_path):
        """@step 데코레이터가 '후처리' step을 done으로 기록한다."""
        audio = tmp_path / "track.wav"
        audio.write_bytes(b"FAKEAUDIO")

        normalized = tmp_path / "track_normalized.wav"
        normalized.write_bytes(b"NORMALIZED")

        from autopilot.nodes.postprocess import postprocess_node
        postprocess_node(ctx, str(audio), runner=_fake_runner_ok)

        step_rec = ctx.store.get_step(ctx.run_id, "후처리")
        assert step_rec is not None
        assert step_rec["status"] == "done"

    def test_ffmpeg_실패시_RuntimeError(self, ctx, tmp_path):
        """ffmpeg returncode != 0이면 RuntimeError가 발생한다."""
        audio = tmp_path / "track.wav"
        audio.write_bytes(b"FAKEAUDIO")

        from autopilot.nodes.postprocess import postprocess_node

        with pytest.raises(RuntimeError, match="ffmpeg"):
            postprocess_node(ctx, str(audio), runner=_fake_runner_fail)

    def test_deprecated_stub_NotImplementedError(self):
        """Phase 2 stub postprocess()는 NotImplementedError를 발생시킨다."""
        from autopilot.nodes.postprocess import postprocess
        with pytest.raises(NotImplementedError):
            postprocess("track.wav")


# ---------------------------------------------------------------------------
# 2. video_node
# ---------------------------------------------------------------------------

class TestVideoNode:
    """영상 생성 노드: ffmpeg mock 검증."""

    def test_mp4_artifact_등록됨(self, ctx, tmp_path):
        """video kind artifact가 등록된다."""
        audio = tmp_path / "track_normalized.wav"
        audio.write_bytes(b"FAKEAUDIO")

        from autopilot.nodes.video import video_node
        result = video_node(ctx, str(audio), title="테스트 곡", runner=_fake_runner_ok)

        assert "path" in result
        assert "sha256" in result

        arts = ctx.store.conn.execute(
            "SELECT * FROM artifacts WHERE run_id=? AND kind='video'",
            (ctx.run_id,)
        ).fetchall()
        assert len(arts) == 1

    def test_커버_있으면_loop_모드_명령_사용됨(self, ctx, tmp_path):
        """커버 이미지가 있으면 -loop 1 을 포함하는 명령이 생성된다."""
        audio = tmp_path / "track.wav"
        audio.write_bytes(b"FAKEAUDIO")
        cover = tmp_path / "cover.jpg"
        cover.write_bytes(b"FAKEJPEG")

        captured: list[list[str]] = []

        def cap_runner(cmd, **kw):
            captured.append(list(cmd))
            return _fake_runner_ok(cmd)

        from autopilot.nodes.video import video_node
        video_node(ctx, str(audio), title="테스트", cover_path=str(cover), runner=cap_runner)

        assert len(captured) == 1
        cmd = captured[0]
        assert "-loop" in cmd and "1" in cmd

    def test_커버_없으면_검정배경_명령_사용됨(self, ctx, tmp_path):
        """커버 없으면 lavfi color=black 배경 명령이 생성된다."""
        audio = tmp_path / "track.wav"
        audio.write_bytes(b"FAKEAUDIO")

        captured: list[list[str]] = []

        def cap_runner(cmd, **kw):
            captured.append(list(cmd))
            return _fake_runner_ok(cmd)

        from autopilot.nodes.video import video_node
        video_node(ctx, str(audio), title="테스트", cover_path=None, runner=cap_runner)

        assert len(captured) == 1
        cmd_str = " ".join(captured[0])
        assert "lavfi" in cmd_str
        assert "black" in cmd_str

    def test_step_done_기록됨(self, ctx, tmp_path):
        """@step 데코레이터가 '영상' step을 done으로 기록한다."""
        audio = tmp_path / "track.wav"
        audio.write_bytes(b"FAKEAUDIO")

        from autopilot.nodes.video import video_node
        video_node(ctx, str(audio), title="테스트", runner=_fake_runner_ok)

        step_rec = ctx.store.get_step(ctx.run_id, "영상")
        assert step_rec is not None
        assert step_rec["status"] == "done"

    def test_trace_이벤트_기록됨(self, ctx, tmp_path, monkeypatch):
        """video_done 이벤트가 trace에 기록된다."""
        import autopilot.trace as trace_mod

        emitted = []
        original_emit = trace_mod.emit
        trace_file = str(tmp_path / "trace.jsonl")

        def capture_emit(event, trace_path=None, **kw):
            emitted.append(event)
            original_emit(event, trace_path=trace_file)

        monkeypatch.setattr(trace_mod, "emit", capture_emit)

        audio = tmp_path / "track.wav"
        audio.write_bytes(b"FAKEAUDIO")

        from autopilot.nodes.video import video_node
        video_node(ctx, str(audio), title="테스트", runner=_fake_runner_ok)

        events = [e.get("event") for e in emitted]
        assert "video_done" in events

    def test_ffmpeg_실패시_RuntimeError(self, ctx, tmp_path):
        """ffmpeg returncode != 0이면 RuntimeError가 발생한다."""
        audio = tmp_path / "track.wav"
        audio.write_bytes(b"FAKEAUDIO")

        from autopilot.nodes.video import video_node
        with pytest.raises(RuntimeError, match="ffmpeg"):
            video_node(ctx, str(audio), title="테스트", runner=_fake_runner_fail)


# ---------------------------------------------------------------------------
# 3. upload_node — Publish-Gate 테스트 (핵심)
# ---------------------------------------------------------------------------

class TestUploadNodeGate:
    """업로드 노드 게시 승인 게이트 검증."""

    def test_게이트_기본_차단됨(self, ctx, tmp_path):
        """승인 없이 upload_node를 호출하면 PublishGateBlocked가 발생한다.
        youtube mock이 절대 호출되지 않는다.
        """
        from autopilot.nodes.upload import upload_node
        from autopilot.gate import PublishGateBlocked

        video = tmp_path / "output.mp4"
        video.write_bytes(b"FAKEVIDEO")

        youtube_mock = mock.MagicMock()

        with pytest.raises(PublishGateBlocked):
            upload_node(ctx, str(video), title="테스트", youtube=youtube_mock)

        # youtube mock이 단 한 번도 호출되지 않아야 함
        youtube_mock.videos.assert_not_called()

    def test_게이트_차단시_step_failed_기록됨(self, ctx, tmp_path):
        """PublishGateBlocked 발생 시 @step이 failed를 기록한다."""
        from autopilot.nodes.upload import upload_node
        from autopilot.gate import PublishGateBlocked

        video = tmp_path / "output.mp4"
        video.write_bytes(b"FAKEVIDEO")

        with pytest.raises(PublishGateBlocked):
            upload_node(ctx, str(video), title="테스트", youtube=mock.MagicMock())

        step_rec = ctx.store.get_step(ctx.run_id, "업로드")
        assert step_rec is not None
        assert step_rec["status"] == "failed"

    def test_승인_후_업로드_성공(self, ctx, tmp_path):
        """approve_publish 후 upload_node가 성공하고 unlisted URL을 반환한다."""
        from autopilot.nodes.upload import upload_node
        from autopilot.gate import approve_publish

        # 승인 부여
        approve_publish(ctx.store, ctx.run_id)

        # YouTube mock 구성
        video = tmp_path / "output.mp4"
        video.write_bytes(b"FAKEVIDEO")

        fake_video_id = "abc123xyz"
        youtube_mock = _build_youtube_mock(fake_video_id)

        # step failed 기록 초기화 (첫 번째 PublishGateBlocked 테스트와 독립된 fixture이므로 불필요)
        result = upload_node(ctx, str(video), title="테스트 곡", youtube=youtube_mock)

        assert result["video_id"] == fake_video_id
        assert result["url"] == f"https://youtu.be/{fake_video_id}"
        assert result["privacy"] == "unlisted"

        # videos().insert()가 1회 호출됐는지 확인
        youtube_mock.videos.assert_called_once()

    def test_unlisted_privacyStatus_사용됨(self, ctx, tmp_path):
        """업로드 시 privacyStatus='unlisted'가 body에 포함된다."""
        from autopilot.nodes.upload import upload_node
        from autopilot.gate import approve_publish

        approve_publish(ctx.store, ctx.run_id)

        video = tmp_path / "output.mp4"
        video.write_bytes(b"FAKEVIDEO")

        captured_bodies: list[dict] = []

        def capture_insert(**kwargs):
            captured_bodies.append(kwargs.get("body", {}))
            req = mock.MagicMock()
            req.next_chunk.return_value = (None, {"id": "vid999"})
            return req

        youtube_mock = mock.MagicMock()
        youtube_mock.videos.return_value.insert.side_effect = capture_insert

        upload_node(ctx, str(video), title="테스트", youtube=youtube_mock)

        assert len(captured_bodies) == 1
        status_block = captured_bodies[0].get("status", {})
        assert status_block.get("privacyStatus") == "unlisted"

    def test_멱등성_두번_호출_insert_한번만(self, ctx, tmp_path):
        """같은 run_id + video_sha로 두 번 호출해도 videos().insert는 1회만 실행된다."""
        from autopilot.nodes.upload import upload_node
        from autopilot.gate import approve_publish

        approve_publish(ctx.store, ctx.run_id)

        video = tmp_path / "output.mp4"
        video.write_bytes(b"FAKEVIDEO")

        insert_call_count = [0]
        fake_video_id = "idempotent_id"

        def counting_insert(**kwargs):
            insert_call_count[0] += 1
            req = mock.MagicMock()
            req.next_chunk.return_value = (None, {"id": fake_video_id})
            return req

        youtube_mock = mock.MagicMock()
        youtube_mock.videos.return_value.insert.side_effect = counting_insert

        # 1차 호출
        result1 = upload_node(ctx, str(video), title="테스트", youtube=youtube_mock)

        # @step이 done을 기록했으므로 2차 호출은 캐시 반환 (insert 재호출 없음)
        result2 = upload_node(ctx, str(video), title="테스트", youtube=youtube_mock)

        assert insert_call_count[0] == 1, f"insert 호출 횟수={insert_call_count[0]}, 기대=1"
        assert result1["video_id"] == result2["video_id"]

    def test_artifact_youtube_unlisted_등록됨(self, ctx, tmp_path):
        """업로드 성공 시 youtube_unlisted kind artifact가 등록된다."""
        from autopilot.nodes.upload import upload_node
        from autopilot.gate import approve_publish

        approve_publish(ctx.store, ctx.run_id)

        video = tmp_path / "output.mp4"
        video.write_bytes(b"FAKEVIDEO")

        youtube_mock = _build_youtube_mock("art_vid_id")
        upload_node(ctx, str(video), title="테스트", youtube=youtube_mock)

        arts = ctx.store.conn.execute(
            "SELECT * FROM artifacts WHERE run_id=? AND kind='youtube_unlisted'",
            (ctx.run_id,)
        ).fetchall()
        assert len(arts) == 1
        assert arts[0]["path"] == "https://youtu.be/art_vid_id"

    def test_deprecated_stub_NotImplementedError(self):
        """Phase 2 stub upload()는 NotImplementedError를 발생시킨다."""
        from autopilot.nodes.upload import upload
        with pytest.raises(NotImplementedError):
            upload("video.mp4")


def _build_youtube_mock(video_id: str) -> mock.MagicMock:
    """지정 video_id를 반환하는 YouTube 서비스 mock을 생성한다."""
    yt = mock.MagicMock()
    req = mock.MagicMock()
    req.next_chunk.return_value = (None, {"id": video_id})
    yt.videos.return_value.insert.return_value = req
    return yt


# ---------------------------------------------------------------------------
# 4. gate.py 단위 테스트
# ---------------------------------------------------------------------------

class TestGate:
    """autopilot.gate 모듈 단위 테스트."""

    def test_PublishGateBlocked_예외_메시지(self):
        from autopilot.gate import PublishGateBlocked
        exc = PublishGateBlocked("run123")
        assert "run123" in str(exc)
        assert exc.run_id == "run123"

    def test_approve_publish_open_task_생성_및_answer(self, store):
        from autopilot.gate import approve_publish, PUBLISH_APPROVAL_KIND

        run_id = store.create_run("gate-test")
        approve_publish(store, run_id)

        answered = store.get_answered_human_task(run_id, PUBLISH_APPROVAL_KIND)
        assert answered is not None

        answer = json.loads(answered["answer_json"])
        assert answer["approved"] is True

    def test_approve_publish_open_task_재사용(self, store):
        """open task가 이미 있으면 새로 만들지 않고 answer한다."""
        from autopilot.gate import approve_publish, PUBLISH_APPROVAL_KIND

        run_id = store.create_run("gate-reuse")
        # 미리 open task 생성
        task_id = store.create_human_task(
            run_id, PUBLISH_APPROVAL_KIND, {}, expires_at=time.time() + 3600
        )

        approve_publish(store, run_id)

        # open task가 2개가 되면 안 됨 (재사용이므로 1개)
        all_tasks = store.conn.execute(
            "SELECT * FROM human_tasks WHERE run_id=? AND kind=?",
            (run_id, PUBLISH_APPROVAL_KIND)
        ).fetchall()
        assert len(all_tasks) == 1
        assert all_tasks[0]["status"] == "answered"

    def test_게이트_체크_미승인_시_예외(self, ctx):
        from autopilot.gate import publish_gate_check, PublishGateBlocked
        with pytest.raises(PublishGateBlocked):
            publish_gate_check(ctx)

    def test_게이트_체크_승인_후_통과(self, ctx):
        from autopilot.gate import publish_gate_check, approve_publish
        approve_publish(ctx.store, ctx.run_id)
        # 예외 없이 통과해야 함
        publish_gate_check(ctx)


# ---------------------------------------------------------------------------
# 5. resume.py 테스트
# ---------------------------------------------------------------------------

class TestResume:
    """autopilot.resume 모듈 테스트."""

    def _make_pipeline_with_gate(self, kind: str):
        """kind 게이트를 포함하는 테스트용 파이프라인 함수를 반환한다."""
        @human_gate(kind)
        def _gate(ctx_inner, *a, **kw):
            return {"gated": True}

        completed_steps: list[str] = []

        @step("사전단계")
        def _pre(ctx_inner):
            completed_steps.append("사전단계")
            return {"pre": "done"}

        @step("사후단계")
        def _post(ctx_inner):
            completed_steps.append("사후단계")
            return {"post": "done"}

        def pipeline(ctx_inner):
            _pre(ctx_inner)
            _gate(ctx_inner)
            _post(ctx_inner)

        return pipeline, completed_steps

    def test_첫_실행_Paused_awaiting(self, store):
        """인간 게이트에서 파이프라인이 Paused 상태로 멈춘다."""
        from autopilot.resume import resume_run

        run_id = store.create_run("resume-test")
        store.update_run_status(run_id, "running")
        ctx = Ctx(run_id=run_id, store=store)

        pipeline, completed_steps = self._make_pipeline_with_gate("test_gate")

        result = run_pipeline(ctx, pipeline)

        assert result["status"] == "awaiting_test_gate"
        # 사전단계는 완료됐어야 함
        assert "사전단계" in completed_steps
        # 사후단계는 아직 실행 안 됨
        assert "사후단계" not in completed_steps

    def test_resume_run_재개_후_done(self, store):
        """resume_run으로 gate를 통과하면 파이프라인이 done으로 완료된다."""
        from autopilot.resume import resume_run

        run_id = store.create_run("resume-done")
        store.update_run_status(run_id, "running")
        ctx = Ctx(run_id=run_id, store=store)

        pipeline, completed_steps = self._make_pipeline_with_gate("test_gate")

        # 1차 실행 → Paused
        run_pipeline(ctx, pipeline)
        assert "사후단계" not in completed_steps

        # resume_run으로 재개
        result = resume_run(
            store=store,
            run_id=run_id,
            kind="test_gate",
            answer={"choice": "yes"},
            pipeline_fn=pipeline,
        )

        assert result["status"] == "done"
        # 사후단계가 이제 실행됨
        assert "사후단계" in completed_steps

    def test_resume_run_완료_step_재실행_안됨(self, store):
        """resume 시 이미 완료된 step(@step done)은 재실행되지 않는다."""
        from autopilot.resume import resume_run

        pre_call_count = [0]
        post_call_count = [0]

        @step("카운팅사전")
        def _counted_pre(c):
            pre_call_count[0] += 1
            return {"counted": True}

        @human_gate("cnt_gate")
        def _gate(c):
            return {}

        @step("카운팅사후")
        def _counted_post(c):
            post_call_count[0] += 1
            return {"counted_post": True}

        def pipeline(c):
            _counted_pre(c)
            _gate(c)
            _counted_post(c)

        run_id = store.create_run("resume-skip")
        store.update_run_status(run_id, "running")
        ctx = Ctx(run_id=run_id, store=store)

        # 1차 실행
        run_pipeline(ctx, pipeline)
        assert pre_call_count[0] == 1

        # resume
        resume_run(store, run_id, "cnt_gate", {"yes": True}, pipeline)
        # 사전단계는 재실행되면 안 됨 (done → skip)
        assert pre_call_count[0] == 1, f"사전단계 재실행됨: {pre_call_count[0]}"
        assert post_call_count[0] == 1

    def test_list_awaiting_반환_형태(self, store):
        """list_awaiting이 awaiting_* 상태 run을 반환한다."""
        from autopilot.resume import list_awaiting

        run_id = store.create_run("awaiting-list")
        store.update_run_status(run_id, "awaiting_publish_approval")
        # open human_task 등록
        store.create_human_task(
            run_id, "publish_approval", {}, expires_at=time.time() + 3600
        )

        result = list_awaiting(store)

        assert len(result) >= 1
        found = [r for r in result if r["run_id"] == run_id]
        assert len(found) == 1
        assert found[0]["kind"] == "publish_approval"
        assert found[0]["status"] == "awaiting_publish_approval"

    def test_list_awaiting_done_run_미포함(self, store):
        """done 상태 run은 list_awaiting에 포함되지 않는다."""
        from autopilot.resume import list_awaiting

        run_id = store.create_run("done-run")
        store.update_run_status(run_id, "done")

        waiting = list_awaiting(store)
        run_ids = [w["run_id"] for w in waiting]
        assert run_id not in run_ids


# ---------------------------------------------------------------------------
# 6. 전체 통합: gate blocked → approve → upload (end-to-end mock)
# ---------------------------------------------------------------------------

class TestEndToEndUploadFlow:
    """게이트 차단 → 승인 → 업로드 전체 흐름 통합 테스트."""

    def test_차단_후_승인_후_업로드_성공(self, ctx, tmp_path):
        """초기 차단 → approve_publish → upload_node 성공 경로 전체 검증."""
        from autopilot.nodes.upload import upload_node
        from autopilot.gate import PublishGateBlocked, approve_publish

        video = tmp_path / "final.mp4"
        video.write_bytes(b"FINALVIDEO")

        youtube_mock = _build_youtube_mock("end_to_end_id")

        # 1. 차단 확인
        with pytest.raises(PublishGateBlocked):
            upload_node(ctx, str(video), title="End-to-End", youtube=youtube_mock)

        # @step은 3번까지 재시도 후 failed 기록 — 테스트를 위해 step을 pending으로 리셋
        ctx.store.conn.execute(
            "DELETE FROM steps WHERE run_id=? AND step_name='업로드'",
            (ctx.run_id,)
        )
        ctx.store.conn.commit()

        # 2. 승인
        approve_publish(ctx.store, ctx.run_id)

        # 3. 업로드 성공
        result = upload_node(ctx, str(video), title="End-to-End", youtube=youtube_mock)

        assert result["video_id"] == "end_to_end_id"
        assert "unlisted" in result["url"] or "youtu.be" in result["url"]
        assert result["privacy"] == "unlisted"
