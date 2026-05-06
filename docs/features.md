# Music Lab 기능 요구사항 (SSOT)

> 시스템 헬스 매니지먼트의 검증 대상. `scripts/health_check.py`가 각 기능 ID를 검증.
> 설계: `~/project-manager/docs/plans/system-health-management.md`

## 우선순위
- **P0** — 핵심 운영 기능. 장애 시 즉시 알림.
- **P1** — 중요 보조 기능. 1일 이내 복구 필요.
- **P2** — 개선/편의 기능. 주간 단위 처리.

## 상태
- ✅ 정상  ⚠️ 경고  🔴 장애  ⏸️ 점검 중  ⛔ 미구현

---

## 기능 표

| ID | 기능 | 기대 동작 | 검증 방법 | 우선순위 | 상태 |
|----|------|----------|---------|---------|------|
| F001 | 텔레그램 봇 | systemd `music-bot.service` active. 자연어 명령(`/lyrics`, `/chord`, `/midi`, `/suno` 등 18개)에 응답. Claude CLI 멀티턴 대화 + DB 히스토리. | health_check.py::check_bot_imports (bot/db/audio import 검증). systemctl 상태는 운영 시점에 확인 | P0 | ✅ |
| F002 | Suno 인스트루멘탈 곡 생성 | Advanced 모드 + 빈 lyrics input event 경로. Style만 입력해도 Suno가 인스트루멘탈 자동 처리. v1/v2 두 버전 다운로드. | health_check.py::check_suno_token (크레딧 조회 OK), check_chrome_profile, check_suno_imports | P0 | ✅ |
| F003 | Suno 보컬 곡 생성 | Advanced 모드 + 가사 입력. 영어/한국어 보컬 지원. v1/v2 다운로드. | health_check.py::check_suno_token. 06_vocal 트랙 발주 시 검증 (PoC #6 + retry 회수) | P0 | ✅ |
| F004 | 후처리 파이프라인 (postprocess_v2) | Demucs 보컬 분리 + Pedalboard 후처리 + 라우드니스 -14 LUFS. 경량 모드(Matchering 제거) 기본. | health_check.py::check_postprocess_script (postprocess_v2.py 존재 + import) | P1 | ⚠️ |
| F005 | 영상 빌드 (ffmpeg) | 9곡 fade concat → master_audio.mp3. cover_a + SRT 자막 → main_video. intro 3s 크로스페이드. concat → final_video.mp4. | health_check.py::check_ffmpeg (`ffmpeg -version` 응답) | P0 | ✅ |
| F006 | YouTube 업로드 | OAuth 토큰(`token.json`) refresh 자동. private/unlisted/public 업로드 + 썸네일 + 챕터 설명. | health_check.py::check_youtube_token (`token.json` expiry 7일 이내 → warn, 1일 이내 → critical) | P0 | ✅ |
| F007 | generate_album.py 9곡 일괄 | concept.md 트랙 매트릭스 + 각 suno_prompt.md 파싱 → 순차 발주 → tracks/{NN}/raw/v1.mp3, v2.mp3 + meta.json. | health_check.py::check_album_runner (스크립트 존재 + 로드) | P1 | ⚠️ |
| F008 | chrome-suno 9222 (Suno UI 자동화) | VNC 디스플레이에서 Chrome remote-debug(9222) 띄우고 Suno 세션 유지. 캡차 발생 시 noVNC 풀이. | health_check.py::check_chrome_remote (HTTP 9222/json/version 응답). 미기동은 skip — 실시간 발주 시점에만 필요 | P1 | ⏸️ |
| F009 | 가사/프롬프트 생성 (서브 에이전트) | `lyricist`(김이나 작사법), `composer`, `suno-prompt-engineer`, `vocalist`, `mixing-engineer` 5종. `.claude/agents/` 정의. | health_check.py::check_agents_dir (`.claude/agents/*.md` 5개 파일 존재) | P1 | ✅ |
| F010 | 5-14 EP 발매 상태 | `songs/14_geuriumi/youtube_upload.json` 존재. 비공개(private)로 업로드 완료(`3Wl2xmyOqrA`). 공개 전환은 사용자 승인 후. | health_check.py::check_album_release (`youtube_upload.json` 읽기) | P1 | ✅ |

---

## ID별 검증 디테일

### F001 텔레그램 봇
- 검증 import: `bot`, `db`, `audio`
- 운영 검증: `systemctl --user status music-bot` (수동/별도)
- DB 무결성: `data/music.db` 파일 + 테이블 무결성 (선택)

### F002 Suno 인스트루멘탈 — (C) 경로 검증 완료
- 검증된 시퀀스: Advanced 모드 + lyrics textarea에 빈 문자열 명시 input event(setNativeValue + input/change/blur) → Style 입력 → Create. Suno placeholder `"Write some lyrics or leave blank for instrumental"` 안내대로 자동 인스트루멘탈 처리.
- 폐기 경로 (보존): Simple 모드 + Instrumental 탭(`_switch_to_simple_instrumental`) — 봇 감지로 4회 실패. 코드 주석으로 보존.
- 검증 자동: 토큰 유효성(크레딧 조회). 실제 발주는 PoC 시점에만 (크레딧 비용).

### F003 Suno 보컬
- F002와 동일 인프라. `--instrumental` 플래그 없이 lyrics 본문 입력.
- Track 06 lyrics_v1_en.md (markdown 헤더 포함 그대로 입력) → 회수 검증 완료.

### F004 후처리 파이프라인
- 위치: `postprocess_v2.py` (루트) 또는 `scripts/postprocess_v2.py`
- 입력: WAV/MP3 + 옵션
- 출력: `processed.wav` + `quality_report_v2.json`
- 미구현 시: ⚠️ 경고 (5-14 EP는 raw v1 그대로 영상 빌드)

### F005 ffmpeg
- 시스템 패키지. `ffmpeg -version` exit 0.
- 의존: scripts/create_video.py, scripts/lyrics_to_srt.py, audio.py 등.

### F006 YouTube 업로드
- `client_secrets.json` (OAuth 클라이언트 시크릿) — gitignore
- `token.json` (refresh_token + access_token + expiry) — gitignore
- 검증: token.json 존재 + 'expiry' 파싱 → 만료 시간 비교
- refresh 자동 동작: scripts/upload_album_private.py에서 검증됨 (5-14 발매 시 자동 갱신 ✅)

### F007 generate_album.py
- 알려진 버그: 'Expected 2 downloads, got 1' 검증이 너무 엄격 (Suno 첫 폴링이 1곡만 잡고 break).
- 해결안 (별건): workspace에서 두 번째 곡 추가 다운로드 fallback 추가.
- 회수 도구: `scripts/recover_album.py` (workspace에서 일괄 회수, 검증됨).

### F008 chrome-suno 9222
- `~/.config/chrome-suno/` 프로필 존재 확인.
- VNC 디스플레이 :1, port 5901 (Xtigervnc), noVNC 6080.
- Chrome remote-debug 9222: 사용자 VNC 클라이언트 접속 후 chrome 자동 기동.
- 9222 미응답은 평소 정상 (실시간 발주 시점에만 필요) → skip 처리.

### F009 서브 에이전트 5종
- `.claude/agents/lyricist.md`, `composer.md`, `suno-prompt-engineer.md`, `vocalist.md`, `mixing-engineer.md`
- Music Lab 작업 흐름의 핵심 (가사 ↔ 코드 진행 ↔ Suno 프롬프트 ↔ 보컬 디렉션 ↔ 믹싱).

### F010 5-14 EP 발매 상태
- `songs/14_geuriumi/youtube_upload.json` 메타 파일.
- 현재 상태: **private** (`3Wl2xmyOqrA`). 청취 검수 후 공개 전환 사용자 결정.

---

## 자동 수정 트리거

| 심각도 | 자동 액션 |
|--------|---------|
| critical | 텔레그램 즉시 알림 + music-lab 세션에 tmux 수정 지시 |
| major | 텔레그램 알림 + daily_report 강조 표시 |
| minor | daily_report 표시만 |

## 변경 이력
- 2026-05-03 — 최초 작성. F001~F010 등록. 5-14 EP 발매 검증 완료.
