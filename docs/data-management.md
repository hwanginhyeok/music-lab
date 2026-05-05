# 데이터 관리 정책

> music-lab의 곡 데이터는 **로컬 / GDrive / DB / YouTube** 4곳에 분산. SSOT 원칙으로 각 위치의 역할을 분리한다.

## 핵심 원칙 (SSOT 우선)

1. **로컬이 SSOT.** 모든 정보의 원본은 로컬 파일시스템.
   - 컨셉 SSOT: `docs/albums/{앨범}.md`
   - 트랙 산출물 SSOT: `songs/{앨범}/`
   - 인덱스 SSOT: `docs/albums/INDEX.md`

2. **GDrive는 사본/공유 채널 (단방향 미러).**
   - 사용자가 GDrive 웹/모바일에서 컨셉을 보고 댓글로 소통하기 위한 채널.
   - **GDrive에서 직접 편집 금지** — 다음 sync에서 덮어씀.
   - 변경은 로컬 → 커밋 → `rclone copy` 단방향.

3. **GDrive에는 md/txt/json만 올림. mp3/wav/mp4는 안 올림.**
   - 음원은 사용자가 Suno 웹/로컬에서 직접 청취.
   - GDrive 비용·동기화 시간 절약.
   - 큰 파일은 로컬과 YouTube에만 존재.

4. **Suno 다운로드는 임시 영역.**
   - `data/suno/`는 거치는 곳. 곡별 `tracks/.../raw/`로 정리되어야 끝.
   - 30일+ 미정리 파일은 정기 점검 시 검토.

5. **DB 기록은 보조.** `data/music.db`는 텔레그램 대화/아이디어/메타데이터용. SSOT 아님 (재생성 가능).

6. **YouTube는 발매 채널.** publish-gate 통과 후만 게시.

---

## 디렉토리 구조 (SSOT)

### 로컬 — `/home/window11/music-lab/`

```
music-lab/
├── docs/
│   ├── albums/                     ← 🟢 컨셉 SSOT
│   │   ├── INDEX.md                  앨범 인덱스 (발매 완료 + 후보 우선순위)
│   │   ├── 무색무취의빈병.md          5-17 컨셉 v0.3
│   │   └── 술병이났다.md              5-18 컨셉 v0.3
│   ├── data-management.md          ← 이 문서
│   ├── suno_guide.md               Suno 프롬프트 가이드
│   ├── poc/                        PoC 보고서 (PIPE-F03 등)
│   ├── plans/                      구현 계획서
│   └── 작사가/                     작사법 분석
│
├── songs/
│   ├── {NN}_{slug}/                ← 🟢 곡/앨범 작업 디렉토리
│   │   ├── README.md                 진행도 트래커
│   │   ├── workflow.md               작업 단계
│   │   ├── concept.md                (또는 docs/albums/{이름}.md SSOT 참조)
│   │   ├── tracks/{NN}_{track}/
│   │   │   ├── suno_prompt.md        ← 트랙 SSOT (스펙 + Suno 입력)
│   │   │   ├── lyrics.md             가사 (보컬 트랙만)
│   │   │   ├── meta.json             트랙 메타데이터
│   │   │   └── raw/                  ← .gitignore (곡 후보)
│   │   │       ├── v1.mp3            Suno 후보 1
│   │   │       ├── v2.mp3            Suno 후보 2
│   │   │       └── master.mp3        선별된 best take (편집 후)
│   │   ├── master_audio.mp3        ← .gitignore (앨범 마스터)
│   │   ├── final_video.mp4         ← .gitignore (최종 영상)
│   │   ├── chapters.{json,srt,txt} 챕터 마커
│   │   ├── cover.jpg               앨범 커버
│   │   ├── thumbnail/              YouTube 썸네일
│   │   └── youtube_upload.json     게시 메타
│   │
│   ├── archive/                    🟡 폐기/중단된 곡 보관
│   ├── _reference/                 레퍼런스 음원 (Laufey 등)
│   └── template/                   새 곡 시작 시 복사할 골격
│
├── data/                           ← 🟡 .gitignore (전체)
│   ├── suno/                         Suno API 다운로드 임시 (UUID 파일명)
│   ├── music.db                      SQLite (대화 + 아이디어 + Suno 메타)
│   └── exports/                      MIDI/오디오 변환 결과
│
├── scripts/                        도구 스크립트
├── .env                            ← .gitignore (토큰)
├── client_secrets.json             ← .gitignore (YouTube OAuth)
├── token.json                      ← .gitignore (YouTube 토큰)
└── credentials/                    ← .gitignore (서비스 계정 키)
```

