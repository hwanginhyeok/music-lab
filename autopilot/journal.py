"""
autopilot/journal.py — PIPE-AUTO HTML 저널 (Phase 5).

두 가지 책임:
  A) seed_sample_run(store, data_dir) — 샘플 앨범 시딩 (SQLite + trace.jsonl 직접)
  B) render(store, trace_path, out_dir) — Jinja2 HTML 렌더링

CLI:
  python3 -m autopilot.journal --seed --render
  python3 -m autopilot.journal --seed --render --db PATH --out DIR --trace PATH --data DATA_DIR
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from autopilot import trace as _trace
from autopilot.store import Store

# ---------------------------------------------------------------------------
# 샘플 앨범 상수
# ---------------------------------------------------------------------------

_ALBUM_SLUG = "샘플무색무취SAMPLE"

_SONGS = [
    {
        "title": "[SAMPLE] 새벽 세 시의 재즈",
        "mood": "쓸쓸하고 몽환적인, 새벽 감성",
        "theme": "이별 후 혼자 남겨진 새벽, 익숙한 공간이 낯설어지는 순간",
        "style": "contemporary jazz, bossa nova inflection, intimate piano trio",
        "bpm": 72,
    },
    {
        "title": "[SAMPLE] 안개 속의 색소폰",
        "mood": "그루비하고 애수 어린, 빗속 재즈바",
        "theme": "다시 돌아갈 수 없는 시간, 기억이 흐릿해지는 과정",
        "style": "jazz ballad, smoky tenor saxophone, walking bass, brushed drums",
        "bpm": 88,
    },
    {
        "title": "[SAMPLE] 마지막 블루스",
        "mood": "담담하고 깊은, 어쿠스틱 블루스 재즈",
        "theme": "모든 것이 끝난 뒤의 고요, 남겨진 것들과의 화해",
        "style": "jazz blues, fingerpicked acoustic guitar, upright bass, sparse",
        "bpm": 64,
    },
]

# 가사 샘플 (SAMPLE 표시 포함, 재즈 감성 한국어)
_LYRICS = [
    """\
[SAMPLE 가사 — 자동 생성 예시]

[Verse 1, Soft, Intimate]
불 꺼진 주방에 남은 온기가
당신 것인지 내 것인지 모르겠어
찻잔 하나가 식어가고 있어
새벽 세 시, 이 냄새가 낯설어

[Pre-Chorus, Build]
익숙했던 이 거리가
오늘은 왜 이렇게 길어

[Chorus, Emotional Vocal]
새벽 재즈가 흘러나와
창밖엔 안개만 가득해
당신 없는 이 공간에서
나 혼자 이 노래를 들어

[Verse 2, Intimate]
피아노 소리에 눈을 감으면
당신 웃음이 잠깐 보였다 사라져
그때 그 카페 구석 자리
우리가 처음 재즈를 들었던 밤

[Bridge, Build]
다시는 오지 않을 그날
기억 속에 고이 두기로 해
이 음악이 끝나면 나도
조용히 잠들 수 있을 것 같아

[Outro, Soft]
새벽 재즈가 흘러나와
당신 없어도 이 노래는 남아
""",
    """\
[SAMPLE 가사 — 자동 생성 예시]

[Verse 1, Smoky, Intimate]
안개 낀 골목 끝에서
색소폰 소리가 새어 나와
그게 당신 목소리 같아서
한참을 서 있었어

[Pre-Chorus]
지나간 것들은
항상 가장 아름다워 보이지

[Chorus, Emotional Vocal]
안개 속에서 당신을 찾아
흐릿한 기억의 가장자리에서
색소폰이 울고 있어
우리가 남긴 노래처럼

[Verse 2, Walking Tempo]
창문에 빗소리가 섞이고
재즈바 간판이 깜빡여
그 안에 있을 것만 같아서
문을 열었지만 당신이 없어

[Bridge, Emotional]
이제는 알아
돌아갈 수 없다는 걸
그래도 이 음악 속에서만큼은
잠깐 다시 만날 수 있어

[Outro]
안개가 걷혀도
이 노래는 남아 있어
""",
    """\
[SAMPLE 가사 — 자동 생성 예시]

[Verse 1, Sparse, Acoustic]
기타 현 하나가 떨리고
먼지 쌓인 레코드가 돌아가
이 방에 남겨진 것들이
모두 당신 얘기를 하고 있어

[Pre-Chorus]
끝이 났다는 걸
이제는 알고 있어

[Chorus, Blues Feel]
마지막 블루스를 연주해
이별이 아니라 작별처럼
기타 소리에 실어서
고마웠다고 전할게

[Verse 2]
창밖에 해가 지고 있어
오늘도 당신 없이 지나가
괜찮다고 말하면서
사실은 아직 여기 있어

[Bridge, Emotional Build]
화해는 상대가 없어도
혼자서도 할 수 있다는 걸
이 블루스가 가르쳐줬어

[Outro, Fade]
마지막 블루스
마지막 블루스
""",
]

# Suno 프롬프트 샘플
_SUNO_PROMPTS = [
    """\
## Style of Music
```
contemporary jazz, bossa nova inflection, intimate piano trio, upright bass, brushed drums, melancholic, late night, emotional dreamy, 72 bpm
```

## Lyrics (Suno format)
```
[Intro]
(피아노 솔로, 부드럽게)

[Verse 1, Soft, Intimate]
불 꺼진 주방에 남은 온기가
당신 것인지 내 것인지 모르겠어
찻잔 하나가 식어가고 있어
새벽 세 시, 이 냄새가 낯설어

[Pre-Chorus, Build]
익숙했던 이 거리가
오늘은 왜 이렇게 길어

[Chorus, Emotional Vocal]
새벽 재즈가 흘러나와
창밖엔 안개만 가득해
당신 없는 이 공간에서
나 혼자 이 노래를 들어

[Verse 2, Intimate]
피아노 소리에 눈을 감으면
당신 웃음이 잠깐 보였다 사라져
그때 그 카페 구석 자리
우리가 처음 재즈를 들었던 밤

[Bridge, Build]
다시는 오지 않을 그날
기억 속에 고이 두기로 해
이 음악이 끝나면 나도
조용히 잠들 수 있을 것 같아

[Outro, Soft, Fade]
새벽 재즈가 흘러나와
당신 없어도 이 노래는 남아
```
""",
    """\
