import os
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class FileDecision:
    """Result of evaluating whether a file path should be formatted."""

    path: str
    accepted: bool
    reason: str


def classify_file(
    file_path: str,
    compiled_include: re.Pattern[str],
    compiled_exclude: re.Pattern[str] | None,
) -> FileDecision:
    """Determine if the file should be formatted and why.

    This function checks if the file matches the include pattern and does not match the
    exclude pattern.

    Args:
        file_path (str): The path to the file.
        compiled_include (re.Pattern[str]): Compiled regex pattern for files to include.
        compiled_exclude (re.Pattern[str] | None): Compiled regex pattern for files to
            exclude, or None to disable exclusion filtering.

    Returns:
        FileDecision: Classification of the file path.
    """
    # Check if the file matches the include pattern
    if not compiled_include.search(file_path):
        return FileDecision(
            path=file_path,
            accepted=False,
            reason="does not match the --include regular expression",
        )

    # Check if the file matches the exclude pattern
    if compiled_exclude and compiled_exclude.search(file_path):
        return FileDecision(
            path=file_path,
            accepted=False,
            reason="matches the --exclude regular expression",
        )

    return FileDecision(path=file_path, accepted=True, reason="included")


def collect_file_decisions(
    paths: list[str],
    include: re.Pattern[str],
    exclude: re.Pattern[str] | None,
    respect_gitignore: bool = True,
) -> list[FileDecision]:
    """Collect decision metadata for each considered file path.

    Directory traversal is deterministic to keep output stable between runs.

    Args:
        paths (list[str]): List of files and directories to consider.
        include (re.Pattern[str]): Compiled regex pattern for files to include.
        exclude (re.Pattern[str] | None): Compiled regex pattern for files to exclude.
        respect_gitignore (bool): Whether to respect .gitignore during discovery.
    """
    decisions: list[FileDecision] = []
    for path in paths:
        if os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                dirs.sort()
                files.sort()
                for name in files:
                    full_path = os.path.join(root, name)
                    decisions.append(classify_file(full_path, include, exclude))
        else:
            decisions.append(classify_file(path, include, exclude))
    return decisions


def collect_files(
    paths: list[str],
    include: re.Pattern[str],
    exclude: re.Pattern[str] | None,
    respect_gitignore: bool = True,
) -> list[str]:
    """Collect files that should be formatted based on include and exclude patterns.

    This function filters the provided list of file paths based on the include and
    exclude patterns. It returns a list of file paths that should be formatted.

    Args:
        paths (list[str]): List of file paths to check.
        include (re.Pattern[str]): Compiled regex pattern for files to include.
        exclude (re.Pattern[str] | None): Compiled regex pattern for files to exclude,
            or None to disable exclusion filtering.
        respect_gitignore (bool): Whether to respect .gitignore during discovery.

    Returns:
        list[str]: List of file paths that should be formatted.
    """
    decisions = collect_file_decisions(
        paths, include, exclude, respect_gitignore=respect_gitignore
    )
    return [decision.path for decision in decisions if decision.accepted]


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
    path: str, subject: str, line_numbers: list[int]
) -> str:
    """Build a compact per-file check message with line or line-range details."""
    label = "lines" if len(line_numbers) > 1 else "line"
    formatted_ranges = format_line_ranges(line_numbers)
    return f"{path}: Needs {subject} formatting on {label} {formatted_ranges}"