### Google Drive — `gdrive:music-lab/`

> **md/txt/json만 sync. mp3/wav/mp4 절대 안 올림.** 사용자가 GDrive 웹에서 컨셉/가사/프롬프트를 읽고 소통하는 용도.

```
music-lab/
├── _INDEX.md                       ← docs/albums/INDEX.md 사본 (앨범 인덱스)
│
├── {NN} {앨범 한국어 제목}/         ← 발매 완료 + 진행 중 모두 (md만)
│   ├── _INDEX.md                     앨범 통합 정리본 (자동 생성, 아래 참고)
│   ├── concept.md                    컨셉 (docs/albums/*.md SSOT 사본)
│   ├── description.md                YouTube description / 곡 소개
│   ├── reference.md                  레퍼런스 / 톤 분석
│   ├── workflow.md                   작업 단계 (진행 중인 앨범만)
│   ├── youtube_description.txt       YouTube 게시 메타
│   ├── chapters.txt / .srt           챕터 마커
│   ├── tracks/{NN}_{slug}/
│   │   ├── suno_prompt.md            트랙 컨셉 + Suno 입력
│   │   ├── lyrics.md                 가사 (보컬 트랙만)
│   │   └── meta.json                 트랙 메타데이터
│   └── thumbnail/concept.md          썸네일 컨셉
│
├── archive/                        폐기/중단 앨범 (md만)
└── _admin/                         관리자 전용 (DB 백업 등)
```

**컨벤션:**
- 폴더명은 **한국어 우선** (`5-18 술병이 났다` 등 — 사용자가 GDrive 웹에서 한 번에 인지)
- `{NN}` = TASK ID 2자리 prefix (`5-14`, `5-18` 등 — TASK.md와 일치)
- 트랙 폴더는 로컬 구조 그대로 (`01_empty_glass/`)

**자동 생성 `_INDEX.md`** — 앨범 폴더 진입 시 첫 화면용 통합 정리:
- 앨범 한 줄 요약 + 발매 정보 (게시일, YouTube 링크)
- 트랙리스트 (BPM/키/편성)
- 핵심 컨셉 (컨셉 md 요약)
- 모든 md 링크 (사이드바 인덱스 역할)
- SSOT 표시 (이 폴더는 로컬 미러 — 편집 금지)

### SQLite DB — `data/music.db`

| 테이블 | 용도 |
|--------|------|
| `messages` | 텔레그램 대화 히스토리 (멀티턴 컨텍스트) |
| `ideas` | `/idea` 명령으로 저장된 영감 라이브러리 |
| `suno_songs` | Suno 곡 메타데이터 (현재 미활용 — 곡별 메타는 `tracks/.../meta.json`로) |

**주의**: `data/music.db`는 .gitignore. 백업 별도 정책 없음 — 손실 시 텔레그램 대화는 재생성 어려움. 추후 정기 백업 검토 (`data/music.db` → GDrive `_admin/`).

### YouTube — `dlsgur5560@gmail.com` 채널

- **재즈 채널 정체성** ([memory: project_jazz_channel.md](../memory/project_jazz_channel.md))
- 발매 단위: 싱글 / EP / 풀앨범 영상
- 게시는 **publish-gate 통과 후만** ([global rule: publish-gate.md](~/project-manager/global-rules/publish-gate.md))

---

## 데이터 흐름 (생성 → 발매)

