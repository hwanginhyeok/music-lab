# Music Lab 작업 규칙

## 코드 컨벤션
- 변수/함수명 영어, 주석/커밋 메시지 한국어
- Python 3.12+ type hints 사용
- MIDI 관련 코드는 midiutil 사용

## MIDI 생성 규칙
- Claude 응답에서 ```midi-json``` 블록 파싱
- pitch: MIDI 노트 번호 (60=C4)
- GM 악기 번호 준수
- 생성 실패 시 에러 메시지를 텔레그램으로 전송 (침묵 실패 금지)

## 봇 규칙
- .env의 토큰은 절대 로그/커밋에 포함하지 않음
- Claude CLI 호출 타임아웃: 120초
- 응답 전 "생각하는 중..." 메시지 전송 (UX)
