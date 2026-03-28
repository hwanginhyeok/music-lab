"""
MIDI 유틸리티 모듈 — 피아노 롤 시각화 등 MIDI 관련 헬퍼 함수 모음.

bot.py의 parse_midi_json이 반환하는 dict 형식을 입력으로 받는다.
외부 패키지 의존성 없음.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# 노트 이름 매핑 (MIDI 노트 번호 → 음이름)
# ---------------------------------------------------------------------------
_NOTE_NAMES: list[str] = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# 피아노 롤에서 사용할 블록 문자
_BLOCK: str = "\u2588"  # █

# 피아노 롤 최대 너비 (비트 단위)
_MAX_DISPLAY_BEATS: int = 16

# 한 비트당 표시할 문자 수 (기본)
_COLS_PER_BEAT: int = 2


def _pitch_to_name(pitch: int) -> str:
    """MIDI 노트 번호를 음이름+옥타브 문자열로 변환. 예: 60 → 'C4'"""
    octave = (pitch // 12) - 1
    note = _NOTE_NAMES[pitch % 12]
    return f"{note}{octave}"


def _name_display_width(name: str) -> int:
    """음이름 문자열의 표시 폭 반환. 패딩 정렬에 사용."""
    return len(name)


def render_piano_roll(midi_data: dict) -> str:
    """
    MIDI JSON 데이터를 텍스트 기반 피아노 롤로 시각화.

    모든 트랙의 노트를 합쳐서 하나의 피아노 롤로 그린다.
    Y축: 음이름 (높은 음이 위), X축: 시간 (비트).
    노트가 존재하는 피치만 표시 (빈 옥타브 생략).

    Args:
        midi_data: parse_midi_json이 반환하는 dict.
                   {"tracks": [{"notes": [{"pitch", "start", "duration", ...}]}]}

    Returns:
        텔레그램 모노스페이스용 코드 블록(``` 감싸기)으로 포맷된 문자열.
    """
    # 모든 트랙에서 노트 수집
    all_notes: list[dict] = []
    for track in midi_data.get("tracks", []):
        all_notes.extend(track.get("notes", []))

    if not all_notes:
        return "```\n(노트 없음)\n```"

    # 전체 시간 범위 계산
    max_end: float = max(n["start"] + n["duration"] for n in all_notes)
    min_start: float = min(n["start"] for n in all_notes)

    # 사용된 피치 수집
    used_pitches: set[int] = {n["pitch"] for n in all_notes}
    # 높은 음부터 낮은 음 순으로 정렬
    sorted_pitches: list[int] = sorted(used_pitches, reverse=True)

    if not sorted_pitches:
        return "```\n(노트 없음)\n```"

    # 스케일 계산: 전체 길이가 _MAX_DISPLAY_BEATS 이내면 1:1, 아니면 축소
    total_beats: float = max_end - min_start
    if total_beats <= 0:
        total_beats = 1.0

    if total_beats <= _MAX_DISPLAY_BEATS:
        # 축소 불필요 — 비트당 _COLS_PER_BEAT 칸
        scale: float = _COLS_PER_BEAT
    else:
        # 전체를 _MAX_DISPLAY_BEATS * _COLS_PER_BEAT 칸에 맞춤
        scale = (_MAX_DISPLAY_BEATS * _COLS_PER_BEAT) / total_beats

    total_cols: int = int(total_beats * scale) + 1

    # 음이름 레이블 최대 폭 계산 (정렬용)
    pitch_names: dict[int, str] = {p: _pitch_to_name(p) for p in sorted_pitches}
    label_width: int = max(len(name) for name in pitch_names.values())

    # 피치별 타임라인 배열 생성
    grid: dict[int, list[str]] = {p: [" "] * total_cols for p in sorted_pitches}

    # 노트를 그리드에 배치
    for note in all_notes:
        pitch: int = note["pitch"]
        if pitch not in grid:
            continue
        start_col: int = int((note["start"] - min_start) * scale)
        end_col: int = int((note["start"] + note["duration"] - min_start) * scale)
        # 최소 1칸 표시
        if end_col <= start_col:
            end_col = start_col + 1
        for col in range(start_col, min(end_col, total_cols)):
            grid[pitch][col] = _BLOCK

    # 텍스트 조립
    lines: list[str] = []
    for pitch in sorted_pitches:
        label: str = pitch_names[pitch].ljust(label_width)
        row: str = "".join(grid[pitch]).rstrip()
        lines.append(f"{label}  {row}")

    # 후행 공백이 있는 빈 줄 정리
    piano_roll: str = "\n".join(lines)
    return f"```\n{piano_roll}\n```"


def format_chord_progression(text: str) -> str:
    """
    코드 진행 텍스트 포맷터 (현재는 패스스루).

    코드 진행 시각화는 Claude 시스템 프롬프트가 직접 처리하므로
    이 함수는 입력을 그대로 반환한다. 향후 확장을 위한 플레이스홀더.

    Args:
        text: 코드 진행이 포함된 텍스트.

    Returns:
        입력 텍스트 그대로.
    """
    return text
