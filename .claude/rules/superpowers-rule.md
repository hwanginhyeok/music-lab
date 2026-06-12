# Superpowers 스킬 규칙

## 세션 시작 시 자동 로드

모든 Claude Code 세션 시작 시 `using-superpowers` 스킬을 **반드시** Skill 도구로 호출할 것.

## 작업 유형별 필수 프로세스

### 새 기능 / 기능 수정
1. **brainstorming** 스킬 호출 → 문제 분석 및 접근법 논의
2. **writing-plans** 스킬 호출 → 구현 계획 작성
3. **matt-tdd** 스킬 호출 → TDD 사이클로 구현 (Red → Green → Refactor)
4. **verification-before-completion** 스킬 호출 → 완료 전 검증

### 버그 수정
1. **systematic-debugging** 스킬 호출
2. 4단계 준수: 재현 → 원인 파악 → 수정 → 검증
3. 수정 후 verification-before-completion 실행

### 계획 수립
1. **brainstorming** → **writing-plans** → **executing-plans** 순서

## 스킬 호출 원칙

- Skill 도구 사용 (Read 도구로 직접 읽지 않음)
- 1% 가능성이라도 관련 스킬이 있으면 반드시 호출
- 프로세스 스킬을 먼저 (brainstorming, debugging), 구현 스킬을 나중에 (TDD)
- 체크리스트가 있으면 TodoWrite로 각 항목 추적

## 언어 규칙

- 한국어로 응답 (로그, 코멘트, 메시지 모두)
- 코드 변수명/함수명은 영어 유지
