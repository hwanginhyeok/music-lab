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


---

## D-004: VNC 메인 도메인이 tailnet only로 빠짐 — 외부 접속 불가

- **날짜**: 2026-05-05
- **상황**: 5-18 앨범 작업 중 사용자가 노트북에서 VNC 접속 시도. 메모리에 저장된 SSH 터널 방식(`ssh -N -L 6080:...`)으로 안 들어가고, music-lab 메모리에서 본 URL(`http://localhost:6080/vnc.html`)도 안 됨.
- **문제**: `tailscale funnel status`에서 메인 도메인 / 매핑이 `(tailnet only)`로 표시 — 외부 인터넷에서 접근 불가. 메모리는 5일 전 상태(SSH 터널 시절) → stale.
- **삽질**:
  - SSH 터널 명령으로 안내 → 사용자 안 들어감
  - 8444 포트에 별도 Funnel 띄움 → 검증은 됐지만 사용자 평소 URL 아님 → 안 들어감
  - **PM 메모리 reference_vnc_setup.md / reference_tailscale_funnel_pattern.md 확인** → 정확한 URL과 복구 명령 발견
- **해결**: `echo "0055" | sudo -S tailscale funnel --bg --set-path=/ http://127.0.0.1:6080` — 메인 / 매핑을 Funnel on으로 다시 살림. URL: `https://desktop-plq9e0i.tailec5aa6.ts.net`
- **노하우**:
  1. **VNC URL SSOT는 PM `reference_vnc_setup.md`** — 프로젝트 메모리는 그걸 가리키게 정정
  2. **메인 / 가 가끔 tailnet only로 빠짐** (PC 재시작/Tailscale 재시작 시) → set-path로 복구 패턴 외울 것
  3. **다른 프로젝트 메모리 참조 적극** — 같은 사용자/같은 PC면 PM 메모리에 SSOT 있을 가능성 높음. music-lab 메모리만 보고 SSH 터널 명령 던지면 시간 낭비
- **관련 파일**: `~/.claude/projects/-home-window11-project-manager/memory/reference/reference_vnc_setup.md`, `reference_tailscale_funnel_pattern.md`, `~/.claude/skills/hih-vnc/SKILL.md`
- **관련 커밋**: `ace764c` (메모리 갱신)

---

## D-005: suno_pipeline.py 폴링이 v1만 잡고 종료

- **날짜**: 2026-05-05
- **상황**: 5-18 8곡 배치 생성 중, suno_pipeline.py 로그에 `[2/3] 다운로드 (1곡)` — Suno는 v1/v2 두 곡 동시 생성하는데 한 곡만 받음.
- **문제**: 폴링 로직이 첫 곡 완성 시점에 break — Suno 정상 동작(2곡 동시) 무시.
- **삽질**: data/suno에 짝 곡이 떨어졌는지 확인 → suno_download.py --list 로 보니 같은 title의 두 번째 곡(짝) 존재 → API로 직접 다운로드 가능 확인.
- **해결 (워크어라운드)**: batch 스크립트에 v2 자동 보충 단계 추가:
  ```python
  songs = api.get_songs()
  matches = [s for s in songs if s.get("title","").strip() == TITLE.strip()]
  if len(matches) >= 2:
      v2 = matches[1]  # 두 번째(짝) 곡
      api.download(v2, SUNO_DIR)
  ```
- **노하우**: **Suno generate API는 1회 호출당 v1/v2 두 곡 생성**이 정상. 폴링은 baseline 크레딧이 +20 이상 차감(2곡 × 10) 또는 같은 title 2개 등장까지 기다리는 게 맞음. 정식 픽스는 PIPE-F11.
- **관련 파일**: `suno_pipeline.py` (폴링 부분), `scripts/batch_5-18_remaining.sh` (워크어라운드)
- **관련 커밋**: `4e79d4d`, `6f67ee6`


## D-004: Suno 배치 동시실행 충돌 + Chrome DISPLAY 문제

