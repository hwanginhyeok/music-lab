# Handoff — 2026-05-10 (세션 2)

> 다음 세션 시작 시 읽고 복구. 복구 끝나면 삭제.

## 작업 중이던 것

### 5-21 시간여행자 — 사용자 Suno에서 트랙 선별 중
- 20트랙 전부 생성 완료 (20:49:36)
- 크기 정상: 2.4M~4.4M
- 트랙 폴더: `songs/21_시간여행자/tracks/01_pressed_and_ready ~ 20_tease_me_time`
- **사용자가 Suno 앱에서 직접 청취 후 best take 선별 중**
- 선별 완료 후: GDrive 동기화 → 후처리(-14 LUFS) → YouTube 게시

### 5-19 Daylight Hours / 5-20 Electric Feelings
- 동시에 선별 중 (GDrive에 mp3 있음)
- 선별 완료되면 후처리(-14 LUFS) → YouTube 게시

## 결정 사항
- **5-21 음악 방향 확정**: jongpop 🔴신남/활기 17곡 + 🟠설렘 3곡 베이스
  - Jackson Laird / Fencetrees / 99 Neighbors / Nabes / Logan Levi / Zafty / Forrest Frank / Confetti / The Orphan The Poet / Hoodie Allen / Pertinence / Little Hurt / Harrison Boe / UPSAHL / The Wrecks / Derik Fein / d4vd / byjaye / Nicky Youre
- **jongpop 베이스 확정** — 방향 재논의 없이 실행
- **6-1 YouTube 관리 파이프라인**: 31일 blocked → 사용자 결정 필요 (P3 격하 or 폐기)

## 중요 노하우 (D-004)
Suno 배치 전 필수 체크:
1. VNC 켜짐 확인: `curl -sI http://127.0.0.1:6080/` → 200 OK
2. Chrome 9222 확인: `curl -s http://127.0.0.1:9222/json | head -3`
3. 기존 프로세스 0개: `ps aux | grep suno_pipeline | grep -v grep | wc -l` → 0

## 다음 세션 첫 액션
1. 사용자에게 선별 완료 여부 확인
2. 완료됐으면: 선별된 트랙 목록 받고 후처리(-14 LUFS) `/audio-process` 실행
3. 5-19/5-20도 선별 완료됐으면 동시에 후처리
