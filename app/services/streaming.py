from __future__ import annotations

SENTENCE_ENDINGS = set("。！？!?；;\n")
CLAUSE_ENDINGS = set("，,：:")
SOFT_SPLITS = set("、 ")

MIN_SEGMENT_CHARS = 8
MAX_SEGMENT_CHARS = 28


def normalize_text(text: str) -> str:
    return " ".join((text or "").strip().split())


def trim_history(history: list[dict[str, str]], max_turns: int) -> list[dict[str, str]]:
    if max_turns <= 0:
        return history
    keep = max_turns * 2
    return history[-keep:]


def _find_boundary(buffer: str) -> int | None:
    if not buffer:
        return None

    for index, char in enumerate(buffer):
        if char in SENTENCE_ENDINGS and index + 1 >= 2:
            return index + 1

    if len(buffer) < MIN_SEGMENT_CHARS:
        return None

    for index, char in enumerate(buffer):
        if char in CLAUSE_ENDINGS and index + 1 >= MIN_SEGMENT_CHARS:
            return index + 1

    if len(buffer) < MAX_SEGMENT_CHARS:
        return None

    last_soft_split = None
    for index, char in enumerate(buffer[:MAX_SEGMENT_CHARS]):
        if char in SOFT_SPLITS:
            last_soft_split = index + 1

    return last_soft_split or MAX_SEGMENT_CHARS


def pull_speakable_segments(buffer: str, *, final: bool = False) -> tuple[list[str], str]:
    segments: list[str] = []
    remaining = buffer

    while True:
        boundary = _find_boundary(remaining)
        if boundary is None:
            break

        segment = remaining[:boundary].strip()
        remaining = remaining[boundary:].lstrip()
        if segment:
            segments.append(segment)

    if final and remaining.strip():
        segments.append(remaining.strip())
        remaining = ""

    return segments, remaining
