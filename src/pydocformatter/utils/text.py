"""Physical source text splitting."""

# Future imports
from __future__ import annotations


def split_physical_lines(source: str, *, keepends: bool = False) -> list[str]:
    """Split source at CR, LF, and CRLF physical line endings.

    Args:
        source (str): Source text to split.
        keepends (bool): Whether returned lines retain their physical line endings.

    Returns:
        list[str]: Physical source lines without a synthetic trailing empty line.
    """
    lines: list[str] = []
    line_start = 0
    index = 0
    while index < len(source):
        character = source[index]
        if character not in "\r\n":
            index += 1
            continue
        ending_start = index
        index += 1
        if character == "\r" and index < len(source) and source[index] == "\n":
            index += 1
        lines.append(source[line_start:index] if keepends else source[line_start:ending_start])
        line_start = index
    if line_start < len(source):
        lines.append(source[line_start:])
    return lines
