# Finished Tasks

## 2026-04

| # | 태스크 | 완료일 | 비고 |
|---|--------|--------|------|
| 4-4 | create_making_video.py | 04-07 | 스크린샷 슬라이드쇼 + edge-tts 나레이션 + BGM 합성 스크립트 |
| 1-5 | npx 버전 고정 @2.1.91 | 04-03 | 사일런트 브레이킹 체인지 방지 |
| 5-2 | Track 02 가사 수정 | 04-04 | "다시 만날 수 있으니까" → "떠올릴 수 있으니까" |
| 5-3 | 앨범 제목 확정 | 04-04 | 봄을 통해 너를 봄 (Seeing You Through Spring) |
| 1-6 | 텔레그램 봇 UX 6건 일괄 개선 | 04-04 | |
| 1-7 | 보안/안정성 이슈 6건 일괄 수정 | 04-04 | |
| 1-8 | defaultdict(Lock) 메모리 누수 방지 | 04-04 | MAX_USER_LOCKS 제한 |

## 2026-03

| # | 태스크 | 완료일 | 비고 |
|---|--------|--------|------|
| 1-1 | 텔레그램 봇 기본 동작 | 03-28 | CLI OAuth, 히스토리, per-user lock, semaphore |
| 1-2 | Claude CLI 히스토리 주입 POC | 03-28 | format_context로 멀티턴 대화 동작 |
| 1-3 | per-user rate limit | 03-28 | _user_locks + "처리 중" 메시지 |
| 1-4 | FluidSynth soundfont 경로 관리 | 03-28 | SOUNDFONT_PATH 환경변수 + 폴백 |
| 1-9 | 글로벌 동시성 캡 (Semaphore) | 03-28 | asyncio.Semaphore(2) |
| 1-10 | /remix용 midi_json 컬럼 | 03-28 | messages + ideas 테이블 |
| 3-6 | manifest.json 지원 | 03-30 | jazz_pipeline.py 메타데이터 자동 생성 |
| 3-7 | scripts/create_video.py | 03-30 | ffmpeg 이미지+오디오 → MP4 |
| 3-8 | scripts/generate_thumbnail.py | 03-30 | Pillow YouTube 썸네일 자동 생성 |
| 3-9 | scripts/youtube_upload.py | 03-30 | YouTube Data API v3 업로드 |
| 3-10 | scripts/publish.py | 03-30 | YouTube 게시 오케스트레이터 |
| 5-4 | 클래식 재즈 프리셋 추가 | 03-30 | jazz bar, bebop, vocal jazz standards |
| 5-5 | 워크플로우 템플릿 세트 | 03-30 | songs/template/ + workflow_guide.md |
| 5-6 | Suno 프롬프트 v3 + 컨템포러리 팝 | 03-30 | lo-fi 금지, indie band + emotional dreamy |
| 5-7 | 영어 번안 "I'll Call You Spring" | 03-30 | 언어유희 보존 (call/spring 이중 의미) |
| 3-11 | Suno 다운로드 파이프라인 | 03-31 | Clerk JWT → studio-api-prod.suno.com API |
| 3-12 | YouTube 업로드 end-to-end | 03-31 | 곡 다운로드 → MP4 → YouTube 성공 |
| 5-8 | lyrics_v2.md 삭제 | 03-31 | lyrics_v1.md 최종 확정본 |
| 5-9 | Suno 원스택 전환 | 03-29 | 후처리 파이프라인 삭제 (mix_stems.py, process.py) |
