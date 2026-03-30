# 야간작업 브리핑 -- 2026-03-30

## 프로젝트: Music Lab
## 목표: Suno -> YouTube 자동화 파이프라인 구축

---

## 작업 결과 요약

| # | 작업 | 결과 | 비고 |
|---|------|------|------|
| 0 | manifest.json 지원 (jazz_pipeline.py) | 완료 | status 필드로 곡 상태 추적 |
| 1 | scripts/create_video.py | 완료 | ffmpeg 미설치 시 안내, 이미지 없으면 검정 배경+drawtext |
| 2 | scripts/generate_thumbnail.py | 완료 | Pillow 미설치 시 안내, 그라데이션 배경+텍스트 |
| 3 | scripts/youtube_upload.py | 완료 | google-api 미설치 시 안내, OAuth2 설정 가이드 포함 |
| 4 | scripts/publish.py | 완료 | 오케스트레이터, --skip-upload / --public 옵션 |
| 5 | 클래식 재즈 프리셋 추가 | 완료 | jazz bar, bebop, vocal jazz standards 추가 / neo soul jazz 제거 |

## 실패/스킵 항목

없음. 6개 항목 모두 완료.

## 커밋 이력

1. `e2a25c1` feat: jazz_pipeline.py에 manifest.json 자동 생성 추가
2. `08cb4d8` feat: create_video.py 추가 -- 커버 이미지 + 오디오 -> MP4 영상 생성
3. `80a152c` feat: generate_thumbnail.py 추가 -- YouTube 썸네일 자동 생성 (Pillow)
4. `ae4561a` feat: youtube_upload.py 추가 -- YouTube Data API v3 업로드
5. `1e8154c` feat: publish.py 추가 -- YouTube 게시 오케스트레이터
6. `3f2edc1` feat: 클래식 재즈 프리셋 3개 추가, neo soul jazz 제거

## 파이프라인 전체 흐름

```
songs/NN_곡이름/
  ├── manifest.json            <- jazz_pipeline.py가 자동 생성
  ├── release/final.wav        <- mix_stems.py 출력
  ├── cover.jpg                <- 사용자 준비 (없으면 검정 배경)
  ├── video/output.mp4         <- create_video.py가 생성
  └── video/thumbnail.jpg      <- generate_thumbnail.py가 생성
                                    |
                            youtube_upload.py로 업로드
                                    |
                            publish.py가 전체 오케스트레이션
```

## 사용자 액션 필요

1. **YouTube API 설정**: client_secrets.json 준비 필요
   - Google Cloud Console에서 YouTube Data API v3 활성화
   - OAuth 2.0 클라이언트 ID 생성 -> JSON 다운로드 -> 프로젝트 루트에 저장
2. **Pillow 설치 확인**: `pip install Pillow` (썸네일 생성용)
3. **ffmpeg 설치 확인**: `sudo apt install ffmpeg` (영상 생성용)
4. **google-api 패키지**: `pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib`
5. **파이프라인 테스트**: 곡 하나로 `python3 scripts/publish.py songs/01_봄이라고_부를게/ --skip-upload` 실행해 영상까지만 생성 테스트

## 재즈 프리셋 현황 (9개)

| 프리셋 | BPM | 핵심 악기 | 레퍼런스 |
|--------|-----|-----------|----------|
| smooth jazz | 80-100 | Rhodes, 소프라노 색소폰 | Kenny G |
| jazz ballad | 60-75 | 어쿠스틱 피아노, 플루겔혼 | Chet Baker |
| bossa nova | 120-140 | 나일론 기타, 플루트 | Jobim |
| cool jazz | 100-130 | 비브라폰, 테너 색소폰 | Miles Davis |
| jazz fusion | 110-140 | 일렉 기타, 슬랩 베이스 | Herbie Hancock |
| swing | 140-180 | 빅밴드, 트럼펫 | Frank Sinatra |
| **jazz bar** (신규) | 70-90 | 피아노 트리오 | Chet Baker, Bill Evans |
| **bebop** (신규) | 160-220 | 알토 색소폰, 트럼펫 | Charlie Parker |
| **vocal jazz standards** (신규) | 80-110 | 피아노, 뮤트 트럼펫 | Ella Fitzgerald |

## WTF 지표

- 전체 파일 수정 횟수: 8회
- 성공률: 100% (8/8)
- WTF: 0%
