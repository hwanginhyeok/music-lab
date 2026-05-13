#!/usr/bin/env python3
"""
Suno 후처리 파이프라인 v1
- 스템 분리 (Demucs htdemucs) → 장르별 이펙트 (Pedalboard) → 마스터링 (Limiter)
- 장르 프리셋: jazz, ballad, pop, rock, hiphop, edm, bossa, lofi
- 커스텀 프리셋 지원

사용법:
  python postprocess.py input.wav --genre jazz
  python postprocess.py input.wav --genre ballad --output output.wav
  python postprocess.py input.wav --preset custom_preset.json
  python postprocess.py --list-presets
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional

import numpy as np
import soundfile as sf
from pedalboard import (
    Pedalboard, Compressor, Reverb, Gain, 
    LowShelfFilter, HighShelfFilter, LowpassFilter, HighpassFilter,
    PeakFilter, Chorus, Delay, Limiter, Clipping,
    Distortion, Phaser, Bitcrush, NoiseGate, Invert, Mix
)

# ============================================================
# 장르별 프리셋 정의
# ============================================================

PRESETS = {
    "jazz": {
        "description": "재즈 — 따뜻한 저음, 자연스러운 다이나믹, 은은한 리버브",
        "stems": True,
        "vocal": {
            "gain_db": 2.0,
            "compressor_threshold_db": -18,
            "compressor_ratio": 2.5,
            "eq_low_cut_hz": 80,
            "eq_low_shelf_hz": 200,
            "eq_low_shelf_gain_db": 2.0,
            "eq_high_shelf_hz": 8000,
            "eq_high_shelf_gain_db": -1.0,
            "reverb_room_size": 0.35,
            "reverb_wet": 0.15,
            "limiter_db": -1.0,
        },
        "drums": {
            "gain_db": 0.0,
            "compressor_threshold_db": -12,
            "compressor_ratio": 3.0,
            "eq_low_shelf_hz": 100,
            "eq_low_shelf_gain_db": 2.0,
            "eq_high_shelf_hz": 6000,
            "eq_high_shelf_gain_db": 1.5,
            "reverb_room_size": 0.25,
            "reverb_wet": 0.10,
            "limiter_db": -1.0,
        },
        "bass": {
            "gain_db": 0.0,
            "compressor_threshold_db": -15,
            "compressor_ratio": 4.0,
            "eq_high_cut_hz": 800,
            "reverb_room_size": 0.0,
            "reverb_wet": 0.0,
            "limiter_db": -1.0,
        },
        "other": {
            "gain_db": -1.0,
            "compressor_threshold_db": -20,
            "compressor_ratio": 2.0,
            "eq_high_shelf_hz": 7000,
            "eq_high_shelf_gain_db": 1.0,
            "reverb_room_size": 0.30,
            "reverb_wet": 0.12,
            "limiter_db": -1.0,
        },
        "master": {
            "compressor_threshold_db": -14,
            "compressor_ratio": 2.0,
            "limiter_db": -1.0,
            "target_lufs": -14,
        },
    },

    "ballad": {
        "description": "발라드 — 보컬 앞으로, 풍부한 리버브, 부드러운 다이나믹",
        "stems": True,
        "vocal": {
            "gain_db": 3.0,
            "compressor_threshold_db": -15,
            "compressor_ratio": 3.0,
            "eq_low_cut_hz": 100,
            "eq_low_shelf_hz": 250,
            "eq_low_shelf_gain_db": 1.5,
            "eq_high_shelf_hz": 10000,
            "eq_high_shelf_gain_db": 2.0,
            "reverb_room_size": 0.55,
            "reverb_wet": 0.25,
            "chorus_rate_hz": 0.5,
            "chorus_depth": 0.3,
            "limiter_db": -1.0,
        },
        "drums": {
            "gain_db": -2.0,
            "compressor_threshold_db": -15,
            "compressor_ratio": 3.5,
            "eq_low_shelf_hz": 80,
            "eq_low_shelf_gain_db": 1.0,
            "reverb_room_size": 0.3,
            "reverb_wet": 0.15,
            "limiter_db": -1.0,
        },
        "bass": {
            "gain_db": -1.0,
            "compressor_threshold_db": -12,
            "compressor_ratio": 4.0,
            "eq_high_cut_hz": 500,
            "reverb_room_size": 0.0,
            "reverb_wet": 0.0,
            "limiter_db": -1.0,
        },
        "other": {
            "gain_db": 0.0,
            "compressor_threshold_db": -20,
            "compressor_ratio": 2.0,
            "eq_high_shelf_hz": 8000,
            "eq_high_shelf_gain_db": 1.5,
            "reverb_room_size": 0.40,
            "reverb_wet": 0.20,
            "limiter_db": -1.0,
        },
        "master": {
            "compressor_threshold_db": -12,
            "compressor_ratio": 2.0,
            "limiter_db": -1.0,
            "target_lufs": -14,
        },
    },

    "pop": {
        "description": "팝 — 펀치 있는 드럼, 밝은 보컬, 라우드 믹스",
        "stems": True,
        "vocal": {
            "gain_db": 2.5,
            "compressor_threshold_db": -16,
            "compressor_ratio": 4.0,
            "eq_low_cut_hz": 120,
            "eq_high_shelf_hz": 10000,
            "eq_high_shelf_gain_db": 3.0,
            "reverb_room_size": 0.30,
            "reverb_wet": 0.12,
            "limiter_db": -1.0,
        },
        "drums": {
            "gain_db": 1.0,
            "compressor_threshold_db": -10,
            "compressor_ratio": 4.0,
            "eq_low_shelf_hz": 80,
            "eq_low_shelf_gain_db": 3.0,
            "eq_high_shelf_hz": 5000,
            "eq_high_shelf_gain_db": 2.0,
            "reverb_room_size": 0.15,
            "reverb_wet": 0.08,
            "limiter_db": -1.0,
        },
        "bass": {
            "gain_db": 0.0,
            "compressor_threshold_db": -10,
            "compressor_ratio": 5.0,
            "eq_high_cut_hz": 600,
            "limiter_db": -1.0,
        },
        "other": {
            "gain_db": 0.0,
            "compressor_threshold_db": -18,
            "compressor_ratio": 3.0,
            "eq_high_shelf_hz": 8000,
            "eq_high_shelf_gain_db": 2.0,
            "reverb_room_size": 0.20,
            "reverb_wet": 0.10,
            "limiter_db": -1.0,
        },
        "master": {
            "compressor_threshold_db": -10,
            "compressor_ratio": 3.0,
            "limiter_db": -1.0,
            "target_lufs": -11,
        },
    },

    "rock": {
        "description": "록 — 공격적인 기타, 펀치 드럼, 가벼운 디스토션",
        "stems": True,
        "vocal": {
            "gain_db": 2.0,
            "compressor_threshold_db": -14,
            "compressor_ratio": 4.0,
            "eq_low_cut_hz": 120,
            "eq_high_shelf_hz": 8000,
            "eq_high_shelf_gain_db": 2.0,
            "distortion_db": 3.0,
            "reverb_room_size": 0.25,
            "reverb_wet": 0.10,
            "limiter_db": -1.0,
        },
        "drums": {
            "gain_db": 2.0,
            "compressor_threshold_db": -8,
            "compressor_ratio": 5.0,
            "eq_low_shelf_hz": 60,
            "eq_low_shelf_gain_db": 4.0,
            "eq_high_shelf_hz": 4000,
            "eq_high_shelf_gain_db": 3.0,
            "reverb_room_size": 0.15,
            "reverb_wet": 0.08,
            "limiter_db": -1.0,
        },
        "bass": {
            "gain_db": 1.0,
            "compressor_threshold_db": -10,
            "compressor_ratio": 6.0,
            "distortion_db": 2.0,
            "eq_high_cut_hz": 700,
            "limiter_db": -1.0,
        },
        "other": {
            "gain_db": 1.0,
            "compressor_threshold_db": -15,
            "compressor_ratio": 3.0,
            "distortion_db": 4.0,
            "eq_high_shelf_hz": 6000,
            "eq_high_shelf_gain_db": 2.0,
            "reverb_room_size": 0.20,
            "reverb_wet": 0.10,
            "limiter_db": -1.0,
        },
        "master": {
            "compressor_threshold_db": -8,
            "compressor_ratio": 3.0,
            "limiter_db": -1.0,
            "target_lufs": -10,
        },
    },

    "hiphop": {
        "description": "힙합 — 808 베이스 부스트, 크랙 하이햇, 드라이 보컬",
        "stems": True,
        "vocal": {
            "gain_db": 2.5,
            "compressor_threshold_db": -14,
            "compressor_ratio": 4.5,
            "eq_low_cut_hz": 100,
            "eq_high_shelf_hz": 10000,
            "eq_high_shelf_gain_db": 2.0,
            "reverb_room_size": 0.10,
            "reverb_wet": 0.05,
            "limiter_db": -1.0,
        },
        "drums": {
            "gain_db": 2.0,
            "compressor_threshold_db": -8,
            "compressor_ratio": 5.0,
            "eq_low_shelf_hz": 60,
            "eq_low_shelf_gain_db": 5.0,
            "eq_high_shelf_hz": 8000,
            "eq_high_shelf_gain_db": 3.0,
            "reverb_room_size": 0.05,
            "reverb_wet": 0.03,
            "limiter_db": -1.0,
        },
        "bass": {
            "gain_db": 3.0,
            "compressor_threshold_db": -8,
            "compressor_ratio": 6.0,
            "eq_high_cut_hz": 400,
            "eq_low_shelf_hz": 50,
            "eq_low_shelf_gain_db": 6.0,
            "limiter_db": -1.0,
        },
        "other": {
            "gain_db": -1.0,
            "compressor_threshold_db": -18,
            "compressor_ratio": 2.5,
            "reverb_room_size": 0.15,
            "reverb_wet": 0.05,
            "limiter_db": -1.0,
        },
        "master": {
            "compressor_threshold_db": -8,
            "compressor_ratio": 4.0,
            "limiter_db": -1.0,
            "target_lufs": -9,
        },
    },

    "edm": {
        "description": "EDM — 사이드체인 펌핑, 밝은 리드, 타이트 베이스",
        "stems": True,
        "vocal": {
            "gain_db": 1.5,
            "compressor_threshold_db": -12,
            "compressor_ratio": 5.0,
            "eq_low_cut_hz": 150,
            "eq_high_shelf_hz": 12000,
            "eq_high_shelf_gain_db": 3.0,
            "reverb_room_size": 0.30,
            "reverb_wet": 0.15,
            "limiter_db": -1.0,
        },
        "drums": {
            "gain_db": 1.5,
            "compressor_threshold_db": -6,
            "compressor_ratio": 6.0,
            "eq_low_shelf_hz": 60,
            "eq_low_shelf_gain_db": 4.0,
            "eq_high_shelf_hz": 10000,
            "eq_high_shelf_gain_db": 2.0,
            "limiter_db": -1.0,
        },
        "bass": {
            "gain_db": 1.0,
            "compressor_threshold_db": -6,
            "compressor_ratio": 8.0,
            "eq_high_cut_hz": 300,
            "eq_low_shelf_hz": 40,
            "eq_low_shelf_gain_db": 4.0,
            "limiter_db": -1.0,
        },
        "other": {
            "gain_db": 0.0,
            "compressor_threshold_db": -15,
            "compressor_ratio": 3.0,
            "eq_high_shelf_hz": 10000,
            "eq_high_shelf_gain_db": 2.0,
            "chorus_rate_hz": 1.5,
            "chorus_depth": 0.4,
            "delay_seconds": 0.375,
            "delay_feedback": 0.3,
            "delay_mix": 0.15,
            "reverb_room_size": 0.40,
            "reverb_wet": 0.20,
            "limiter_db": -1.0,
        },
        "master": {
            "compressor_threshold_db": -6,
            "compressor_ratio": 4.0,
            "limiter_db": -1.0,
            "target_lufs": -8,
        },
    },

    "bossa": {
        "description": "보사노바 — 나일론 기타 질감, 부드러운 보컬, 따뜻한 저음",
        "stems": True,
        "vocal": {
            "gain_db": 2.5,
            "compressor_threshold_db": -18,
            "compressor_ratio": 2.0,
            "eq_low_cut_hz": 80,
            "eq_high_shelf_hz": 8000,
            "eq_high_shelf_gain_db": 0.5,
            "reverb_room_size": 0.40,
            "reverb_wet": 0.20,
            "limiter_db": -1.0,
        },
        "drums": {
            "gain_db": -2.0,
            "compressor_threshold_db": -18,
            "compressor_ratio": 2.0,
            "eq_low_shelf_hz": 120,
            "eq_low_shelf_gain_db": -1.0,
            "eq_high_shelf_hz": 5000,
            "eq_high_shelf_gain_db": 1.0,
            "reverb_room_size": 0.30,
            "reverb_wet": 0.15,
            "limiter_db": -1.0,
        },
        "bass": {
            "gain_db": 0.0,
            "compressor_threshold_db": -15,
            "compressor_ratio": 3.0,
            "eq_high_cut_hz": 600,
            "reverb_room_size": 0.0,
            "reverb_wet": 0.0,
            "limiter_db": -1.0,
        },
        "other": {
            "gain_db": 1.0,
            "compressor_threshold_db": -20,
            "compressor_ratio": 2.0,
            "eq_high_shelf_hz": 6000,
            "eq_high_shelf_gain_db": 1.0,
            "reverb_room_size": 0.45,
            "reverb_wet": 0.25,
            "chorus_rate_hz": 0.3,
            "chorus_depth": 0.2,
            "limiter_db": -1.0,
        },
        "master": {
            "compressor_threshold_db": -16,
            "compressor_ratio": 1.5,
            "limiter_db": -1.0,
            "target_lufs": -15,
        },
    },

    "lofi": {
        "description": "로파이 — 비트크러시, 빈티지 웜핑, 테이프 리버브",
        "stems": True,
        "vocal": {
            "gain_db": 1.5,
            "compressor_threshold_db": -16,
            "compressor_ratio": 3.0,
            "eq_low_cut_hz": 200,
            "eq_high_cut_hz": 6000,
            "eq_low_shelf_hz": 300,
            "eq_low_shelf_gain_db": 2.0,
            "bitcrush_bit_depth": 12,
            "reverb_room_size": 0.50,
            "reverb_wet": 0.25,
            "limiter_db": -1.0,
        },
        "drums": {
            "gain_db": 0.0,
            "compressor_threshold_db": -10,
            "compressor_ratio": 4.0,
            "eq_low_shelf_hz": 100,
            "eq_low_shelf_gain_db": 2.0,
            "eq_high_cut_hz": 5000,
            "bitcrush_bit_depth": 10,
            "reverb_room_size": 0.35,
            "reverb_wet": 0.20,
            "limiter_db": -1.0,
        },
        "bass": {
            "gain_db": 1.0,
            "compressor_threshold_db": -12,
            "compressor_ratio": 4.0,
            "eq_high_cut_hz": 400,
            "reverb_room_size": 0.0,
            "reverb_wet": 0.0,
            "limiter_db": -1.0,
        },
        "other": {
            "gain_db": -1.0,
            "compressor_threshold_db": -20,
            "compressor_ratio": 2.0,
            "eq_high_cut_hz": 5000,
            "eq_low_shelf_hz": 400,
            "eq_low_shelf_gain_db": 3.0,
            "bitcrush_bit_depth": 8,
            "chorus_rate_hz": 0.2,
            "chorus_depth": 0.5,
            "reverb_room_size": 0.60,
            "reverb_wet": 0.30,
            "limiter_db": -1.0,
        },
        "master": {
            "compressor_threshold_db": -14,
            "compressor_ratio": 2.0,
            "limiter_db": -1.0,
            "target_lufs": -14,
        },
    },
}

# ============================================================
# 스템 분리 (Demucs CLI)
# ============================================================

def separate_stems(input_path: str, output_dir: str, model_name: str = "htdemucs") -> dict:
    """Demucs로 스템 분리 (직접 API 호출 + soundfile 저장). 반환: {stem_name: wav_path}"""
    import torch
    from demucs.pretrained import get_model
    from demucs.apply import apply_model
    from demucs.audio import AudioFile

    print(f"  [Demucs] 분리 중... model={model_name}")
    model = get_model(model_name)
    model.eval()

    # 오디오 로드
    wav = AudioFile(input_path).read(streams=0, samplerate=44100, channels=2)
    
    # 정규화
    ref = wav.mean(0)
    wav_input = (wav - ref.mean()) / ref.std()
    
    # 분리
    with torch.no_grad():
        sources = apply_model(model, wav_input[None], progress=True)[0]
    
    # 역정규화
    sources = sources * ref.std() + ref.mean()
    
    # 저장
    os.makedirs(output_dir, exist_ok=True)
    stems = {}
    for i, name in enumerate(model.sources):
        out_path = os.path.join(output_dir, f"{name}.wav")
        audio = sources[i].numpy().T  # (samples, channels)
        sf.write(out_path, audio, 44100)
        stems[name] = out_path
    
    print(f"  [Demucs] 분리 완료: {list(stems.keys())}")
    return stems


def separate_stems_fallback(input_path: str) -> dict:
    """Demucs가 안 되면 사운드파일로 그냥 통째로 리턴"""
    print("  [Fallback] Demucs 없이 통째로 처리")
    return {"mix": input_path}


# ============================================================
# 이펙트 적용
# ============================================================

def build_stem_effects(config: dict) -> Pedalboard:
    """스템 설정 딕셔너리 → Pedalboard 이펙트 체인"""
    effects = []

    # Gain
    if "gain_db" in config:
        effects.append(Gain(gain_db=config["gain_db"]))

    # Compressor
    if "compressor_threshold_db" in config:
        effects.append(Compressor(
            threshold_db=config["compressor_threshold_db"],
            ratio=config.get("compressor_ratio", 3.0),
            attack_ms=config.get("compressor_attack_ms", 10.0),
            release_ms=config.get("compressor_release_ms", 100.0),
        ))

    # EQ - Low Cut (Highpass)
    if "eq_low_cut_hz" in config:
        effects.append(HighpassFilter(cutoff_frequency_hz=config["eq_low_cut_hz"]))

    # EQ - Low Shelf
    if "eq_low_shelf_hz" in config:
        effects.append(LowShelfFilter(
            cutoff_frequency_hz=config["eq_low_shelf_hz"],
            gain_db=config.get("eq_low_shelf_gain_db", 0.0),
        ))

    # EQ - High Shelf
    if "eq_high_shelf_hz" in config:
        effects.append(HighShelfFilter(
            cutoff_frequency_hz=config["eq_high_shelf_hz"],
            gain_db=config.get("eq_high_shelf_gain_db", 0.0),
        ))

    # EQ - High Cut (Lowpass)
    if "eq_high_cut_hz" in config:
        effects.append(LowpassFilter(cutoff_frequency_hz=config["eq_high_cut_hz"]))

    # Distortion
    if "distortion_db" in config:
        effects.append(Distortion(drive_db=config["distortion_db"]))

    # Bitcrush
    if "bitcrush_bit_depth" in config:
        effects.append(Bitcrush(bit_depth=config["bitcrush_bit_depth"]))

    # Chorus
    if "chorus_rate_hz" in config:
        effects.append(Chorus(
            rate_hz=config["chorus_rate_hz"],
            depth=config.get("chorus_depth", 0.3),
        ))

    # Delay
    if "delay_seconds" in config:
        effects.append(Delay(
            delay_seconds=config["delay_seconds"],
            feedback=config.get("delay_feedback", 0.3),
            mix=config.get("delay_mix", 0.2),
        ))

    # Reverb
    if config.get("reverb_room_size", 0) > 0:
        effects.append(Reverb(
            room_size=config.get("reverb_room_size", 0.3),
            dry_level=0.8,
            wet_level=config.get("reverb_wet", 0.15),
            width=config.get("reverb_width", 1.0),
        ))

    # Limiter
    effects.append(Limiter(threshold_db=config.get("limiter_db", -1.0)))

    return Pedalboard(effects)


def process_stem(audio: np.ndarray, sr: int, config: dict) -> np.ndarray:
    """단일 스템에 이펙트 적용"""
    board = build_stem_effects(config)
    
    # mono → stereo 처리 지원
    if audio.ndim == 1:
        audio = audio.reshape(1, -1)
    
    processed = board(audio, sr)
    return processed


def process_master(mix: np.ndarray, sr: int, config: dict) -> np.ndarray:
    """마스터 버스 이펙트 (최종 믹스에 적용)"""
    effects = []
    
    if "compressor_threshold_db" in config:
        effects.append(Compressor(
            threshold_db=config["compressor_threshold_db"],
            ratio=config.get("compressor_ratio", 2.0),
            attack_ms=5.0,
            release_ms=50.0,
        ))
    
    # LUFS 근사치 조정 (간단한 gain으로)
    target_lufs = config.get("target_lufs", -14)
    # 간단 라우드니스 조정: 현재 RMS vs 타겟
    rms = np.sqrt(np.mean(mix ** 2))
    if rms > 0:
        current_lufs_approx = 20 * np.log10(rms) - 0.691
        gain_adjust = target_lufs - current_lufs_approx
        gain_adjust = np.clip(gain_adjust, -10, 10)  # 극단적 조정 방지
        effects.append(Gain(gain_db=gain_adjust))
    
    effects.append(Limiter(threshold_db=config.get("limiter_db", -1.0)))
    
    board = Pedalboard(effects)
    
    if mix.ndim == 1:
        mix = mix.reshape(1, -1)
    
    return board(mix, sr)


# ============================================================
# 메인 파이프라인
# ============================================================

def postprocess(input_path: str, output_path: str, preset_name: str = "jazz",
                custom_preset: Optional[dict] = None, skip_stems: bool = False):
    """전체 후처리 파이프라인 실행"""
    
    preset = custom_preset or PRESETS.get(preset_name)
    if not preset:
        print(f"  [Error] 프리셋 '{preset_name}' 없음. 사용 가능: {list(PRESETS.keys())}")
        sys.exit(1)
    
    print(f"\n{'='*60}")
    print(f"  Suno 후처리 — 프리셋: {preset_name}")
    print(f"  입력: {input_path}")
    print(f"  출력: {output_path}")
    print(f"{'='*60}")
    
    # 1. 오디오 로드
    audio, sr = sf.read(input_path)
    print(f"  [Load] {audio.shape}, {sr}Hz, {len(audio)/sr:.1f}s")
    
    # 스테레오로 변환
    if audio.ndim == 1:
        audio = np.stack([audio, audio], axis=0)
    elif audio.ndim == 2:
        audio = audio.T  # (samples, channels) → (channels, samples)
    
    # 2. 스템 분리
    if not skip_stems and preset.get("stems", True):
        try:
            stems = separate_stems(input_path, "/tmp/demucs_output")
        except Exception as e:
            print(f"  [Demucs] 실패, fallback: {e}")
            stems = separate_stems_fallback(input_path)
    else:
        stems = separate_stems_fallback(input_path)
    
    # 3. 스템별 이펙트 적용 + 믹싱
    if len(stems) > 1:
        processed_stems = {}
        stem_mix = None
        
        for stem_name, stem_path in stems.items():
            stem_audio, stem_sr = sf.read(stem_path)
            if stem_audio.ndim == 1:
                stem_audio = np.stack([stem_audio, stem_audio], axis=0)
            elif stem_audio.ndim == 2:
                stem_audio = stem_audio.T
            
            # 스템 타입에 맞는 프리셋 선택
            if "vocal" in stem_name.lower():
                stem_config = preset.get("vocal", preset.get("other", {}))
            elif "drum" in stem_name.lower():
                stem_config = preset.get("drums", preset.get("other", {}))
            elif "bass" in stem_name.lower():
                stem_config = preset.get("bass", preset.get("other", {}))
            else:
                stem_config = preset.get("other", {})
            
            print(f"  [Process] {stem_name}: {list(stem_config.keys())[:5]}...")
            processed = process_stem(stem_audio, stem_sr, stem_config)
            processed_stems[stem_name] = processed
            
            # 믹스에 추가
            if stem_mix is None:
                stem_mix = processed.copy()
            else:
                # 길이 맞추기
                min_len = min(stem_mix.shape[1], processed.shape[1])
                stem_mix = stem_mix[:, :min_len] + processed[:, :min_len]
        
        mix = stem_mix
    else:
        # 통째로 처리
        mix_config = preset.get("other", {})
        print(f"  [Process] 전체 믹스 처리")
        mix = process_stem(audio, sr, mix_config)
    
    # 4. 마스터 이펙트
    master_config = preset.get("master", {})
    if master_config:
        print(f"  [Master] 적용 중...")
        mix = process_master(mix, sr, master_config)
    
    # 5. 출력
    # (channels, samples) → (samples, channels) for soundfile
    out = mix.T
    if out.ndim == 2 and out.shape[1] == 2 and np.allclose(out[:, 0], out[:, 1]):
        out = out[:, 0]  # 모노면 모노로 저장
    
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    sf.write(output_path, out, sr)
    
    duration = len(out) / sr
    filesize = os.path.getsize(output_path)
    print(f"\n  [Done] {output_path}")
    print(f"  길이: {duration:.1f}s / 크기: {filesize/1024:.0f}KB")
    print(f"{'='*60}\n")


# ============================================================
# CLI
# ============================================================

def list_presets():
    print(f"\n{'='*50}")
    print("  사용 가능한 장르 프리셋")
    print(f"{'='*50}")
    for name, preset in PRESETS.items():
        desc = preset.get("description", "")
        print(f"  {name:12s} — {desc}")
    print(f"{'='*50}\n")


def main():
    parser = argparse.ArgumentParser(description="Suno 후처리 파이프라인")
    parser.add_argument("input", nargs="?", help="입력 WAV/MP3 파일")
    parser.add_argument("--genre", "-g", default="jazz", help="장르 프리셋")
    parser.add_argument("--output", "-o", help="출력 파일 (기본: input_processed.wav)")
    parser.add_argument("--preset", "-p", help="커스텀 프리셋 JSON 파일")
    parser.add_argument("--list-presets", "-l", action="store_true", help="프리셋 목록")
    parser.add_argument("--skip-stems", action="store_true", help="스템 분리 건너뛰기")
    
    args = parser.parse_args()
    
    if args.list_presets:
        list_presets()
        return
    
    if not args.input:
        parser.print_help()
        return
    
    if not os.path.exists(args.input):
        print(f"파일 없음: {args.input}")
        sys.exit(1)
    
    # 출력 경로
    if args.output:
        output = args.output
    else:
        base, ext = os.path.splitext(args.input)
        output = f"{base}_{args.genre}{ext}"
    
    # 커스텀 프리셋
    custom = None
    if args.preset:
        with open(args.preset) as f:
            custom = json.load(f)
    
    postprocess(args.input, output, args.genre, custom, args.skip_stems)


if __name__ == "__main__":
    main()