```
1. 컨셉 단계
   docs/albums/{앨범}.md (SSOT) ← 컨셉 변경은 여기서만
   ↓
   GDrive sync (md only) → gdrive:music-lab/{앨범}/concept.md
   ↓
2. 작업 디렉토리 생성
   songs/{NN}_{slug}/{README.md, workflow.md, tracks/}
   ↓
   GDrive sync → gdrive:music-lab/{앨범}/{README.md, workflow.md, tracks/*/suno_prompt.md}
   ↓
3. Suno 생성 (사용자가 직접 청취 — GDrive 안 거침)
   suno_pipeline.py → data/suno/{uuid}.mp3 (임시)
   ↓
4. 트랙 정리 (필수)
   data/suno/{uuid}.mp3 → songs/{앨범}/tracks/{NN}/raw/v{1,2}.mp3 (로컬만)
   meta.json 작성 (song_id, prompt 사용본, 생성일시)
   ↓
   GDrive sync → meta.json만 sync (mp3 X)
   ↓
5. 청취 + 선별 (사용자)
   사용자가 Suno 웹 또는 로컬에서 v1/v2 청취 → best take 결정
   ↓
6. 마스터링 (로컬 only)
   라우드니스 노멀라이즈 (-14 LUFS) → songs/{앨범}/master_audio.mp3
   챕터 마커 → songs/{앨범}/chapters.{json,srt,txt}
   ↓
   GDrive sync → chapters.{txt,srt}만 sync (mp3 X)
   ↓
7. 시각 산출물 (로컬)
   앨범 커버 / 썸네일 / 영상 → songs/{앨범}/{cover.jpg, thumbnail/, final_video.mp4}
   ↓
   GDrive sync → thumbnail/concept.md, prompts.md만 sync (jpg/mp4 X)
   ↓
8. YouTube 게시 (publish-gate)
   사용자 승인 → scripts/youtube_upload.py
   ↓
   GDrive sync → youtube_description.txt, youtube_upload.json
```

**SSOT 흐름:** 모든 단계에서 로컬이 SSOT. GDrive는 각 단계 완료 시점에 md/txt/json만 단방향 push.

---

## .gitignore 정책

**git에 안 들어가는 것 (큰 파일 / 시크릿):**
- `data/` 전체 (Suno 다운로드, DB)
- `songs/*/tracks/*/raw/` (mp3 후보들)
- `songs/*/master_audio.{mp3,wav}`
- `songs/*/final_video.mp4`
- `songs/*/intro.mp4`, `main_video.mp4`
- `.env`, `client_secrets.json`, `token.json`, `credentials/`

**git에 들어가는 것:**
- `docs/` 전체 (컨셉, 가이드, PoC 보고서)
- `songs/*/{README.md, workflow.md, concept.md}`
- `songs/*/tracks/*/{suno_prompt.md, lyrics.md, meta.json}`
- `songs/*/{cover.jpg, thumbnail/}` (PNG/JPG는 작아서 OK)
- `songs/*/chapters.{json,srt,txt}`
- `songs/*/youtube_upload.json`
- `scripts/` 전체

**원칙:** "재생성 가능 + 큰 파일" → 로컬+GDrive만. "재생성 어려움 + 작은 파일" → git.

---

## 명령어 치트시트

### Suno 트랙 정리 (생성 후 첫 단계)
```bash
# data/suno/ → tracks/{NN}/raw/ 이동
mv data/suno/{uuid}.mp3 songs/{앨범}/tracks/{NN}_{slug}/raw/v1.mp3

# 짝(v2) 다운로드
python3 -c "
import sys, shutil
sys.path.insert(0, '.')
from suno_download import SunoAPI, SUNO_DIR
from pathlib import Path
api = SunoAPI()
song = next(s for s in api.get_songs() if s['id'].startswith('UUID_PREFIX'))
p = api.download(song, SUNO_DIR)
shutil.move(str(p), 'songs/{앨범}/tracks/{NN}/raw/v2.mp3')
"
```

### GDrive sync — md/txt/json 단방향 미러 (mp3/wav/mp4 제외)

