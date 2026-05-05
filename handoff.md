# Handoff — 2026-05-05 (이전 세션 → 다음 세션)

> 다음 세션 시작 시 이 파일 읽고 컨텍스트 복구. 복구 끝나면 삭제.

## 작업 중이던 것

**5-18 술병이 났다 풀앨범** — 9트랙 v1/v2 Suno 생성까지 완료. 사용자 청취·선별 단계.

진행 상태:
- ✅ 컨셉 v0.3 (`docs/albums/술병이났다.md`) — Late-night smoky jazz, 색스 중심, 333 동음 역설, 9번 영어 남성 바리톤 (Gregory Porter 결)
- ✅ 작업 디렉토리 (`songs/18_sulbyeong_natda/`) — _INDEX.md / README.md / workflow.md / 9개 트랙 폴더
- ✅ Suno 9트랙 v1/v2 생성 (2026-05-05, 캡차 0회, 23분, 80 크레딧)
- ✅ visual_prompts.md v0.2 (tragicomic 강화 — Roy Andersson 결)
- ⏳ 사용자 산책하며 청취 → best take 픽 + Part III 가사 디벨롭 안 결정 대기
- ⏳ 사용자가 이미지 컨셉 더 고민 중

## 사용자 결정 대기 (다음 세션 첫 액션)

1. **5-18 트랙별 best take 결정** (v1 또는 v2)
   - Suno feed 가서 9 트랙 × 2 = 18곡 청취
   - 또는 로컬 `songs/18_sulbyeong_natda/tracks/{NN}/raw/v{1,2}.mp3`
2. **Part III 가사 디벨롭 안 선택** (산책 중 수정본 가져온다고 함)
   - 옵션 A: 회복 과정 4줄 다리 + "흉이 결국 살이 됐다" + "이자로 살기로 했다"
   - 옵션 B: 더 짧고 시적, 마지막 "갚으면 너도 사라질 테니"로 비틂
3. **이미지 톤 재검토** — visual_prompts v0.2(tragicomic)도 사용자가 제대로 안 나온다 함. 결과 보고 추가 수정 가능

## 컨텍스트 (이번 세션 결정 사항)

### 사용자 명시 피드백 (메모리/룰 반영됨)
- ✅ **재즈 채널 정체성** — 비-재즈 단독 제안 금지 (`memory: project_jazz_channel.md`)
- ✅ **GDrive는 md만** — mp3/wav/mp4 절대 안 올림. 음원은 사용자 Suno 직접 청취 (`docs/data-management.md` v0.2)
- ✅ **SSOT 강화** — 로컬이 SSOT, GDrive 단방향 미러, GDrive에서 직접 편집 금지
- ✅ **단일 장르, 정서 변화는 차원 변수로** — 5-18 333은 장르 변화 아님. 편성·색스 톤·BPM·키로 표현
- ✅ **9번 보컬: 영어 남성 굵은 바리톤** (한국어 여성 X) — Gregory Porter / Kurt Elling 결
- ✅ **"엽기/개그 추가"** — visual_prompts v0.2 tragicomic 톤 (사실적 사진은 유지, 연출이 darkly funny)

### 시스템 결정
- PIPE-F03 (asyncio 병렬 PoC) → **보류 결론**. 시리얼 + 프롬프트 최적화가 ROI 우월. 월 3 EP+ 시점에 멀티프로필 재검토
- PIPE-F11 신규 P1: suno_pipeline.py 폴링 v2 누락 정식 픽스 (현재 batch 스크립트 워크어라운드)
- 6-1 YouTube 관리 → blocked, P3 격하 검토 (2 발매로는 관리 도구 필요성 약함)
- 5-16 Art/Artist EP → P2 보류 (5-17 무색무취 후 재평가)

### VNC 운영 (D-004 학습)
- VNC URL SSOT: **PM `reference_vnc_setup.md`**
- 정상 URL: `https://desktop-plq9e0i.tailec5aa6.ts.net` (비번 `suno`)
- 메인 / 가 가끔 tailnet only로 빠짐 → 복구: `echo "0055" | sudo -S tailscale funnel --bg --set-path=/ http://127.0.0.1:6080`

## 파일 변경 요약 (이번 세션)

신규:
- `docs/albums/술병이났다.md` v0.3 (5-18 컨셉 SSOT)
- `docs/albums/INDEX.md` (앨범 인덱스)
- `docs/data-management.md` v0.2 (SSOT + GDrive md only 정책)
- `docs/poc/pipe_f03_report.md` (PIPE-F03 PoC 보고서)
- `songs/18_sulbyeong_natda/{_INDEX.md, README.md, workflow.md, visual_prompts.md, tracks/*/suno_prompt.md}`
- `songs/14_geuriumi/_INDEX.md`, `songs/01_봄이라고_부를게/_INDEX.md`
- `scripts/sync_gdrive.sh`, `scripts/batch_5-18_remaining.sh`

이동:
- `songs/02_너를_다시/` → `songs/archive/02_너를_다시/` (4-3 폐기)

수정:
- `CURRENT_TASK.md`, `PREPARED_TASK.md`, `FINISHED_TASK.md`, `TASK.md` — 태스크 흐름
- `DIFFICULTY.md` — D-004 (VNC tailnet only), D-005 (suno_pipeline 폴링 v2)
- `.gitignore` — credentials/ 추가
- `~/.claude/projects/-home-window11-music-lab/memory/MEMORY.md` — `project_jazz_channel.md` 등재
- `~/.claude/projects/-home-window11-music-lab/memory/project_suno_vnc_automation.md` — Tailscale URL 갱신

## 다음 세션 첫 액션

1. **5-18 사용자 청취 결과 확인** — 트랙별 best take + 재생성 필요한 트랙
2. **Part III 가사 디벨롭 확정** — 사용자 수정본 받은 후 `songs/18_sulbyeong_natda/youtube_description.md` 저장
3. **9번 영어 가사 lyricist 호출** — Gregory Porter 결, "I'm done" / "sober" 다중 의미
4. **이미지 결과 받아 추가 조정** (사용자가 진행)
5. (백그라운드 후보) PIPE-F11 정식 픽스 — suno_pipeline.py 폴링 로직

## Git 상태 (잔여 미커밋 — 이전 세션 산출물, Opus 손 X 영역)

- `suno_client.py` (5-14 작업 산출물)
- `scripts/probe_suno_*.py`, `dump_suno_dom.py`, `recover_album.py`, `health_check.py` 등
- `docs/features.md`
- `songs/14_geuriumi/cover_a.jpg`, `cover_b.jpg`
- `songs/14_geuriumi/tracks/*/raw/` (mp3는 .gitignore 됨)
- `songs/14_geuriumi/tracks/_tools/` (probe 결과물)

→ 다음 세션에서 사용자가 정리 결정. 코드 변경은 GLM 위임 필수.
