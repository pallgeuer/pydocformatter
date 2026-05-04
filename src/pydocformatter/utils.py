import os
import re
import subprocess
from collections import defaultdict
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

    if not respect_gitignore:
        return decisions

    accepted_paths = [decision.path for decision in decisions if decision.accepted]
    if not accepted_paths:
        return decisions

    accepted_paths_by_git_root = _group_paths_by_git_root(accepted_paths)
    gitignored_absolute_paths = _collect_gitignored_absolute_paths(
        accepted_paths_by_git_root
    )

    return [
        (
            FileDecision(
                path=decision.path, accepted=False, reason="matches .gitignore"
            )
            if decision.accepted
            and os.path.abspath(decision.path) in gitignored_absolute_paths
            else decision
        )
        for decision in decisions
    ]


def _group_paths_by_git_root(paths: list[str]) -> dict[str, list[str]]:
    """Group absolute file paths by containing git root as repo-relative paths."""
    root_cache: dict[str, str | None] = {}
    grouped_paths: dict[str, list[str]] = defaultdict(list)

    for path in paths:
        absolute_path = os.path.abspath(path)
        git_root = _find_git_root_for_path(absolute_path, root_cache)
        if git_root is None:
            continue
        relative_path = os.path.relpath(absolute_path, git_root).replace(os.sep, "/")
        grouped_paths[git_root].append(relative_path)

    return dict(grouped_paths)


def _find_git_root_for_path(
    absolute_path: str, root_cache: dict[str, str | None]
) -> str | None:
    """Find the git repository root that contains the path, if any."""
    start_dir = (
        absolute_path
        if os.path.isdir(absolute_path)
        else os.path.dirname(absolute_path)
    )
    if start_dir in root_cache:
        return root_cache[start_dir]

    current_dir = os.path.abspath(start_dir)
    git_root: str | None = None
    while True:
        if os.path.exists(os.path.join(current_dir, ".git")):
            git_root = current_dir
            break
        parent_dir = os.path.dirname(current_dir)
        if parent_dir == current_dir:
            break
        current_dir = parent_dir

    root_cache[start_dir] = git_root
    return root_cache[start_dir]


def _collect_gitignored_absolute_paths(
    paths_by_git_root: dict[str, list[str]],
) -> set[str]:
    """Return all absolute paths matched by gitignore semantics across git roots."""
    gitignored_paths: set[str] = set()

    for git_root, relative_paths in paths_by_git_root.items():
        ignored_relative_paths, error = _query_git_ignored_paths(
            git_root, relative_paths
        )
        if error is not None:
            print(
                f"{git_root} WARNING: unable to apply gitignore filtering ({error}); "
                f"continuing without gitignore filtering for this repository root"
            )
            continue
        gitignored_paths.update(
            os.path.abspath(os.path.join(git_root, path))
            for path in ignored_relative_paths
        )

    return gitignored_paths


def _query_git_ignored_paths(
    git_root: str, relative_paths: list[str]
) -> tuple[set[str], str | None]:
    """Query git for ignored repo-relative paths using pattern-based semantics."""
    unique_relative_paths = list(dict.fromkeys(relative_paths))
    if not unique_relative_paths:
        return set(), None

    stdin_bytes = ("\0".join(unique_relative_paths) + "\0").encode("utf-8")
    try:
        process = subprocess.run(
            ["git", "-C", git_root, "check-ignore", "--stdin", "--no-index", "-z"],
            input=stdin_bytes,
            capture_output=True,
            check=False,
        )
    except OSError as error:
        return set(), str(error)

    if process.returncode not in {0, 1}:
        error_message = process.stderr.decode("utf-8", errors="replace").strip()
        return (
            set(),
            error_message
            or f"git check-ignore exited with status {process.returncode}",
        )

    stdout = process.stdout.decode("utf-8", errors="surrogateescape")
    ignored_paths = {path for path in stdout.split("\0") if path}
    return ignored_paths, None


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
