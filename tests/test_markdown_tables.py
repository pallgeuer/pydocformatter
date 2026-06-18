import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
SEPARATOR_CELL_RE = re.compile(r":?-{3,}:?")


def test_markdown_tables_are_pycharm_style_aligned_and_minimal() -> None:
    """Check that repository Markdown pipe tables use minimal PyCharm-style alignment."""
    failures: list[str] = []
    for path in _tracked_markdown_paths():
        failures.extend(_markdown_table_failures(path))

    assert not failures, "Markdown table style failures:\n" + "\n".join(failures)


def test_table_failures_rejects_oversized_columns() -> None:
    """Check that table columns cannot be wider than their stripped content requires."""
    table_lines = [
        "| Name  | Value |",
        "|-------|-------|",
        "| one   | two   |",
    ]

    failures = _table_failures(ROOT / "example.md", 0, table_lines)

    assert failures == [
        "example.md:1: expected '| Name | Value |', found '| Name  | Value |'",
        "example.md:2: expected '|------|-------|', found '|-------|-------|'",
        "example.md:3: expected '| one  | two   |', found '| one   | two   |'",
    ]


def test_table_failures_accepts_minimal_pycharm_style_table() -> None:
    """Check that minimally sized PyCharm-style tables are accepted."""
    table_lines = [
        "| Name | Value |",
        "|------|-------|",
        "| one  | two   |",
    ]

    assert _table_failures(ROOT / "example.md", 0, table_lines) == []


def test_table_failures_preserves_separator_alignment_markers() -> None:
    """Check that separator rows stay unpadded and keep their alignment style."""
    table_lines = [
        "| Default | Left | Center | Right |",
        "|---------|:-----|:------:|------:|",
        "| a       | b    |   c    |     d |",
    ]

    assert _table_failures(ROOT / "example.md", 0, table_lines) == []


def _tracked_markdown_paths() -> tuple[pathlib.Path, ...]:
    """Return Git-tracked Markdown paths."""
    output = subprocess.check_output(("git", "ls-files", "*.md"), cwd=ROOT, text=True)
    return tuple(ROOT / line for line in output.splitlines())


def _markdown_table_failures(path: pathlib.Path) -> list[str]:
    """Return table alignment failures for one Markdown file."""
    lines = path.read_text(encoding="utf-8").splitlines()
    failures: list[str] = []
    fence: tuple[str, int] | None = None
    line_index = 0

    while line_index < len(lines):
        fence_marker = _fence_marker(lines[line_index])
        if fence_marker is not None:
            if fence is None:
                fence = fence_marker
            elif fence_marker[0] == fence[0] and fence_marker[1] >= fence[1]:
                fence = None
            line_index += 1
            continue

        if fence is None and line_index + 1 < len(lines) and _is_table_row(lines[line_index]) and _is_separator_row(lines[line_index + 1]):
            table_start = line_index
            table_lines = [lines[line_index], lines[line_index + 1]]
            line_index += 2
            while line_index < len(lines) and _is_table_row(lines[line_index]):
                table_lines.append(lines[line_index])
                line_index += 1
            failures.extend(_table_failures(path, table_start, table_lines))
            continue

        line_index += 1

    return failures


def _table_failures(path: pathlib.Path, table_start: int, table_lines: list[str]) -> list[str]:
    """Return alignment failures for one Markdown pipe table."""
    failures: list[str] = []
    rows = tuple(tuple(cell.strip() for cell in _split_table_row(line)) for line in table_lines)
    header_cells = rows[0]
    separator_cells = _split_table_row(table_lines[1])

    if len(separator_cells) != len(header_cells):
        return [f"{_display_path(path)}:{table_start + 2}: expected {len(header_cells)} cells, found {len(separator_cells)}"]

    alignments = tuple(_alignment_for_separator_cell(cell) for cell in separator_cells)
    for row_offset, cells in enumerate(rows):
        line_number = table_start + row_offset + 1
        if len(cells) != len(header_cells):
            failures.append(f"{_display_path(path)}:{line_number}: expected {len(header_cells)} cells, found {len(cells)}")

    if failures:
        return failures

    column_widths = tuple(max(len(row[column]) for row in rows[:1] + rows[2:]) for column in range(len(header_cells)))
    expected_lines = _render_table(rows, alignments=alignments, column_widths=column_widths)

    for row_offset, (line, expected_line) in enumerate(zip(table_lines, expected_lines, strict=True)):
        line_number = table_start + row_offset + 1
        if line != expected_line:
            failures.append(f"{_display_path(path)}:{line_number}: expected {expected_line!r}, found {line!r}")
            continue

    return failures


def _render_table(rows: tuple[tuple[str, ...], ...], *, alignments: tuple[str, ...], column_widths: tuple[int, ...]) -> tuple[str, ...]:
    """Return Markdown table lines in PyCharm's pipe-table style."""
    rendered = ["|" + "|".join(_render_data_cell(cell, width=column_widths[column], alignment=alignments[column]) for column, cell in enumerate(rows[0])) + "|"]
    rendered.append("|" + "|".join(_render_separator_cell(width=width, alignment=alignment) for width, alignment in zip(column_widths, alignments, strict=True)) + "|")
    rendered.extend("|" + "|".join(_render_data_cell(cell, width=column_widths[column], alignment=alignments[column]) for column, cell in enumerate(row)) + "|" for row in rows[2:])
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


def _fence_marker(line: str) -> tuple[str, int] | None:
    """Return a Markdown fence marker character and width if the line opens or closes a fence."""
    stripped = line.lstrip()
    match = re.match(r"([`~])\1{2,}", stripped)
    if match is None:
        return None
    marker = match.group(0)
    return marker[0], len(marker)


def _is_table_row(line: str) -> bool:
    """Return whether a line is a pipe table row."""
    stripped = line.rstrip().lstrip()
    return stripped.startswith("|") and stripped.endswith("|")


def _is_separator_row(line: str) -> bool:
    """Return whether a line is a Markdown table separator row."""
    return _is_table_row(line) and all(SEPARATOR_CELL_RE.fullmatch(cell.strip()) is not None for cell in _split_table_row(line))


def _split_table_row(line: str) -> list[str]:
    """Split a pipe table row into raw cell strings."""
    return line.rstrip().lstrip()[1:-1].split("|")


def _display_path(path: pathlib.Path) -> str:
    """Return a stable repository-relative display path."""
    return path.relative_to(ROOT).as_posix()
