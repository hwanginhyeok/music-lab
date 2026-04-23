# Prepared Tasks

## P1

| # | 태스크 | 우선순위 | depends | 비고 |
|---|--------|----------|---------|------|
| PIPE-F05 | Drive 서비스 계정 JSON 수정 (버그) | P1 | user: GCP 발급 | `client_secrets.json`은 OAuth 포맷. GCP 콘솔 `music-lab-491900` → IAM → 서비스 계정 생성 → 키 JSON → `credentials/drive-sa.json` 저장 + `.env GOOGLE_CREDENTIALS_PATH` 갱신 |
| PIPE-F10 | YouTube OAuth refresh_token 자동 갱신 | P1 | — | 4-1에서 겪은 토큰 만료 재발 방지. 만료 7일 전 텔레그램 경고 + 재인증 링크 |
| PIPE-F04 | 후처리 체인 파이프라인 (postprocess.py) | P1 | user: 레퍼런스 곡 | Demucs(4-stem) + Pedalboard(vocal/bass/other 체인) + Matchering + ffmpeg loudnorm -14 LUFS. R-3: 레퍼런스 라이브러리 구성 필요 |
| PIPE-F01 | 품질 자동 분석 (quality analyzer) | P1 | — | pyloudnorm + librosa + essentia + Claude 멀티모달. `quality/{song_id}.json` 스코어 출력 |
| PIPE-F02 | 텔레그램 봇 /review 인라인 | P1 | F-01 | 6곡 카드 + 인라인 버튼(pick/extend/reject/edit). 픽 시 자동 F-04 큐 진입 |
| PIPE-F03 | Suno asyncio 병렬 생성 | P1 | PoC 검증 | R-1: 단일 JWT 동시 3요청 rate limit 검증 필수. PoC 후 탭/프로필 전략 결정 |
| 2-1 | Phase 1: 코드 진행 이해 (1주) | P1 | — | Suno 연계 학습 커리큘럼 |
| 5-12 | Jazz Suite 후처리 (라우드니스 노멀라이즈) | P1 | 4-1 완료 | 트랙 간 볼륨 편차 보정 (-14 LUFS) — PIPE-F04로 통합 예정 |
| 6-1 | YouTube 관리 파이프라인 구축 | P1 | — | (CURRENT 중복 — 정리 예정) /youtube_list/delete/통계 |
| ~~4-2~~ | ~~메이킹 영상 제작 (스크린샷 + TTS)~~ | ~~P1~~ | — | **취소됨 (2026-04-23)** — 우선순위 제거. 스크립트(create_making_video.py)는 유지, 재개 시 사용 |

## P2

| # | 태스크 | 우선순위 | depends | 비고 |
|---|--------|----------|---------|------|
| 2-2 | Phase 2: 멜로디 만들기 (1~2주) | P2 | 2-1 완료 | |
| 2-3 | Phase 3: 곡 구조 설계 (1~2주) | P2 | 2-2 완료 | |
| 3-3 | 코드 진행 시각화 (이미지 생성) | P2 | — | |

## P3

| # | 태스크 | 우선순위 | depends | 비고 |
|---|--------|----------|---------|------|
| 2-4 | Phase 4: DAW 프로덕션 입문 (2~4주) | P3 | 2-3 완료 | |
| 3-4 | 음성 메시지 입력 → 허밍 분석 | P3 | — | |
