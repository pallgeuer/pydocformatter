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


def format_line_ranges(line_numbers: list[int]) -> str:
    """Format sorted line numbers as compressed ranges.

    Args:
        line_numbers (list[int]): Sorted 1-based line numbers to compress.

    Returns:
        str: Comma-separated line ranges, such as `1-3, 7, 9-10`, or an empty string for no lines.
    """
    if not line_numbers:
        return ""

    ranges: list[str] = []
    start = line_numbers[0]
    end = line_numbers[0]

    for current in line_numbers[1:]:
        if current == end + 1:
            end = current
            continue
        ranges.append(f"{start}-{end}" if start != end else str(start))
        start = current
        end = current

    ranges.append(f"{start}-{end}" if start != end else str(start))
    return ", ".join(ranges)


def format_needs_formatting_message(
    path: str,
    subject: str,
    line_numbers: list[int],
) -> str:
    """Build a compact per-file check message with line or line-range details.

    Args:
        path (str): File path to include in the diagnostic.
        subject (str): Formatting subject, such as `docstring` or `comment`.
        line_numbers (list[int]): Sorted 1-based line numbers that need formatting.

    Returns:
        str: Human-readable diagnostic message for check mode.
    """
    label = "lines" if len(line_numbers) > 1 else "line"
    formatted_ranges = format_line_ranges(line_numbers)
    return f"{path}: Needs {subject} formatting on {label} {formatted_ranges}"