## Style of Music
```
jazz ballad, smoky tenor saxophone, walking bass, brushed drums, minor key, melancholic, atmospheric, emotional dreamy, 88 bpm
```

## Lyrics (Suno format)
```
[Intro]
(색소폰 인트로, 안개 낀 분위기)

[Verse 1, Smoky, Intimate]
안개 낀 골목 끝에서
색소폰 소리가 새어 나와
그게 당신 목소리 같아서
한참을 서 있었어

[Pre-Chorus]
지나간 것들은
항상 가장 아름다워 보이지

[Chorus, Emotional Vocal]
안개 속에서 당신을 찾아
흐릿한 기억의 가장자리에서
색소폰이 울고 있어
우리가 남긴 노래처럼

[Verse 2, Walking Tempo]
창문에 빗소리가 섞이고
재즈바 간판이 깜빡여
그 안에 있을 것만 같아서
문을 열었지만 당신이 없어

[Bridge, Emotional]
이제는 알아
돌아갈 수 없다는 걸
그래도 이 음악 속에서만큼은
잠깐 다시 만날 수 있어

[Outro, Fade]
안개가 걷혀도
이 노래는 남아 있어
```
""",
    """\
## Style of Music
```
jazz blues, fingerpicked acoustic guitar, upright bass, sparse arrangement, intimate, melancholic resolve, 64 bpm
```

