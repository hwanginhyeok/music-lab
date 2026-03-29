#!/usr/bin/env python3
"""
봄이라고 부를게 — Stems 기반 믹싱 + 마스터링

Suno Stems 8트랙을 개별 처리하고 합친다.
실제 분석 데이터 기반 파라미터.

사용법:
  python3 mix_stems.py
  python3 mix_stems.py -r reference.wav   # 레퍼런스 마스터링
"""
from __future__ import annotations

import argparse
import glob
import numpy as np
import soundfile as sf
import pyloudnorm as pyln
from pathlib import Path
from pedalboard import (
    Pedalboard,
    Compressor,
    HighpassFilter,
    LowpassFilter,
    LowShelfFilter,
    HighShelfFilter,
    NoiseGate,
    Reverb,
    Gain,
    Limiter,
)

SONG_DIR = Path(__file__).parent.parent
SUNO_DIR = SONG_DIR / "suno"
PROCESSED_DIR = SONG_DIR / "processed"
RELEASE_DIR = SONG_DIR / "release"


def ensure_dirs():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)


def load_stem(name: str) -> tuple[np.ndarray, int]:
    """스템 파일 로드."""
    matches = glob.glob(str(SUNO_DIR / f"*{name}*.wav"))
    if not matches:
        raise FileNotFoundError(f"스템 없음: {name}")
    audio, sr = sf.read(matches[0])
    if audio.ndim == 1:
        audio = np.column_stack([audio, audio])
    return audio, sr


def apply_board(audio: np.ndarray, sr: int, board: Pedalboard) -> np.ndarray:
    """Pedalboard 적용."""
    processed = board(audio.T.astype(np.float32), sr)
    return processed.T


# ---------------------------------------------------------------------------
# 트랙별 처리 (실제 분석 데이터 기반)
# ---------------------------------------------------------------------------

def process_lead_vocal(audio: np.ndarray, sr: int) -> np.ndarray:
    """메인 보컬 처리. 원본 LUFS: -16.9, Peak: -5.3dB"""
    print("  Lead Vocals: HPF 80Hz → 노이즈게이트 → 컴프 3:1 → EQ → 리버브")
    board = Pedalboard([
        HighpassFilter(cutoff_frequency_hz=80.0),
        NoiseGate(threshold_db=-40.0, release_ms=100.0),
        Compressor(threshold_db=-18.0, ratio=3.0, attack_ms=5.0, release_ms=100.0),
        LowShelfFilter(cutoff_frequency_hz=200.0, gain_db=-2.0),    # 머디함 제거
        HighShelfFilter(cutoff_frequency_hz=3000.0, gain_db=2.0),   # 프레즌스
        HighShelfFilter(cutoff_frequency_hz=8000.0, gain_db=1.5),   # 에어
        Reverb(room_size=0.25, wet_level=0.12, dry_level=0.88, damping=0.7),
        Gain(gain_db=1.0),
        Limiter(threshold_db=-2.0, release_ms=50.0),  # 스템 단위 피크 제한
    ])
    return apply_board(audio, sr, board)


def process_backing_vocal(audio: np.ndarray, sr: int) -> np.ndarray:
    """배킹 보컬 처리. 원본 LUFS: -28.9 (매우 작음) → 볼륨 올림."""
    print("  Backing Vocals: HPF → 컴프 → EQ → 리버브 넓게 → 볼륨 업")
    board = Pedalboard([
        HighpassFilter(cutoff_frequency_hz=120.0),
        Compressor(threshold_db=-25.0, ratio=2.5, attack_ms=10.0, release_ms=150.0),
        HighShelfFilter(cutoff_frequency_hz=5000.0, gain_db=1.0),
        Reverb(room_size=0.5, wet_level=0.20, dry_level=0.80, damping=0.5),  # 넓은 공간감, wet 0.25 이하
        Gain(gain_db=6.0),  # -28.9 → 올려서 존재감
    ])
    return apply_board(audio, sr, board)


def process_drums(audio: np.ndarray, sr: int) -> np.ndarray:
    """드럼 처리. 원본 Peak: -2.4dB (높음) → 리미팅."""
    print("  Drums: HPF → 컴프 → 리미터 → 볼륨 조절")
    board = Pedalboard([
        HighpassFilter(cutoff_frequency_hz=40.0),
        Compressor(threshold_db=-15.0, ratio=4.0, attack_ms=2.0, release_ms=50.0),
        LowShelfFilter(cutoff_frequency_hz=100.0, gain_db=1.0),    # 킥 펀치
        HighShelfFilter(cutoff_frequency_hz=8000.0, gain_db=0.5),   # 하이햇 밝기
        Limiter(threshold_db=-3.0, release_ms=50.0),
        Gain(gain_db=-1.0),  # 살짝 낮춤 (보컬 자리)
    ])
    return apply_board(audio, sr, board)


