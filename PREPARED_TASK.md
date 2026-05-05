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
| 5-17 | '무색무취의 빈병' 인스트루멘털 앨범 9곡 | P1 | PIPE-F03 완료 | Max Richter 중심(Nils Frahm/Ólafur Arnalds/Hania Rani/Joep Beving). 향수병 자아 컨셉, 가사 없음, 남성 보컬리즈 3곡(2/6/8). 컨셉 v0.3 완성 (`docs/albums/무색무취의빈병.md`) — 9트랙 BPM/키/편성/모티프 매핑 끝. PIPE-F03 병렬 생성으로 가속화 |
| 5-18 | '술병이 났다' 풀앨범 9곡 (3·3·3 동음 역설) | P1 | PIPE-F03 완료 | 같은 문장 "술병이 났다" 세 챕터 다른 의미. Part I 빈병(이별 비움) / Part II 몸병(숙취·신체화) / Part III 회복(졸업). 화자: 넥타이 머리 매고 참이슬 들이키는 한국 아저씨 클리셰. 한국어 가사. 1번↔9번 수미상관. 컨셉 v0.1 완성 (`docs/albums/술병이났다.md`). 장르 미정(트로트+시티팝/발라드+보사/재즈 발라드 후보). 5-17 후 또는 병행 |

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
