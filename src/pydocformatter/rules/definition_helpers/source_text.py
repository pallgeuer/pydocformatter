"""Source text range and line-bound helpers."""

from __future__ import annotations

from collections.abc import Sequence

import libcst.metadata as cst_metadata

LineBounds = tuple[tuple[int, int], ...]


def source_lines(source: str) -> list[str]:
    """Split source into lines retaining only Python physical line endings."""
    if not source:
        return [""]

    lines: list[str] = []
    pending = ""
    for split_line in source.splitlines(keepends=True):
        pending += split_line
        if split_line.endswith(("\r", "\n")):
            lines.append(pending)
            pending = ""
    if pending or source.endswith(("\r", "\n")):
        lines.append(pending)
    return lines


def line_bounds_from_lines(source_lines: Sequence[str]) -> LineBounds:
    """Return source offsets bounding each line without its line ending."""
    bounds: list[tuple[int, int]] = []
    line_start = 0
    for line in source_lines:
        line_ending_length = _python_line_ending_length(line)
        line_end = line_start + len(line) - line_ending_length
        bounds.append((line_start, line_end))
        line_start += len(line)
    return tuple(bounds)


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


def _python_line_ending_length(line: str) -> int:
    """Return the length of a trailing Python physical line ending."""
    if line.endswith("\r\n"):
        return 2
    if line.endswith(("\r", "\n")):
        return 1
    return 0
