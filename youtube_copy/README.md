# YouTube Copy

YouTube 게시용 제목/설명문/해시태그 생성 결과물.

## 템플릿
- `TEMPLATE_lyrics.md` — 가사 앨범용
- `TEMPLATE_instrumental.md` — 인스트루멘털 앨범용

## 형식 규칙
- **제목**: 앨범명만 (아티스트 표기 없음)
- **서문**: 사용자가 직접 작성 후 입력
- **트랙리스트**: `00:00 Track 01` 형식 (트랙명 없이 번호+시간만)
- **고정 해시태그**: `#BeAnalogue #황인혁` 모든 앨범 공통
- **AI 디스클로저**: 설명문 마지막 고정 (가사/인스트루멘털 문구 구분)

## 파일명 규칙
`{앨범명}.md` — 제목, 설명문, 해시태그, JSON 포함

## 생성 방법
`python scripts/generate_youtube_copy.py <곡디렉토리>` (7-1 파이프라인)
