# Current Tasks

| # | 태스크 | 시작일 | blocked | 비고 |
|---|--------|--------|---------|------|
| 5-17 | 무색무취의 빈병 — 9트랙 생성 + best take 선별 | 2026-05-15 | — | Track 1~9 v1/v2 생성 완료(2026-05-15). 다음: 이동하며 청취 → best take 선별 → 후처리(-14 LUFS) → YouTube 게시 |
| 5-19 | Daylight Hours 후처리 + 발매 | 2026-05-10 | ⏸️ 보류 | 종팝 15곡. v1.mp3 완료(GDrive). 다음: best take 선별 → 후처리(-14 LUFS) → YouTube 게시 |
| 5-20 | Electric Feelings 후처리 + 발매 | 2026-05-10 | ⏸️ 보류 | 팝록 분기 15곡. v1.mp3 완료(GDrive). 다음: best take 선별 → 후처리(-14 LUFS) → YouTube 게시 |
| 7-1 | YouTube 게시 문구 자동 생성 파이프라인 | 2026-04-23 | — | P1. 곡 메타 → Claude API → 제목/설명/해시태그/타임스탬프. Phase 1 CLI → Phase 2 텔레그램 /youtube_copy → Phase 3 uploader 자동 주입 |

## 7-1 상세 스펙

### 범위
- (a) 곡 메타데이터(제목/컨셉/가사/장르/아트워크) → Claude API → YouTube 설명문 생성
- (b) 제목 템플릿: `{곡명} — {아티스트/프로젝트명}` 또는 `{앨범명} Track N: {곡명}`
- (c) 설명문 구성: 곡 소개 → 가사 → 크레딧(Suno 생성/후처리) → 앨범 안내 → 해시태그 → 라이선스
- (d) 해시태그 자동 생성 (장르/무드/키워드 기반 10~15개)
- (e) 타임스탬프 (멀티트랙 앨범 영상인 경우) 자동 생성
- (f) 썸네일 문구 (제목 2줄 요약) 옵션

### 입출력
- **입력**: 곡 디렉토리 (`songs/{NN}_{곡명}/` — 메타 json + lyrics md + suno prompt md + mix 결과)
- **출력**: `youtube_copy/{곡명}.md` + `{곡명}.json` (제목/설명/해시태그 구조화)

### 통합
- 텔레그램 봇 `/youtube_copy` 명령 (Suno 자연어 명령과 동일 패턴)
- `youtube_uploader` 스크립트가 이 결과를 자동 주입

### Phase 구분
- **Phase 1**: CLI 스크립트 — `python scripts/generate_youtube_copy.py <곡디렉토리>`
- **Phase 2**: 텔레그램 봇 명령 통합
- **Phase 3**: upload 파이프라인 자동 주입
