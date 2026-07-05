#!/usr/bin/env python3
"""Normalize repository Markdown pipe tables.

Attributes:
    ROOT (pathlib.Path): Repository root used for default Git-tracked file discovery and relative display paths.
    SEPARATOR_CELL_RE (re.Pattern[str]): Markdown separator cell pattern used to identify pipe table separator rows.
"""

from __future__ import annotations

import argparse
import dataclasses
import pathlib
import re
import subprocess
import sys
import typing

ROOT = pathlib.Path(__file__).resolve().parents[1]
SEPARATOR_CELL_RE = re.compile(r":?-{3,}:?")


@dataclasses.dataclass(frozen=True)
class _MarkdownLine:
    """One Markdown line split into content and original line ending."""

    text: str
    ending: str


@dataclasses.dataclass(frozen=True)
class _Fence:
    """Active fenced-code-block delimiter state."""

    marker: str
    width: int


@dataclasses.dataclass(frozen=True)
class _TableBlock:
    """Contiguous Markdown pipe-table lines and their source range."""

    start: int
    end: int
    lines: tuple[str, ...]


@dataclasses.dataclass(frozen=True)
class _TableRow:
    """Parsed Markdown table row indentation and cell text."""

    indent: str
    cells: tuple[str, ...]


@dataclasses.dataclass(frozen=True)
class _FileTableStatus:
    """Markdown table normalization result for one file."""

    normalized_text: str
    changed: bool
    remaining_failures: tuple[str, ...]


def main(argv: list[str] | None = None) -> int:
    """Normalize Markdown pipe tables in selected files.

    Args:
        argv: Command-line arguments, excluding the executable name.

    Returns:
        Zero when all selected files are already normalized or were fixed, otherwise one in check mode when any selected file would change.
    """
    parser = argparse.ArgumentParser(description="Normalize Markdown pipe tables to the minimal PyCharm-style alignment enforced by pytest.")
    parser.add_argument("paths", nargs="*", type=pathlib.Path, help="Markdown files to normalize. Defaults to all Git-tracked Markdown files.")
    parser.add_argument("--check", action="store_true", help="Report files that would change without writing them.")
    args = parser.parse_args(argv)

    paths = tuple(args.paths) if args.paths else tracked_markdown_paths()
    changed_paths: list[pathlib.Path] = []
    remaining_failures: list[str] = []
    for path in paths:
        status = _inspect_markdown_tables_file(path)
        if status.changed:
            changed_paths.append(path)
            if not args.check:
                _write_text(path, status.normalized_text)
        remaining_failures.extend(status.remaining_failures)

    if not changed_paths and not remaining_failures:
        return 0

    if args.check:
        _print_check_failures(changed_paths, remaining_failures)
        return 1

    if changed_paths:
        print("Fixed Markdown table style in:")
        for path in changed_paths:
            print(f"- {_display_path(path)}")

    if remaining_failures:
        _print_validation_failures(remaining_failures)
        return 1

    return 0


def tracked_markdown_paths() -> tuple[pathlib.Path, ...]:
    """Return present Git-tracked Markdown paths.

    Returns:
        Absolute paths for existing Git-tracked Markdown files below the repository root.
    """
    output = subprocess.check_output(("git", "ls-files", "*.md"), cwd=ROOT, text=True)
    return tuple(path for line in output.splitlines() if (path := ROOT / line).exists())


def normalize_markdown_tables_file(path: pathlib.Path, *, check: bool = False) -> bool:
    """Normalize Markdown pipe tables in one file.

    Args:
        path: Markdown file to inspect.
        check: Whether to skip writing normalized content.

    Returns:
        Whether the file content changed or would change.
    """
    status = _inspect_markdown_tables_file(path)
    if status.changed and not check:
        _write_text(path, status.normalized_text)
    return status.changed


def normalize_markdown_tables_text(text: str) -> str:
    """Return text with Markdown pipe tables normalized.

    Args:
        text: Markdown text whose pipe tables should be normalized.

    Returns:
        Markdown text with pipe tables normalized outside fenced code blocks.
    """
    lines = _split_markdown_lines(text)
    normalized_line_texts = _normalize_markdown_line_texts(tuple(line.text for line in lines))
    return "".join(line_text + line.ending for line_text, line in zip(normalized_line_texts, lines, strict=True))


