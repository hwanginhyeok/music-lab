# Prepared Tasks

## P1

| # | 태스크 | 우선순위 | depends | 비고 |
|---|--------|----------|---------|------|
| PIPE-F05 | Drive 서비스 계정 JSON 수정 (버그) | P1 | user: GCP 발급 | `client_secrets.json`은 OAuth 포맷. GCP 콘솔 `music-lab-491900` → IAM → 서비스 계정 생성 → 키 JSON → `credentials/drive-sa.json` 저장 + `.env GOOGLE_CREDENTIALS_PATH` 갱신 |
| PIPE-F10 | YouTube OAuth refresh_token 자동 갱신 | P1 | — | 4-1에서 겪은 토큰 만료 재발 방지. 만료 7일 전 텔레그램 경고 + 재인증 링크 |
| PIPE-F01 | 품질 자동 분석 (quality analyzer) | P1 | — | pyloudnorm + librosa + essentia + Claude 멀티모달. `quality/{song_id}.json` 스코어 출력 |
| PIPE-F02 | 텔레그램 봇 /review 인라인 | P1 | PIPE-F01 | 6곡 카드 + 인라인 버튼(pick/extend/reject/edit). 픽 시 자동 F-04 큐 진입 |
| 2-1 | Phase 1: 코드 진행 이해 (1주) | P1 | — | Suno 연계 학습 커리큘럼 |
| 5-12 | Jazz Suite 후처리 (라우드니스 노멀라이즈) | P1 | 4-1 완료 | 트랙 간 볼륨 편차 보정 (-14 LUFS) — PIPE-F04 경량 경로 재사용 가능 |
| 5-17 | '무색무취의 빈병' 인스트루멘털 앨범 9곡 | P1 | — | Max Richter 중심(Nils Frahm/Ólafur Arnalds/Hania Rani/Joep Beving). 향수병 자아 컨셉, 가사 없음, 남성 보컬리즈 3곡(2/6/8). 컨셉 v0.3 완성 (`docs/albums/무색무취의빈병.md`) — 9트랙 BPM/키/편성/모티프 매핑 끝. PIPE-F03 병렬 생성으로 가속화 |
| PIPE-F11 | suno_pipeline 폴링 v2 누락 버그 수정 | P1 | — | Suno는 generate 1회당 v1/v2 두 곡 생성하는데 suno_pipeline.py 폴링이 첫 곡 완료 시점에 종료. v2는 사후 suno_download.py로 보충 중. batch 스크립트에서 회피 패턴 검증됨 — 정식 픽스 필요 |

## P2

| # | 태스크 | 우선순위 | depends | 비고 |
|---|--------|----------|---------|------|
| 5-16 | 'Art / Artist' 재즈 EP — 동음 역설 9곡 | P2 | — | **보류 (2026-05-05)**. Bill Evans 톤 Vol.2. 그리움 대상 'Art'(사람 이름) + 'artist'(화자 자아) 동음 역설. 영어 가사. 컨셉 초안 `songs/16_art_artist/concept_draft.md`. 5-17(무색무취) 후 재평가 |
| 2-2 | Phase 2: 멜로디 만들기 (1~2주) | P2 | 2-1 완료 | |
| 2-3 | Phase 3: 곡 구조 설계 (1~2주) | P2 | 2-2 완료 | |
| 3-3 | 코드 진행 시각화 (이미지 생성) | P2 | — | |

## P3

| # | 태스크 | 우선순위 | depends | 비고 |
|---|--------|----------|---------|------|
| 2-4 | Phase 4: DAW 프로덕션 입문 (2~4주) | P3 | 2-3 완료 | |
| 3-4 | 음성 메시지 입력 → 허밍 분석 | P3 | — | |
