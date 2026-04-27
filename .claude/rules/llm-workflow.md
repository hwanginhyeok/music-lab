# LLM 워크플로우 규칙 (be-a-studio)

## 핵심: Opus는 코드에 손 안 댄다

코드 분석/작성/수정/리팩토링 — 전부 GLM에 위임.
Opus는 지시 + 리뷰 + 사용자 보고만.

## GLM 위임 대상 (예외 없음)

- 코드 작성/수정
- 코드 분석 (파일 읽고 구조 파악)
- 테스트 생성
- 리팩토링
- 디버깅 (단순 에러)

## Opus가 하는 것

- 사용자와 대화
- 작업 플래닝/설계
- GLM 지시 프롬프트 작성
- GLM 결과 리뷰 → 사용자 보고
- 결과 부족 시 재지시 (직접 수정 X)
- 문서(md) 작성

## GLM 호출 방법

```bash
python3 ~/project-manager/scripts/glm_client.py \
    --prompt "분석할 내용" \
    --project be-a-studio \
    --feature 기능명
```

## 위반 시

Opus가 직접 Grep/Read로 코드 분석하거나, Edit/Write로 코드 수정하면 **아키텍처 위반**.
반드시 glm_client.py 경유.
