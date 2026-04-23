# Current Tasks

| # | 태스크 | 시작일 | blocked | 비고 |
|---|--------|--------|---------|------|
| 4-3 | "너를 다시" Suno 생성 + YouTube 게시 | 2026-04-23 | — | 컨셉/가사/프롬프트 완성. Suno 생성만 남음. 7-1과 연계 |
| 7-1 | YouTube 게시 문구 자동 생성 파이프라인 | 2026-04-23 | — | P1. 곡 메타 → Claude API → 제목/설명/해시태그/타임스탬프. Phase 1 CLI → Phase 2 텔레그램 /youtube_copy → Phase 3 uploader 자동 주입 |
| 6-1 | YouTube 관리 파이프라인 구축 | 2026-04-09 | — | /youtube_list(목록), /youtube_delete(삭제), 통계 기능 구현 |

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
