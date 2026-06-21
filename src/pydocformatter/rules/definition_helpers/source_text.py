from __future__ import annotations

from collections.abc import Sequence

import libcst.metadata as cst_metadata


def source_lines(source: str) -> list[str]:
    """Split source into lines retaining only Python physical line endings."""
    lines: list[str] = []
    line_start = 0
    index = 0
    while index < len(source):
        if source[index] == "\r":
            index += 2 if index + 1 < len(source) and source[index + 1] == "\n" else 1
            lines.append(source[line_start:index])
            line_start = index
        elif source[index] == "\n":
            index += 1
            lines.append(source[line_start:index])
            line_start = index
        else:
            index += 1
    lines.append(source[line_start:])
    return lines


def source_for_range(code_range: cst_metadata.CodeRange, *, source_lines: Sequence[str]) -> str:
    """Return the exact source inside a LibCST code range."""
    first_index = code_range.start.line - 1
    last_index = code_range.end.line - 1
    if first_index == last_index:
        return source_lines[first_index][code_range.start.column : code_range.end.column]
    lines = [source_lines[first_index][code_range.start.column :]]
    lines.extend(source_lines[first_index + 1 : last_index])
    lines.append(source_lines[last_index][: code_range.end.column])
    return "".join(lines)
