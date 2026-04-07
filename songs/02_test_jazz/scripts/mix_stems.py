#!/usr/bin/env python3
"""
재즈 곡 — Stems 기반 믹싱 + 마스터링 (smooth jazz)

Suno Stems 8트랙을 재즈 장르에 맞게 처리.
재즈 특성: 다이내믹 레인지 넓게, 자연스러운 리버브, 악기 분리감.

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
# 트랙별 처리 — 재즈 (smooth jazz) 최적화
# ---------------------------------------------------------------------------

def process_lead_vocal(audio: np.ndarray, sr: int) -> np.ndarray:
    """메인 보컬. 재즈: 넓은 다이내믹, 따뜻한 톤, 자연스러운 룸."""
    print("  Lead Vocals: HPF -> NoiseGate -> Comp 2.5:1 -> EQ -> Room Reverb")
    board = Pedalboard([
        HighpassFilter(cutoff_frequency_hz=80.0),
        NoiseGate(threshold_db=-45.0, release_ms=120.0),
        # 재즈: 컴프 약하게 (다이내믹 보존)
        Compressor(threshold_db=-20.0, ratio=2.5, attack_ms=8.0, release_ms=120.0),
        LowShelfFilter(cutoff_frequency_hz=200.0, gain_db=-1.5),
        HighShelfFilter(cutoff_frequency_hz=3000.0, gain_db=1.5),
        HighShelfFilter(cutoff_frequency_hz=8000.0, gain_db=1.0),
        # 재즈: 넓은 룸, 자연스러운 감쇠
        Reverb(room_size=0.40, wet_level=0.15, dry_level=0.85, damping=0.5),
        Gain(gain_db=0.5),
        Limiter(threshold_db=-2.0, release_ms=80.0),
    ])
    return apply_board(audio, sr, board)


def process_backing_vocal(audio: np.ndarray, sr: int) -> np.ndarray:
    """배킹 보컬 / 스캣. 재즈: 공간감 넓게."""
    print("  Backing Vocals: HPF -> Comp -> Wide Reverb -> Gain")
    board = Pedalboard([
        HighpassFilter(cutoff_frequency_hz=120.0),
        Compressor(threshold_db=-25.0, ratio=2.0, attack_ms=10.0, release_ms=150.0),
        HighShelfFilter(cutoff_frequency_hz=5000.0, gain_db=1.0),
        Reverb(room_size=0.55, wet_level=0.22, dry_level=0.78, damping=0.4),
        Gain(gain_db=5.0),
    ])
    return apply_board(audio, sr, board)


def process_drums(audio: np.ndarray, sr: int) -> np.ndarray:
    """드럼 (브러시/라이드). 재즈: 어택 살리고, 자연스러운 서스테인."""
    print("  Drums: HPF -> Light Comp -> EQ -> Room Reverb")
    board = Pedalboard([
        HighpassFilter(cutoff_frequency_hz=35.0),
        Compressor(threshold_db=-18.0, ratio=2.5, attack_ms=5.0, release_ms=80.0),
        LowShelfFilter(cutoff_frequency_hz=100.0, gain_db=0.5),
        HighShelfFilter(cutoff_frequency_hz=6000.0, gain_db=1.5),
        Reverb(room_size=0.35, wet_level=0.10, dry_level=0.90, damping=0.6),
        Gain(gain_db=-0.5),
    ])
    return apply_board(audio, sr, board)


def process_bass(audio: np.ndarray, sr: int) -> np.ndarray:
    """베이스 (업라이트/핑거). 재즈: 따뜻한 톤, 워킹 베이스 선명도."""
    print("  Bass: HPF -> LPF -> Light Comp -> EQ -> Room")
    board = Pedalboard([
        HighpassFilter(cutoff_frequency_hz=30.0),
        LowpassFilter(cutoff_frequency_hz=6000.0),
        Compressor(threshold_db=-22.0, ratio=3.0, attack_ms=8.0, release_ms=100.0),
        LowShelfFilter(cutoff_frequency_hz=80.0, gain_db=1.0),
        HighShelfFilter(cutoff_frequency_hz=2000.0, gain_db=1.0),
        Reverb(room_size=0.20, wet_level=0.06, dry_level=0.94, damping=0.7),
        Gain(gain_db=0.5),
    ])
    return apply_board(audio, sr, board)


def process_guitar(audio: np.ndarray, sr: int) -> np.ndarray:
    """기타 (재즈 클린톤/나일론). 재즈: 클린 톤, 따뜻한 중역."""
    print("  Guitar: HPF -> Light Comp -> EQ -> Reverb")
    board = Pedalboard([
        HighpassFilter(cutoff_frequency_hz=80.0),
        Compressor(threshold_db=-20.0, ratio=2.0, attack_ms=12.0, release_ms=120.0),
        LowShelfFilter(cutoff_frequency_hz=250.0, gain_db=-1.0),
        HighShelfFilter(cutoff_frequency_hz=4000.0, gain_db=0.5),
        Reverb(room_size=0.30, wet_level=0.12, dry_level=0.88, damping=0.6),
        Gain(gain_db=0.0),
    ])
    return apply_board(audio, sr, board)


def process_keyboard(audio: np.ndarray, sr: int) -> np.ndarray:
    """키보드/피아노 (어쿠스틱 or Rhodes). 재즈: 핵심 악기, 공간감."""
    print("  Keyboard: HPF -> Light Comp -> EQ -> Room Reverb")
    board = Pedalboard([
        HighpassFilter(cutoff_frequency_hz=60.0),
        Compressor(threshold_db=-22.0, ratio=2.0, attack_ms=15.0, release_ms=150.0),
        LowShelfFilter(cutoff_frequency_hz=200.0, gain_db=-0.5),
        HighShelfFilter(cutoff_frequency_hz=5000.0, gain_db=1.0),
        HighShelfFilter(cutoff_frequency_hz=10000.0, gain_db=0.5),
        Reverb(room_size=0.40, wet_level=0.15, dry_level=0.85, damping=0.5),
        Gain(gain_db=0.5),
    ])
    return apply_board(audio, sr, board)


def process_synth(audio: np.ndarray, sr: int) -> np.ndarray:
    """신스/패드. 재즈: 배경 텍스처, 뒤로 밀기."""
    print("  Synth: HPF -> Comp -> Reverb -> Gain")
    board = Pedalboard([
        HighpassFilter(cutoff_frequency_hz=60.0),
        Compressor(threshold_db=-20.0, ratio=2.0, attack_ms=15.0, release_ms=120.0),
        Reverb(room_size=0.50, wet_level=0.18, dry_level=0.82, damping=0.4),
        Gain(gain_db=-2.0),
    ])
    return apply_board(audio, sr, board)


def process_other(audio: np.ndarray, sr: int) -> np.ndarray:
    """기타 악기 (색소폰, 트럼펫 등이 여기 올 수 있음)."""
    print("  Other: HPF -> Light Comp -> EQ -> Reverb")
    board = Pedalboard([
        HighpassFilter(cutoff_frequency_hz=60.0),
        Compressor(threshold_db=-20.0, ratio=2.0, attack_ms=10.0, release_ms=100.0),
        HighShelfFilter(cutoff_frequency_hz=4000.0, gain_db=1.0),
        Reverb(room_size=0.35, wet_level=0.12, dry_level=0.88, damping=0.5),
        Gain(gain_db=0.5),
    ])
    return apply_board(audio, sr, board)


# ---------------------------------------------------------------------------
# 믹싱 — 재즈 밸런스
# ---------------------------------------------------------------------------

MIX_LEVELS = {
    "Lead Vocals":   1.00,
    "Backing Vocals":   0.30,
    "Drums":   0.45,
    "Bass":   0.55,
    "Guitar":   0.40,
    "Keyboard":   0.65,
    "Synth":   0.25,
    "Other":   0.55,
}


def mix_all(stems: dict[str, np.ndarray], sr: int) -> np.ndarray:
    """모든 트랙 믹싱."""
    print("\n믹싱...")

    min_len = min(len(s) for s in stems.values())
    mixed = np.zeros((min_len, 2), dtype=np.float64)

    for name, audio in stems.items():
        level = MIX_LEVELS.get(name, 0.3)
        mixed += audio[:min_len] * level
        print(f"  + {name}: x{level}")

    peak = np.max(np.abs(mixed))
    if peak > 0.95:
        mixed = mixed * (0.90 / peak)
        print(f"  피크 제한 적용 ({peak:.2f} -> 0.90)")

    output_path = PROCESSED_DIR / "mixed.wav"
    sf.write(str(output_path), mixed, sr)
    print(f"  -> {output_path}")
    return mixed


# ---------------------------------------------------------------------------
# 마스터링 — 재즈: 다이내믹 보존, 과도한 리미팅 금지
# ---------------------------------------------------------------------------

def master(audio: np.ndarray, sr: int, reference_path: Path | None = None) -> np.ndarray:
    """마스터링. 재즈: 다이내믹 레인지 넓게 유지."""
    print("\n마스터링...")

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
        print("  기본 마스터링 (재즈 — 다이내믹 우선)")
        board = Pedalboard([
            HighpassFilter(cutoff_frequency_hz=25.0),
            LowShelfFilter(cutoff_frequency_hz=80.0, gain_db=0.5),
            HighShelfFilter(cutoff_frequency_hz=10000.0, gain_db=0.5),
            Compressor(threshold_db=-15.0, ratio=1.5, attack_ms=15.0, release_ms=250.0),
            Limiter(threshold_db=-1.0, release_ms=120.0),
        ])
        return apply_board(audio, sr, board)


def normalize(audio: np.ndarray, sr: int, target_lufs: float = -14.0) -> np.ndarray:
    """라우드니스 노멀라이제이션."""
    print(f"\n라우드니스 -> {target_lufs} LUFS")
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
    parser = argparse.ArgumentParser(description="재즈 곡 — Stems 믹싱 (smooth jazz)")
    parser.add_argument("--reference", "-r", help="레퍼런스 곡 WAV", default=None)
    args = parser.parse_args()

    ensure_dirs()
    reference = Path(args.reference).resolve() if args.reference else None

    print("=" * 60)
    print("재즈 곡 — Stems 믹싱 + 마스터링 (smooth jazz)")
    print("=" * 60)

    print("\n스템 로드 + 처리...")
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

    for name, audio in stems.items():
        safe_name = name.replace(" ", "_").lower()
        sf.write(str(PROCESSED_DIR / f"{safe_name}.wav"), audio, sr)

    mixed = mix_all(stems, sr)
    mastered = master(mixed, sr, reference)
    final = normalize(mastered, sr, target_lufs=-14.0)

    output = RELEASE_DIR / "final.wav"
    sf.write(str(output), final, sr, subtype="PCM_16")

    meter = pyln.Meter(sr)
    final_lufs = meter.integrated_loudness(final)
    peak_db = 20 * np.log10(np.max(np.abs(final)))
    duration = len(final) / sr

    print("\n" + "=" * 60)
    print("완료!")
    print(f"  파일: {output}")
    print(f"  길이: {duration:.0f}초 ({duration/60:.1f}분)")
    print(f"  LUFS: {final_lufs:.1f}")
    print(f"  피크: {peak_db:.1f} dBFS")
    print(f"  포맷: WAV 16bit {sr}Hz")
    print("=" * 60)


if __name__ == "__main__":
    main()
