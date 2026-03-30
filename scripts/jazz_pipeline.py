#!/usr/bin/env python3
"""
재즈 곡 자동 생성 파이프라인

컨셉 → 가사 → Suno 프롬프트 → mix_stems.py 까지 한 번에 생성.
Claude CLI를 사용해 각 단계를 자동으로 처리한다.

사용법:
  # 대화형 (서브장르 선택)
  python3 scripts/jazz_pipeline.py

  # 옵션 지정
  python3 scripts/jazz_pipeline.py --subgenre "smooth jazz" --mood "밤거리" --theme "도시의 밤"

  # Claude 호출 없이 구조만 생성 (테스트용)
  python3 scripts/jazz_pipeline.py --dry-run --theme "테스트"

  # 특정 단계만 실행
  python3 scripts/jazz_pipeline.py --steps concept,lyrics --theme "비 오는 날"
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

# ---------------------------------------------------------------------------
# 재즈 서브장르 프리셋
# ---------------------------------------------------------------------------

JAZZ_PRESETS: dict[str, dict] = {
    "smooth jazz": {
        "bpm": "80-100",
        "key": "Eb Major / Bb Major",
        "instruments": "일렉트릭 피아노 (Rhodes), 소프라노 색소폰, 핑거 베이스, 브러시 드럼",
        "feel": "부드럽고 세련된, 도시적, 야경",
        "progressions": "IΔ7 → vi7 → ii7 → V7, I → IV → iii7 → VI7",
        "suno_style": "smooth jazz, electric piano Rhodes, soprano saxophone, finger bass, brush drums, mellow, sophisticated, city night",
        "vocal_style": "smooth warm vocal, breathy tone, jazz phrasing, gentle scatting",
        "reference": "Kenny G, Grover Washington Jr., George Benson",
    },
    "jazz ballad": {
        "bpm": "60-75",
        "key": "Db Major / F Major",
        "instruments": "어쿠스틱 피아노, 업라이트 베이스, 브러시 드럼, 플루겔혼",
        "feel": "깊고 서정적인, 새벽 감성, 고백",
        "progressions": "IΔ7 → vi7 → ii7 → V7, iii7 → vi7 → ii7 → V7sus4",
        "suno_style": "jazz ballad, acoustic piano, upright bass, brush drums, flugelhorn, deep emotional, intimate, late night confession",
        "vocal_style": "warm intimate vocal, rich vibrato, emotional jazz phrasing, slight rasp",
        "reference": "Chet Baker, Norah Jones, Bill Evans",
    },
    "bossa nova": {
        "bpm": "120-140",
        "key": "C Major / A minor",
        "instruments": "나일론 기타, 피아노, 업라이트 베이스, 쉐이커/하이햇, 플루트",
        "feel": "따뜻하고 여유로운, 카페, 오후 햇살",
        "progressions": "IΔ7 → ii7 → V7 → IΔ7, IΔ7 → #IVm7b5 → ii7 → V7",
        "suno_style": "bossa nova, nylon guitar, soft piano, upright bass, shaker, flute, warm breeze, cafe afternoon, Brazilian jazz",
        "vocal_style": "soft whispery vocal, gentle bossa phrasing, light and airy, Portuguese-inspired",
        "reference": "Antonio Carlos Jobim, Stan Getz, Astrud Gilberto",
    },
    "cool jazz": {
        "bpm": "100-130",
        "key": "C Major / G Major",
        "instruments": "피아노, 테너 색소폰, 업라이트 베이스, 브러시 드럼, 비브라폰",
        "feel": "차분하고 지적인, 모던, 절제된",
        "progressions": "IΔ7 → vi7 → ii7 → V7, I → bVII7 → bVI7 → V7",
        "suno_style": "cool jazz, piano, tenor saxophone, upright bass, brush drums, vibraphone, restrained, modern, intellectual",
        "vocal_style": "cool detached vocal, understated emotion, jazz phrasing, clean tone",
        "reference": "Miles Davis, Dave Brubeck, Chet Baker",
    },
    "jazz fusion": {
        "bpm": "110-140",
        "key": "E minor / D Dorian",
        "instruments": "일렉 기타, 신스 패드, 일렉 베이스 (슬랩), 드럼 (하이햇 16th), 키보드",
        "feel": "에너지틱하고 실험적, 그루비, 펑키",
        "progressions": "i7 → IV7 → bVII7 → i7, Dorian vamp + chromatic approach",
        "suno_style": "jazz fusion, electric guitar, synth pad, slap bass, funky drums, groovy, experimental, energetic",
        "vocal_style": "powerful vocal, rhythmic phrasing, scat improvisation, funky groove",
        "reference": "Herbie Hancock, Weather Report, Chick Corea",
    },
    "swing": {
        "bpm": "140-180",
        "key": "Bb Major / F Major",
        "instruments": "빅밴드 — 트럼펫, 트롬본, 알토 색소폰, 피아노, 업라이트 베이스, 스윙 드럼",
        "feel": "활기차고 클래식한, 빈티지, 댄스",
        "progressions": "I6 → vi7 → ii7 → V7, I → I7 → IV → #IVdim → I",
        "suno_style": "swing jazz, big band, trumpet, trombone, alto saxophone, piano, upright bass, swing drums, vintage, lively, dance",
        "vocal_style": "charismatic vocal, swing phrasing, rhythmic syncopation, crooner style",
        "reference": "Frank Sinatra, Ella Fitzgerald, Count Basie",
    },
    "neo soul jazz": {
        "bpm": "85-105",
        "key": "Ab Major / Eb minor",
        "instruments": "로즈 피아노, 일렉 베이스, 드럼 (하이햇 ghost), 신스 패드, 색소폰",
        "feel": "따뜻하고 그루비한, R&B 감성, 힙합 비트",
        "progressions": "IΔ9 → iv7 → bVII9 → IΔ9, ii9 → V13 → IΔ9",
        "suno_style": "neo soul jazz, Rhodes piano, electric bass, ghost note drums, synth pad, saxophone, warm groovy, R&B jazz, lo-fi",
        "vocal_style": "soulful warm vocal, R&B jazz phrasing, gentle runs, breathy intimate",
        "reference": "Robert Glasper, Erykah Badu, D'Angelo, Tom Misch",
    },
}

# ---------------------------------------------------------------------------
# Claude CLI 호출
# ---------------------------------------------------------------------------

def call_claude(prompt: str, system_prompt: str = "") -> str:
    """Claude CLI로 텍스트 생성."""
    cmd = [
        "npx", "@anthropic-ai/claude-code",
        "-p", prompt,
        "--tools", "",
        "--no-session-persistence",
    ]
    if system_prompt:
        cmd += ["--system-prompt", system_prompt]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=180,
            cwd=str(PROJECT_ROOT),
        )
    except subprocess.TimeoutExpired:
        print("  [오류] Claude 응답 시간 초과 (180초)")
        return ""

    if result.returncode != 0:
        print(f"  [오류] Claude 호출 실패: {result.stderr[:300]}")
        return ""
    return result.stdout.strip()


# ---------------------------------------------------------------------------
# 단계 1: 컨셉 생성
# ---------------------------------------------------------------------------

CONCEPT_SYSTEM = """\
너는 재즈 음악 프로듀서다. 곡 컨셉 문서를 만들어야 한다.
마크다운 형식으로 출력하되, 코드블록(```)이나 마크다운 코드블록으로 감싸지 마.
바로 마크다운 본문을 출력해."""

def generate_concept(preset: dict, theme: str, mood: str, song_dir: Path, dry_run: bool = False) -> str:
    """concept.md 생성."""
    print("\n[1/4] 컨셉 생성...")

    if dry_run:
        content = textwrap.dedent(f"""\
        # [곡 제목] — 곡 컨셉

        ## 기본 정보
        - **장르**: 재즈 ({mood})
        - **BPM**: {preset['bpm']}
        - **키**: {preset['key']}
        - **악기**: {preset['instruments']}
        - **참조**: {preset['reference']}
        - **테마**: {theme}

        ## 핵심 컨셉
        (Claude가 생성할 영역)

        ## 화자 캐릭터
        (Claude가 생성할 영역)

        ## 감정 곡선
        (Claude가 생성할 영역)

        ## 코드 진행
        {preset['progressions']}

        ## 악기 구성
        {preset['instruments']}
        """)
    else:
        prompt = textwrap.dedent(f"""\
        재즈 곡 컨셉 문서를 만들어줘.

        조건:
        - 서브장르: {mood} 느낌의 재즈
        - 테마/주제: {theme}
        - BPM: {preset['bpm']}
        - 키: {preset['key']}
        - 메인 악기: {preset['instruments']}
        - 코드 진행 참고: {preset['progressions']}
        - 레퍼런스 아티스트: {preset['reference']}
        - 느낌: {preset['feel']}

        다음 항목을 포함해:
        1. 곡 제목 (한국어, 재즈 감성)
        2. 기본 정보 (장르, BPM, 키, 악기)
        3. 핵심 컨셉 (2-3문단, 곡의 이야기)
        4. 화자 캐릭터 (나이, 상황, 감정 표현 방식)
        5. 감정 곡선 (Intro → Verse 1 → Chorus → Verse 2 → Solo → Chorus → Outro)
        6. 코드 진행 (섹션별 재즈 보이싱)
        7. 악기 구성 (섹션별 어떤 악기가 들어오고 빠지는지)
        8. 레퍼런스 곡 3개

        한국어로 작성. 마크다운 형식.""")

        content = call_claude(prompt, CONCEPT_SYSTEM)
        if not content:
            content = f"# 컨셉 생성 실패\n\n테마: {theme}\n서브장르: {mood}"

    path = song_dir / "concept.md"
    path.write_text(content, encoding="utf-8")
    print(f"  -> {path}")
    return content


# ---------------------------------------------------------------------------
# 단계 2: 가사 생성
# ---------------------------------------------------------------------------

LYRICS_SYSTEM = """\
너는 재즈 전문 작사가다. 김이나 작사법을 재즈에 적용한다.
규칙:
- 캐릭터 우선: 화자의 성격이 가사 전체를 관통
- 감각적 은유: 직접 감정 표현 대신 풍경/소리/냄새로
- 재즈 특유의 리듬감: 싱코페이션에 맞는 음절 배치
- 영어 훅 포함 (재즈 장르 특성)
- 섹션 구조: [Verse 1], [Chorus], [Verse 2], [Solo Break], [Bridge], [Chorus], [Outro]
- 마크다운 형식으로 출력하되 코드블록으로 감싸지 마."""

def generate_lyrics(concept: str, preset: dict, theme: str, song_dir: Path, dry_run: bool = False) -> str:
    """lyrics.md 생성."""
    print("\n[2/4] 가사 생성...")

    if dry_run:
        content = textwrap.dedent(f"""\
        # [곡 제목] — 가사

        [Verse 1]
        (Claude가 생성할 가사)

        [Pre-Chorus]
        (Claude가 생성할 가사)

        [Chorus]
        (Claude가 생성할 가사 + 영어 훅)

        [Verse 2]
        (Claude가 생성할 가사)

        [Solo Break]
        (악기 솔로 섹션)

        [Bridge]
        (Claude가 생성할 가사)

        [Chorus]
        (Claude가 생성할 가사)

        [Outro]
        (Claude가 생성할 가사)
        """)
    else:
        prompt = textwrap.dedent(f"""\
        다음 컨셉을 기반으로 재즈 곡 가사를 써줘.

        === 컨셉 ===
        {concept}
        === 끝 ===

        요구사항:
        - 재즈 리듬에 맞는 싱코페이션 음절 배치
        - 감각적 은유 중심 (날씨, 도시, 빛, 소리, 냄새)
        - 영어 훅 1-2줄 포함 (Chorus에서)
        - 직접적 감정 표현 최소화
        - 섹션: [Verse 1] → [Pre-Chorus] → [Chorus] → [Verse 2] → [Solo Break] → [Bridge] → [Final Chorus] → [Outro]
        - [Solo Break]은 (색소폰/피아노 솔로) 같이 악기만 표기
        - 총 길이: 3-4분 분량

        한국어 가사 + 영어 훅. 마크다운 형식.""")

        content = call_claude(prompt, LYRICS_SYSTEM)
        if not content:
            content = f"# 가사 생성 실패\n\n테마: {theme}"

    path = song_dir / "lyrics.md"
    path.write_text(content, encoding="utf-8")
    print(f"  -> {path}")
    return content


# ---------------------------------------------------------------------------
# 단계 3: Suno 프롬프트 생성
# ---------------------------------------------------------------------------

SUNO_SYSTEM = """\
너는 Suno AI 프롬프트 엔지니어다. 재즈 곡을 위한 최적화된 Suno 프롬프트를 만든다.
규칙:
- Style of Music: 200자 이내, 장르 → 보컬 → 악기 → 텍스처 → BPM 순서
- 가사에 섹션 마커와 무드 태그 삽입: [Verse 1], [Chorus], [Solo Break] 등
- [Soft, Intimate], [Build], [Saxophone Solo], [Piano Solo] 같은 무드 태그 활용
- Suno가 인식하는 태그만 사용
- 마크다운 형식으로 출력하되 코드블록으로 감싸지 마 (Style of Music 값만 코드블록 허용)."""

def generate_suno_prompt(concept: str, lyrics: str, preset: dict, song_dir: Path, dry_run: bool = False) -> str:
    """suno_prompt.md 생성."""
    print("\n[3/4] Suno 프롬프트 생성...")

    if dry_run:
        content = textwrap.dedent(f"""\
        # Suno 프롬프트

        ## Style of Music
        ```
        {preset['suno_style']}, {preset['vocal_style'].split(',')[0]}, (BPM)
        ```

        ## Lyrics
        (가사 + 섹션 마커 + 무드 태그)
        """)
    else:
        prompt = textwrap.dedent(f"""\
        다음 컨셉과 가사를 기반으로 Suno AI 프롬프트를 만들어줘.

        === 컨셉 ===
        {concept[:1500]}
        === 가사 ===
        {lyrics}
        === 끝 ===

        Suno 참고 정보:
        - 스타일 태그: {preset['suno_style']}
        - 보컬 태그: {preset['vocal_style']}

        출력 형식:
        1. Style of Music (200자 이내, 코드블록으로)
           - 순서: 장르 → 보컬 스타일 → 메인 악기 → 텍스처/무드 → BPM
        2. Lyrics (가사 전문 + 섹션 마커 + 무드 태그)
           - 각 섹션 앞에 [Verse 1], [Chorus] 등 마커
           - 무드 태그: [Soft, Intimate], [Build], [Saxophone Solo], [Piano Solo], [Scat] 등
           - [Solo Break]에는 [Instrumental] + 악기 표기
        3. 메타 프롬프트 설계 근거 테이블""")

        content = call_claude(prompt, SUNO_SYSTEM)
        if not content:
            content = textwrap.dedent(f"""\
            # Suno 프롬프트 생성 실패

            ## Style of Music
            ```
            {preset['suno_style']}
            ```
            """)

    path = song_dir / "suno_prompt.md"
    path.write_text(content, encoding="utf-8")
    print(f"  -> {path}")
    return content


# ---------------------------------------------------------------------------
# 단계 4: 재즈 전용 mix_stems.py 생성
# ---------------------------------------------------------------------------

_MIX_TEMPLATE = '''\
#!/usr/bin/env python3
"""
재즈 곡 — Stems 기반 믹싱 + 마스터링 ({{SUBGENRE}})

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
# 트랙별 처리 — 재즈 ({{SUBGENRE}}) 최적화
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

MIX_LEVELS = {{MIX_LEVELS}}


def mix_all(stems: dict[str, np.ndarray], sr: int) -> np.ndarray:
    """모든 트랙 믹싱."""
    print("\\n믹싱...")

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
    print("\\n마스터링...")

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
    print(f"\\n라우드니스 -> {target_lufs} LUFS")
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
    parser = argparse.ArgumentParser(description="재즈 곡 — Stems 믹싱 ({{SUBGENRE}})")
    parser.add_argument("--reference", "-r", help="레퍼런스 곡 WAV", default=None)
    args = parser.parse_args()

    ensure_dirs()
    reference = Path(args.reference).resolve() if args.reference else None

    print("=" * 60)
    print("재즈 곡 — Stems 믹싱 + 마스터링 ({{SUBGENRE}})")
    print("=" * 60)

    print("\\n스템 로드 + 처리...")
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

    print("\\n" + "=" * 60)
    print("완료!")
    print(f"  파일: {output}")
    print(f"  길이: {duration:.0f}초 ({duration/60:.1f}분)")
    print(f"  LUFS: {final_lufs:.1f}")
    print(f"  피크: {peak_db:.1f} dBFS")
    print(f"  포맷: WAV 16bit {sr}Hz")
    print("=" * 60)


if __name__ == "__main__":
    main()
'''

def generate_mix_script(preset: dict, subgenre: str, song_dir: Path) -> None:
    """재즈 장르에 맞는 mix_stems.py 생성."""
    print("\n[4/4] 재즈 믹싱 스크립트 생성...")

    scripts_dir = song_dir / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)

    mix_levels = _get_jazz_mix_levels(subgenre)

    # 믹스 레벨을 코드 형태로 직접 생성
    mix_lines = []
    for k, v in mix_levels.items():
        mix_lines.append(f'    "{k}": {v:>6.2f},')
    mix_block = "{\n" + "\n".join(mix_lines) + "\n}"

    content = _MIX_TEMPLATE.replace("{{SUBGENRE}}", subgenre).replace("{{MIX_LEVELS}}", mix_block)

    path = scripts_dir / "mix_stems.py"
    path.write_text(content, encoding="utf-8")
    print(f"  -> {path}")


def _get_jazz_mix_levels(subgenre: str) -> dict[str, float]:
    """서브장르별 믹스 레벨."""
    base = {
        "Lead Vocals":    1.0,
        "Backing Vocals": 0.30,
        "Drums":          0.50,
        "Bass":           0.55,
        "Guitar":         0.45,
        "Keyboard":       0.60,
        "Synth":          0.25,
        "Other":          0.40,   # 재즈: 관악기(색소폰/트럼펫) 가능성
    }

    # 서브장르별 미세 조정
    adjustments = {
        "smooth jazz": {"Keyboard": 0.65, "Other": 0.55, "Guitar": 0.40, "Drums": 0.45},
        "jazz ballad": {"Keyboard": 0.70, "Bass": 0.50, "Drums": 0.40, "Other": 0.45},
        "bossa nova": {"Guitar": 0.65, "Keyboard": 0.50, "Drums": 0.40, "Bass": 0.50},
        "cool jazz": {"Keyboard": 0.60, "Other": 0.55, "Drums": 0.50, "Bass": 0.55},
        "jazz fusion": {"Guitar": 0.60, "Bass": 0.60, "Drums": 0.60, "Keyboard": 0.55, "Synth": 0.35},
        "swing": {"Other": 0.60, "Drums": 0.55, "Bass": 0.55, "Keyboard": 0.55},
        "neo soul jazz": {"Keyboard": 0.65, "Bass": 0.60, "Drums": 0.55, "Other": 0.45, "Synth": 0.35},
    }

    if subgenre in adjustments:
        base.update(adjustments[subgenre])

    return base


# ---------------------------------------------------------------------------
# 메인 파이프라인
# ---------------------------------------------------------------------------

VALID_STEPS = {"concept", "lyrics", "suno", "mix"}


def interactive_select_subgenre() -> str:
    """대화형 서브장르 선택."""
    print("\n재즈 서브장르를 선택하세요:\n")
    names = list(JAZZ_PRESETS.keys())
    for i, name in enumerate(names, 1):
        preset = JAZZ_PRESETS[name]
        print(f"  {i}. {name:<15} — {preset['feel']}")
        print(f"     악기: {preset['instruments']}")
        print(f"     BPM: {preset['bpm']}, 키: {preset['key']}")
        print()

    while True:
        try:
            choice = input("번호 입력 (1-7): ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(names):
                selected = names[idx]
                print(f"\n  -> '{selected}' 선택됨\n")
                return selected
        except (ValueError, EOFError):
            pass
        print("  1-7 사이 숫자를 입력하세요.")


def main():
    parser = argparse.ArgumentParser(
        description="재즈 곡 자동 생성 파이프라인",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
        사용 예시:
          python3 scripts/jazz_pipeline.py --subgenre "smooth jazz" --theme "도시의 밤"
          python3 scripts/jazz_pipeline.py --subgenre "bossa nova" --mood "카페" --theme "오후의 커피"
          python3 scripts/jazz_pipeline.py --dry-run --theme "테스트"
          python3 scripts/jazz_pipeline.py --steps concept,lyrics --theme "비 오는 날"
        """),
    )
    parser.add_argument("--subgenre", "-s", help=f"재즈 서브장르: {', '.join(JAZZ_PRESETS.keys())}")
    parser.add_argument("--mood", "-m", help="분위기 키워드 (예: 밤거리, 비, 카페)", default="")
    parser.add_argument("--theme", "-t", help="곡 테마/주제 (예: 도시의 밤, 이별 후 재즈바)", default="")
    parser.add_argument("--dry-run", action="store_true", help="Claude 호출 없이 구조만 생성")
    parser.add_argument("--steps", help=f"실행할 단계 (쉼표 구분): {','.join(VALID_STEPS)}", default="concept,lyrics,suno,mix")
    parser.add_argument("--song-name", help="곡 디렉토리 이름 (미지정 시 자동 생성)")
    args = parser.parse_args()

    # 서브장르 선택
    subgenre = args.subgenre
    if not subgenre:
        subgenre = interactive_select_subgenre()

    subgenre = subgenre.lower().strip()
    if subgenre not in JAZZ_PRESETS:
        print(f"[오류] 지원하지 않는 서브장르: {subgenre}")
        print(f"  지원 목록: {', '.join(JAZZ_PRESETS.keys())}")
        sys.exit(1)

    preset = JAZZ_PRESETS[subgenre]

    # 테마
    theme = args.theme
    if not theme and not args.dry_run:
        theme = input("곡 테마/주제를 입력하세요: ").strip()
    if not theme:
        theme = f"{subgenre} 재즈"

    mood = args.mood or preset["feel"].split(",")[0].strip()

    # 실행 단계
    steps = set(args.steps.split(","))
    invalid = steps - VALID_STEPS
    if invalid:
        print(f"[오류] 잘못된 단계: {invalid}. 유효: {VALID_STEPS}")
        sys.exit(1)

    # 곡 디렉토리 생성
    if args.song_name:
        song_name = args.song_name
    else:
        # 기존 곡 번호 파악
        songs_dir = PROJECT_ROOT / "songs"
        songs_dir.mkdir(exist_ok=True)
        existing = sorted(songs_dir.iterdir()) if songs_dir.exists() else []
        nums = []
        for d in existing:
            if d.is_dir() and d.name[:2].isdigit():
                nums.append(int(d.name[:2]))
        next_num = max(nums, default=0) + 1

        # 테마에서 디렉토리명 생성
        safe_theme = re.sub(r"[^\w가-힣]", "_", theme).strip("_")[:20]
        song_name = f"{next_num:02d}_{safe_theme}_jazz"

    song_dir = PROJECT_ROOT / "songs" / song_name
    for sub in ["midi", "suno", "processed", "release", "scripts"]:
        (song_dir / sub).mkdir(parents=True, exist_ok=True)

    # 배너
    print("=" * 60)
    print(f"  재즈 곡 자동 생성 파이프라인")
    print(f"  서브장르: {subgenre}")
    print(f"  테마: {theme}")
    print(f"  분위기: {mood}")
    print(f"  BPM: {preset['bpm']}, 키: {preset['key']}")
    print(f"  디렉토리: {song_dir}")
    if args.dry_run:
        print(f"  [DRY RUN] Claude 호출 건너뜀")
    print("=" * 60)

    concept = ""
    lyrics = ""

    # 단계 실행
    if "concept" in steps:
        concept = generate_concept(preset, theme, mood, song_dir, args.dry_run)

    if "lyrics" in steps:
        if not concept and (song_dir / "concept.md").exists():
            concept = (song_dir / "concept.md").read_text(encoding="utf-8")
        lyrics = generate_lyrics(concept, preset, theme, song_dir, args.dry_run)

    if "suno" in steps:
        if not concept and (song_dir / "concept.md").exists():
            concept = (song_dir / "concept.md").read_text(encoding="utf-8")
        if not lyrics and (song_dir / "lyrics.md").exists():
            lyrics = (song_dir / "lyrics.md").read_text(encoding="utf-8")
        generate_suno_prompt(concept, lyrics, preset, song_dir, args.dry_run)

    if "mix" in steps:
        generate_mix_script(preset, subgenre, song_dir)

    # manifest.json 생성 — 곡 메타데이터 + 상태 추적
    manifest_path = song_dir / "manifest.json"
    manifest = {
        "title": theme,
        "subgenre": subgenre,
        "theme": theme,
        "status": "generated",
        "scheduled_date": None,
        "youtube_id": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  manifest.json 생성: {manifest_path}")

    # 완료 요약
    print("\n" + "=" * 60)
    print("  파이프라인 완료!")
    print(f"  곡 디렉토리: {song_dir}")
    print()
    print("  생성된 파일:")
    for f in sorted(song_dir.rglob("*")):
        if f.is_file():
            print(f"    {f.relative_to(song_dir)}")
    print()
    print("  다음 단계:")
    print("    1. concept.md, lyrics.md 검토 및 수정")
    print("    2. suno_prompt.md를 Suno AI에 입력")
    print("    3. Suno 생성 결과 스템을 suno/ 디렉토리에 저장")
    print("    4. python3 scripts/mix_stems.py 실행")
    print("=" * 60)


if __name__ == "__main__":
    main()
