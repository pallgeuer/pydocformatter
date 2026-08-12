"""Project-specific semantic helpers for parsed Markdown tables."""

# Standard library imports
import re
import typing

# Third-party imports
from la_dev_codex_plugins import markdown_tables


_ATX_HEADING_RE = re.compile(r"^ {0,3}(?P<marker>#{1,6})(?:[ \t]+|$)")
_FENCE_RE = re.compile(r"^ {0,3}(?P<marker>`{3,}|~{3,})(?P<suffix>.*)$")


def parsed_tables(text: str, *, label: str) -> tuple[markdown_tables.MarkdownTable, ...]:
    """Return all parsed tables with project-specific assertion context.

    Args:
        text (str): Complete Markdown document.
        label (str): Document identity included in assertion failures.

    Returns:
        Safely parsed Markdown tables in source order.

    Raises:
        AssertionError: The shared parser finds a malformed table candidate.
    """
    try:
        return typing.cast("tuple[markdown_tables.MarkdownTable, ...]", markdown_tables.parse_markdown_tables(text))
    except markdown_tables.MarkdownTableError as error:
        raise AssertionError(f"{label}: {error}") from error


def table_headers(table: markdown_tables.MarkdownTable, *, label: str) -> tuple[str, ...]:
    """Return validated nonempty unique table headers.

    Args:
        table (markdown_tables.MarkdownTable): Parsed table to validate.
        label (str): Document identity included in assertion failures.

    Returns:
        Header cells in source order.
    """
    headers = typing.cast("tuple[str, ...]", table.rows[0].cells)
    assert headers, f"{label}: table at line {table.start_line} has no columns"
    assert all(headers), f"{label}: table at line {table.start_line} has an empty header"
    assert len(headers) == len(set(headers)), f"{label}: table at line {table.start_line} has duplicate headers"
    return headers


def table_rows(table: markdown_tables.MarkdownTable, *, label: str, require_body: bool = True) -> tuple[dict[str, str], ...]:
    """Return body rows keyed by validated header text.

    Args:
        table (markdown_tables.MarkdownTable): Parsed table to convert.
        label (str): Document identity included in assertion failures.
        require_body (bool): Whether an empty body is invalid for this semantic consumer.

    Returns:
        Body cells keyed by their unique header text.
    """
    headers = table_headers(table, label=label)
    body = table.rows[2:]
    if require_body:
        assert body, f"{label}: table at line {table.start_line} has no body rows"
    return tuple(dict(zip(headers, typing.cast("tuple[str, ...]", row.cells), strict=True)) for row in body)


def table_after_heading(text: str, heading: str, *, label: str, expected_leading_lines: tuple[str, ...] | None = (), require_body: bool = True) -> markdown_tables.MarkdownTable:
    """Return the unique parsed table immediately owned by one heading.

    Args:
        text (str): Complete Markdown document.
        heading (str): Exact ATX heading that owns the table.
        label (str): Document identity included in assertion failures.
        expected_leading_lines (tuple[str, ...] | None): Exact nonblank structural lines permitted between the heading
            and table, or None to allow arbitrary section prose.
        require_body (bool): Whether the selected table must contain body rows.

    Returns:
        Unique table before the next heading at the same or a higher level.
    """
    lines = text.splitlines()
    headings = _markdown_headings(lines)
    heading_indexes = [index for index, _level in headings if lines[index] == heading]
    assert len(heading_indexes) == 1, f"{label}: expected exactly one {heading!r} heading, found {len(heading_indexes)}"
    heading_level = _atx_heading_level(heading)
    assert heading_level, f"{label}: expected an ATX heading, found {heading!r}"
    section_end = next((index for index, level in headings if index > heading_indexes[0] and level <= heading_level), len(lines))
    matches = tuple(table for table in parsed_tables(text, label=label) if heading_indexes[0] + 1 < table.start_line <= section_end)
    assert len(matches) == 1, f"{label}: expected exactly one Markdown table in the section following {heading!r}, found {len(matches)}"
    table = matches[0]
    leading_lines = tuple(line for line in lines[heading_indexes[0] + 1 : table.start_line - 1] if line.strip())
    if expected_leading_lines is not None:
        assert leading_lines == expected_leading_lines, f"{label}: expected leading lines {expected_leading_lines!r} between {heading!r} and its table, found {leading_lines!r}"
    table_rows(table, label=label, require_body=require_body)
    return table


def _atx_heading_level(line: str) -> int:
    """Return an ATX heading level, or zero for another line."""
    match = _ATX_HEADING_RE.match(line)
    return len(match.group("marker")) if match else 0


def _markdown_headings(lines: list[str]) -> tuple[tuple[int, int], ...]:
    """Return ATX headings outside fenced code blocks."""
    headings: list[tuple[int, int]] = []
    fence_character = ""
    fence_length = 0
    for index, line in enumerate(lines):
        fence_match = _FENCE_RE.match(line)
        if fence_character:
            if fence_match and fence_match.group("marker")[0] == fence_character and len(fence_match.group("marker")) >= fence_length and not fence_match.group("suffix").strip():
                fence_character = ""
                fence_length = 0
            continue
        if fence_match and (fence_match.group("marker")[0] == "~" or "`" not in fence_match.group("suffix")):
            fence_character = fence_match.group("marker")[0]
            fence_length = len(fence_match.group("marker"))
            continue
        if level := _atx_heading_level(line):
            headings.append((index, level))
    return tuple(headings)


def tables_with_headers(text: str, headers: tuple[str, ...], *, label: str, require_body: bool = True) -> tuple[markdown_tables.MarkdownTable, ...]:
    """Return every parsed table with the requested headers.

    Args:
        text (str): Complete Markdown document.
        headers (tuple[str, ...]): Exact header sequence used to select tables.
        label (str): Document identity included in assertion failures.
        require_body (bool): Whether selected tables must contain body rows.

    Returns:
        Matching tables in source order.
    """
    matches = tuple(table for table in parsed_tables(text, label=label) if table_headers(table, label=label) == headers)
    for table in matches:
        table_rows(table, label=label, require_body=require_body)
    return matches


def validate_tables(text: str, *, label: str, require_body: bool = True) -> tuple[markdown_tables.MarkdownTable, ...]:
    """Validate every parsed table and return them.

    Args:
        text (str): Complete Markdown document.
        label (str): Document identity included in assertion failures.
        require_body (bool): Whether every table must contain body rows.

    Returns:
        Validated tables in source order.
    """
    tables = parsed_tables(text, label=label)
    for table in tables:
        table_rows(table, label=label, require_body=require_body)
    return tables
