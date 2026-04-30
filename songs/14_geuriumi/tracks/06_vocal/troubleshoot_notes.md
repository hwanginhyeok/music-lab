# Troubleshoot Notes — 다음 발주 전 참고

## 사전 점검 false negative (2026-04-30)
**증상**: 발주 직전 환경 점검에서 "Xtigervnc 미실행, Chrome 9222 응답 없음" 보고했으나 실제로는 Xtigervnc:1이 04-26부터 떠있었고, 사용자가 VNC 클라이언트 Connect 직후 chrome-suno 프로필이 정상 기동.

**원인**: `pgrep -af "Xvnc\|Xtigervnc"` 결과만 보고 단정. 그러나 점검 시점에서 사용자가 noVNC/VNC 클라이언트 connect 전이라 디스플레이 위 Chrome이 **dormant 또는 미기동** 상태였을 뿐, VNC 서버 자체는 살아있었음.

**교훈**:
- VNC 환경 검증은 `ss -tlnp | grep -E ':(5901|6080|9222) '` 셋 다 LISTEN인지 + `curl -s http://127.0.0.1:9222/json/version` 200 OK인지 두 단계 모두 확인할 것.
- pgrep 단독 결과로 "VNC 죽었다" 단정 X.
- Chrome remote-debug는 사용자가 VNC connect 후 chrome 켜야 LISTEN. 사용자 액션과 분리해서 점검.

## 다음 봇 발주 전 체크리스트
1. `curl -s http://127.0.0.1:9222/json/version` → 200 + Browser 필드 확인
2. `ss -tlnp | grep ':9222 '` → LISTEN
3. SUNO_COOKIE 갱신일 확인 (`stat -c '%y' .env`) — 7일 이상이면 갱신 의심
4. Suno 크레딧 잔액 사전 조회 (`SunoClient().get_credits()`)