```bash
# 단일 앨범 sync (5-18 예시)
rclone copy songs/18_sulbyeong_natda/ "gdrive:music-lab/5-18 술병이 났다/" \
  --include "*.md" --include "*.txt" --include "*.json" \
  --exclude "raw/**" --exclude "**/raw/**" \
  --progress

# 컨셉 SSOT (docs/albums/) sync
rclone copy docs/albums/ "gdrive:music-lab/_docs/albums/" --include "*.md" --progress

# 인덱스 sync
rclone copy docs/albums/INDEX.md "gdrive:music-lab/_INDEX.md"

# 공유 링크 (앨범 폴더 통째)
rclone link "gdrive:music-lab/5-18 술병이 났다"

# 양방향 sync는 절대 사용 금지 (GDrive 편집 흔적이 로컬 SSOT를 덮어씀)
# rclone sync 도 단방향 push로만 (로컬 → GDrive)
```

**`scripts/sync_gdrive.sh`** (있으면 사용, 없으면 위 명령 직접):
- 인자 없으면 모든 앨범 sync
- 인자 있으면 해당 앨범만

### 폐기/중단된 곡 archive로 이동
```bash
git mv songs/{NN}_{slug} songs/archive/{NN}_{slug}
# GDrive (md만)
rclone move "gdrive:music-lab/{NN} {앨범}" "gdrive:music-lab/archive/{NN} {앨범}"
```

### 발매 완료 앨범 _INDEX.md 자동 생성

```bash
# 발매 완료 앨범 정리본 — 한 폴더에 모든 핵심 정보 통합
# (수동 작성 또는 추후 scripts/build_album_index.py로 자동화)
```

### Suno data/ 정리 (오래된 임시 파일 삭제)
```bash
# 30일 넘은 data/suno/*.mp3 삭제 (정리는 곡별 raw로 이동 후)
find data/suno -name "*.mp3" -mtime +30 -delete
find data/suno -name "*_cover.jpeg" -mtime +30 -delete
```

---

## 정기 점검 (월 1회)

- [ ] `data/suno/` 임시 파일 — 곡별 raw로 이동되지 않은 게 있나?
- [ ] GDrive sync — 로컬에 새로 추가된 md가 GDrive에 반영됐나?
- [ ] GDrive에 mp3/wav/mp4 잘못 올라간 거 없나? (정책 위반 검사)
  ```bash
  rclone lsf -R gdrive:music-lab/ --files-only | grep -E "\.(mp3|wav|mp4|m4a|ogg)$"
  ```
- [ ] `songs/archive/` 폐기 곡들 GDrive에도 archive로 옮겼나?
- [ ] `.env`/`credentials/` 시크릿 git에 안 들어갔나? (`git status` 매 커밋 시)
- [ ] DB 백업 — `data/music.db` GDrive `_admin/`로 백업
- [ ] `docs/albums/INDEX.md` 후보군 정리 — 굳어진 컨셉은 별도 md로 분리

---

## 알려진 문제 (PIPE 태스크에 등록됨)

- **PIPE-F05** Drive 서비스 계정 JSON — `client_secrets.json`(OAuth)을 Drive에 잘못 사용. 서비스 계정 키 별도 발급 필요. **현재 우회**: `rclone gdrive:` 사용 중 (개인 계정 OAuth)
- **suno_pipeline.py 폴링 1곡만 잡음** — Suno 정상은 v1/v2 동시 생성인데 폴링이 첫 곡 완성 시 종료. 사후에 `suno_download.py`로 v2 보충해야 함. 새 P1 후보로 등록 필요
- **DB 백업 정책 없음** — `data/music.db` 손실 시 복구 불가. 정기 GDrive 백업 cron 필요

---

## 변경 이력

- v0.1 (2026-05-05): 초안 작성. 5-18 1번 트랙 GDrive 업로드 후 데이터 흐름 정리 필요성 → 통합 문서로 등재.
- **v0.2 (2026-05-05): SSOT 원칙 강화. GDrive 정책 변경 — mp3/wav/mp4 제외, md/txt/json만 단방향 sync. 사용자가 GDrive 웹에서 컨셉/가사/프롬프트 보고 소통하는 채널로 재정의. 음원 청취는 Suno 웹/로컬에서 직접. 발매 완료 앨범은 `_INDEX.md` 통합 정리본 생성 패턴 추가.**
