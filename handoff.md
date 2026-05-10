# Handoff — 2026-05-10

> 다음 세션 시작 시 이 파일 읽고 컨텍스트 복구. 복구 끝나면 삭제.

## 작업 중이던 것

### 5-21 시간여행자 — Suno 배치 생성 실행 중
- **배치 PID**: 55942
- **로그**: `/tmp/suno_시간여행자.log`
- 상태 확인: `tail -f /tmp/suno_시간여행자.log`
- 완료 여부: `ls songs/21_시간여행자/tracks/*/raw/*.mp3 | wc -l` (목표: 20개)
- 크레딧: 배치 시작 시 2010 크레딧 확인됨
- 오류 시: 개별 트랙 `python3 suno_pipeline.py --title "..." --prompt-file "..." --skip-drive --model v5.5`

### 5-19 Daylight Hours / 5-20 Electric Feelings
- 사용자가 GDrive에서 best take 선별 중
- 선별 완료 후: 후처리(-14 LUFS) → YouTube 게시

## 결정 사항 (2026-05-10)
- 5-21 시간여행자: jongpop 플레이리스트 3개 분석 기반 20트랙 앨범
- 썸네일: thumbnail_v1.jpg(에코+파우더 앉은 컷), thumbnail_v2.jpg(시간역행 소용돌이 컷)
- 6-1 YouTube 관리 파이프라인: 31일 정체 → P3 격하 검토 필요 (사용자 결정)
- docs/suno_prompts/ 폴더: Suno 프롬프트 파일 전용 (albums/에서 분리)

## 파일 변경 요약
- `docs/suno_prompts/시간여행자_suno.md` — 20트랙 풀 프롬프트
- `docs/albums/시간여행자_이미지/` — AI 이미지 3장 + 썸네일 2장
- `scripts/setup_시간여행자.py`, `scripts/batch_시간여행자.sh` — 배치 스크립트
- `songs/21_시간여행자/tracks/` — 20개 트랙 폴더 (로컬, GDrive 이전 전)

## 다음 세션 첫 액션
1. Suno Chrome 시작 실패 — 전 트랙 mp3 0개 생성, 크레딧 차감 없음(2010 유지)
   → chrome 프로세스 정리 후 재시도: `pkill -f chrome; pkill -f chromedriver`
   → 또는 suno_pipeline.py --headless 옵션 확인
   → 개별 트랙 테스트: `python3 suno_pipeline.py --title "Slow Reverse" --prompt-file songs/21_시간여행자/tracks/01_slow_reverse/suno_prompt.md --skip-drive --model v5.5`
2. 완료됐으면: 생성된 mp3 청취 → best take 선별 → 후처리
3. 미완료면: 실패 트랙 재실행
4. 5-19/5-20 선별 완료됐으면 후처리(-14 LUFS) 시작
