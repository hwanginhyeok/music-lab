# 봄이라고 부를게 — Suno 프롬프트 v3 (사용자 피드백 반영)

## Style of Music
```
Korean indie band, emotional dreamy male vocal, acoustic guitar, light drums, soft piano, bittersweet spring longing, intimate, 92bpm
```

> 글자 수: 131자 (200자 제한 이내)
>
> **사용자 검증 조합**: `male vocal, emotional, dreamy, indie band, acoustic guitar, light drums`
> lo-fi 태그 완전 제거 (음질 저하 원인 확인됨)

---

## Lyrics (Suno 형식 — 바로 복붙 가능)

[Instrumental Intro]

[Verse 1]
자꾸 네 이름이 입에서 피어나
벚꽃 같다고 하면 너무 뻔한 거잖아
그냥 삼월의 바람이 불 때마다
고개를 돌리게 돼 네가 걷던 쪽으로

커피잔 위에 김이 피는 것처럼
네 흔적도 그렇게 흐릿하게 올라와
선명하진 않은데 분명히 따뜻해
그런 너를 뭐라고 불러야 되는 걸까

[Pre-Chorus]
[Build]
이름을 불러도 돌아오지 않으니까
계절을 빌려 너를 부를게

[Chorus]
너를 봄이라고 부를게
따뜻한 게 네 탓인 것 같아서
꽃이 피는 건 원래 그런 거라며
괜히 설레는 것도 네 탓이라고 할게

I wanna call you spring
그래야 일 년에 한 번은
너를 다시 만날 수 있으니까

[Interlude]

[Verse 2]
둘 다 알면서 모른 척했던 밤
택시 두 대가 반대로 꺾어진 골목
그렇게 우리 처음 싸웠잖아
그 길을 오늘도 그냥 지나쳐왔어

사실은 우리 눈 오던 날 끝났잖아
그날 네 목도리가 눈에 선명하잖아
네가 없는 계절이 이렇게 밝으면
좀 이상하잖아 혼자만 봄인 것 같아

[Pre-Chorus]
[Build]
이름을 불러도 돌아오지 않으니까
번호를 눌러 너를 불러볼게

[Chorus]
센치 해져서가 아니라
네가 보고 싶어서 전화했어
꽃이 피는 건 사실 다 핑계였어
그냥 네 목소리가 듣고 싶었던 거야

I just called you, wanna see you
사실은 매일 너를 생각해
봄보다 네가 항상 먼저였어

[Bridge]
[Stripped Back]
[Spoken Word]
투르르 투르르
신호만 다섯 번째
니 목소리가 들리면
나는 아마 또
요즘 날씨 낭만 있지 않아?
물어보겠지

괜히 날씨 얘길 하겠지
네 안부를 묻고 싶은데

[Final Chorus]
[Fragile]
너를 봄이라고 부를게
네가 보고 싶어서 전화했어
같은 말인데... 이상해
봄은 매년 오잖아, 근데 너는

I wanna call you spring
I just called you, wanna see you
너를 봄이라고 부르고 싶어서
네가 보고 싶어서 전화했어

[Outro]
[Fade Out]

---

## 프롬프트 설계 노트

| 항목 | v2/final | v3 | 변경 이유 |
|------|----------|----|-----------|
| 텍스처 | `lo-fi bedroom recording, warm tape texture` | 제거 | **사용자 확인**: lo-fi가 음질 저하 직접 원인 |
| 장르 | `Korean indie pop` | `Korean indie band` | **사용자 검증**: indie band가 원하는 사운드에 가장 가까움 |
| 보컬 | `clear bright male vocal, youthful pure tone, gentle vibrato` | `emotional dreamy male vocal` | **사용자 검증**: emotional + dreamy 조합이 감성적 톤을 노이즈 없이 유도 |
| 드럼 | 없음 | `light drums` 추가 | **사용자 검증**: 밴드 사운드에 가벼운 드럼 필요 |
| 악기 태그 | `acoustic guitar fingerpicking` | `acoustic guitar` | fingerpicking은 Suno 재량에 맡김 |
| 섹션 태그 | 악기 진입 지시 5개 | 제거 | 편곡 세부지시 → Suno 해석 실패 시 아티팩트 유발 |

---

## 이전 버전 대비 변경 사항 요약

### 핵심 변경
1. **`lo-fi bedroom recording, warm tape texture` 완전 제거** — 노이즈 유발 태그 소거
2. **`clear Korean pronunciation` 신규 추가** — 한국어 발음 안정화
3. **`clean male vocal`로 보컬 지시 단순화** — bright/pure/youthful 중 clean 하나로 집중

### 섹션 태그 간소화
- 악기 진입 지시 태그 전부 제거 (5개 → 0개)
- 편곡 힌트는 `[Build]`, `[Stripped Back]`, `[Fragile]`, `[Fade Out]` 4개만 유지
- `[Spoken Word]`는 Bridge 통화 분위기에 필수이므로 유지

### 유지한 것
- `[Build]` x2 — Pre-Chorus 긴장감 유도에 효과적
- `[Stripped Back]` — Bridge 미니멀 사운드 유도
- `[Spoken Word]` — 전화 통화 질감 필수
- 영어 후크 라인 (`I wanna call you spring`, `I just called you, wanna see you`) — 멜로디 레이아웃 앵커 역할
- 배경 코러스 괄호 표기 `(봄이라고 부르고 싶어서)` — Final 여운

---

## Extend 전략 (권장)

**1단계**: [Verse 1] + [Pre-Chorus] + [Chorus 1] 생성 → 보컬 마음에 드는 클립 선택
**2단계**: 선택 클립에서 Extend → [Verse 2] + [Pre-Chorus 2] + [Chorus 2]
**3단계**: 다시 Extend → [Bridge] + [Final Chorus] + [Outro]

> 한 번에 전곡 생성 시 노이즈 발생 확률 높아짐. Extend 분할 권장.