def process_bass(audio: np.ndarray, sr: int) -> np.ndarray:
    """베이스 처리. 원본 LUFS: -22.8"""
    print("  Bass: LPF → 컴프 → EQ")
    board = Pedalboard([
        HighpassFilter(cutoff_frequency_hz=30.0),
        LowpassFilter(cutoff_frequency_hz=8000.0),
        Compressor(threshold_db=-20.0, ratio=4.0, attack_ms=5.0, release_ms=80.0),
        LowShelfFilter(cutoff_frequency_hz=80.0, gain_db=1.5),     # 저역 펀치
        Gain(gain_db=0.5),
    ])
    return apply_board(audio, sr, board)


def process_guitar(audio: np.ndarray, sr: int) -> np.ndarray:
    """기타 처리. 원본 Peak: -3.3dB (높음). 이 곡의 메인 악기. lo-fi 기타팝 저음 살림."""
    print("  Guitar: HPF → 컴프 → EQ → 리미터")
    board = Pedalboard([
        HighpassFilter(cutoff_frequency_hz=80.0),                   # 100 → 80Hz: lo-fi 저음 살리기
        Compressor(threshold_db=-18.0, ratio=2.5, attack_ms=10.0, release_ms=100.0),
        LowShelfFilter(cutoff_frequency_hz=300.0, gain_db=-1.5),    # 보컬 중역 양보
        HighShelfFilter(cutoff_frequency_hz=5000.0, gain_db=1.0),   # 밝기 유지
        Limiter(threshold_db=-4.0, release_ms=80.0),
        Gain(gain_db=-0.5),
    ])
    return apply_board(audio, sr, board)


def process_keyboard(audio: np.ndarray, sr: int) -> np.ndarray:
    """키보드/피아노 처리. 원본 LUFS: -25.3"""
    print("  Keyboard: HPF → 컴프 → EQ")
    board = Pedalboard([
        HighpassFilter(cutoff_frequency_hz=80.0),
        Compressor(threshold_db=-22.0, ratio=2.0, attack_ms=15.0, release_ms=120.0),
        HighShelfFilter(cutoff_frequency_hz=6000.0, gain_db=1.0),
        Gain(gain_db=1.0),
    ])
    return apply_board(audio, sr, board)


def process_synth(audio: np.ndarray, sr: int) -> np.ndarray:
    """신스 처리. 원본 LUFS: -22.8"""
    print("  Synth: HPF → 컴프 → 볼륨")
    board = Pedalboard([
        HighpassFilter(cutoff_frequency_hz=60.0),
        Compressor(threshold_db=-20.0, ratio=2.0, attack_ms=10.0, release_ms=100.0),
        Gain(gain_db=-1.0),  # 살짝 뒤로
    ])
    return apply_board(audio, sr, board)


def process_other(audio: np.ndarray, sr: int) -> np.ndarray:
    """기타 악기. 원본 LUFS: -25.1"""
    print("  Other: 가볍게 처리")
    board = Pedalboard([
        HighpassFilter(cutoff_frequency_hz=60.0),
        Compressor(threshold_db=-22.0, ratio=2.0, attack_ms=10.0, release_ms=100.0),
    ])
    return apply_board(audio, sr, board)


# ---------------------------------------------------------------------------
# 믹싱
# ---------------------------------------------------------------------------

# 트랙별 볼륨 비율 (보컬 중심 믹스)
MIX_LEVELS = {
    "Lead Vocals":    1.0,     # 기준
    "Backing Vocals": 0.35,    # 뒤에서 살짝
    "Drums":          0.55,    # 리듬 지탱하되 보컬 방해 안 되게
    "Bass":           0.50,    # 저역 기반
    "Guitar":         0.65,    # 메인 악기, 보컬 다음으로 크게
    "Keyboard":       0.40,    # Chorus에서 보조
    "Synth":          0.30,    # 텍스처
    "Other":          0.25,    # 배경
}


def mix_all(stems: dict[str, np.ndarray], sr: int) -> np.ndarray:
    """모든 트랙 믹싱."""
    print("\n🎛️  믹싱...")

    # 길이 맞추기
    min_len = min(len(s) for s in stems.values())
    mixed = np.zeros((min_len, 2), dtype=np.float64)

    for name, audio in stems.items():
        level = MIX_LEVELS.get(name, 0.3)
        mixed += audio[:min_len] * level
        print(f"  + {name}: ×{level}")

    # 클리핑 방지
    peak = np.max(np.abs(mixed))
    if peak > 0.95:
        mixed = mixed * (0.90 / peak)
        print(f"  ⚠️  피크 제한 적용 ({peak:.2f} → 0.90)")

    output_path = PROCESSED_DIR / "mixed.wav"
    sf.write(str(output_path), mixed, sr)
    print(f"  ✅ {output_path}")
    return mixed