def markdown_table_failures(path: pathlib.Path) -> list[str]:
    """Return table alignment failures for one Markdown file.

    Args:
        path: Markdown file to inspect.

    Returns:
        Human-readable table alignment failures with repository-relative paths when possible.
    """
    return _markdown_table_failures_for_text(path, _read_text(path))


def _markdown_table_failures_for_text(path: pathlib.Path, text: str) -> list[str]:
    """Return table alignment failures for Markdown text."""
    lines = tuple(line.text for line in _split_markdown_lines(text))
    failures: list[str] = []
    for table_block in _iter_table_blocks(lines):
        failures.extend(table_failures(path, table_block.start, list(table_block.lines)))
    return failures


def table_failures(path: pathlib.Path, table_start: int, table_lines: list[str]) -> list[str]:
    """Return alignment failures for one Markdown pipe table.

    Args:
        path: Markdown file containing the table.
        table_start: Zero-based line index of the first table row.
        table_lines: Physical lines belonging to the table.

    Returns:
        Human-readable alignment failures for the table.
    """
    failures: list[str] = []
    rows = _parsed_table_rows(table_lines)
    header_cells = rows[0].cells
    separator_cells = rows[1].cells

    if len(separator_cells) != len(header_cells):
        return [f"{_display_path(path)}:{table_start + 2}: expected {len(header_cells)} cells, found {len(separator_cells)}"]

    for row_offset, row in enumerate(rows):
        line_number = table_start + row_offset + 1
        if len(row.cells) != len(header_cells):
            failures.append(f"{_display_path(path)}:{line_number}: expected {len(header_cells)} cells, found {len(row.cells)}")

    if failures:
        return failures

    expected_lines = _normalized_table_lines(table_lines)
    for row_offset, (line, expected_line) in enumerate(zip(table_lines, expected_lines, strict=True)):
        line_number = table_start + row_offset + 1
        if line != expected_line:
            failures.append(f"{_display_path(path)}:{line_number}: expected {expected_line!r}, found {line!r}")
            continue

    return failures


def _normalized_table_lines(table_lines: list[str]) -> tuple[str, ...]:
    """Return normalized Markdown pipe table lines."""
    rows = _parsed_table_rows(table_lines)
    if any(len(row.cells) != len(rows[0].cells) for row in rows):
        return tuple(table_lines)
    alignments = tuple(_alignment_for_separator_cell(cell) for cell in rows[1].cells)
    column_widths = tuple(max(len(row.cells[column]) for row in rows[:1] + rows[2:]) for column in range(len(rows[0].cells)))
    return _render_table(rows, alignments=alignments, column_widths=column_widths)


def _render_table(rows: tuple[_TableRow, ...], *, alignments: tuple[str, ...], column_widths: tuple[int, ...]) -> tuple[str, ...]:
    """Return Markdown table lines in PyCharm's pipe-table style."""
    indent = rows[0].indent
    rendered = [indent + "|" + "|".join(_render_data_cell(cell, width=column_widths[column], alignment=alignments[column]) for column, cell in enumerate(rows[0].cells)) + "|"]
    rendered.append(indent + "|" + "|".join(_render_separator_cell(width=width, alignment=alignment) for width, alignment in zip(column_widths, alignments, strict=True)) + "|")
    rendered.extend(indent + "|" + "|".join(_render_data_cell(cell, width=column_widths[column], alignment=alignments[column]) for column, cell in enumerate(row.cells)) + "|" for row in rows[2:])
    return tuple(rendered)


def _render_data_cell(cell: str, *, width: int, alignment: str) -> str:
    """Return one padded Markdown table data cell."""
    if alignment in {"default", "left"}:
        return f" {cell.ljust(width)} "
    if alignment == "right":
        return f" {cell.rjust(width)} "
    left_padding = (width - len(cell)) // 2
    right_padding = width - len(cell) - left_padding
    return f"{' ' * (left_padding + 1)}{cell}{' ' * (right_padding + 1)}"


