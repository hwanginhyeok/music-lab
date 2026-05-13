# Suno AI 고급 활용 가이드 (2025–2026)

> **목적**: music-lab 재즈 채널 운영에서 Suno로 더 정교한 곡을 만들기 위한 실전 레퍼런스.
> **모델 기준**: v4.5 (2025-05-01 출시) / v4.5+ (2025-07-17) / v5 (2025-09) / v5.5.
> **마지막 업데이트**: 2026-05-13.

목차:
1. [모델별 변화 요약](#1-모델별-변화-요약)
2. [스타일 프롬프트 엔지니어링](#2-스타일-프롬프트-엔지니어링)
3. [메타태그와 보컬 제어](#3-메타태그와-보컬-제어)
4. [Negative Prompt(Exclude Styles)](#4-negative-promptexclude-styles)
5. [곡 구조 설계 — Structure Tags](#5-곡-구조-설계--structure-tags)
6. [가사(Lyrics) 최적화](#6-가사lyrics-최적화)
7. [v4.5/4.5+ 핵심 기능 — Extend, Cover, Persona, Spark](#7-v4545-핵심-기능--extend-cover-persona-spark)
8. [Audio Input & Inspire](#8-audio-input--inspire)
9. [스템 분리 & 후처리 워크플로우](#9-스템-분리--후처리-워크플로우)
10. [프로덕션 파이프라인 — 반복·선별·자동화](#10-프로덕션-파이프라인--반복선별자동화)
11. [실전 예시 프롬프트 7선 (재즈 중심)](#11-실전-예시-프롬프트-7선-재즈-중심)
12. [music-lab 통합 체크리스트](#12-music-lab-통합-체크리스트)
13. [참고 자료](#13-참고-자료)

---

## 1. 모델별 변화 요약

| 모델 | 출시 | 핵심 변화 | 곡 길이 | Style 길이 |
|------|------|----------|--------|-----------|
| v3.5 | 2024 | 한국어 가사 약함, 보컬 거칠음 | 4분 | 200자 |
| v4 | 2024-11 | 보컬 명료도/믹스 개선 | 4분 | 200자 |
| **v4.5** | **2025-05-01** | 자연어 프롬프트, 장르 블렌딩, 8분, Persona 강화 | **8분** | **1000자** |
| v4.5+ | 2025-07-17 | Vocal Swap, Instrumental Flip, Spark | 8분 | 1000자 |
| v5 | 2025-09 | 다국어(한국어) 발음 대폭 개선, 스튜디오 | 8분+ | 1000자 |
| v5.5 | 2025말 | 보컬 페르소나(Voice Clone), MILO-1080 | 8분+ | 1000자 |

**실무 권장**: 한국어 보컬은 **v5 이상**. 가성비/안정성은 v4.5. v3.5는 더 이상 사용하지 않음.

---

## 2. 스타일 프롬프트 엔지니어링

### 2.1 길이와 토큰 우선순위

- v4.5+ 부터 **Style Prompt 1,000자 제한**. 초과분은 **경고 없이 잘림(silent truncation)**.
- 따라서 **앞쪽 20–30 단어에 핵심 태그**(장르 + 보컬 + 분위기 + 핵심 악기)를 배치.
- 권장 분량: 핵심 200–400자 + 디테일 200–400자. 1,000자 꽉 채우는 게 좋지 않음 — 노이즈로 작동.

### 2.2 키워드형 vs 자연어형

| 방식 | 예시 | 권장 시점 |
|------|------|-----------|
| **키워드 나열** | `deep house, emotional, melodic, hypnotic, organic textures` | v4 이하, 빠른 A/B 테스트 |
| **자연어 서술** | `Create a melodic, emotional deep house song with organic textures and hypnotic rhythms. Begin with soft ambient layers and a deep, steady groove. Build gradually with flowing melodic synths, warm basslines, and intricate, subtle percussion.` | **v4.5+ 표준** |

v4.5 부터 자연어가 강하게 반영된다. "Create"/"Make"/"Generate" 같은 **명령형은 빼고 묘사형으로** 쓸 것.
- ❌ "Create an upbeat pop track..."
- ✅ "Upbeat pop track..."

### 2.3 태그 우선순위 (절대 규칙)

```
[1] 메인 장르 + 서브장르      ← 반드시 첫 줄
[2] 시대/지역 (1960s, K-, Latin)
[3] 보컬 (gender, texture, language)
[4] BPM + Key (선택, 안정성 ↑)
[5] 핵심 악기 2–3개
[6] 분위기/감정 1–2개
[7] 프로덕션 디테일 (warm, dry, lo-fi, hi-fi)
```

> **"1–2 장르 / 2–3 악기 / 1–2 분위기" 원칙**. 더 늘리면 평균화돼서 generic해진다.

### 2.4 흔한 실패 패턴 → 수정

| 실패 패턴 | 왜 안 됨 | 수정 |
|-----------|----------|------|
| "Rock music" | 너무 광범위 → AI가 평균치 생성 | "Energetic 1980s synth-pop with gated drums, bright analog arps" |
| "Sounds like The Beatles" | 아티스트명은 무시되거나 모방 위험 | "Jangly guitar-driven pop with vocal harmonies, 1960s British Invasion style" |
| "Happy song" | 무드만 있으면 평면적 | "Uplifting and triumphant, big anthemic chorus and wide pads, for a product launch" |
| 30+ 태그 나열 | 충돌·노이즈로 generic해짐 | 5–8개로 압축 |
| "Drum fill at 0:45, crash at 1:12..." | 과도한 타임라인 지시 → 기계적 | 구조 태그로만 가이드 |

---

## 3. 메타태그와 보컬 제어

### 3.1 메타태그 문법

- **대괄호 `[]`**: 가사 박스 안에서 사용 — 구조/악기/효과 지시.
- **소괄호 `()`**: 보컬 딜리버리 지시 — `(whispered)`, `(belted)`, `(falsetto)` 등.
- **중괄호 `{}`** (v5+): 그룹 보컬 지시 — `{backup vocals: "ohh ahh"}`.

### 3.2 보컬 텍스처 사전

Suno가 인식하는 보컬 텍스처:

```
breathy, raspy, smooth, gritty, airy, warm, powerful, intimate,
whispered, belted, falsetto, nasal, operatic, husky, silky,
sultry, ethereal, raw, polished, gravelly
```

조합 예: `smoky jazz vocal, husky female, intimate breathy delivery`.

### 3.3 보컬 다이내믹 아크

가사 안에 단계적 변화를 지시:

```
[Verse - whispered]
손끝에 닿는 차가운 공기

[Pre-Chorus - building intensity]
하나둘 떠오르는 잔상들이

[Chorus - belted, powerful]
지금 이 순간을 붙잡아
```

### 3.4 BPM/Key 지정

- **BPM은 정확한 메트로놈 락이 아님** — "approximate guidance"로 작동. 그래도 그루브 안정에 효과 있음.
- **Key 지정**(예: `G major`, `A minor`)은 후처리 믹싱 호환성에 유리.
- 권장: BPM은 ±10 정도 흔들린다 가정. 정확한 BPM이 필요하면 후처리에서 타임스트레치.

### 3.5 Instrumental Toggle vs 메타태그

| 목표 | 수단 |
|------|------|
| 전체 트랙 가사 없음 | Create 화면 **Instrumental 토글** ON |
| 특정 섹션만 인스트루멘탈 | 가사에 `[Instrumental Break]` 또는 `[Solo: Saxophone]` |
| 보컬 없이 백킹만 | 토글 + Style에 `instrumental only, no vocals` |

---

## 4. Negative Prompt (Exclude Styles)

### 4.1 접근 경로

- **Pro/Premier 플랜 전용** 기능.
- Create → **Custom Mode** → **Advanced Options** → **Exclude Styles** 토글 ON.
- 입력란에 빼고 싶은 요소 콤마로 나열.

### 4.2 제외 가능 요소

- **악기**: `piano, electric guitar, saxophone, autotune`
- **스타일**: `lo-fi, country, EDM drop`
- **보컬**: `male vocals`, `female vocals`, `choir`, `crowd vocals`
- **음향 효과**: `vinyl crackle, tape hiss, distortion`

### 4.3 실전 팁

- Style 본문(positive)에는 `one lead singer only`처럼 **긍정형 지시**를 먼저 쓰고, Exclude에 추가로 `choir, crowd vocals, harmonies`를 넣으면 백킹 보컬을 효과적으로 차단할 수 있다.
- Exclude 총 길이 **200자 이내** 권장. 2–3개 핵심 제외만.
- **steering instruction**이지 absolute command가 아님 → 10–20% 확률로 새어 나옴. 마음에 안 들면 재생성.

### 4.4 음악-랩 적용 예 (재즈 채널)

| 시나리오 | Positive 핵심 | Exclude |
|----------|---------------|---------|
| Instrumental jazz | `acoustic jazz trio, brushed drums, upright bass` | `vocals, choir, autotune, synth` |
| Vocal jazz (남성만) | `male jazz vocal, smoky baritone, intimate` | `female vocals, choir, crowd vocals` |
| Bossa nova | `bossa nova, nylon guitar, soft female vocal` | `electric guitar, autotune, EDM drum` |

---

## 5. 곡 구조 설계 — Structure Tags

### 5.1 핵심 태그

| 태그 | 역할 | 평균 길이 |
|------|------|-----------|
| `[Intro]` | 무드 셋업 | 8–15초 |
| `[Verse]` | 스토리텔링, 낮은 에너지 | 16–24초 |
| `[Pre-Chorus]` | 코러스 빌드업 | 8–12초 |
| `[Chorus]` | 후크, 최고 에너지 | 16–24초 |
| `[Bridge]` | 대비 섹션 (조성/감정 변화) | 12–20초 |
| `[Break]` | 리듬·텍스처만 남기는 구간 (드럼/신스만) | 4–12초 |
| `[Solo: Sax]` / `[Solo: Guitar]` | 악기 솔로 | 8–20초 |
| `[Outro]` | 페이드/엔딩 | 8–16초 |
| `[End]` | 명확한 종결(이게 없으면 곡이 어색하게 자름) | — |

### 5.2 검증된 곡 구조 템플릿

**A. 표준 팝/재즈 (3분대)**
```
[Intro] → [Verse 1] → [Pre-Chorus] → [Chorus]
→ [Verse 2] → [Pre-Chorus] → [Chorus]
→ [Bridge] → [Chorus] → [Outro] [End]
```

**B. 재즈 인스트루멘탈 (4–5분)**
```
[Intro - head melody]
[Verse - melody statement]
[Solo: Piano]
[Solo: Saxophone]
[Bridge - reharmonization]
[Verse - melody restatement]
[Outro - tag ending] [End]
```

**C. 짧은 광고/숏폼 (60–90초)**
```
[Intro 4s] → [Verse 12s] → [Chorus 20s] → [Outro 8s] [End]
```

### 5.3 곡 길이 제어

- v4.5+ 부터 **단일 생성으로 8분까지** 가능 (이전엔 4분 + Extend).
- 가사 분량으로 길이를 간접 제어: 짧은 가사(8–12줄) → 2–3분, 긴 가사(30+줄) → 5–7분.
- 정확한 길이가 필요하면 **Extend 기능**으로 후속 섹션을 이어 붙이고 마지막에 트림.
- `[End]` 태그를 반드시 마지막에 — 없으면 페이드 아웃이 어색하게 잘릴 수 있다.

### 5.4 반복 vs 변형

- Suno는 같은 `[Chorus]` 태그가 반복되면 **거의 동일한 멜로디**를 다시 부른다. 좋다.
- 변형을 원하면 `[Chorus - softer]`, `[Final Chorus - key change, full band]`처럼 **부연 설명**을 붙인다.
- `[Bridge]` 다음 `[Chorus]`는 자연스럽게 **반음/온음 키체인지**를 시도하는 경향이 있음.

---

## 6. 가사(Lyrics) 최적화

### 6.1 가사 길이 규칙

- **Lyrics 박스 3,000자 제한** (약 40–60줄, 200–300 단어).
- 한 섹션은 4–8줄 권장. 너무 길면 한 섹션 안에서 멜로디가 평면화.
- 한 줄은 **6–10 음절** 권장. 11+ 음절이면 Suno가 빨리 뱉으면서 발음이 뭉개진다.

### 6.2 한국어 가사 — 핵심 규칙

| 규칙 | 이유 |
|------|------|
| **반드시 한글로**, 로마자 절대 금지 | v4.5+ 는 Hangul을 직접 잘 처리. 로마자는 영어로 오인식. |
| 한 줄 6–10 음절 | 한국어는 음절 밀도가 높아 영어보다 짧게 끊어야 자연스러움. |
| 받침 많은 단어는 줄 끝에 배치 | 자음 클러스터가 줄 중간에 오면 발음이 뭉친다. |
| Style에 `Clear Vocals`, `High Fidelity Vocals` 추가 | 한국어 발음 명료도 ↑. |
| v5 이상 사용 | 한국어 발음 품질이 v4.5 대비 체감 큼. |

### 6.3 영어+한국어 혼합 (K-Pop 패턴)

```
[Verse]
어둠 속에서 (in the dark)
빛나는 너의 그림자

[Pre-Chorus]
망설이지 마, don't look back

[Chorus]
Take my hand, 나를 잡아
끝까지 함께 가자, all night long
```

- 영어 구를 후크/포스트 코러스에 배치 — K-Pop의 전형적 구조.
- 한 줄 안에서 언어를 바꾸면 가끔 끊김 → **줄 단위로 언어 분리** 권장.

### 6.4 보컬 디렉팅 인라인 태그

```
[Verse]
(whispered) 손끝에 닿는 너의 온기
(softly) 멀어지는 발자국 소리

[Chorus]
(belted, powerful) 다시는 놓지 않을 거야!
(harmony: "ohh yeah") 끝까지 함께 가자

[Bridge]
(falsetto) 멀리서 들려오는

[Outro]
(ad-lib: "yeah, oh oh")
[End]
```

### 6.5 백킹 보컬·하모니·애드립 문법

| 효과 | 문법 | 예시 |
|------|------|------|
| 백킹 보컬 | `{backup vocals: "텍스트"}` | `{backup vocals: "ooh la la"}` |
| 하모니 | `{harmony: "텍스트"}` 또는 `[Harmony]` 섹션 | `{harmony: "ohh yeah"}` |
| 레이어드 보컬 | `{layered vocals: "텍스트"}` | `{layered vocals: "all night"}` |
| 애드립 | `(ad-lib: "yeah")` 또는 `[Ad-lib]` | `(ad-lib: "uh huh")` |
| 콜앤리스폰스 | 일반 라인 + `{response: "텍스트"}` | — |

### 6.6 발음 교정 6가지 기법 (영어 단어)

생성 후엔 발음 수정 불가 — **생성 전에 가사 단계에서 수정** 필수.

1. **단순 표기**: `through` → `thru`, `enough` → `enuff`
2. **하이픈 분절**: `tonight` → `to-night`, `something` → `some-thing`
3. **음성 표기**: `colonel` → `kernel`, `Wednesday` → `Wenz-day`
4. **약어 분리**: `AI` → `A-I`, `DJ` → `dee-jay`
5. **동음이의어 치환**: `your` → `yore`, `read(past)` → `red`
6. **숫자 풀어쓰기**: `24/7` → `twenty four seven`, `2024` → `twenty twenty-four`

한국어는 받침 문제가 많을 때 띄어쓰기·하이픈으로 음절을 분리해 보면 개선될 때 있음.

---

## 7. v4.5/4.5+ 핵심 기능 — Extend, Cover, Persona, Spark

### 7.1 Extend

기존 곡 끝에 새 섹션을 이어 붙임.
- **사용 시점**: 좋은 후렴이 나왔는데 브릿지·아웃트로가 어색할 때.
- **워크플로우**:
  1. 만족스러운 곡 선택 → ⋮ → **Extend**
  2. 잘라낼 시작점 선택 (보통 후렴 직후)
  3. 새 가사·새 스타일 입력 → 생성
- **팁**: Extend는 **앞 구간의 톤·믹스를 99% 유지**한다 → 톤 일관성 활용. 단, 장르 급변은 어색.

### 7.2 Cover

원곡의 **멜로디·구조는 유지**, **장르·악기·보컬은 바꿈**.
- 예: 발라드 → 보사노바, 록 → 재즈.
- v4.5에서 **장르 전환이 매끄러워짐**.
- **음악-랩 활용**: 같은 곡을 5개 장르 버전으로 만들어 채널 다양성 확보.

### 7.3 Persona — 보컬 캐릭터 고정

**A. 곡에서 Persona 생성** (모든 유료 플랜)
1. Library에서 마음에 드는 곡 선택 → ⋮ → **Create Persona**
2. 이름 지정 → 저장
3. 이후 새 곡 만들 때 Persona 선택 가능

**B. 내 목소리로 Persona 만들기 (v5.5 Voice Persona, Pro/Premier)**
1. 3–5분 분량의 **드라이 보컬**(리버브·BGM 없음) 녹음
2. Upload → 짧은 voice check (한 줄 낭독)
3. Suno가 Persona 모델 빌드 (3–5분 처리)
4. 테스트 클립 들어보고 → 마음에 들면 저장
5. 새 곡 생성 시 voice 옵션에서 선택

> **주의**: Voice Persona는 "정확한 클론"이 아니라 **음색·피치 특성을 캡처한 모델**. AI가 자기 스타일로 부른다.

### 7.4 Vocal Swap & Instrumental Flip (v4.5+, 2025-07-17)

- **Vocal Swap**: 가사·멜로디 유지, 보컬리스트만 교체. Library → ⋮ → Vocal Swap.
- **Instrumental Flip**: 보컬 유지, 백킹만 다른 장르로. 발라드 보컬에 재즈 백킹 입히기 등.
- 두 개를 조합하면 **장르 마이그레이션**이 사실상 자유롭다.

### 7.5 Spark from Playlist

- 5–10곡짜리 **플레이리스트를 레퍼런스로** 새 곡 생성.
- 텍스트 프롬프트를 안 써도 됨 → 본인이 만든 좋은 곡들을 모아 두면 스타일 일관성 유지.
- **음악-랩 활용**: 채널 정체성이 잡힌 후, 채널 베스트 10곡을 Spark에 넣어 후속곡 생성.

### 7.6 Remaster

같은 곡을 두 가지 AI 믹스 버전으로 다시 마스터링.
- 같은 가사·멜로디로 **다른 톤·믹스**를 비교할 때.
- 출시 전 A/B 테스트용.

---

## 8. Audio Input & Inspire

### 8.1 Audio Input (Upload Audio)

- **6–60초 클립**(Free) / **최대 8분**(Pro/Premier)을 업로드해서 그 무드·텍스처를 새 곡으로 발전.
- 가능 입력: 허밍, 즉흥 연주, 인스트루멘탈 데모, 환경 사운드.
- **저작권 곡은 자동 차단**. 보컬 포함 업로드는 비공개 보호.
- **음악-랩 활용**: MIDI/FluidSynth로 만든 데모(OGG)를 업로드해서 Suno 보컬 곡으로 발전.

### 8.2 Inspire (+Inspo 버튼)

- 본인이 이미 만든 곡들로 구성된 **플레이리스트**를 기반으로 새 곡 영감 생성.
- Spark와 비슷하지만 더 가볍게 "분위기만" 가져온다.
- 곡 작업 폼 우측 가사 박스 위 **+Inspo** 버튼.

---

## 9. 스템 분리 & 후처리 워크플로우

### 9.1 Suno Stem Extraction

Library/Workspace/Song Editor → ⋮ → **Get Stems**.

**Basic**: Vocals + Instrumental (2 stems)
**Advanced (Stem Extraction Pro)**: 최대 **12 stems**
- drums, bass, lead vocals, background vocals, guitar, piano, synths, strings, brass, effects, additional layers

**출력 포맷**:
- MP3 / WAV / Tempo-Locked WAV (평균 BPM 동기화) / MIDI / WAV+MIDI 콤보

### 9.2 스템의 한계 (필독)

- **재생성 방식 분리**: 빼기 방식이 아니라 AI가 "이렇게 들렸을 것"을 재합성 → **블리드 발생** (드럼 스템에 보컬 잔향, 보컬 스템에 악기 노이즈).
- **레벨 불균형**: 베이스가 보컬 압도, 중역 충돌, 고역이 너무 거칠거나 너무 둔함.
- 따라서 **그대로 쓰지 말 것** — DAW에서 EQ + 게인 스테이징 + 컴프 필수.

### 9.3 DAW 후처리 워크플로우

```
1. Suno 생성 → Stem Export (Advanced, WAV)
2. DAW(Ableton/Logic/FL Studio/Reaper)에 임포트
3. Gain Staging — 각 스템 -18 dBFS 기준
4. EQ — 보컬 200Hz 컷, 드럼 8kHz 부스트 등 기본 처리
5. Compression — 보컬 3:1, 드럼 4:1
6. Bleed Cleanup — 드럼 스템의 보컬 잔향은 사이드체인 게이트
7. 결손 음원 추가 — 베이스가 약하면 신스 베이스 레이어
8. Master Bus — Limiter -1.0dB 천장, -14 LUFS(YouTube/Spotify) or -9 LUFS(Loud)
9. Bounce → 외부 마스터링 (Cryo Mix, RoEx Automix, Matchering 등)
```

### 9.4 무료/저비용 후처리 도구

| 도구 | 용도 | 비용 |
|------|------|------|
| **Demucs** (오픈소스) | 추가 스템 분리, Suno 스템 보강 | Free |
| **Matchering** | 레퍼런스 곡에 매칭 마스터링 | Free (PyPI) |
| **Pedalboard** (Spotify) | Python에서 리버브/컴프 자동화 | Free |
| **iZotope Ozone Elements** | 원클릭 마스터링 | ~$129 |
| **RoEx Automix** | AI 자동 믹싱 | 구독 |
| **LANDR / CloudBounce** | AI 마스터링 | 구독 |

> music-lab에 이미 `mix_stems.py`와 `audio-process` 스킬이 있음 — Demucs + Pedalboard + Matchering 파이프라인이 구축돼 있다. 이걸 표준으로 쓸 것.

### 9.5 라우드니스 목표

| 채널 | 목표 LUFS | True Peak |
|------|-----------|-----------|
| YouTube | -14 | -1.0 dBTP |
| Spotify | -14 | -1.0 dBTP |
| Apple Music | -16 | -1.0 dBTP |
| TikTok/Reels | -10 ~ -12 | -1.0 dBTP |

---

## 10. 프로덕션 파이프라인 — 반복·선별·자동화

### 10.1 권장 사이클

```
1. 컨셉 (1곡) — 가사 v1 + Style Prompt v1
2. 1차 배치 — 같은 프롬프트로 4–8회 생성 (Suno는 한 번 클릭에 2 variant)
3. 1차 선별 — 30초 들으며 후크 살아있는지만 체크 → 50% 컷
4. 2차 배치 — 살아남은 후보 각각 Extend or Vocal Swap or Remaster
5. 2차 선별 — 풀버전 듣고 1–2곡 픽
6. Stem Export → DAW 후처리 → 마스터링
7. 썸네일 + 메타데이터 → 게시 게이트(사용자 승인) → 업로드
```

### 10.2 버전 관리 — 프롬프트·결과 매핑

곡 디렉토리에 **`suno_runs.jsonl`** 같은 로그를 남길 것:

```jsonl
{"run_id": "01-001", "ts": "2026-05-13T14:22", "model": "v4.5", "style": "...", "lyrics_hash": "abc123", "exclude": "...", "song_ids": ["uuid1","uuid2"], "rating": null}
{"run_id": "01-002", "ts": "2026-05-13T14:35", "model": "v4.5", "style": "...", "lyrics_hash": "abc123", "exclude": "...", "song_ids": ["uuid3","uuid4"], "rating": 4}
```

- `lyrics_hash`만 같으면 동일 가사로 다른 스타일 비교 가능.
- 좋은 결과의 run_id를 메모리에 저장하면 다음 곡 작업 때 재활용.

### 10.3 자동화 가능 부분

| 단계 | 자동화 가능? | 방법 |
|------|--------------|------|
| 가사 생성 | ✅ | Claude/GLM → `[Verse]` 태그 포함 가사 |
| Style Prompt 생성 | ✅ | suno-prompt-engineer 에이전트 |
| Suno 생성 | △ | 공식 API 없음. 비공식 API(`gcui-art/suno-api`) 또는 undetected-chromedriver |
| 다운로드 | ✅ | music-lab `suno_download.py` (Clerk JWT) |
| 영상 생성 | ✅ | `scripts/create_video.py` (커버 + 오디오 → MP4) |
| 썸네일 | ✅ | `scripts/generate_thumbnail.py` (Pillow) |
| YouTube 업로드 | ✅ | `scripts/youtube_upload.py` (OAuth) |
| 게시 결정 | ❌ | **사용자 승인 게이트 필수** (publish-gate.md) |

### 10.4 Suno API 현황 (2026-05 기준)

- **공식 API는 베타 파트너 전용** — 일반 사용자는 키 발급 불가.
- 비공식/3rd party:
  - `gcui-art/suno-api` (오픈소스, Clerk JWT 우회) — 안정적
  - `docs.sunoapi.org` (유료 API 게이트웨이)
  - APIPASS, LaoZhang, kie.ai — 계정 풀 관리형 유료
- music-lab은 **`suno_download.py`에서 Clerk JWT 방식으로 다운로드만 자동화**. 생성은 VNC + undetected-chromedriver 또는 수동 (D-004 히스토리 참고).
- 동시실행 충돌: VNC 1개당 1세션만 (DIFFICULTY D-004).

---

## 11. 실전 예시 프롬프트 7선 (재즈 중심)

### 예시 1: 스무드 재즈 발라드 (보컬, v4.5)

**Style Prompt:**
```
Smooth contemporary jazz ballad, intimate female vocals in Korean,
warm Rhodes electric piano, brushed drums, upright bass, soft tenor sax solo,
86 BPM in F major, late-night cafe mood, dry intimate mix,
high fidelity vocals, clear pronunciation
```

**Lyrics (발췌):**
```
[Intro - Rhodes only, 8s]

[Verse 1 - whispered]
새벽 두 시의 골목길에
혼자 걷는 너의 그림자

[Pre-Chorus - building]
멀어지는 발자국 소리
들리지 않게 숨죽이고

[Chorus - intimate, breathy]
괜찮아 나는, 괜찮을 거야
이 밤이 지나면 다 잊을 수 있어
{harmony: "ohh yeah, ohh"}

[Solo: Tenor Sax, 16s]

[Verse 2 - softer]
...

[Final Chorus - belted, fuller band]
괜찮아 나는, 괜찮을 거야

[Outro - sax tag]
[End]
```

**Exclude**: `EDM drum, autotune, choir, crowd vocals`

---

### 예시 2: 재즈 인스트루멘탈 트리오 (악기 위주, v4.5)

**Style Prompt:**
```
Acoustic jazz trio, piano lead, walking upright bass, brushed drums,
ballad tempo 72 BPM in Bb major, late Bill Evans style,
warm reverb, intimate club recording, no vocals, instrumental only
```

**Lyrics**: (비워두고 Instrumental 토글 ON) 또는 구조 가이드만:
```
[Intro - solo piano head, 12s]
[Head - piano melody, bass walks, 32s]
[Solo: Piano, 48s]
[Solo: Upright Bass, 32s]
[Head restatement, 24s]
[Outro - tag ending]
[End]
```

**Exclude**: `vocals, drums kit aggressive, synth, electric guitar`

---

### 예시 3: 보사노바 (한국어 보컬, v5)

**Style Prompt:**
```
Bossa nova, soft Korean female vocals, nylon string guitar, light percussion,
shaker, soft flugelhorn, 110 BPM in A minor, warm Rio de Janeiro evening mood,
clean dry production, high fidelity vocals, clear pronunciation
```

**Lyrics:**
```
[Intro - nylon guitar, 8s]

[Verse 1]
바람이 부는 해변에
모래 위 발자국 하나둘

[Chorus]
오늘은 천천히 걸어볼래
시간이 멈춘 것처럼
{backup vocals: "ahh, ahh"}

[Verse 2]
파도가 멀어지는 소리
나의 마음도 멀리

[Bridge - flugelhorn solo, 16s]

[Final Chorus]
오늘은 천천히 걸어볼래

[Outro - shaker only fade]
[End]
```

**Exclude**: `electric guitar, EDM, autotune, choir`

---

### 예시 4: K-Jazz 퓨전 (영한 혼합, v5)

**Style Prompt:**
```
Contemporary K-jazz fusion, smooth male vocals mixing Korean and English,
neo-soul influence, Fender Rhodes, fingerstyle bass, hip-hop drums,
muted trumpet, 92 BPM in D minor, modern intimate production,
high fidelity vocals
```

**Lyrics (혼합 패턴):**
```
[Intro - Rhodes + bass, 12s]

[Verse 1]
어둠 속 (in the dark)
빛나는 너의 그림자
멀어지는 (don't look back)
손끝의 온기

[Chorus]
Take my hand, 나를 잡아
끝까지 함께 가자, all night long
{harmony: "all night long, baby"}

[Solo: Muted Trumpet, 16s]

[Verse 2]
거리의 (down the street)
조명들이 흔들려

[Bridge - half-time, softer]
잊을 수 있을까 (can I forget)
잊지 않을 거야 (I won't)

[Final Chorus - key change up, fuller]
Take my hand, 나를 잡아

[Outro]
{ad-lib: "yeah, all night"}
[End]
```

**Exclude**: `country, rock guitar, EDM drop`

---

### 예시 5: 재즈 빅밴드 스윙 (인스트루멘탈, v4.5)

**Style Prompt:**
```
Big band swing, full horn section with saxophones trumpets and trombones,
rhythm section with piano upright bass and ride cymbal-driven drums,
Count Basie influence, 160 BPM swing feel in C major,
1950s recording warmth, no vocals, instrumental only
```

**Structure:**
```
[Intro - rhythm section pickup, 4s]
[Head - full band melody, 32s]
[Solo: Tenor Saxophone, 32s]
[Solo: Trumpet, 32s]
[Shout Chorus - full band climax, 24s]
[Head restatement, 16s]
[Outro - punchy tag ending]
[End]
```

**Exclude**: `vocals, synth, electric guitar, autotune`

---

### 예시 6: 로파이 재즈힙합 (인스트루멘탈, v4.5)

**Style Prompt:**
```
Jazzy lo-fi hip-hop beat, warm Rhodes piano with vinyl crackle,
upright bass loop, soft brushed drums with boom-bap feel,
muted trumpet sample, 78 BPM in E minor,
rainy night study mood, tape saturation, instrumental only
```

**Structure:**
```
[Intro - vinyl crackle + Rhodes, 8s]
[Loop A - main groove, 48s]
[Break - drums drop out, Rhodes only, 8s]
[Loop B - trumpet enters, 48s]
[Outro - fade with rain SFX]
[End]
```

**Exclude**: `vocals, EDM drop, autotune, aggressive drums`

> ⚠️ 메모리 노트 — Suno에서 `lo-fi` 태그가 직접 약하게 작동했던 사례 있음(`feedback_suno_style.md`). 위처럼 `jazzy lo-fi hip-hop`처럼 **앵커 장르를 명시**하고, 디테일 텍스처(`vinyl crackle`, `tape saturation`)는 별도로 풀어쓰면 더 안정적이다.

---

### 예시 7: 1960s 모던 재즈 (블루노트 스타일, v4.5)

**Style Prompt:**
```
1960s modern jazz quintet, Blue Note Records style,
hard bop influence, tenor saxophone and trumpet front line,
piano with rich chord voicings, upright bass walking lines,
Art Blakey style drums with strong ride cymbal, 140 BPM swing,
F minor, warm analog recording, no vocals, instrumental only
```

**Structure:**
```
[Intro - drum solo pickup, 4s]
[Head - sax + trumpet harmony melody, 32s]
[Solo: Tenor Saxophone, 64s]
[Solo: Trumpet, 48s]
[Solo: Piano, 48s]
[4-Bar Trades - drums and horns, 16s]
[Head restatement, 32s]
[Outro - tag and ride cymbal fade]
[End]
```

**Exclude**: `vocals, synth, electric guitar, modern production, autotune`

---

## 12. music-lab 통합 체크리스트

매 곡 작업 시 다음 체크:

- [ ] **장르 게이트**: 재즈 서브장르인가? (channel identity: jazz)
- [ ] **모델 선택**: 한국어 보컬이면 v5+, 인스트루멘탈이면 v4.5도 OK
- [ ] **Style Prompt**:
  - [ ] 첫 30 단어에 핵심 태그 (장르/보컬/BPM/Key)
  - [ ] 1,000자 이내, 핵심 200–400자 우선
  - [ ] 자연어 서술 (명령형 X)
  - [ ] `Clear Vocals`/`High Fidelity Vocals` 포함(한국어일 때)
- [ ] **Exclude Styles**:
  - [ ] 보컬 제어 (남/여 명시)
  - [ ] 원하지 않는 악기/장르 명시
  - [ ] 200자 이내
- [ ] **Lyrics**:
  - [ ] 한글로 작성(로마자 금지)
  - [ ] 한 줄 6–10 음절
  - [ ] 구조 태그 (`[Verse]`, `[Chorus]`, `[Bridge]`, `[End]`) 포함
  - [ ] 보컬 디렉팅 인라인 (`(whispered)`, `(belted)`)
  - [ ] 3,000자 이내
- [ ] **버전 관리**:
  - [ ] `songs/{번호}_{곡명}/suno_prompt_final.md` 저장
  - [ ] 생성 결과 `suno_runs.jsonl`에 로그
- [ ] **후처리**:
  - [ ] 1차 선별 후 Stem Export (Advanced)
  - [ ] `audio-process` 스킬로 보컬 분리 + 마스터링
  - [ ] -14 LUFS 라우드니스 매칭
- [ ] **게시 게이트**:
  - [ ] 사용자 리뷰 → 승인 후 YouTube 업로드 (publish-gate.md)

---

## 13. 참고 자료

### 공식 문서
- [Suno Help — V4.5 Detailed Style Instructions](https://help.suno.com/en/articles/5782849)
- [Suno Help — Better Prompts in Lyrics (V4.5)](https://help.suno.com/en/articles/5782977)
- [Suno Help — What's new in V4.5](https://help.suno.com/en/articles/5782593)
- [Suno Help — How to Use: Stem Extraction](https://help.suno.com/en/articles/6141441)
- [Suno Help — How to Exclude Elements](https://help.suno.com/en/articles/3161921)
- [Suno Help — How to Use: Audio Uploads](https://help.suno.com/en/articles/6141569)
- [Suno Help — Inspire Feature](https://help.suno.com/en/articles/6882753)
- [Suno Help — Voices: Use Your Voice in Suno (v5.5 Voice Persona)](https://help.suno.com/en/articles/11362369)
- [Suno Blog — Introducing v4.5](https://suno.com/blog/introducing-v4-5)
- [Suno Blog — Audio Inputs](https://suno.com/blog/audio-inputs)
- [Suno API Docs](https://docs.sunoapi.org/)

### 심층 가이드
- [Jack Righteous — Suno AI Meta Tags & Structure Guide](https://jackrighteous.com/en-us/pages/suno-ai-meta-tags-guide)
- [Jack Righteous — v4.5+ Features (Vocal Swap, Flip, Spark)](https://jackrighteous.com/en-us/blogs/guides-using-suno-ai-music-creation/suno-v45-plus-features-guide)
- [Jack Righteous — Negative Prompting Guide](https://jackrighteous.com/en-us/blogs/guides-using-suno-ai-music-creation/negative-prompting-suno-v5-guide)
- [Jack Righteous — Multilingual & Pronunciation Guide](https://jackrighteous.com/en-us/blogs/guides-using-suno-ai-music-creation/suno-v5-multilingual-english-pronunciation-guide)
- [Civitai — Ultimate v4.5 How-To (Personas, Extend, Cover)](https://civitai.com/articles/14849)
- [HookGenius — Complete Suno Prompt Guide 2026](https://hookgenius.app/learn/suno-prompt-guide-2026/)
- [HookGenius — Suno Pronunciation Fix Guide](https://hookgenius.app/learn/fix-suno-pronunciation/)
- [HookGenius — Korean Suno Prompts](https://hookgenius.app/learn/suno-korean-prompts/)
- [HookGenius — Vocal Effects, Harmonies & Layers](https://hookgenius.app/learn/suno-vocal-effects/)
- [MusicSmith — Why Suno Songs Sound Generic (20 Prompts)](https://musicsmith.ai/blog/ai-music-generation-prompts-best-practices)
- [HowToPromptSuno — Voice Tags & Lyrics Guide](https://howtopromptsuno.com/making-music/voice-tags)

### 후처리/스템 워크플로우
- [Cryo Mix — Mixing Suno Stems Pro Sound](https://cryo-mix.com/blog/posts/mixing-suno-stems)
- [RoEx — Mix and Master Suno Tracks](https://www.roexaudio.com/blog/how-to-mix-and-master-your-suno-tracks-(and-actually-sound-professional))
- [Undetectr — Suno Studio Guide 2026](https://undetectr.com/blog/suno-studio-guide)
- [Undetectr — Suno Stems in DAW (Ableton/Logic/FL)](https://undetectr.com/blog/suno-stems-daw-workflow)
- [Moe Lueker — Suno Song Editor & Stem Extraction 2025](https://moelueker.com/blog/suno-ai-song-editor-stem-extraction-full-2025-guide)

### API & 자동화
- [GitHub — gcui-art/suno-api (오픈소스)](https://github.com/gcui-art/suno-api)
- [SunoAPI.org — Public API Docs](https://docs.sunoapi.org/)
- [Kie.ai — Suno API Quickstart](https://docs.kie.ai/suno-api/quickstart)

### Persona / Voice Clone
- [MindStudio — Train a Voice in Suno 5.5](https://www.mindstudio.ai/blog/suno-5-5-voice-cloning-ai-music)
- [Jack Righteous — Suno Personas Update Dec 2025](https://jackrighteous.com/en-us/blogs/guides-using-suno-ai-music-creation/suno-ai-personas-update-dec-2025-what-changed-how-to-use-it)
- [Suno Hub — AI Voice Cloning Guide 2026](https://suno.com/hub/ai-voice-cloning)
