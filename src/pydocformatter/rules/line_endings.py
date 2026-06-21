from __future__ import annotations

import os

from pydocformatter.cli.settings_check import LineEnding


def resolve_line_ending(source: str, *, line_ending: LineEnding) -> str:
    """Return the concrete line ending to use for rewritten source.

    Args:
        source (str): Source text used when auto-detecting line endings.
        line_ending (LineEnding): Configured line ending mode.

    Returns:
        str: Concrete line ending string.

    Raises:
        ValueError: If `line_ending` is not a known `LineEnding` member.
    """
    if line_ending == LineEnding.AUTO:
        return detect_line_ending(source)
    elif line_ending == LineEnding.LF:
        return "\n"
    elif line_ending == LineEnding.CR_LF:
        return "\r\n"
    elif line_ending == LineEnding.NATIVE:
        return os.linesep
    else:
        raise ValueError(f"Unexpected line ending specification: {line_ending}")


def detect_line_ending(source: str) -> str:
    """Return the first line ending in source, defaulting to LF when absent.

    Args:
        source (str): Source text to inspect.

    Returns:
        str: First detected line ending, or LF when the source contains no line endings.
    """
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
    """Convert every line ending in text to line_ending.

    Args:
        text (str): Text whose line endings should be normalized.
        line_ending (str): Replacement line ending.

    Returns:
        str: Text with all CRLF, CR, and LF endings converted to `line_ending`.
    """
    return text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", line_ending)
