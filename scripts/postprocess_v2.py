"""경량 마스터링 v2 — Do No Harm + Analog Humanizer (Matchering/Demucs 제거).

Suno v5.5 raw 존중. full mix 직접 체인: HPF(60) → 약한 Comp → subtle Distortion →
미세 Reverb → Gain 0.5dB → loudnorm -14 LUFS.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

import soundfile as sf
from pedalboard import (
    Compressor,
    Distortion,
    Gain,
    HighpassFilter,
    Pedalboard,
    Reverb,
)

from postprocess import analyze


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--output-dir", required=True)
    args = p.parse_args()
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    src_wav = out / "original.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-i", args.input, str(src_wav), "-loglevel", "error"],
        check=True,
    )

    board = Pedalboard(
        [
            HighpassFilter(60),
            Compressor(threshold_db=-14, ratio=1.5, attack_ms=10, release_ms=100),
            Distortion(drive_db=2),
            Reverb(room_size=0.18, damping=0.5, wet_level=0.05, dry_level=0.95),
            Gain(gain_db=0.5),
        ]
    )

    data, sr = sf.read(str(src_wav))
    processed = board(data, sr)
    sf.write(str(out / "processed.wav"), processed, sr)

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(out / "processed.wav"),
            "-af",
            "loudnorm=I=-14:TP=-1.0:LRA=11",
            str(out / "mastered.wav"),
            "-loglevel",
            "error",
        ],
        check=True,
    )

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            args.input,
            "-b:a",
            "192k",
            str(out / "A_original.mp3"),
            "-loglevel",
            "error",
        ],
        check=True,
    )
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(out / "mastered.wav"),
            "-b:a",
            "192k",
            str(out / "C_minimal.mp3"),
            "-loglevel",
            "error",
        ],
        check=True,
    )

    report = {
        "original": analyze(src_wav),
        "minimal_v2": analyze(out / "mastered.wav"),
    }
    (out / "quality_report_v2.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False)
    )
    print("OK", out)


if __name__ == "__main__":
    main()
