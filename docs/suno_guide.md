# Suno AI 실전 가이드

## 기본 원리

음악 생성 = **가사 + 스타일 프롬프트 + 랜덤값(seed)**
Suno는 100% 지시를 따르는 시스템이 아니다. 같은 프롬프트라도 매번 다른 결과가 나온다.

---

## 1. 스타일 프롬프트 작성법 (GMIV 법칙)

Style of Music 칸에 입력. 쉼표로 구분.

| 요소 | 설명 | 예시 |
|------|------|------|
| **G**enre | 장르 | K-Pop, indie pop, lo-fi, jazz |
| **M**ood | 분위기/감정 | nostalgic, bittersweet, dreamy, melancholic |
| **I**nstrument | 강조 악기 | acoustic guitar, piano, strings, 808s |
| **V**ocal | 보컬 질감 | soft male vocal, breathy female, husky |

**핵심 규칙:**
- 처음 20~30단어가 가장 영향력 큼
- 악기는 2~4개만 (너무 많으면 혼동)
- 모순 태그 피하기 (`High Energy` + `Chill` ❌)
- 강조하고 싶으면 반복 (`pop, pop, rock`)
- 구체적으로 (`Synth` ❌ → `Warm Analog Synth` ✅)

**예시:**
```
Korean indie pop, soft breathy male vocal, acoustic guitar fingerpicking,
warm piano, light strings, bittersweet spring longing, intimate, 88bpm
```

---

## 2. 가사 내 섹션 태그

가사(Lyrics) 칸에 입력. 대괄호 [] 사용.

### 구조 태그
| 태그 | 용도 |
|------|------|
| `[Intro]` | 도입부 |
| `[Verse]` | 절 |
| `[Pre-Chorus]` | 프리코러스 |
| `[Chorus]` | 후렴 |
| `[Bridge]` | 브릿지 |
| `[Outro]` | 아웃트로 |
| `[Interlude]` | 간주 |
| `[Break]` | 브레이크 (멈춤) |
| `[Drop]` | 도입부 스킵, 바로 시작 |
| `[End]` | 곡 종료 신호 |

### 편곡 힌트 태그 (섹션 사이에 삽입)
| 태그 | 효과 |
|------|------|
| `[Instrumental Intro]` | 악기만 나오는 인트로 |
| `[Soft Piano]` | 피아노 단독 구간 |
| `[Build]` | 점점 고조 |
| `[Powerful Explosion]` | 후렴 터지는 느낌 |
| `[Stripped Back]` | 악기 최소화 |
| `[Fade Out]` | 페이드 아웃 |
| `[Guitar Solo]` | 기타 솔로 |
| `[Piano Solo]` | 피아노 솔로 |

### 보컬 스타일 태그
| 태그 | 효과 |
|------|------|
| `[Male Vocal]` | 남성 보컬 |
| `[Female Vocal]` | 여성 보컬 |
| `[Whisper]` | 속삭이는 보컬 |
| `[Spoken Word]` | 말하듯이 |
| `[Rap]` | 랩 |
| `[Falsetto]` | 가성 |
| `[Belting]` | 힘 있는 고음 |
| `[Duet]` | 듀엣 |
| `[Choir]` | 합창 |
| `[Vocal Style: Raspy]` | 거친 목소리 |
| `[Vocal Style: Breathy]` | 호흡 섞인 목소리 |

### 에너지/다이나믹 태그
| 태그 | 효과 |
|------|------|
| `[High Energy]` | 고에너지 |
| `[Low Energy]` | 저에너지 |
| `[Chill]` | 차분 |
| `[Driving]` | 추진력 |
| `[Explosive]` | 폭발적 |

### 프로덕션 텍스처 태그
| 태그 | 효과 |
|------|------|
| `[Lo-fi]` | 로파이 질감 |
| `[Clean]` | 깔끔한 사운드 |
| `[Raw]` | 날것의 느낌 |
| `[Atmospheric]` | 공간감 |
| `[Tape-Saturated]` | 테이프 포화 느낌 |

