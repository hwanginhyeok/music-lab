# Difficulties & Know-how

## D-001: Suno hCaptcha — generate API로 곡 생성 불가

- **날짜**: 2026-03-29 ~ 현재
- **상황**: Suno API로 곡 생성 자동화를 시도. suno_client.py에서 undetected-chromedriver로 Cloudflare Turnstile 우회 성공.
- **문제**: generate API 호출 시 hCaptcha 추가 검증이 발생. Turnstile은 우회했지만 hCaptcha는 우회 불가.
- **삽질**: 
  - undetected-chromedriver로 Turnstile 우회 → 성공
  - generate API 직접 호출 → hCaptcha 차단
  - VNC 환경에서 Chrome attach → 캡차만 수동 해결 시도
- **해결**: **수동 Suno 웹 생성 + 자동 다운로드 조합**으로 전환. `suno_download.py`는 Clerk JWT로 안정적 동작.
- **노하우**: **Suno의 곡 생성은 자동화 불가 (2026-03 기준)**. 다운로드/메타데이터 조회는 Clerk JWT로 가능. 생성은 웹에서 수동 + noVNC로 원격 접근.
- **관련 파일**: `suno_client.py`, `suno_download.py`, `suno_pipeline.py`

---

## D-002: Clerk JWT 인증 — 세션 쿠키 만료 주기 짧음

- **날짜**: 2026-03-31 ~ 2026-04-02
- **상황**: suno_download.py가 Clerk JWT로 Suno API를 호출. 처음엔 잘 되다가 며칠 후 인증 실패.
- **문제**: Suno의 Clerk 세션 쿠키(`__client`)가 짧은 주기(수일)로 만료. .env의 SUNO_COOKIE를 갱신해야 함.
- **삽질**:
  - 만료된 JWT로 계속 재시도 → 403
  - refresh 엔드포인트 탐색 → Clerk는 브라우저 세션 기반이라 서버사이드 갱신 불가
- **해결**: **브라우저에서 Suno 로그인 → DevTools > Application > Cookies에서 `__client` 복사 → .env 갱신**. 주기적 수동 갱신 필요.
- **노하우**: **Clerk JWT는 서버사이드 자동 갱신 불가**. 브라우저 세션에 의존. 쿠키 만료 시 로그에 명확한 에러 메시지 출력하도록 구현해둘 것.
- **관련 파일**: `suno_download.py`, `.env` (SUNO_COOKIE)

---

## D-003: Claude CLI 사일런트 브레이킹 체인지

- **날짜**: 2026-04-03
- **상황**: 텔레그램 봇이 npx로 Claude CLI를 호출. 특정 시점부터 응답 형식이 달라지거나 에러 발생.
- **문제**: npx가 최신 버전을 자동 설치하면서, Claude CLI의 출력 형식이나 플래그가 예고 없이 변경됨.
- **삽질**:
  - 에러 로그만 보고 봇 코드를 수정 → 원인은 CLI 버전 차이
  - `--bare` 플래그 시도 → OAuth 비활성화되어 사용 불가
- **해결**: **`npx @anthropic-ai/claude-code@2.1.91`로 버전 핀**. 업그레이드는 테스트 후 수동으로.
- **노하우**: **npx로 CLI 호출 시 반드시 버전 고정**. 자동 최신 설치는 프로덕션에서 사일런트 장애 원인. 버전 업그레이드는 로컬 테스트 → 봇 반영 순서로.
- **관련 파일**: `bot.py` (CLI 호출 부분)
- **관련 커밋**: `ca2cec2`