- **날짜**: 2026-05-10
- **상황**: 5-21 시간여행자 20트랙 배치 생성 시도
- **문제**: 3가지 문제가 동시 발생
  1. **Chrome 시작 실패** — VNC DISPLAY가 꺼진 상태에서 배치 실행 → 전 트랙 실패
  2. **가짜 mp3 이동** — 배치 스크립트가 Chrome 실패 후에도 `data/suno/`의 기존 다른 mp3를 트랙 폴더로 이동 (LATEST_MP3 체크 로직이 실패 후에도 이전 파일 잡아냄)
  3. **동시실행 충돌** — 재시도 스크립트 3개가 동시에 실행되면서 같은 Chrome 9222포트에 동시 접속 → 가사/스타일 뒤섞여 생성
- **삽질**: VNC_DISPLAY=:99 설정, DISPLAY 환경변수 조정, pkill 반복, 로그 뒤지기
- **해결**:
  1. VNC 먼저 켠 후 (`nohup websockify ...`) Chrome 시작 확인 (`curl http://127.0.0.1:9222/json`)
  2. 배치 실행 전 `pkill -9 -f suno_pipeline` 으로 잔여 프로세스 완전 정리
  3. **반드시 배치 1개만 실행** — 재시도도 기존 배치 kill 후 단일 실행
  4. 가짜 mp3 판별: 크기 < 1M이면 의심 (정상은 2.4M~6M)
- **노하우**:
  - Suno 배치 전 체크리스트: ① VNC 켜짐 확인 ② Chrome 9222 응답 확인 ③ 기존 suno_pipeline 프로세스 0개 확인
  - `ps aux | grep suno_pipeline | grep -v grep | wc -l` → 0이어야 시작
  - 배치 스크립트에 `pgrep -f suno_pipeline && echo "이미 실행 중" && exit 1` 가드 추가 권장
- **관련 파일**: `scripts/batch_시간여행자.sh`, `suno_client.py`, `suno_pipeline.py`

## D-007: Suno 인스트루멘털 길이 제어 불가

- **날짜**: 2026-05-15
- **상황**: 무색무취의 빈병 앨범 Track 2~8 생성 중. 목표 2~4분인데 1:40~2:20으로 짧게 끊김
- **문제**: Suno v5.5 UI에 duration 슬라이더 없음. `[Instrumental]` 태그만으로는 길이 신호 부족
- **삽질**:
  - 섹션 마커(`[Intro][Verse][Bridge][Outro]`) 추가 → 2:20까지만 늘어남
  - mmm...ah...mmm 패턴 → 사용자가 "허밍 왜 들어가냐" 불만. 허밍 생성됨
  - Oo-oo-ooh 하이픈 음절 → 비슷한 결과
  - Style에 `3 minute song, long form` 추가 → 미미한 효과
  - API (`suno_client.py`) 확인 → duration 파라미터 없음
  - Exclude 필드 탐색 → UI에서 찾지 못함 (More Options 안에 있다는 정보 있으나 미확인)
- **결론**:
  - Suno는 가사 콘텐츠 양 = 곡 길이. 인스트루멘털은 구조적으로 짧음
  - v5.5 단일 생성 최대 이론치 8분이나 인스트루멘털은 2분대가 현실적 한계
  - **유일한 검증된 방법: Extend 기능 (UI에서 수동)**
  - 보컬리즈 음절 입력 시 허밍 생성되고 2분+ 달성 가능 — 컨셉상 허밍이 필요한 트랙(2·6·8번)에만 사용
- **노하우**:
  - 인스트루멘털 트랙은 현재 길이 수용하거나 Extend로 이음
  - 보컬리즈 트랙(2·6·8번): `Oo-oo-ooh Mm-mm` 하이픈 음절 + 6섹션 구조
  - Style에 `3 minute song` 명시는 효과 미미하나 넣을 것
  - 순수 인스트루멘털: `[Instrumental]` 섹션 마커 5~6개 + `instrumental only, no vocals`
- **관련파일**: `songs/17_무색무취의빈병/tracks/*/suno_prompt.md`, `suno_client.py`
