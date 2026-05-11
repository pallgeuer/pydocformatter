import os

from pydocformatter.config import LineEnding


def resolve_line_ending(source: str, *, line_ending: LineEnding) -> str:
    """Return the concrete line ending to use for rewritten source."""
    if line_ending == "lf":
        return "\n"
    if line_ending == "cr-lf":
        return "\r\n"
    if line_ending == "native":
        return os.linesep
    return detect_line_ending(source)


def detect_line_ending(source: str) -> str:
    """Return the first line ending in source, defaulting to LF when absent."""
    for index, char in enumerate(source):
        if char == "\n":
            return "\n"
        if char == "\r":
            next_index = index + 1
            if next_index < len(source) and source[next_index] == "\n":
                return "\r\n"
            return "\r"
    return "\n"


def normalize_line_endings(text: str, *, line_ending: str) -> str:
    """Convert every line ending in text to line_ending."""
    return text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", line_ending)