## Lyrics (Suno format)
```
[Intro]
(기타 솔로, 핑거피킹)

[Verse 1, Sparse, Acoustic]
기타 현 하나가 떨리고
먼지 쌓인 레코드가 돌아가
이 방에 남겨진 것들이
모두 당신 얘기를 하고 있어

[Pre-Chorus]
끝이 났다는 걸
이제는 알고 있어

[Chorus, Blues Feel]
마지막 블루스를 연주해
이별이 아니라 작별처럼
기타 소리에 실어서
고마웠다고 전할게

[Verse 2]
창밖에 해가 지고 있어
오늘도 당신 없이 지나가
괜찮다고 말하면서
사실은 아직 여기 있어

[Bridge, Emotional Build]
화해는 상대가 없어도
혼자서도 할 수 있다는 걸
이 블루스가 가르쳐줬어

[Outro, Fade]
마지막 블루스
마지막 블루스
```
""",
]

# 후보 메트릭스 샘플 (각 곡 3개 후보, 1개는 탈락)
_CANDIDATE_METRICS = [
    [
        {"lufs": -14.2, "peak_dbfs": -1.8, "duration_sec": 187.3},
        {"lufs": -13.9, "peak_dbfs": -2.1, "duration_sec": 192.0},
        {"lufs": -15.1, "peak_dbfs": -1.5, "duration_sec": 18.4},  # 탈락: 길이 너무 짧음
    ],
    [
        {"lufs": -14.8, "peak_dbfs": -0.05, "duration_sec": 203.5},  # 탈락: 클리핑
        {"lufs": -13.7, "peak_dbfs": -2.4, "duration_sec": 198.1},
        {"lufs": -14.5, "peak_dbfs": -1.9, "duration_sec": 205.7},
    ],
    [
        {"lufs": -15.3, "peak_dbfs": -2.0, "duration_sec": 174.2},
        {"lufs": -14.1, "peak_dbfs": -1.6, "duration_sec": 168.9},
        {"lufs": -14.7, "peak_dbfs": -1.8, "duration_sec": 22.1},  # 탈락: 길이 너무 짧음
    ],
]

# 각 곡에서 선택된 후보 인덱스 (passed 배열 기준)
_SELECTED_TAKE_IDX = [0, 0, 1]

# 가짜 YouTube URL
_YOUTUBE_URLS = [
    "https://youtu.be/SAMPLE_a1b2c3d4",
    "https://youtu.be/SAMPLE_e5f6g7h8",
    "https://youtu.be/SAMPLE_i9j0k1l2",
]


# ---------------------------------------------------------------------------
# A) seed_sample_run
# ---------------------------------------------------------------------------

def seed_sample_run(store: Store, data_dir: str | Path) -> list[str]:
    """샘플 앨범을 SQLite + trace.jsonl에 직접 시딩한다.

    이미 동일 album_slug의 run이 존재하면 삭제 후 재생성 (멱등 실행).

    returns: 생성된 run_id 목록
    """
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)

    # 기존 샘플 run 정리 (멱등)
    existing_runs = store.conn.execute(
        "SELECT id FROM runs WHERE album_slug = ?", (_ALBUM_SLUG,)
    ).fetchall()
    for row in existing_runs:
        old_id = row["id"]
        store.conn.execute("DELETE FROM steps WHERE run_id = ?", (old_id,))
        store.conn.execute("DELETE FROM artifacts WHERE run_id = ?", (old_id,))
        store.conn.execute("DELETE FROM human_tasks WHERE run_id = ?", (old_id,))
        store.conn.execute("DELETE FROM runs WHERE id = ?", (old_id,))
    store.conn.commit()

    run_ids: list[str] = []

    # 타임스탬프 기준점 (순서가 있는 타임라인 확보)
    base_ts = time.time() - 7200  # 2시간 전 시작처럼 보이도록

    for song_idx, (song, lyrics_text, suno_prompt_text, candidate_metrics, selected_idx, yt_url) in enumerate(
        zip(_SONGS, _LYRICS, _SUNO_PROMPTS, _CANDIDATE_METRICS, _SELECTED_TAKE_IDX, _YOUTUBE_URLS)
    ):
        # 곡별 타임 오프셋 (40분 간격)
        song_offset = song_idx * 2400  # 40분

        run_id = store.create_run(_ALBUM_SLUG)
        run_ids.append(run_id)

        # run 시작
        store.conn.execute(
            "UPDATE runs SET created_at = ?, updated_at = ?, status = 'running' WHERE id = ?",
            (base_ts + song_offset, base_ts + song_offset, run_id),
        )
        store.conn.commit()

        run_dir = data_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        t = base_ts + song_offset  # 현재 시각 트래킹

        # ── 작사 ─────────────────────────────────────────────────────────────
        t_step_start = t
        t += 45  # 45초 소요

        lyrics_path = run_dir / "lyrics.txt"
        lyrics_path.write_text(lyrics_text, encoding="utf-8")
        lyrics_sha = hashlib.sha256(lyrics_text.encode()).hexdigest()

        store.conn.execute(
            """INSERT INTO steps (run_id, step_name, status, attempt, input_json, output_json, started_at, ended_at)
               VALUES (?, '작사', 'done', 1, ?, ?, ?, ?)""",
            (
                run_id,
                json.dumps({"concept": song}),
                json.dumps({"lyrics_path": str(lyrics_path), "sha256": lyrics_sha}),
                t_step_start, t,
            ),
        )
        store.conn.commit()
        store.add_artifact(run_id, "작사", "lyrics", str(lyrics_path), lyrics_sha)
        _trace.emit({
            "event": "lyrics_done",
            "run_id": run_id,
            "lyrics_path": str(lyrics_path),
            "sha256": lyrics_sha,
            "ts": t,
        })

        # ── Suno프롬프트 ──────────────────────────────────────────────────────
        t_step_start = t
        t += 30

        suno_prompt_path = run_dir / "suno_prompt.txt"
        suno_prompt_path.write_text(suno_prompt_text, encoding="utf-8")
        suno_sha = hashlib.sha256(suno_prompt_text.encode()).hexdigest()

        store.conn.execute(
            """INSERT INTO steps (run_id, step_name, status, attempt, input_json, output_json, started_at, ended_at)
               VALUES (?, 'Suno프롬프트', 'done', 1, ?, ?, ?, ?)""",
            (
                run_id,
                json.dumps({"concept": song, "lyrics_path": str(lyrics_path)}),
                json.dumps({"prompt_path": str(suno_prompt_path), "sha256": suno_sha}),
                t_step_start, t,
            ),
        )
        store.conn.commit()
        store.add_artifact(run_id, "Suno프롬프트", "suno_prompt", str(suno_prompt_path), suno_sha)
        _trace.emit({
            "event": "suno_prompt",
            "run_id": run_id,
            "prompt": suno_prompt_text,
            "prompt_path": str(suno_prompt_path),
            "sha256": suno_sha,
            "ts": t,
        })

        # ── 생성 ─────────────────────────────────────────────────────────────
        t_step_start = t
        t += 300  # 5분 소요

        candidates_out: list[dict] = []
        for cand_idx, metrics in enumerate(candidate_metrics):
            # 플레이스홀더 오디오 파일 (실제 오디오 없음 — SAMPLE)
            placeholder_path = run_dir / f"candidate_{cand_idx:02d}.mp3.txt"
            placeholder_content = (
                f"[SAMPLE PLACEHOLDER — 실제 오디오 없음]\n"
                f"곡: {song['title']}\n"
                f"후보 인덱스: {cand_idx}\n"
                f"예상 LUFS: {metrics.get('lufs', 'N/A')}\n"
                f"예상 길이: {metrics.get('duration_sec', 'N/A')}s\n"
            )
            placeholder_path.write_text(placeholder_content, encoding="utf-8")
            cand_sha = hashlib.sha256(placeholder_content.encode()).hexdigest()

            cand_url = f"https://suno.com/song/SAMPLE_{run_id}_{cand_idx:02d}"
            store.add_artifact(
                run_id, "생성", "audio_candidate", str(placeholder_path), cand_sha,
                meta={"url": cand_url, "index": cand_idx},
            )
            candidates_out.append({"path": str(placeholder_path), "sha256": cand_sha})

        store.conn.execute(
            """INSERT INTO steps (run_id, step_name, status, attempt, input_json, output_json, started_at, ended_at)
               VALUES (?, '생성', 'done', 1, ?, ?, ?, ?)""",
            (
                run_id,
                json.dumps({"prompt_path": str(suno_prompt_path)}),
                json.dumps({"candidates": candidates_out}),
                t_step_start, t,
            ),
        )
        store.conn.commit()
        _trace.emit({
            "event": "generate_done",
            "run_id": run_id,
            "candidate_count": len(candidates_out),
            "ts": t,
        })

        # ── 프리필터 ──────────────────────────────────────────────────────────
        t_step_start = t
        t += 60

        passed: list[dict] = []
        rejected: list[dict] = []
        for cand_idx, (cand, metrics) in enumerate(zip(candidates_out, candidate_metrics)):
            dur = metrics.get("duration_sec", 0)
            peak = metrics.get("peak_dbfs", -10.0)
            reason = None
            if dur < 30.0:
                reason = f"길이 너무 짧음 ({dur:.1f}s < 30.0s)"
            elif peak >= -0.1:
                reason = f"클리핑 (peak={peak:.2f} dBFS >= -0.1)"

            cand_with_metrics = {**cand, "metrics": metrics}
            store.add_artifact(
                run_id, "프리필터", "prefilter_metrics", cand["path"], cand["sha256"],
                meta={"metrics": metrics, "result": reason or "pass"},
            )
            _trace.emit({
                "event": "prefilter_candidate",
                "run_id": run_id,
                "path": cand["path"],
                "metrics": metrics,
                "result": reason or "pass",
                "ts": t + cand_idx * 5,
            })

            if reason is None:
                passed.append(cand_with_metrics)
            else:
                rejected.append({**cand_with_metrics, "reason": reason})

        store.conn.execute(
            """INSERT INTO steps (run_id, step_name, status, attempt, input_json, output_json, started_at, ended_at)
               VALUES (?, '프리필터', 'done', 1, ?, ?, ?, ?)""",
            (
                run_id,
                json.dumps({"candidates": candidates_out}),
                json.dumps({"passed": passed, "rejected": rejected}),
                t_step_start, t,
            ),
        )
        store.conn.commit()
        _trace.emit({
            "event": "prefilter_done",
            "run_id": run_id,
            "passed_count": len(passed),
            "rejected_count": len(rejected),
            "ts": t,
        })

        # ── human_task: selection ─────────────────────────────────────────────
        t += 10
        # 선택 대상: passed 목록
        selected_cand = passed[selected_idx] if selected_idx < len(passed) else passed[0]
        selection_payload = {
            "passed": [p["path"] for p in passed],
            "prompt": "어떤 테이크를 선택하시겠습니까?",
        }
        task_id_row = store.create_human_task(
            run_id, "selection", selection_payload, expires_at=t + 7 * 86400
        )
        # created_at 조정
        store.conn.execute(
            "UPDATE human_tasks SET created_at = ? WHERE id = ?", (t, task_id_row)
        )
        store.conn.commit()

        # 답변 (시뮬레이션 — 1분 후 선택)
        t += 60
        selection_answer = {
            "selected_path": selected_cand["path"],
            "selected_sha256": selected_cand["sha256"],
            "note": f"[SAMPLE] 테이크 {_SELECTED_TAKE_IDX[song_idx]} 선택 — LUFS {selected_cand['metrics'].get('lufs', 'N/A')} 기준",
        }
        store.answer_human_task(task_id_row, selection_answer)

        # ── 업로드 (Phase-4 플레이스홀더) ─────────────────────────────────────
        t_step_start = t
        t += 30

        upload_output = {
            "youtube_unlisted_url": yt_url,
            "status": "unlisted",
            "note": "[SAMPLE] Phase-4 플레이스홀더 — 실제 업로드 아님",
        }
        store.conn.execute(
            """INSERT INTO steps (run_id, step_name, status, attempt, input_json, output_json, started_at, ended_at)
               VALUES (?, '업로드', 'done', 1, ?, ?, ?, ?)""",
            (
                run_id,
                json.dumps({"selected_path": selected_cand["path"]}),
                json.dumps(upload_output),
                t_step_start, t,
            ),
        )
        store.conn.commit()
        store.add_artifact(
            run_id, "업로드", "youtube_unlisted", yt_url,
            hashlib.sha256(yt_url.encode()).hexdigest(),
            meta={"status": "unlisted", "sample": True},
        )
        _trace.emit({
            "event": "upload_done",
            "run_id": run_id,
            "youtube_url": yt_url,
            "ts": t,
        })

        # ── run 완료 ─────────────────────────────────────────────────────────
        store.conn.execute(
            "UPDATE runs SET status = 'done', updated_at = ? WHERE id = ?",
            (t, run_id),
        )
        store.conn.commit()

    _trace.flush()
    return run_ids


# ---------------------------------------------------------------------------
# B) render
# ---------------------------------------------------------------------------

_INDEX_TEMPLATE = """\
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PIPE-AUTO Journal</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: #0f0f14;
    color: #d4d4d8;
    font-family: 'Segoe UI', system-ui, sans-serif;
    font-size: 14px;
    padding: 24px;
  }
  h1 { font-size: 22px; color: #a78bfa; margin-bottom: 6px; }
  .subtitle { color: #71717a; margin-bottom: 28px; font-size: 12px; }
  .album-card {
    background: #18181b;
    border: 1px solid #3f3f46;
    border-radius: 10px;
    padding: 20px 24px;
    margin-bottom: 20px;
  }
  .album-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 14px;
  }
  .album-slug { font-size: 17px; font-weight: 700; color: #e4e4e7; }
  .sample-badge {
    background: #7c3aed;
    color: #fff;
    font-size: 10px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 4px;
    letter-spacing: 1px;
  }
  .song-list { display: flex; flex-direction: column; gap: 8px; }
  .song-row {
    background: #09090b;
    border: 1px solid #27272a;
    border-radius: 7px;
    padding: 10px 14px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .song-title { font-weight: 600; color: #c4b5fd; }
  .song-meta { color: #71717a; font-size: 12px; margin-top: 2px; }
  .status-done { color: #4ade80; }
  .status-failed { color: #f87171; }
  .status-running { color: #facc15; }
  .song-link {
    color: #818cf8;
    text-decoration: none;
    font-size: 12px;
    border: 1px solid #3730a3;
    padding: 3px 10px;
    border-radius: 5px;
  }
  .song-link:hover { background: #1e1b4b; }
  .stat-row { display: flex; gap: 20px; margin-top: 12px; color: #71717a; font-size: 12px; }
  .gen-note { margin-top: 18px; color: #52525b; font-size: 11px; border-top: 1px solid #27272a; padding-top: 10px; }
</style>
</head>
<body>
<h1>PIPE-AUTO Journal</h1>
<p class="subtitle">생성: {{ generated_at }} — canonical source: SQLite</p>

{% for album in albums %}
<div class="album-card">
  <div class="album-header">
    <span class="album-slug">{{ album.slug }}</span>
    {% if album.is_sample %}<span class="sample-badge">SAMPLE</span>{% endif %}
  </div>

  <div class="song-list">
  {% for run in album.runs %}
    <div class="song-row">
      <div>
        <div class="song-title">{{ run.title }}</div>
        <div class="song-meta">
          run_id: <code>{{ run.run_id }}</code> &nbsp;|&nbsp;
          상태: <span class="status-{{ run.status }}">{{ run.status }}</span> &nbsp;|&nbsp;
          {{ run.step_count }}개 스텝 &nbsp;|&nbsp;
          시작: {{ run.created_at_str }}
        </div>
      </div>
      <a class="song-link" href="{{ run.run_id }}/index.html">상세 보기 →</a>
    </div>
  {% endfor %}
  </div>

  <div class="stat-row">
    <span>총 {{ album.runs | length }}곡</span>
    <span>완료: {{ album.done_count }}곡</span>
    <span>실패: {{ album.failed_count }}곡</span>
  </div>
</div>
{% endfor %}

<p class="gen-note">이 저널은 자동 생성된 파일입니다. 원본: SQLite + trace.jsonl<br>
재생성: <code>python3 -m autopilot.journal --seed --render</code></p>
</body>
</html>
"""

_RUN_TEMPLATE = """\
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{ run_title }} — PIPE-AUTO Journal</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: #0f0f14;
    color: #d4d4d8;
    font-family: 'Segoe UI', system-ui, sans-serif;
    font-size: 14px;
    padding: 24px;
    max-width: 1100px;
    margin: 0 auto;
  }
  a { color: #818cf8; }
  h1 { font-size: 20px; color: #a78bfa; margin-bottom: 4px; }
  .breadcrumb { font-size: 12px; color: #71717a; margin-bottom: 20px; }
  .breadcrumb a { color: #6366f1; text-decoration: none; }
  .sample-badge {
    background: #7c3aed; color: #fff;
    font-size: 10px; font-weight: 700;
    padding: 2px 8px; border-radius: 4px; letter-spacing: 1px;
    vertical-align: middle; margin-left: 8px;
  }
  .section {
    background: #18181b;
    border: 1px solid #3f3f46;
    border-radius: 10px;
    padding: 18px 22px;
    margin-bottom: 18px;
  }
  .section-title {
    font-size: 13px;
    font-weight: 700;
    color: #a78bfa;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 12px;
  }
  /* timeline */
  .timeline { display: flex; flex-direction: column; gap: 10px; }
  .tl-item {
    background: #09090b;
    border: 1px solid #27272a;
    border-left: 3px solid #3730a3;
    border-radius: 6px;
    padding: 10px 14px;
  }
  .tl-item.done { border-left-color: #4ade80; }
  .tl-item.failed { border-left-color: #f87171; }
  .tl-item.running { border-left-color: #facc15; }
  .tl-header { display: flex; justify-content: space-between; align-items: center; }
  .tl-name { font-weight: 700; color: #e4e4e7; }
  .tl-status-done { color: #4ade80; font-size: 12px; }
  .tl-status-failed { color: #f87171; font-size: 12px; }
  .tl-meta { color: #71717a; font-size: 11px; margin-top: 4px; }

  details { margin-top: 8px; }
  summary { cursor: pointer; color: #818cf8; font-size: 12px; user-select: none; }
  summary:hover { color: #a78bfa; }
  .json-block {
    background: #09090b;
    border: 1px solid #27272a;
    border-radius: 5px;
    padding: 10px;
    margin-top: 6px;
    font-family: 'Cascadia Code', 'Fira Code', monospace;
    font-size: 11px;
    white-space: pre-wrap;
    word-break: break-all;
    color: #a1a1aa;
    max-height: 300px;
    overflow-y: auto;
  }

  /* lyrics / prompt */
  pre.content-block {
    background: #09090b;
    border: 1px solid #27272a;
    border-radius: 6px;
    padding: 14px;
    font-family: 'Cascadia Code', 'Fira Code', monospace;
    font-size: 12px;
    white-space: pre-wrap;
    word-break: break-word;
    color: #c4b5fd;
    line-height: 1.7;
  }

  /* metrics table */
  table { width: 100%; border-collapse: collapse; font-size: 12px; }
  th {
    background: #27272a; color: #a1a1aa;
    padding: 7px 10px; text-align: left;
    font-weight: 600; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px;
  }
  td { padding: 7px 10px; border-bottom: 1px solid #27272a; color: #d4d4d8; }
  tr.selected-row td { background: #1e1b4b; color: #c4b5fd; font-weight: 600; }
  tr.rejected-row td { background: #1c0a0a; color: #ef4444; }
  .badge-pass { background: #052e16; color: #4ade80; padding: 2px 7px; border-radius: 4px; font-size: 10px; }
  .badge-reject { background: #1c0a0a; color: #f87171; padding: 2px 7px; border-radius: 4px; font-size: 10px; }
  .badge-selected { background: #2e1065; color: #c4b5fd; padding: 2px 7px; border-radius: 4px; font-size: 10px; }

  /* audio placeholder */
  .audio-placeholder {
    background: #09090b;
    border: 1px dashed #3f3f46;
    border-radius: 6px;
    padding: 14px;
    color: #52525b;
    font-size: 12px;
    text-align: center;
  }
  .audio-placeholder .audio-label { color: #a1a1aa; font-weight: 600; margin-bottom: 4px; }

  /* youtube link */
  .yt-link {
    display: inline-block;
    background: #991b1b;
    color: #fef2f2;
    padding: 8px 18px;
    border-radius: 6px;
    text-decoration: none;
    font-weight: 700;
    font-size: 13px;
    margin-top: 4px;
  }
  .yt-link:hover { background: #7f1d1d; }
  .yt-note { color: #71717a; font-size: 11px; margin-top: 6px; }

  /* human selection */
  .selection-box {
    background: #0c1520;
    border: 1px solid #1e3a5f;
    border-radius: 7px;
    padding: 14px;
  }
  .selection-label { color: #60a5fa; font-weight: 700; font-size: 13px; margin-bottom: 6px; }
  .selection-detail { color: #93c5fd; font-size: 12px; font-family: monospace; }

  .gen-note { color: #3f3f46; font-size: 11px; margin-top: 24px; }
</style>
</head>
<body>
<div class="breadcrumb"><a href="../index.html">← 앨범 목록</a></div>
<h1>{{ run_title }}<span class="sample-badge">SAMPLE</span></h1>
<p style="color:#71717a;font-size:12px;margin-bottom:20px;">
  run_id: <code>{{ run_id }}</code> &nbsp;|&nbsp; album: {{ album_slug }} &nbsp;|&nbsp;
  상태: <strong style="color:{% if status == 'done' %}#4ade80{% else %}#f87171{% endif %}">{{ status }}</strong>
  &nbsp;|&nbsp; 시작: {{ created_at_str }} &nbsp;|&nbsp; 완료: {{ updated_at_str }}
</p>

<!-- 타임라인 -->
<div class="section">
  <div class="section-title">노드 타임라인</div>
  <div class="timeline">
  {% for step in steps %}
    <div class="tl-item {{ step.status }}">
      <div class="tl-header">
        <span class="tl-name">{{ loop.index }}. {{ step.step_name }}</span>
        <span class="tl-status-{{ step.status }}">{{ step.status }} (attempt {{ step.attempt }})</span>
      </div>
      <div class="tl-meta">
        시작: {{ step.started_at_str }} &nbsp;|&nbsp; 완료: {{ step.ended_at_str }}
        &nbsp;|&nbsp; 소요: {{ step.duration_str }}
      </div>
      <details>
        <summary>입력 보기</summary>
        <div class="json-block">{{ step.input_pretty }}</div>
      </details>
      <details>
        <summary>출력 보기</summary>
        <div class="json-block">{{ step.output_pretty }}</div>
      </details>
    </div>
  {% endfor %}
  </div>
</div>

<!-- 가사 전문 -->
{% if lyrics_text %}
<div class="section">
  <div class="section-title">가사 전문</div>
  <pre class="content-block">{{ lyrics_text }}</pre>
</div>
{% endif %}

<!-- Suno 프롬프트 전문 -->
{% if suno_prompt_text %}
<div class="section">
  <div class="section-title">Suno 프롬프트 전문</div>
  <pre class="content-block">{{ suno_prompt_text }}</pre>
</div>
{% endif %}

<!-- 후보 메트릭스 테이블 -->
{% if candidates %}
<div class="section">
  <div class="section-title">후보 메트릭스</div>
  <table>
    <thead>
      <tr>
        <th>#</th>
        <th>파일</th>
        <th>LUFS</th>
        <th>Peak dBFS</th>
        <th>길이(초)</th>
        <th>결과</th>
      </tr>
    </thead>
    <tbody>
    {% for cand in candidates %}
      <tr class="{% if cand.is_selected %}selected-row{% elif cand.is_rejected %}rejected-row{% endif %}">
        <td>{{ loop.index }}</td>
        <td style="font-family:monospace;font-size:11px;word-break:break-all;">{{ cand.filename }}</td>
        <td>{{ cand.lufs }}</td>
        <td>{{ cand.peak_dbfs }}</td>
        <td>{{ cand.duration_sec }}</td>
        <td>
          {% if cand.is_selected %}
            <span class="badge-selected">선택됨</span>
          {% elif cand.is_rejected %}
            <span class="badge-reject">{{ cand.reject_reason }}</span>
          {% else %}
            <span class="badge-pass">통과</span>
          {% endif %}
        </td>
      </tr>
    {% endfor %}
    </tbody>
  </table>

  <!-- 오디오 플레이스홀더 -->
  {% if selected_audio_path %}
  <div style="margin-top:14px;">
    <div class="audio-label" style="color:#a1a1aa;font-weight:600;margin-bottom:6px;">선택 테이크 (SAMPLE 플레이스홀더)</div>
    <div class="audio-placeholder">
      <div class="audio-label">🎵 {{ selected_audio_filename }}</div>
      <div>[SAMPLE] 실제 오디오 파일 없음 — Phase-4 구현 시 &lt;audio&gt; 태그 활성화</div>
      <div style="margin-top:6px;font-size:10px;color:#3f3f46;">경로: {{ selected_audio_path }}</div>
    </div>
  </div>
  {% endif %}
</div>
{% endif %}

<!-- YouTube 링크 -->
{% if youtube_url %}
<div class="section">
  <div class="section-title">YouTube Unlisted</div>
  <a class="yt-link" href="{{ youtube_url }}" target="_blank" rel="noopener">▶ YouTube에서 보기</a>
  <div class="yt-note">[SAMPLE] Phase-4 플레이스홀더 URL — 실제 업로드 아님 ({{ youtube_url }})</div>
</div>
{% endif %}

<!-- 휴먼 선택 -->
{% if selection %}
<div class="section">
  <div class="section-title">사람 선택 기록</div>
  <div class="selection-box">
    <div class="selection-label">선택된 테이크</div>
    <div class="selection-detail">{{ selection.selected_path }}</div>
    <div style="margin-top:8px;color:#60a5fa;font-size:12px;">{{ selection.note }}</div>
    <div style="margin-top:6px;color:#71717a;font-size:11px;">answered: {{ selection.answered_at }}</div>
  </div>
</div>
{% endif %}

<!-- 이벤트 타임라인 (trace.jsonl) -->
{% if trace_events %}
<div class="section">
  <div class="section-title">이벤트 타임라인 (trace.jsonl)</div>
  <table>
    <thead>
      <tr><th>시각</th><th>이벤트</th><th>상세</th></tr>
    </thead>
    <tbody>
    {% for ev in trace_events %}
      <tr>
        <td style="font-family:monospace;font-size:11px;white-space:nowrap;">{{ ev.ts_str }}</td>
        <td><code style="color:#c4b5fd;">{{ ev.event }}</code></td>
        <td style="font-family:monospace;font-size:10px;color:#71717a;word-break:break-all;">{{ ev.detail }}</td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
</div>
{% endif %}

<p class="gen-note">자동 생성 — <code>python3 -m autopilot.journal --seed --render</code></p>
</body>
</html>
"""


def _fmt_ts(ts: float | None) -> str:
    """유닉스 타임스탬프를 읽기 좋은 문자열로 변환한다."""
    if ts is None:
        return "—"
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def _fmt_duration(started: float | None, ended: float | None) -> str:
    """두 타임스탬프 차이를 초 단위로 표현한다."""
    if started is None or ended is None:
        return "—"
    secs = ended - started
    if secs < 60:
        return f"{secs:.1f}s"
    return f"{secs / 60:.1f}분"


def _safe_json_pretty(json_str: str | None) -> str:
    """JSON 문자열을 예쁘게 포맷한다. 실패 시 원본 반환."""
    if not json_str:
        return "(없음)"
    try:
        return json.dumps(json.loads(json_str), ensure_ascii=False, indent=2)
    except Exception:
        return json_str


def _load_trace_events(trace_path: str, run_id: str) -> list[dict]:
    """trace.jsonl에서 해당 run_id 이벤트만 읽는다."""
    events: list[dict] = []
    p = Path(trace_path)
    if not p.exists():
        return events
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
                if ev.get("run_id") == run_id:
                    events.append(ev)
            except Exception:
                pass
    return events


def _read_artifact_text(artifacts: list, kind: str) -> str | None:
    """artifacts 목록에서 kind에 맞는 첫 번째 파일을 읽어 반환한다."""
    for art in artifacts:
        if art["kind"] == kind:
            p = Path(art["path"])
            if p.exists():
                try:
                    return p.read_text(encoding="utf-8")
                except Exception:
                    return None
    return None


def render(store: Store, trace_path: str, out_dir: str | Path) -> None:
    """SQLite + trace.jsonl을 읽어 HTML 저널을 out_dir에 렌더링한다."""
    try:
        from jinja2 import Template
    except ImportError as e:
        raise RuntimeError("jinja2가 필요합니다: pip install jinja2") from e

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 모든 run 읽기
    all_runs = store.conn.execute(
        "SELECT * FROM runs ORDER BY album_slug, created_at"
    ).fetchall()

    # album 단위로 그룹핑
    albums_map: dict[str, dict] = {}
    for run in all_runs:
        slug = run["album_slug"]
        if slug not in albums_map:
            albums_map[slug] = {
                "slug": slug,
                "is_sample": "SAMPLE" in slug,
                "runs": [],
                "done_count": 0,
                "failed_count": 0,
            }
        step_count = store.conn.execute(
            "SELECT COUNT(*) as c FROM steps WHERE run_id = ?", (run["id"],)
        ).fetchone()["c"]

        # 곡 제목 추출 (작사 step input의 concept.title)
        lyrics_step = store.get_step(run["id"], "작사")
        title = slug
        if lyrics_step and lyrics_step["input_json"]:
            try:
                inp = json.loads(lyrics_step["input_json"])
                title = inp.get("concept", {}).get("title", slug)
            except Exception:
                pass

        albums_map[slug]["runs"].append({
            "run_id": run["id"],
            "title": title,
            "status": run["status"],
            "step_count": step_count,
            "created_at_str": _fmt_ts(run["created_at"]),
        })
        if run["status"] == "done":
            albums_map[slug]["done_count"] += 1
        elif run["status"] == "failed":
            albums_map[slug]["failed_count"] += 1

    # index.html
    index_tmpl = Template(_INDEX_TEMPLATE)
    index_html = index_tmpl.render(
        albums=list(albums_map.values()),
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
    (out_dir / "index.html").write_text(index_html, encoding="utf-8")

    # 각 run 상세 페이지
    for run in all_runs:
        run_id = run["id"]
        run_out = out_dir / run_id
        run_out.mkdir(parents=True, exist_ok=True)

        # 스텝 목록
        steps_rows = store.conn.execute(
            "SELECT * FROM steps WHERE run_id = ? ORDER BY started_at",
            (run_id,),
        ).fetchall()
        steps_data = []
        for s in steps_rows:
            steps_data.append({
                "step_name": s["step_name"],
                "status": s["status"],
                "attempt": s["attempt"],
                "started_at_str": _fmt_ts(s["started_at"]),
                "ended_at_str": _fmt_ts(s["ended_at"]),
                "duration_str": _fmt_duration(s["started_at"], s["ended_at"]),
                "input_pretty": _safe_json_pretty(s["input_json"]),
                "output_pretty": _safe_json_pretty(s["output_json"]),
            })

        # artifact 목록
        artifacts = store.conn.execute(
            "SELECT * FROM artifacts WHERE run_id = ?", (run_id,)
        ).fetchall()
        artifacts_list = [dict(a) for a in artifacts]

        # 가사 + Suno 프롬프트 텍스트
        lyrics_text = _read_artifact_text(artifacts_list, "lyrics")
        suno_prompt_text = _read_artifact_text(artifacts_list, "suno_prompt")

        # 후보 메트릭스 (프리필터 + 생성 조합)
        prefilter_step = store.get_step(run_id, "프리필터")
        generate_step = store.get_step(run_id, "생성")

        candidates_data: list[dict] = []
        selected_path: str | None = None
        youtube_url: str | None = None

        # human selection 정보
        selection_task = store.get_answered_human_task(run_id, "selection")
        selection_info: dict | None = None
        if selection_task:
            answer = json.loads(selection_task["answer_json"] or "{}")
            selected_path = answer.get("selected_path")
            selection_info = {
                "selected_path": selected_path or "—",
                "note": answer.get("note", ""),
                "answered_at": _fmt_ts(selection_task["created_at"]),
            }

        # 후보 목록 조합 (생성 출력에서 후보 경로, 프리필터 artifact에서 메트릭스)
        if generate_step and generate_step["output_json"]:
            gen_out = json.loads(generate_step["output_json"])
            candidates_raw = gen_out.get("candidates", [])
        else:
            candidates_raw = []

        # 프리필터 출력에서 passed/rejected 가져오기
        pf_passed_paths: set[str] = set()
        pf_rejected: dict[str, str] = {}  # path → reason
        pf_metrics: dict[str, dict] = {}  # path → metrics
        if prefilter_step and prefilter_step["output_json"]:
            pf_out = json.loads(prefilter_step["output_json"])
            for p in pf_out.get("passed", []):
                pf_passed_paths.add(p["path"])
                pf_metrics[p["path"]] = p.get("metrics", {})
            for r in pf_out.get("rejected", []):
                pf_rejected[r["path"]] = r.get("reason", "알 수 없음")
                pf_metrics[r["path"]] = r.get("metrics", {})

        for cand in candidates_raw:
            cpath = cand["path"]
            is_rejected = cpath in pf_rejected
            is_selected = (selected_path is not None and cpath == selected_path)
            metrics = pf_metrics.get(cpath, {})

            candidates_data.append({
                "filename": Path(cpath).name,
                "full_path": cpath,
                "lufs": f"{metrics.get('lufs', '—'):.1f}" if isinstance(metrics.get("lufs"), float) else "—",
                "peak_dbfs": f"{metrics.get('peak_dbfs', '—'):.2f}" if isinstance(metrics.get("peak_dbfs"), float) else "—",
                "duration_sec": f"{metrics.get('duration_sec', '—'):.1f}" if isinstance(metrics.get("duration_sec"), float) else "—",
                "is_rejected": is_rejected,
                "is_selected": is_selected,
                "reject_reason": pf_rejected.get(cpath, ""),
            })

        # 선택된 오디오 경로
        selected_audio_path = selected_path
        selected_audio_filename = Path(selected_path).name if selected_path else None

        # YouTube URL
        upload_step = store.get_step(run_id, "업로드")
        if upload_step and upload_step["output_json"]:
            up_out = json.loads(upload_step["output_json"])
            youtube_url = up_out.get("youtube_unlisted_url")

        # trace 이벤트
        raw_events = _load_trace_events(trace_path, run_id)
        trace_events_data = []
        for ev in raw_events:
            ts = ev.get("ts", 0)
            event_name = ev.get("event", "—")
            # 상세: 주요 필드만 추려서 표시 (ts/event/run_id 제외)
            detail_dict = {k: v for k, v in ev.items() if k not in ("ts", "event", "run_id")}
            # 사이드카 참조는 [sidecar]로 축약
            for k, v in list(detail_dict.items()):
                if isinstance(v, dict) and v.get("__sidecar__"):
                    detail_dict[k] = f"[sidecar: {v.get('path', '')}]"
            detail_str = json.dumps(detail_dict, ensure_ascii=False)
            if len(detail_str) > 200:
                detail_str = detail_str[:197] + "..."
            trace_events_data.append({
                "ts_str": _fmt_ts(ts),
                "event": event_name,
                "detail": detail_str,
            })

        # 곡 제목 (작사 step input에서)
        lyrics_step = store.get_step(run_id, "작사")
        run_title = run["album_slug"]
        if lyrics_step and lyrics_step["input_json"]:
            try:
                inp = json.loads(lyrics_step["input_json"])
                run_title = inp.get("concept", {}).get("title", run_title)
            except Exception:
                pass

        run_tmpl = Template(_RUN_TEMPLATE)
        run_html = run_tmpl.render(
            run_id=run_id,
            run_title=run_title,
            album_slug=run["album_slug"],
            status=run["status"],
            created_at_str=_fmt_ts(run["created_at"]),
            updated_at_str=_fmt_ts(run["updated_at"]),
            steps=steps_data,
            lyrics_text=lyrics_text,
            suno_prompt_text=suno_prompt_text,
            candidates=candidates_data,
            selected_audio_path=selected_audio_path,
            selected_audio_filename=selected_audio_filename,
            youtube_url=youtube_url,
            selection=selection_info,
            trace_events=trace_events_data,
        )
        (run_out / "index.html").write_text(run_html, encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI __main__
# ---------------------------------------------------------------------------

def _main() -> None:
    parser = argparse.ArgumentParser(
        description="PIPE-AUTO HTML 저널 — 시딩 + 렌더링"
    )
    parser.add_argument("--seed", action="store_true", help="샘플 앨범 시딩")
    parser.add_argument("--render", action="store_true", help="HTML 렌더링")
    parser.add_argument(
        "--db",
        default="data/autopilot/journal_sample.db",
        help="SQLite DB 경로 (기본: data/autopilot/journal_sample.db)",
    )
    parser.add_argument(
        "--out",
        default="runs",
        help="HTML 출력 디렉토리 (기본: runs/)",
    )
    parser.add_argument(
        "--trace",
        default=None,
        help="trace.jsonl 경로 (기본: logs/traces/trace.jsonl)",
    )
    parser.add_argument(
        "--data",
        default="data/autopilot",
        help="샘플 아티팩트 데이터 디렉토리 (기본: data/autopilot)",
    )
    args = parser.parse_args()

    # DB 부모 디렉토리 생성
    db_path = Path(args.db)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    store = Store(str(db_path))

    if args.trace is None:
        # store.py 기준 프로젝트 루트 로그 경로
        project_root = Path(__file__).parent.parent
        trace_path = str(project_root / "logs" / "traces" / "trace.jsonl")
    else:
        trace_path = args.trace

    if not args.seed and not args.render:
        print("사용법: python3 -m autopilot.journal --seed --render", file=sys.stderr)
        parser.print_help()
        sys.exit(1)

    run_ids: list[str] = []

    if args.seed:
        print(f"[시딩] DB: {args.db} | 데이터 디렉토리: {args.data}")
        run_ids = seed_sample_run(store, args.data)
        print(f"[시딩 완료] {len(run_ids)}개 run 생성")
        for rid in run_ids:
            print(f"  • run_id: {rid}")

    if args.render:
        print(f"[렌더링] 출력: {args.out} | trace: {trace_path}")
        render(store, trace_path, args.out)
        out_dir = Path(args.out)
        print(f"[렌더링 완료]")
        print(f"  • {out_dir / 'index.html'}")
        for run_id in run_ids:
            print(f"  • {out_dir / run_id / 'index.html'}")
        if not run_ids:
            # seed 없이 render만 했을 경우 목록 추출
            runs_in_db = store.conn.execute("SELECT id FROM runs").fetchall()
            for row in runs_in_db:
                p = out_dir / row["id"] / "index.html"
                if p.exists():
                    print(f"  • {p}")


if __name__ == "__main__":
    _main()
