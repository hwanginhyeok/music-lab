"""후처리 PoC — Demucs 스템 분리 + Pedalboard 보컬 체인 + Matchering + loudnorm.

Pipeline v2 Phase 1 (F-04). 입력 mp3/wav → 마스터링된 mp3 + 품질 지표 리포트.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import librosa
import matchering as mg
import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from pedalboard import (
    Chorus,
    Compressor,
    Gain,
    HighpassFilter,
    HighShelfFilter,
    LowShelfFilter,
    NoiseGate,
    Pedalboard,
    Reverb,
)


def analyze(wav_path):
    data, sr = sf.read(str(wav_path))
    y = data.mean(axis=1) if data.ndim == 2 else data
    meter = pyln.Meter(sr)
    lufs = meter.integrated_loudness(data)
    peak_db = 20 * np.log10(np.max(np.abs(data)) + 1e-9)
    rms = np.sqrt(np.mean(y ** 2))
    crest_db = 20 * np.log10((np.max(np.abs(y)) + 1e-9) / (rms + 1e-9))
    cent = librosa.feature.spectral_centroid(y=y, sr=sr).mean()
    flat = librosa.feature.spectral_flatness(y=y).mean()
    rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr).mean()
    if data.ndim == 2:
        mid = (data[:, 0] + data[:, 1]) / 2
        side = (data[:, 0] - data[:, 1]) / 2
        width = float(np.sqrt(np.mean(side ** 2)) / (np.sqrt(np.mean(mid ** 2)) + 1e-9))
    else:
        width = 0.0
    return dict(
        lufs=float(lufs),
        peak_db=float(peak_db),
        crest_db=float(crest_db),
        centroid_hz=float(cent),
        spectral_flatness=float(flat),
        rolloff_hz=float(rolloff),
        stereo_width=float(width),
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--reference", required=True)
    p.add_argument("--output-dir", required=True)
    args = p.parse_args()
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    src_wav = out / "original.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-i", args.input, str(src_wav), "-loglevel", "error"],
        check=True,
    )

    subprocess.run(
        [
            "python3",
            "-m",
            "demucs",
            "--two-stems=vocals",
            "-n",
            "htdemucs",
            "-o",
            str(out / "stems"),
            str(src_wav),
        ],
        check=True,
    )
    stem_dir = out / "stems" / "htdemucs" / "original"
    vocals = sf.read(str(stem_dir / "vocals.wav"))
    nonvocals = sf.read(str(stem_dir / "no_vocals.wav"))

    board = Pedalboard(
        [
            HighpassFilter(80),
            NoiseGate(threshold_db=-60),
            Compressor(threshold_db=-18, ratio=3.0, attack_ms=5, release_ms=80),
            HighShelfFilter(cutoff_frequency_hz=12000, gain_db=-1.0),
            LowShelfFilter(cutoff_frequency_hz=200, gain_db=1.5),
            Chorus(rate_hz=0.3, depth=0.02, mix=0.08),
            Reverb(room_size=0.25, damping=0.4, wet_level=0.1, dry_level=0.9),
            Gain(gain_db=1.0),
        ]
    )
    v_data, v_sr = vocals
    v_processed = board(v_data, v_sr)
    sf.write(str(out / "vocal_processed.wav"), v_processed, v_sr)

    nv_data, nv_sr = nonvocals
    assert v_sr == nv_sr
    min_len = min(len(v_processed), len(nv_data))
    mixed = v_processed[:min_len] * 1.0 + nv_data[:min_len] * 0.95
    peak = float(np.max(np.abs(mixed)))
    if peak > 1.0:
        mixed = mixed / peak
    sf.write(str(out / "premaster.wav"), mixed, v_sr)

    mg.log(lambda msg: None)
    mg.process(
        target=str(out / "premaster.wav"),
        reference=args.reference,
        results=[mg.Result(str(out / "matched.wav"), subtype="FLOAT")],
    )

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(out / "matched.wav"),
            "-af",
            "loudnorm=I=-14:TP=-1.0:LRA=11",
            str(out / "mastered.wav"),
            "-loglevel",
            "error",
        ],
        check=True,
    )

    report = {
        "original": analyze(src_wav),
        "mastered": analyze(out / "mastered.wav"),
        "reference": analyze(args.reference),
    }
    (out / "quality_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False)
    )

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(src_wav),
            "-b:a",
            "192k",
            str(out / "A_original.mp3"),
            "-loglevel",
            "error",
        ]
    )
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(out / "mastered.wav"),
            "-b:a",
            "192k",
            str(out / "B_mastered.mp3"),
            "-loglevel",
            "error",
        ]
    )
    print("OK", out)


if __name__ == "__main__":
    main()
