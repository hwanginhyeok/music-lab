# Music Lab 작업 규칙

## MIDI 생성 규칙
- Claude 응답에서 ```midi-json``` 블록 파싱
- pitch: MIDI 노트 번호 (60=C4)
- GM 악기 번호 준수
- 생성 실패 시 에러 메시지를 텔레그램으로 전송 (침묵 실패 금지)

## 봇 규칙
- .env의 토큰은 절대 로그/커밋에 포함하지 않음
- Claude CLI 호출 타임아웃: 120초
- 응답 전 "생각하는 중..." 메시지 전송 (UX)

## Suno 관련
- SUNO_COOKIE는 주기적으로 만료됨 — 갱신 필요 시 .env 수정
- suno_download.py의 Clerk JWT는 세션 쿠키에서 자동 발급
- generate API (곡 생성)는 불안정 — 수동 Suno 웹 생성 + 자동 다운로드 조합 권장

## 곡 디렉토리 규칙
- `songs/{번호}_{곡명}/` 형식
- 필수 파일: `concept.md`, `lyrics_v{N}.md`, `suno_prompt*.md`
- 템플릿: `songs/template/` 참고

## 서비스 운영
- 봇 코드 변경 후: `systemctl --user restart music-bot`
- 로그 확인: `journalctl --user -u music-bot -f`
- 서비스 중단 없이 DB만 변경하는 경우 재시작 불필요