def _render_separator_cell(*, width: int, alignment: str) -> str:
    """Return one unpadded Markdown table separator cell."""
    cell_width = max(width + 2, 3)
    if alignment == "left":
        return ":" + "-" * (cell_width - 1)
    if alignment == "right":
        return "-" * (cell_width - 1) + ":"
    if alignment == "center":
        return ":" + "-" * (cell_width - 2) + ":"
    return "-" * cell_width


def _alignment_for_separator_cell(cell: str) -> str:
    """Return the Markdown alignment indicated by one separator cell."""
    stripped = cell.strip()
    if stripped.startswith(":") and stripped.endswith(":"):
        return "center"
    if stripped.startswith(":"):
        return "left"
    if stripped.endswith(":"):
        return "right"
    return "default"


def _normalize_markdown_line_texts(lines: tuple[str, ...]) -> tuple[str, ...]:
    """Return normalized Markdown line text without changing line endings."""
    normalized_lines = list(lines)
    for table_block in _iter_table_blocks(lines):
        normalized_lines[table_block.start : table_block.end] = _normalized_table_lines(list(table_block.lines))
    return tuple(normalized_lines)


def _iter_table_blocks(lines: typing.Sequence[str]) -> typing.Iterator[_TableBlock]:
    """Yield Markdown pipe table blocks outside fenced code blocks."""
    fence: _Fence | None = None
    line_index = 0

    while line_index < len(lines):
        if fence is not None:
            if _is_closing_fence(lines[line_index], fence):
                fence = None
            line_index += 1
            continue

        fence = _opening_fence_for_line(lines[line_index])
        if fence is not None:
            line_index += 1
            continue

        if line_index + 1 < len(lines) and not _is_indented_code_line(lines[line_index]) and _is_table_row(lines[line_index]) and _is_separator_row(lines[line_index + 1]):
            table_start = line_index
            line_index += 2
            while line_index < len(lines) and _is_table_row(lines[line_index]):
                line_index += 1
            yield _TableBlock(start=table_start, end=line_index, lines=tuple(lines[table_start:line_index]))
            continue

        line_index += 1


def _opening_fence_for_line(line: str) -> _Fence | None:
    """Return the fenced-code opener for a Markdown line when present."""
    match = re.match(r" {0,3}([`~])\1{2,}", line)
    if match is None:
        return None
    marker = match.group(0)
    stripped_marker = marker.lstrip(" ")
    if stripped_marker[0] == "`" and "`" in line[match.end() :]:
        return None
    return _Fence(marker=stripped_marker[0], width=len(stripped_marker))


def _is_closing_fence(line: str, fence: _Fence) -> bool:
    """Return whether a Markdown line closes the current fenced code block."""
    indent_width = len(line) - len(line.lstrip(" "))
    if indent_width > 3:
        return False

    stripped = line[indent_width:]
    marker_width = 0
    while marker_width < len(stripped) and stripped[marker_width] == fence.marker:
        marker_width += 1

    if marker_width < fence.width:
        return False

    return stripped[marker_width:].strip(" \t") == ""


def _is_table_row(line: str) -> bool:
    """Return whether a line is a pipe table row."""
    stripped = line.strip(" \t")
    return len(stripped) >= 2 and stripped.startswith("|") and stripped.endswith("|") and not _is_escaped_pipe(stripped, len(stripped) - 1)


def _is_indented_code_line(line: str) -> bool:
    """Return whether a line starts as Markdown indented code."""
    return line.startswith("    ") or line.startswith("\t")


def _is_separator_row(line: str) -> bool:
    """Return whether a line is a Markdown table separator row."""
    return _is_table_row(line) and all(SEPARATOR_CELL_RE.fullmatch(cell.strip()) is not None for cell in _split_table_row(line))


def _split_table_row(line: str) -> list[str]:
    """Split a pipe table row into raw cell strings."""
    stripped = line.strip(" \t")
    return _split_unescaped_pipes(stripped[1:-1])


def _parsed_table_rows(table_lines: typing.Sequence[str]) -> tuple[_TableRow, ...]:
    """Return parsed Markdown table rows with indentation preserved."""
    return tuple(_TableRow(indent=_table_indent(line), cells=tuple(cell.strip() for cell in _split_table_row(line))) for line in table_lines)


def _table_indent(line: str) -> str:
    """Return leading whitespace before a table row's opening pipe."""
    match = re.match(r"[ \t]*", line)
    if match is None:
        return ""
    return match.group(0)