### 음향효과 태그
| 태그 | 효과 |
|------|------|
| `[Rain]` | 비 소리 |
| `[Phone Ringing]` | 전화벨 |
| `[Silence]` | 무음 구간 |
| `[Applause]` | 박수 |

---

## 3. 가사 작성 팁

- **괄호 ( ) 안의 가사**: 코러스/배경 보컬처럼 겹쳐 들림
  ```
  너를 봄이라고 부를게 (봄이라고 부를게)
  ```
- **마침표/쉼표**: 호흡과 발음 조절에 도움
- **가사 줄 수**: 한 섹션에 6줄 권장. 10줄 넘으면 랩처럼 빨라짐
- **한국어 발음**: 스타일란에 `Clear Korean Pronunciation` 추가하면 개선

---

## 4. Extend (곡 확장) 사용법

기본 생성은 ~2분. 전곡 만들려면 Extend 필수.

### 방법:
1. 마음에 드는 클립 생성 (Verse 1 + Chorus 1)
2. 해당 클립에서 **Extend** 클릭
3. 이어질 가사 입력 (Verse 2부터)
4. 같은 보컬/사운드가 유지됨

### 보컬 일관성 유지 핵심:
```
1단계: Verse 1 + Pre-Chorus + Chorus 1 생성 → 좋은 보컬 클립 선택
2단계: 그 클립에서 Extend → Verse 2 + Chorus 2
3단계: 다시 Extend → Bridge + Final
```

### 팁:
- 처음부터 전체를 한 번에 생성하지 말 것
- Extend 시 이전 가사를 프롬프트에 포함하면 더 잘 인식
- `[Drop]` 태그로 앞부분 생략 가능

---

## 5. Custom Mode 활용

직접 작성한 가사를 넣는 모드.

- Style of Music: 스타일 프롬프트 입력
- Lyrics: 가사 + 섹션 태그 + 편곡 태그 입력
- Title: 곡 제목

**AI가 가사의 운율에 맞춰 멜로디를 설계한다.**

---

## 6. 녹음파일 업로드

자신의 목소리나 악기 녹음을 업로드하면 그 위에 확장.

- 길이: 6초~60초
- 용도: 원하는 분위기/음색을 직접 입력
- Extend로 확장 가능

---

## 7. 실전 워크플로우

```
1. 가사 완성 (섹션 태그 포함)
2. 스타일 프롬프트 작성 (GMIV 법칙)
3. Custom Mode로 1~2분 클립 생성 (여러 번 시도)
4. 마음에 드는 보컬/사운드 클립 선택
5. Extend로 나머지 섹션 이어붙이기
6. 필요하면 스타일 프롬프트 미세 조정 후 재생성
7. 최종 버전 다운로드
```

---

## 8. 주의사항

- Suno는 랜덤 기반이라 같은 프롬프트도 매번 다른 결과
- 태그를 너무 많이 넣으면 오히려 혼란
- 남의 프롬프트를 그대로 쓰면 같은 결과가 안 나올 수 있음 (seed가 다르니까)
- 효과 있는 태그 조합은 기록해두기
- 무료 플랜: 상업적 이용 불가 / 유료 플랜: 수익화 가능

---

## Sources
- [Suno Tags Complete Guide - Musci.io](https://musci.io/blog/suno-tags)
- [Suno AI 사용법 2026 - 캐럿 블로그](https://carat.im/blog/suno-ai-usage-guide)
- [AI 창작 갤러리 - Suno 초보자 가이드](https://gall.dcinside.com/mgallery/board/view/?id=aicreate&no=36443)
- [AI 창작 갤러리 - Suno 사용 후기](https://gall.dcinside.com/mgallery/board/view/?id=aicreate&no=55963)
- [Suno Meta Tags Guide - Jack Righteous](https://jackrighteous.com/en-us/pages/suno-ai-meta-tags-guide)
- [Suno Voice Tags Guide](https://howtopromptsuno.com/making-music/voice-tags)
