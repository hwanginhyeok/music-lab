# Music Lab 태스크

## 현재 진행 중

| # | 작업 | 상태 | 비고 |
|---|------|------|------|
| 1-1 | 텔레그램 봇 기본 동작 확인 | 진행 | CLI OAuth 방식 |
| 1-2 | Phase 1 학습 커리큘럼 설계 | 예정 | 코드 진행 + Suno 연계 |
| 1-3 | MIDI 생성 품질 개선 | 예정 | 멀티트랙, 드럼, 베이스 |

## 사용자 액션 대기

| # | 작업 | 남은 사용자 액션 |
|---|------|-----------------|
| 1-1 | 봇 테스트 | 텔레그램에서 /start, /chord, /midi 테스트 |

## 작업 현황 (백로그)

| # | 카테고리 | 작업 | 우선순위 | 상태 |
|---|----------|------|----------|------|
| 2-1 | 학습 | Phase 1: 코드 진행 이해 (1주) | P1 | 예정 |
| 2-2 | 학습 | Phase 2: 멜로디 만들기 (1~2주) | P2 | 예정 |
| 2-3 | 학습 | Phase 3: 곡 구조 설계 (1~2주) | P2 | 예정 |
| 2-4 | 학습 | Phase 4: DAW 프로덕션 입문 (2~4주) | P3 | 예정 |
| 3-1 | 기능 | 대화 히스토리 유지 (세션별) | P1 | 예정 |
| 3-2 | 기능 | Suno 연계 (가사+장르 → Suno URL 생성) | P2 | 예정 |
| 3-3 | 기능 | 코드 진행 시각화 (이미지 생성) | P2 | 예정 |
| 3-4 | 기능 | 음성 메시지 입력 → 허밍 분석 | P3 | 예정 |
| 3-5 | 기능 | 생성된 MIDI 재생 (인라인 오디오) | P2 | 예정 |

## TODO (CEO 리뷰에서 도출, 2026-03-28)

| # | 작업 | 우선순위 | Effort | 비고 |
|---|------|----------|--------|------|
| T-1 | Claude CLI 히스토리 주입 POC 검증 | P0 | S | `claude -p`에 수동 히스토리 넣어 멀티턴 동작 확인. 실패 시 전체 플랜 재설계 |
| T-2 | per-user rate limit (동시 요청 lock) | P1 | S | 한 사용자의 요청 처리 중이면 "처리 중" 메시지. subprocess 폭발 방지 |
| T-3 | npx 버전 고정 | P2 | S | `@anthropic-ai/claude-code@x.x.x`으로 핀. 사일런트 브레이킹 체인지 방지 |
| T-4 | FluidSynth soundfont 경로 관리 | P2 | S | .env에 SOUNDFONT_PATH. ~140MB GM soundfont 필요. 미설치 시 .mid fallback |
| T-5 | Claude CLI `--bare` 플래그 추가 | P0 | S | `--bare --tools "" --no-session-persistence` 필수. CLAUDE.md 자동로딩 방지, 툴 비활성화(보안), 세션파일 누적 방지, cold start 단축 |
| T-6 | 글로벌 동시성 캡 (semaphore) | P2 | S | asyncio.Semaphore(2)로 전체 동시 Claude 프로세스 제한. 개발 중 메시지 연타 시 OOM 방지 |
| T-7 | /remix용 midi_json 컬럼 추가 | P1 | S | messages 테이블에 midi_json TEXT 컬럼. 원본 JSON 보존해야 /remix에서 재사용 가능 |

## 완료

| # | 작업 | 완료일 | 비고 |
|---|------|--------|------|
| N-0 | manifest.json 지원 (jazz_pipeline.py) | 2026-03-30 | 파이프라인 실행 시 곡 메타데이터 자동 생성 |
| N-1 | scripts/create_video.py | 2026-03-30 | ffmpeg로 이미지+오디오 -> MP4 영상 |
| N-2 | scripts/generate_thumbnail.py | 2026-03-30 | Pillow로 YouTube 썸네일 자동 생성 |
| N-3 | scripts/youtube_upload.py | 2026-03-30 | YouTube Data API v3 업로드 |
| N-4 | scripts/publish.py | 2026-03-30 | YouTube 게시 오케스트레이터 |
| N-5 | 클래식 재즈 프리셋 추가 | 2026-03-30 | jazz bar, bebop, vocal jazz standards 추가 / neo soul jazz 제거 |
| N-6 | 워크플로우 템플릿 세트 | 2026-03-30 | songs/template/ + workflow_guide.md |
| N-7 | Suno 프롬프트 v3 + 영어/한국어 contemporary pop | 2026-03-30 | lo-fi 금지, indie band + emotional dreamy 검증 |
| N-8 | 영어 번안 가사 "I'll Call You Spring" | 2026-03-30 | 언어유희 보존 (call=name/phone, spring=season) |
| N-9 | Suno 다운로드 파이프라인 (suno_download.py) | 2026-03-31 | Clerk JWT → studio-api-prod.suno.com API 직접 호출 |
| N-10 | YouTube 업로드 파이프라인 end-to-end | 2026-03-31 | 곡 다운로드 → MP4 변환 → YouTube 업로드 성공 |
| N-11 | lyrics_v2.md 삭제 | 2026-03-31 | lyrics_v1.md가 최종 확정본 |
| N-12 | Suno 원스택 전환 — 후처리 파이프라인 삭제 | 2026-03-29 | mix_stems.py, process.py, MIDI 데모 제거 |
