def format_line_ranges(line_numbers: list[int]) -> str:
    """Format sorted line numbers as compressed ranges like 1-3, 7, 9-10."""
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
    """Build a compact per-file check message with line or line-range details."""
    label = "lines" if len(line_numbers) > 1 else "line"
    formatted_ranges = format_line_ranges(line_numbers)
    return f"{path}: Needs {subject} formatting on {label} {formatted_ranges}"
