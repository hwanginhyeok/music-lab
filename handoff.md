# Handoff — 2026-06-14

## 무엇을 하고 있었나
PIPE-AUTO 음악제작 풀자동화 파이프라인 **전체 완성·배포·정리** (FSM코어 Phase2 → 노드 Phase3 → 후처리/영상/업로드 Phase4 → HTML저널 → 풀 파이프라인 조립 → F02 텔레그램 후보카드 → 실데이터 e2e → F13 2-pass loudnorm → F14 단일인스턴스 가드 → master 머지/배포/브랜치정리 → DIFFICULTY/메모리/ADMIN_CHAT_ID).

## 맥락 (이번 세션 결정)
- Suno 자동생성은 D-001 안티봇 벽으로 불가 재확인(캡차 풀어도 큐진입 0) → **프리필터부터 우회 운영**(실곡 주입).
- F14 flock single-instance + systemd-only(좀비봇 사고). 멀티봇 호스트는 pgrep -f 금지, cwd/cgroup 식별.
- 머지 검증은 PIPE-AUTO 경로 한정 two-dot diff=0. merge≠deploy(봇 재시작이 실배포).
- pytest 202, master e76952f, 라이브봇 F02/F14 가동.

## 다음 세션 첫 액션
**개발 작업 없음 — 형님 액션 2건 대기:**
1. run `86494cf1d566`에 텔레그램 **'올려'** → 실 YouTube unlisted 업로드(후처리/영상 산출물 준비됨, publish-gate가 그 전까지 업로드 0 유지).
2. **Suno 안티봇 자동생성 대응** 방향 결정(현재 수동/반자동 생성→다운로드 우회).
설계 SSOT: `plans/PIPE-AUTO.md`. 봇 운영은 systemd만(수동 python3 bot.py 금지).
