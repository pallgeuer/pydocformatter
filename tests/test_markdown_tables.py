import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
SEPARATOR_CELL_RE = re.compile(r":?-{3,}:?")


def test_markdown_tables_are_padded_and_aligned() -> None:
    """Check that repository Markdown pipe tables have stable visual alignment."""
    failures: list[str] = []
    for path in _tracked_markdown_paths():
        failures.extend(_markdown_table_failures(path))

    assert not failures, "Markdown table alignment failures:\n" + "\n".join(failures)


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
    header_cells = _split_table_row(table_lines[0])
    separator_cells = _split_table_row(table_lines[1])
    expected_widths = tuple(len(cell) for cell in header_cells)

    if len(separator_cells) != len(header_cells):
        return [f"{_display_path(path)}:{table_start + 2}: expected {len(header_cells)} cells, found {len(separator_cells)}"]

    alignments = tuple(_alignment_for_separator_cell(cell) for cell in separator_cells)
    for row_offset, line in enumerate(table_lines):
        cells = _split_table_row(line)
        line_number = table_start + row_offset + 1
        if len(cells) != len(expected_widths):
            failures.append(f"{_display_path(path)}:{line_number}: expected {len(expected_widths)} cells, found {len(cells)}")
            continue

        widths = tuple(len(cell) for cell in cells)
        if widths != expected_widths:
            failures.append(f"{_display_path(path)}:{line_number}: expected cell widths {expected_widths}, found {widths}")
            continue

        if row_offset == 1:
            continue
        for column_number, (cell, alignment) in enumerate(zip(cells, alignments, strict=True), start=1):
            if not cell.strip():
                continue
            if not _cell_respects_alignment(cell, alignment):
                failures.append(f"{_display_path(path)}:{line_number}: column {column_number} should be {alignment}-aligned, found {cell!r}")

    return failures


def _cell_respects_alignment(cell: str, alignment: str) -> bool:
    """Return whether a padded cell respects its Markdown separator alignment."""
    left_padding = len(cell) - len(cell.lstrip(" "))
    right_padding = len(cell) - len(cell.rstrip(" "))
    if alignment == "left":
        return left_padding == 1 and right_padding >= 1
    if alignment == "right":
        return left_padding >= 1 and right_padding == 1
    return left_padding >= 1 and right_padding >= 1 and abs(left_padding - right_padding) <= 1


def _alignment_for_separator_cell(cell: str) -> str:
    """Return the Markdown alignment indicated by one separator cell."""
    stripped = cell.strip()
    if stripped.startswith(":") and stripped.endswith(":"):
        return "center"
    if stripped.endswith(":"):
        return "right"
    return "left"


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
