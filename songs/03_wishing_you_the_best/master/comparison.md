# 후처리 PoC — Before / After 비교

> **곡**: Wishing You The Best (B시안, Suno `e27caa61-...`)
> **레퍼런스**: Laufey — From The Start (official live, 2:50)
> **일자**: 2026-04-23
> **파이프라인**: Demucs htdemucs → Pedalboard vocal chain → Matchering → ffmpeg loudnorm -14 LUFS

---

## 1. 청취 파일

| 파일 | GDrive |
|------|--------|
| 원본 (A) | https://drive.google.com/open?id=1FW34eDt52a8KQ8B6D-9XfLOR0kAJU6HY |
| 마스터 (B) | https://drive.google.com/open?id=1QHjjt0_pFjjfBC45_BIQe6T6Lq5Rr6S4 |
| 지표 리포트 | https://drive.google.com/open?id=1aBkU2BKfZUGG3ssQtRgm7XRXCEIf2yxi |

> ⚠️ **블라인드 가이드**: 파일명 "A/B"를 먼저 보지 말고 각각 2회씩 들어본 뒤 아래 체크리스트로 판정해주세요.

---

## 2. 9지표 비교표

| 지표 | 원본 | 마스터 | 레퍼런스 (Laufey) | 해석 |
|------|------|--------|------|------|
| **LUFS (라우드니스)** | -13.01 | **-13.41** | -7.46 | -14 LUFS 타겟 달성 (YouTube/Spotify 표준) |
| **True Peak (dB)** | -0.43 | **-2.63** | ~0.00 | 마스터가 더 보수적 (클리핑 여유 ↑) |
| **Crest Factor (dB)** | 14.38 | **13.05** | 10.05 | 다이나믹 약간 줄음, 레퍼런스 쪽으로 이동 |
| **Spectral Centroid (Hz)** | 2564 | **1741** | 1923 | 중심 주파수 낮아짐 → 따뜻/빈티지 톤 |
| **Spectral Flatness** | 0.0037 | 0.000066 | 0.0079 | **이상값** — Matchering이 톤 과도하게 집약 |
| **Spectral Rolloff (Hz)** | 5704 | **2986** | 3652 | 고역 롤오프 ↓ → **답답하게 들릴 위험** |
| **Stereo Width** | 0.251 | 0.230 | 0.245 | 거의 유지 |
| 원본 대비 LUFS 변화 | — | +0.4dB (거의 동일) | — | loudnorm이 Matchering 후 재조정 |
| 원본 대비 Rolloff 변화 | — | **-48%** | — | 핵심 차이점 — 사용자 평가 포인트 |

---

## 3. 사용자 블라인드 A/B 리뷰 체크포인트

두 버전을 각각 들으며 5가지 관점에서 평가:

1. **보컬 선명도** — 가사가 더 잘 들리는 쪽?
2. **보컬 공간감** — 리버브 양이 적절한가? 너무 wet / 너무 dry?
3. **밴드와의 밸런스** — 악기가 보컬을 가리는가?
4. **톤 성향** — 밝고 공기감 있는 쪽 (A) vs 따뜻하고 빈티지한 쪽 (B) — Laufey 스타일에 가까운 쪽은?
5. **전체 볼륨 느낌** — 둘을 연속 재생했을 때 레벨 점프가 있는가?

### 정답 대조 (먼저 듣고 나서만 확인)

<details>
<summary>▶ 매핑 공개 (클릭)</summary>

- **A_original.mp3** = Suno 원본 (무가공)
- **B_mastered.mp3** = Demucs + Pedalboard vocal chain + Matchering + loudnorm -14 LUFS

**파이프라인이 향해야 할 지표**: B가 A보다 "Laufey 쪽에 더 가까운 질감"이어야 합격.
</details>

---

## 4. Pedalboard Vocal Chain 파라미터

```python
Pedalboard([
    HighpassFilter(80),                                   # 럼블 컷
    NoiseGate(threshold_db=-60),                          # 무음 구간 정리
    Compressor(threshold_db=-18, ratio=3.0,
               attack_ms=5, release_ms=80),               # 보컬 게이트
    HighShelfFilter(cutoff_frequency_hz=12000,
                    gain_db=-1.0),                        # 치찰음 완화
    LowShelfFilter(cutoff_frequency_hz=200,
                   gain_db=1.5),                          # 가슴 톤 보강
    Chorus(rate_hz=0.3, depth=0.02, mix=0.08),            # 미세 공간감
    Reverb(room_size=0.25, damping=0.4,
           wet_level=0.1, dry_level=0.9),                 # 플레이트 느낌 소량
    Gain(gain_db=1.0),                                    # 레벨 회복
])
```

**재결합**: `vocal_processed × 1.0 + no_vocals × 0.95` (보컬 우위 믹스)

---

## 5. PoC 결론 + 다음 단계

### 성공
- 전체 파이프라인 **end-to-end 실행 성공** (Demucs 약 1분 50초 + 나머지 ~30초)
- 파일 구조 정상 (stems/, premaster, matched, mastered, mp3, 리포트)
- 9지표 자동 산출 + 레퍼런스 대조 가능

### 이슈 (Phase 1 구현 시 개선)
1. **고역 롤오프 과다 (-48%)** — Matchering이 레퍼런스의 어두운 톤에 너무 강하게 맞춤. 완화안:
   - Pedalboard HighShelf +1dB (현재 -1dB, 치찰음과 반대 방향)
   - Matchering `preview` + 블렌드 70% 혼합
2. **spectral_flatness 극단값 (6.6e-05)** — 과도한 톤 집약. Matchering 단계 가중치 조정 or Dynamic EQ 추가 필요
3. **CUDA 경고** (NVIDIA 드라이버 12070 < PyTorch 요구) — Demucs CPU 모드 동작. GPU 전환 시 5배 속도 향상 가능하지만 선행 이슈 아님
4. **torchaudio 2.11 + torchcodec 의존성** — PoC에서 추가 설치. requirements.txt 재freeze 필요

### 다음 반복 제안
- PIPE-F04 Phase 1 본 구현 시 위 3개 이슈 반영
- 사용자 청취 결과로 파라미터 재튜닝
- `postprocess.py --blend 0.7` 옵션 추가 (원본 ↔ 마스터 혼합 비율)
