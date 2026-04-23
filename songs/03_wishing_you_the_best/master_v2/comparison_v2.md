# 경량 마스터링 v2 — Do No Harm + Analog Humanizer

> **곡**: Wishing You The Best (B-1 GOOD, Suno `e27caa61-...`)
> **철학**: Suno v5.5 raw 존중 · 표준만 맞춤 · Matchering/Demucs 제거
> **일자**: 2026-04-23

---

## 1. 청취 파일 (블라인드 리뷰)

| 파일 | GDrive |
|------|--------|
| A | https://drive.google.com/open?id=1iPbapcTkNfVLMfrsnJPa5G6EjjoplMGa |
| C | https://drive.google.com/open?id=19RC2K5Kl-9CYiL_NZJ20dI1Q2Lf4sNh5 |
| 지표 리포트 | https://drive.google.com/open?id=1ENk7WO9mQRwJB2GVbuKN4j93-T_61SDI |

> ⚠️ 파일명의 A/C 힌트 **먼저 보지 말고** 각각 2회씩 청취 후 평가.

---

## 2. 9지표 비교표 — 원본 / v1 (Matchering 실패본) / v2 (경량)

| 지표 | 원본 | v1 (Matchering) | **v2 (경량)** | v2 변화 |
|------|------|------|------|------|
| LUFS | -13.01 | -13.41 | **-13.24** | ≈ 유지, -14 타겟 근접 |
| True Peak (dB) | -0.43 | -2.63 | **-3.41** | 여유 확대 (클리핑 위험 ↓) |
| Crest Factor (dB) | 14.38 | 13.05 | **12.35** | 약한 Comp만 (1.5:1) |
| Spectral Centroid (Hz) | 2564 | 1741 | **2441** | 원본 거의 유지 (-5%, v1은 -32%) |
| Spectral Flatness | 0.0037 | 0.000066 | **0.000518** | v1의 8배, 원본의 14% |
| Spectral Rolloff (Hz) | 5704 | 2986 | **5084** | **-11% (v1은 -48%)** ← 핵심 |
| Stereo Width | 0.251 | 0.230 | **0.273** | +9% 자연 확장 |

### 요약
- **v1 대비 훨씬 덜 침해적** — 고역 rolloff 손실이 -48% → -11%로 개선
- **원본 톤 유지** — centroid 거의 그대로 (5% 감소만)
- **-14 LUFS 표준 달성**, True Peak 여유 3.4dB

---

## 3. 사용자 블라인드 A vs C 청취 포인트

각각 2회 청취 후 5개 관점에서 평가:

1. **보컬 호흡 잔존** — 숨소리/디테일이 살아있는가?
2. **고역 선명도** — 심벌·시빌런스가 제대로 들리는가? 답답하지 않은가?
3. **공간감 자연스러움** — 리버브가 과하지도 부족하지도 않은가?
4. **저역 깔끔** — 베이스 라인이 흐리지 않은가? 럼블은 제거되었는가?
5. **볼륨 점프** — A→C 연속 재생 시 레벨이 튀는가?

### 정답 대조

<details>
<summary>▶ 매핑 공개 (클릭)</summary>

- **A = Suno 원본** (무가공)
- **C = v2 경량 마스터링** (HPF(60) + 약한 Comp(1.5:1) + Distortion(2dB) + Reverb(5%) + loudnorm -14)

"v2가 원본을 해치지 않으면서 표준만 맞췄는가" 가 핵심 평가 기준.

</details>

---

## 4. Pedalboard 체인 (v2, full mix 직접)

```python
Pedalboard([
    HighpassFilter(60),                            # low rumble만
    Compressor(threshold_db=-14, ratio=1.5,
               attack_ms=10, release_ms=100),      # 거의 안 누름
    Distortion(drive_db=2),                        # subtle tape warmth
    Reverb(room_size=0.18, damping=0.5,
           wet_level=0.05, dry_level=0.95),        # 5% 공간감
    Gain(gain_db=0.5),                             # 미세 boost
])
# + ffmpeg loudnorm=I=-14:TP=-1.0:LRA=11
```

**삭제된 것**: Matchering, Demucs stems 분리, 보컬 전용 체인 (HighShelf/LowShelf/Chorus/NoiseGate).

---

## 5. 다음 단계 판단 기준

| 블라인드 결과 | 결정 |
|-------------|------|
| A 선호 | 원본이 이미 완성. 마스터링 제거 또는 loudnorm만 적용 |
| C 선호 | v2 기본값으로 파이프라인 확정. 나머지 3트랙(B-2/C-1/C-2)도 v2 처리 |
| 차이 없음 | 편의상 v2 (loudnorm 표준만 확보됨) 채택 |
