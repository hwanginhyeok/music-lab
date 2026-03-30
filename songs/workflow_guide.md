# 곡 제작 워크플로우 가이드

> 첫 곡 "봄이라고 부를게" 제작 경험에서 도출한 워크플로우.
> Suno 원스택 방식 — 후처리 없이 Suno에서 바로 완성.

---

## 워크플로우 5단계

### 1단계: 컨셉 설계

`template/concept.md` 복사 후 채우기.

체크리스트:
- [ ] 핵심 컨셉 한 문장으로 정리
- [ ] 화자 캐릭터 구체화 (나이, 상황, 감정)
- [ ] 감정 곡선 그리기 (섹션별 에너지 레벨)
- [ ] 언어유희/장치 있으면 맵 작성
- [ ] 레퍼런스 곡 2~3개 선정
- [ ] 장르, BPM, 키 결정

### 2단계: 작사

`template/lyrics.md` 복사 후 채우기.

체크리스트:
- [ ] Verse/Pre-Chorus/Chorus/Bridge/Final 구조 작성
- [ ] 음절 수 대략 맞추기 (Verse 10~12, Chorus 9~11)
- [ ] 1절→2절 감정 변화 확인
- [ ] 영어 훅라인 필요 시 작성
- [ ] 작사 노트 기록 (의도, 스타일 참조)

### 3단계: Suno 프롬프트 엔지니어링

`template/suno_prompt.md` 복사 후 채우기.

체크리스트:
- [ ] Style of Music 태그 작성 (200자 이내)
- [ ] GMIV 법칙 확인 (Genre + Mood + Instrument + Vocal)
- [ ] 가사를 Suno 형식으로 변환 (섹션 태그 포함)
- [ ] 편곡 힌트 태그는 핵심만 (4~5개 이내)
- [ ] 설계 노트 기록

### 4단계: Suno 생성 + 피드백 루프

체크리스트:
- [ ] Suno에 Style + Lyrics 복붙
- [ ] 생성 결과 청취
- [ ] 불만족 시 태그 조정 후 재생성
- [ ] 만족스러운 버전 선택
- [ ] 필요 시 Extend로 곡 연장

### 5단계: 결과물 관리

체크리스트:
- [ ] 최종 Suno 결과물 다운로드
- [ ] 곡 폴더에 정리
- [ ] 사용한 프롬프트 최종본 저장
- [ ] 배운 점 이 가이드에 추가

---

## Suno 태그 레시피 (검증된 조합)

### 인디 밴드 (감성적)
```
Korean indie band, emotional dreamy male vocal, acoustic guitar, light drums, soft piano, bittersweet spring longing, intimate, 92bpm
```
> 검증: "봄이라고 부를게" v3에서 사용자 확인

### Contemporary Pop (쿨/스무스)
```
Cool and smooth contemporary pop love song, cool bass hook and groove, distinct sing-along chorus, synth-based atmospheric production, vocalisation, smooth silky falsetto vocal, syncopated groove
```
> 검증: 영어 버전에서 "노래 개좋다" 평가

### 추가 레시피
<!-- 새 곡 만들면서 검증된 조합 여기에 추가 -->

---

## 함정 모음 (Suno 사용 시 주의사항)

### 절대 금지
- **lo-fi, tape, bedroom recording** → 음질 저하(노이즈/히스) 직접 원인
- **breathy** → 노이즈와 구분 어려움

### 주의
- **편곡 힌트 태그 과다** → 5개 이상 넣으면 Suno가 혼란, 아티팩트 발생
- **두 지시를 한 태그에 묶기** → `[Piano Enters, Emotional Vocal]` 같은 복합 태그는 Suno가 무시하는 경향
- **악기 단독 지정** → `[Guitar Only, 2 bars]` 같은 세부 지시는 해석 실패 시 문제
- **모순 태그** → `High Energy` + `Chill` 같은 조합 금지

### 효과적인 태그
- `[Build]` — Pre-Chorus 고조에 효과적
- `[Stripped Back]` — Bridge 미니멀 사운드
- `[Fragile]` — Final Chorus 여린 보컬
- `[Fade Out]` — Outro
- `[Spoken Word]` — 말하듯 부르는 구간
- `[Vocalisation]` — falsetto/멜리스마 (Style에 vocalisation 포함 시)

### 따뜻한 느낌이 필요할 때
lo-fi 대신: `intimate`, `warm tone`, `dreamy`

---

## 피드백 루프 패턴

Suno 생성 결과가 마음에 안 들 때 조정하는 축:

| 조정 축 | 예시 |
|---------|------|
| 보컬 톤 | `emotional` → `clear`, `dreamy` → `bright` |
| 악기 비중 | `acoustic guitar` 빼고 `piano` 추가 |
| BPM | 92bpm → 88bpm (더 느리게) |
| 텍스처 | `intimate` 추가/제거 |
| 장르 | `indie pop` → `indie band` |
| 에너지 | 태그 순서 변경 (앞 20단어가 가장 영향력 큼) |

**반복 전략:**
1. 한 번에 1~2개 태그만 변경
2. 변경 전후 비교 청취
3. 만족스러운 조합 발견 시 레시피에 추가

---

## 곡별 폴더 구조

```
songs/
├── template/           ← 빈 템플릿 (복사해서 사용)
│   ├── concept.md
│   ├── lyrics.md
│   └── suno_prompt.md
├── workflow_guide.md   ← 이 파일
├── 01_봄이라고_부를게/ ← 첫 곡
│   ├── concept.md
│   ├── lyrics_v1.md
│   ├── suno_prompt_final.md
│   ├── suno_prompt_v3.md
│   ├── suno_prompt_en_v1.md
│   └── suno_prompt_kr_contemporary.md
└── 02_[다음곡]/        ← template/ 복사해서 시작
    ├── concept.md
    ├── lyrics.md
    └── suno_prompt.md
```

**새 곡 시작하기:**
1. `cp -r songs/template/ songs/02_곡이름/`
2. concept.md부터 채우기
3. 이 가이드의 체크리스트 따라가기

---

## 첫 곡에서 배운 교훈

1. **lo-fi 태그 = 노이즈.** 따뜻한 느낌은 `intimate`, `warm tone`으로 충분.
2. **후처리(믹싱/마스터링)보다 Suno 프롬프트 최적화가 현실적.** stems 분리 + NoiseGate + 스펙트럴 디노이즈 전부 시도했지만 한계. Suno 원스택이 답.
3. **가사 버전 관리 중요.** lyrics_v1이 최종인데 v2 기준으로 작업해서 가사가 꼬인 적 있음. 최종본을 명확히 표시할 것.
4. **편곡 힌트 태그는 적을수록 좋다.** 과도한 지시 → Suno 해석 실패 → 아티팩트.
5. **검증된 스타일 조합을 레시피로 축적.** 새 곡마다 처음부터 태그 실험하지 말고, 검증된 조합에서 시작.
6. **영어 가사로 스타일 테스트 → 한국어 가사에 적용.** 영어가 Suno 해석이 더 안정적. 스타일 잡은 후 한국어로 전환.