# ---------------------------------------------------------------------------
# 마스터링
# ---------------------------------------------------------------------------

def master(audio: np.ndarray, sr: int, reference_path: Path | None = None) -> np.ndarray:
    """마스터링."""
    print("\n💿 마스터링...")

    if reference_path and reference_path.is_file():
        print(f"  레퍼런스: {reference_path.name}")
        import matchering as mg
        temp_in = str(PROCESSED_DIR / "mixed.wav")
        temp_out = str(RELEASE_DIR / "mastered.wav")
        mg.process(
            target=temp_in,
            reference=str(reference_path),
            results=[mg.Result(temp_out, subtype="PCM_16", use_limiter=True)],
        )
        mastered, _ = sf.read(temp_out)
        return mastered
    else:
        print("  기본 마스터링 (Pedalboard)")
        board = Pedalboard([
            HighpassFilter(cutoff_frequency_hz=25.0),
            LowShelfFilter(cutoff_frequency_hz=80.0, gain_db=1.0),
            HighShelfFilter(cutoff_frequency_hz=10000.0, gain_db=1.0),
            Compressor(threshold_db=-12.0, ratio=2.0, attack_ms=10.0, release_ms=200.0),
            Limiter(threshold_db=-1.0, release_ms=100.0),
        ])
        return apply_board(audio, sr, board)


def normalize(audio: np.ndarray, sr: int, target_lufs: float = -14.0) -> np.ndarray:
    """라우드니스 노멀라이제이션."""
    print(f"\n📊 라우드니스 → {target_lufs} LUFS")
    meter = pyln.Meter(sr)
    current = meter.integrated_loudness(audio)
    print(f"  현재: {current:.1f} LUFS")

    normalized = pyln.normalize.loudness(audio, current, target_lufs)

    peak = np.max(np.abs(normalized))
    if peak > 0.99:
        normalized = normalized * (0.99 / peak)

    final_lufs = meter.integrated_loudness(normalized)
    print(f"  최종: {final_lufs:.1f} LUFS")
    return normalized


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="봄이라고 부를게 — Stems 믹싱")
    parser.add_argument("--reference", "-r", help="레퍼런스 곡 WAV", default=None)
    args = parser.parse_args()

    ensure_dirs()
    reference = Path(args.reference).resolve() if args.reference else None

    print("=" * 60)
    print("🎵 봄이라고 부를게 — Stems 믹싱 + 마스터링")
    print("=" * 60)

    # 스템 로드 + 개별 처리
    print("\n📂 스템 로드 + 처리...")
    vocals, sr = load_stem("Lead Vocals")
    backing, _ = load_stem("Backing Vocals")
    drums, _ = load_stem("Drums")
    bass, _ = load_stem("Bass")
    guitar, _ = load_stem("Guitar")
    keyboard, _ = load_stem("Keyboard")
    synth, _ = load_stem("Synth")
    other, _ = load_stem("Other")

    stems = {
        "Lead Vocals":    process_lead_vocal(vocals, sr),
        "Backing Vocals": process_backing_vocal(backing, sr),
        "Drums":          process_drums(drums, sr),
        "Bass":           process_bass(bass, sr),
        "Guitar":         process_guitar(guitar, sr),
        "Keyboard":       process_keyboard(keyboard, sr),
        "Synth":          process_synth(synth, sr),
        "Other":          process_other(other, sr),
    }

    # 처리된 개별 스템 저장 (디버깅/재조정용)
    for name, audio in stems.items():
        safe_name = name.replace(" ", "_").lower()
        sf.write(str(PROCESSED_DIR / f"{safe_name}.wav"), audio, sr)

    # 믹싱
    mixed = mix_all(stems, sr)

    # 마스터링
    mastered = master(mixed, sr, reference)

    # 라우드니스
    final = normalize(mastered, sr, target_lufs=-14.0)

    # 최종 저장
    output = RELEASE_DIR / "final.wav"
    sf.write(str(output), final, sr, subtype="PCM_16")

    # 결과 보고
    meter = pyln.Meter(sr)
    final_lufs = meter.integrated_loudness(final)
    peak_db = 20 * np.log10(np.max(np.abs(final)))
    duration = len(final) / sr

    print("\n" + "=" * 60)
    print("✅ 완료!")
    print(f"  📁 파일: {output}")
    print(f"  ⏱️  길이: {duration:.0f}초 ({duration/60:.1f}분)")
    print(f"  📊 LUFS: {final_lufs:.1f}")
    print(f"  📈 피크: {peak_db:.1f} dBFS")
    print(f"  🎵 포맷: WAV 16bit {sr}Hz")
    print("=" * 60)


if __name__ == "__main__":
    main()