def _split_unescaped_pipes(text: str) -> list[str]:
    """Split Markdown table row content on unescaped pipe characters."""
    cells: list[str] = []
    current_cell: list[str] = []
    code_span_width: int | None = None
    index = 0
    while index < len(text):
        character = text[index]
        if character == "`":
            backtick_width = _backtick_run_width(text, index)
            if code_span_width == backtick_width:
                code_span_width = None
            elif code_span_width is None and not _is_escaped_character(text, index) and _has_matching_code_span_close(text, index + backtick_width, backtick_width):
                code_span_width = backtick_width
            current_cell.append(text[index : index + backtick_width])
            index += backtick_width
            continue

        if character == "|" and code_span_width is None and not _is_escaped_pipe(text, index):
            cells.append("".join(current_cell))
            current_cell = []
            index += 1
            continue
        current_cell.append(character)
        index += 1
    cells.append("".join(current_cell))
    return cells


def _is_escaped_pipe(text: str, pipe_index: int) -> bool:
    """Return whether a pipe character is escaped by an odd number of backslashes."""
    return _is_escaped_character(text, pipe_index)


def _is_escaped_character(text: str, character_index: int) -> bool:
    """Return whether a character is escaped by an odd number of backslashes."""
    backslash_count = 0
    backslash_index = character_index - 1
    while backslash_index >= 0 and text[backslash_index] == "\\":
        backslash_count += 1
        backslash_index -= 1
    return backslash_count % 2 == 1


def _backtick_run_width(text: str, start: int) -> int:
    """Return the width of the backtick run starting at an index."""
    end = start
    while end < len(text) and text[end] == "`":
        end += 1
    return end - start


def _has_matching_code_span_close(text: str, start: int, width: int) -> bool:
    """Return whether a matching code-span close appears later in the row."""
    index = start
    while index < len(text):
        if text[index] != "`":
            index += 1
            continue
        backtick_width = _backtick_run_width(text, index)
        if backtick_width == width:
            return True
        index += backtick_width
    return False


def _inspect_markdown_tables_file(path: pathlib.Path) -> _FileTableStatus:
    """Return normalization status and remaining validation failures for one file."""
    original = _read_text(path)
    normalized = normalize_markdown_tables_text(original)
    return _FileTableStatus(normalized_text=normalized, changed=normalized != original, remaining_failures=tuple(_markdown_table_failures_for_text(path, normalized)))


def _read_text(path: pathlib.Path) -> str:
    """Read text while preserving newline spellings."""
    with path.open("r", encoding="utf-8", newline="") as handle:
        return handle.read()


def _write_text(path: pathlib.Path, text: str) -> None:
    """Write text while preserving supplied newline spellings."""
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(text)


def _split_markdown_lines(text: str) -> tuple[_MarkdownLine, ...]:
    """Split Markdown text into physical lines with newline spellings."""
    lines: list[_MarkdownLine] = []
    for line in text.splitlines(keepends=True):
        if line.endswith("\r\n"):
            lines.append(_MarkdownLine(text=line[:-2], ending="\r\n"))
            continue
        if line.endswith("\n"):
            lines.append(_MarkdownLine(text=line[:-1], ending="\n"))
            continue
        if line.endswith("\r"):
            lines.append(_MarkdownLine(text=line[:-1], ending="\r"))
            continue
        lines.append(_MarkdownLine(text=line, ending=""))
    return tuple(lines)


def _print_check_failures(changed_paths: list[pathlib.Path], remaining_failures: list[str]) -> None:
    """Print check-mode Markdown table failures."""
    if changed_paths:
        print("Markdown table style fixes needed:", file=sys.stderr)
        for path in changed_paths:
            print(f"- {_display_path(path)}", file=sys.stderr)
    if remaining_failures:
        _print_validation_failures(remaining_failures)


def _print_validation_failures(failures: list[str]) -> None:
    """Print non-fixable Markdown table validation failures."""
    print("Markdown table validation failures:", file=sys.stderr)
    for failure in failures:
        print(f"- {failure}", file=sys.stderr)


def _display_path(path: pathlib.Path) -> str:
    """Return a stable repository-relative display path."""
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
