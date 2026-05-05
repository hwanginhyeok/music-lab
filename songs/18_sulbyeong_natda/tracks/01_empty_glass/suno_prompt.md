# Track 01 — 잔이 비었다 (Empty Glass)

> Part I 빈병 / 인트로 트랙 / 모티프 A 도입

## 스펙 (컨셉 v0.2)

| 항목 | 값 |
|------|-----|
| 러닝타임 | 3:00 |
| BPM | 60 (느림) |
| 키 | D minor |
| 편성 | 솔로 색소폰(테너) + 피아노 + 더블베이스 |
| 색스 톤 | clean ballad, 절제. 비브라토 약함 |
| 다이나믹 | p → mp |
| 박자감 | rubato, 침묵 많음 |
| 공간감 | 룸톤 살림, 공허 |
| 레퍼런스 | Coleman Hawkins 〈Body and Soul〉 도입부 / Ben Webster 〈Danny Boy〉 |

## 정서

멍하게 비어있는 정서. 인트로. 화자가 술상 앞에 앉아 잔 비어있음을 자각.

## 멜로디 모티프

**모티프 A** (4음 라인) — 색스 long tone으로 등장. 9번에서 회귀할 핵심 라인.
- composer 에이전트 호출 후 채워질 것
- 미리 작성: composer 결과를 `motif_a.json`(midi-json)으로 저장

## 세부 사운드 디자인

- 색스 long tone, 피아노 코드 듬성듬성, 베이스 워킹 거의 없음
- 노트 사이 침묵 1.5~2초
- 마이킹: 색스 가까이, 룸톤 살림
- 페달링 길게 (잔향 = 빈 잔의 부피)

## Suno 프롬프트 (v1 — Suno Style 칸용 압축본)

### Style of Music (Suno 입력)

```
late-night smoky jazz, tenor saxophone ballad, 1950s East Coast jazz, BPM 60, D minor, instrumental, sparse, intimate room mic, Coleman Hawkins style, sax + piano + double bass trio, no drums, no electronic, acoustic, restrained vibrato
```

### Lyrics (Suno 입력)

```
[Instrumental]
```

### 모드

`--instrumental` 플래그 사용 (가사 칸 비움, Suno 인스트루멘털 모드)

### 모델

v5.5 (최신, Suno 기본값)

### 풀 컨텍스트 (참고용 — 실제 Suno 입력은 위 압축본만)

공통 베이스:
```
Late-night smoky jazz, 1950s-60s East Coast tone, saxophone-led,
acoustic recording, intimate room tone, deep dynamic range,
no electronic elements, no lo-fi, no indie, no K-pop,
analog warmth, vintage studio mic
```

이 트랙 차별:
```
[BPM 60] [Key: D minor] [Slow ballad]
Tenor saxophone melody — clean tone, soft, restrained vibrato
Piano: sparse extended chords, long sustain
Double bass: minimal walking, root notes mostly
No drums
Reference: Coleman Hawkins "Body and Soul" intro, Ben Webster "Danny Boy"
Mood: empty glass, quiet melancholy, sitting alone
Long silences between phrases, rubato feel
```
