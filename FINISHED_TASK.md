# Finished Tasks

## 2026-04

| # | 태스크 | 완료일 | 비고 |
|---|--------|--------|------|
| 5-1 | Jazz Suite 트랙별 Suno 생성+선별+앨범 영상 | 04-08 | 9트랙 v1/v2 품질 비교 → 베스트 선별 → 앨범 오디오(27:52) + 영상(89MB) + 챕터마커 |
| 5-10 | 싱글 최종본 확정 (fa7aabee) | 04-07 | 20개 버전 품질 분석 → 다이나믹 레인지 최대(16.5dB)+SRT 보유 버전 선택 |
| 3-13 | create_video.py/publish.py SRT 자막 지원 | 04-07 | --srt CLI 인자 + 자동 탐색(lyrics.srt) + cover.jpeg/png 폴백 |
| 3-14 | .env.example 생성 | 04-08 | 5개 키 placeholder |
| 5-11 | YouTube 설명문 작성 (hostless 참조) | 04-07 | 감성 산문 + 챕터마커 + 크레딧 구조 |
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
| 3-1 | 대화 히스토리 유지 (세션별) | 03-28 | format_context()로 멀티턴 대화. 1-2와 동시 구현 |
| 3-2 | Suno 연계 (가사+장르 → Suno 생성) | 03-31 | /suno 명령어 + suno_client.py. 3-11과 동시 구현 |
| 3-5 | MIDI 재생 (인라인 오디오) | 03-28 | audio.py → midi_to_audio() → OGG 텔레그램 전송 |
| 5-9 | Suno 원스택 전환 | 03-29 | 후처리 파이프라인 삭제 (mix_stems.py, process.py) |
