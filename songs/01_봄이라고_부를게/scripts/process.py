#!/usr/bin/env python3
"""
봄이라고 부를게 — 후처리 파이프라인

사용법:
  python3 process.py ../suno/input.mp3

파이프라인:
  1. 보컬/반주 분리 (Demucs)
  2. 보컬 후처리 (Pedalboard: HPF → 노이즈게이트 → 컴프 → EQ → 리버브)
  3. 반주 EQ (보컬 자리 확보)
  4. 믹싱 (보컬 + 반주)
  5. 마스터링 (Matchering, 레퍼런스 있을 때) 또는 기본 마스터링
  6. 라우드니스 노멀라이제이션 (-14 LUFS)

결과물: ../processed/ 와 ../release/ 에 저장
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf


SONG_DIR = Path(__file__).parent.parent
STEMS_DIR = SONG_DIR / "stems"
PROCESSED_DIR = SONG_DIR / "processed"
RELEASE_DIR = SONG_DIR / "release"


def ensure_dirs() -> None:
    for d in (STEMS_DIR, PROCESSED_DIR, RELEASE_DIR):
        d.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Step 1: 보컬 분리
# ---------------------------------------------------------------------------
def separate_vocals(input_path: Path) -> tuple[Path, Path]:
    """Demucs로 보컬/반주 분리."""
    print("\n🎤 Step 1: 보컬 분리 (Demucs)...")
    print("   (첫 실행 시 모델 다운로드 ~300MB, 3~5분 소요)")

    subprocess.run(
        [sys.executable, "-m", "demucs",
         "--two-stems=vocals",
         "-n", "htdemucs",
         str(input_path),
         "-o", str(STEMS_DIR)],
        check=True,
    )

    stem_name = input_path.stem
    vocals = STEMS_DIR / "htdemucs" / stem_name / "vocals.wav"
    no_vocals = STEMS_DIR / "htdemucs" / stem_name / "no_vocals.wav"

    if vocals.is_file() and no_vocals.is_file():
        print(f"   ✅ 보컬: {vocals}")
        print(f"   ✅ 반주: {no_vocals}")
    else:
        print("   ❌ 분리 실패")
        sys.exit(1)

    return vocals, no_vocals


# ---------------------------------------------------------------------------
# Step 2: 보컬 후처리
# ---------------------------------------------------------------------------
def process_vocals(vocals_path: Path) -> Path:
    """Pedalboard로 보컬 후처리."""
    print("\n🎧 Step 2: 보컬 후처리...")

    from pedalboard import (
        Pedalboard,
        Compressor,
        HighpassFilter,
        LowShelfFilter,
        HighShelfFilter,
        NoiseGate,
        Reverb,
        Gain,
    )

    audio, sr = sf.read(str(vocals_path))
    if audio.ndim == 1:
        audio = np.column_stack([audio, audio])

    board = Pedalboard([
        # 1. 하이패스 80Hz — 보컬에 불필요한 저역 럼블 제거
        HighpassFilter(cutoff_frequency_hz=80.0),

        # 2. 노이즈 게이트 — 무음 구간 잡음 제거
        NoiseGate(
            threshold_db=-40.0,
            release_ms=100.0,
        ),

        # 3. 컴프레션 — 볼륨 균일화
        Compressor(
            threshold_db=-20.0,
            ratio=3.0,
            attack_ms=5.0,
            release_ms=100.0,
        ),

        # 4. EQ — 보컬 프레즌스 강화
        LowShelfFilter(cutoff_frequency_hz=200.0, gain_db=-2.0),   # 머디함 제거
        HighShelfFilter(cutoff_frequency_hz=8000.0, gain_db=1.5),  # 에어/밝기

        # 5. 리버브 — 자연스러운 공간감 (lo-fi bedroom 느낌)
        Reverb(
            room_size=0.3,
            wet_level=0.15,
            dry_level=0.85,
            damping=0.7,
        ),

        # 6. 살짝 볼륨 올림 (보컬이 앞에 나오게)
        Gain(gain_db=2.0),
    ])

    processed = board(audio.T.astype(np.float32), sr)

    output_path = PROCESSED_DIR / "vocals_processed.wav"
    sf.write(str(output_path), processed.T, sr)
    print(f"   ✅ {output_path}")
    return output_path


# ---------------------------------------------------------------------------
# Step 3: 반주 EQ
# ---------------------------------------------------------------------------
def process_mr(mr_path: Path) -> Path:
    """반주 경량 처리 — 보컬 자리 확보."""
    print("\n🎸 Step 3: 반주 EQ...")

    from pedalboard import Pedalboard, LowShelfFilter, HighShelfFilter, NoiseGate

    audio, sr = sf.read(str(mr_path))
    if audio.ndim == 1:
        audio = np.column_stack([audio, audio])

    board = Pedalboard([
        NoiseGate(threshold_db=-50.0, release_ms=150.0),
        # 보컬 대역 살짝 깎아 보컬이 앉을 자리 확보
        LowShelfFilter(cutoff_frequency_hz=250.0, gain_db=-1.0),
        HighShelfFilter(cutoff_frequency_hz=6000.0, gain_db=0.5),
    ])

    processed = board(audio.T.astype(np.float32), sr)

    output_path = PROCESSED_DIR / "mr_processed.wav"
    sf.write(str(output_path), processed.T, sr)
    print(f"   ✅ {output_path}")
    return output_path


# ---------------------------------------------------------------------------
# Step 4: 믹싱
# ---------------------------------------------------------------------------
def mix_tracks(vocals_path: Path, mr_path: Path) -> Path:
    """보컬 + 반주 합치기."""
    print("\n🎛️  Step 4: 믹싱...")

    vocals, sr_v = sf.read(str(vocals_path))
    mr, sr_m = sf.read(str(mr_path))

    # 샘플레이트 맞추기
    assert sr_v == sr_m, f"샘플레이트 불일치: {sr_v} vs {sr_m}"

    # 길이 맞추기
    min_len = min(len(vocals), len(mr))
    vocals = vocals[:min_len]
    mr = mr[:min_len]

    # 믹싱 (보컬 약간 더 크게)
    mixed = mr * 0.75 + vocals * 0.85

    # 클리핑 방지
    peak = np.max(np.abs(mixed))
    if peak > 0.95:
        mixed = mixed * (0.95 / peak)

    output_path = PROCESSED_DIR / "mixed.wav"
    sf.write(str(output_path), mixed, sr_v)
    print(f"   ✅ {output_path}")
    return output_path


# ---------------------------------------------------------------------------
# Step 5: 마스터링
# ---------------------------------------------------------------------------
def master_track(mixed_path: Path, reference_path: Path | None = None) -> Path:
    """마스터링 — 레퍼런스 있으면 Matchering, 없으면 기본."""
    print("\n💿 Step 5: 마스터링...")

    output_path = RELEASE_DIR / "mastered.wav"

    if reference_path and reference_path.is_file():
        print(f"   레퍼런스 기반 마스터링 (Matchering): {reference_path.name}")
        import matchering as mg
        mg.process(
            target=str(mixed_path),
            reference=str(reference_path),
            results=[
                mg.Result(str(output_path), subtype="PCM_16", use_limiter=True),
            ],
        )
    else:
        print("   기본 마스터링 (Pedalboard)...")
        from pedalboard import (
            Pedalboard, HighpassFilter, LowShelfFilter,
            HighShelfFilter, Compressor, Limiter,
        )

        audio, sr = sf.read(str(mixed_path))
        if audio.ndim == 1:
            audio = np.column_stack([audio, audio])

        board = Pedalboard([
            HighpassFilter(cutoff_frequency_hz=30.0),
            LowShelfFilter(cutoff_frequency_hz=100.0, gain_db=1.0),
            HighShelfFilter(cutoff_frequency_hz=10000.0, gain_db=1.5),
            Compressor(threshold_db=-15.0, ratio=2.0, attack_ms=10.0, release_ms=200.0),
            Limiter(threshold_db=-1.0, release_ms=100.0),
        ])

        processed = board(audio.T.astype(np.float32), sr)
        sf.write(str(output_path), processed.T, sr, subtype="PCM_16")

    print(f"   ✅ {output_path}")
    return output_path


# ---------------------------------------------------------------------------
# Step 6: 라우드니스 노멀라이제이션
# ---------------------------------------------------------------------------
def normalize_loudness(input_path: Path, target_lufs: float = -14.0) -> Path:
    """스트리밍 플랫폼 표준 -14 LUFS로 노멀라이즈."""
    print(f"\n📊 Step 6: 라우드니스 노멀라이제이션 (목표: {target_lufs} LUFS)...")

    import pyloudnorm as pyln

    audio, sr = sf.read(str(input_path))
    meter = pyln.Meter(sr)
    current_lufs = meter.integrated_loudness(audio)
    print(f"   현재: {current_lufs:.1f} LUFS")

    normalized = pyln.normalize.loudness(audio, current_lufs, target_lufs)

    # 클리핑 방지
    peak = np.max(np.abs(normalized))
    if peak > 0.99:
        normalized = normalized * (0.99 / peak)
        print(f"   ⚠️  피크 제한 적용 (True Peak 방지)")

    output_path = RELEASE_DIR / "final.wav"
    sf.write(str(output_path), normalized, sr, subtype="PCM_16")

    final_lufs = meter.integrated_loudness(normalized)
    print(f"   최종: {final_lufs:.1f} LUFS")
    print(f"   ✅ {output_path}")
    return output_path


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="봄이라고 부를게 — 후처리 파이프라인")
    parser.add_argument("input", help="Suno 출력 파일 경로 (mp3/wav)")
    parser.add_argument("--reference", "-r", help="레퍼런스 곡 (마스터링용)", default=None)
    parser.add_argument("--skip-separation", action="store_true", help="보컬 분리 스킵 (Suno 원본 그대로 마스터링)")
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    if not input_path.is_file():
        print(f"❌ 파일 없음: {input_path}")
        sys.exit(1)

    reference_path = Path(args.reference).resolve() if args.reference else None
    ensure_dirs()

    print(f"🎵 입력: {input_path.name}")
    print(f"📁 출력: {RELEASE_DIR}/")

    if args.skip_separation:
        # Suno 원본을 그대로 마스터링만
        print("\n⏭️  보컬 분리 스킵 — 원본 그대로 마스터링")
        shutil.copy(input_path, PROCESSED_DIR / "mixed.wav")
        mixed_path = PROCESSED_DIR / "mixed.wav"
    else:
        # 풀 파이프라인
        vocals_path, mr_path = separate_vocals(input_path)
        vocals_processed = process_vocals(vocals_path)
        mr_processed = process_mr(mr_path)
        mixed_path = mix_tracks(vocals_processed, mr_processed)

    mastered_path = master_track(mixed_path, reference_path)
    final_path = normalize_loudness(mastered_path)

    print("\n" + "=" * 50)
    print("✅ 완료!")
    print(f"   최종 파일: {final_path}")
    print(f"   포맷: WAV 16bit 44.1kHz, -14 LUFS")
    print("=" * 50)


if __name__ == "__main__":
    main()
