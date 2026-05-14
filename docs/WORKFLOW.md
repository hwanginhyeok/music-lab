# music-lab 앨범 제작 워크플로우

> 버전: v1.0 (2026-05-14)

## 파이프라인 개요

```
컨셉 설계 → 가사/프롬프트 → Suno 생성 → 선별 → 후처리 → 게시 준비 → YouTube 업로드
```

---

## Type A — 가사 앨범

```
1. 컨셉        docs/albums/{앨범명}.md 작성 (사용자+PM 논의)
2. 가사        /lyrics 스킬 → songs/{NN}_{곡명}/lyrics_v1.md
3. Suno 프롬프트  /suno-prompt 스킬 → docs/suno_prompts/{앨범명}_suno.md
4. 보컬 디렉션  /vocal 스킬 → 필요 시 Style 태그 수정
5. Suno 생성   suno_pipeline.py 또는 수동
6. 선별        사용자 리뷰 → best take 확정
7. 후처리      /audio-process 스킬 (-14 LUFS 노멀라이즈)
8. 믹스 조정   /mix 스킬 → 필요 시 (선택)
9. 영상 제작   scripts/create_video.py
10. 게시 준비  youtube_copy/{앨범명}.md (TEMPLATE_lyrics.md 기반)
             서문은 사용자가 직접 작성 후 입력
11. 업로드     scripts/publish.py
```

## Type B — 인스트루멘털 앨범

```
1. 컨셉        docs/albums/{앨범명}.md 작성 (사용자+PM 논의)
2. Suno 프롬프트  /suno-prompt 스킬 (인스트루멘털 모드)
             → docs/suno_prompts/{앨범명}_suno.md
3. Suno 생성   suno_pipeline.py 또는 수동
4. 선별        사용자 리뷰 → best take 확정
5. 후처리      /audio-process 스킬 (-14 LUFS, 최소 처리)
6. 영상 제작   scripts/create_video.py
7. 게시 준비  youtube_copy/{앨범명}.md (TEMPLATE_instrumental.md 기반)
             서문은 사용자가 직접 작성 후 입력
8. 업로드     scripts/publish.py
```

---

## 문서 위치 SSOT

| 종류 | 경로 |
|------|------|
| 앨범 컨셉 | `docs/albums/{앨범명}.md` |
| Suno 프롬프트 | `docs/suno_prompts/{앨범명}_suno.md` |
| YouTube 게시 문구 | `youtube_copy/{앨범명}.md` |
| 가사 (Type A) | `songs/{NN}_{곡명}/lyrics_v{N}.md` |
| 곡 파일 | GDrive `music-lab/songs/{NN}_{곡명}/` (로컬 .gitignore) |

## 스킬 라우팅

| 상황 | 스킬 |
|------|------|
| 가사 작성/수정 | `/lyrics` |
| Suno 프롬프트 생성 | `/suno-prompt` |
| 보컬 방향 결정 | `/vocal` |
| 후처리 (-14 LUFS) | `/audio-process` |
| 믹스 파라미터 조정 | `/mix` |

## 현재 앨범 현황

| 앨범 | 타입 | 상태 |
|------|------|------|
| 봄을 통해 너를 봄 | A | ✅ 완료 |
| 왜 그리 울고만 있어요? | A | ✅ 완료 |
| 술병이 났다 | A | ✅ 완료 |
| 시간여행자 | A | ✅ 완료 (unlisted) |
| Daylight Hours | A | ⏸️ 선별 대기 |
| Electric Feelings | A | ⏸️ 선별 대기 |
| 무색무취의 빈병 | B | 🔄 컨셉 논의 중 |
