import os
import re


def should_format_file(
    file_path: str,
    compiled_include: re.Pattern[str],
    compiled_exclude: re.Pattern[str] | None,
) -> bool:
    """Determine if the file should be formatted.

    This function checks if the file matches the include pattern and does not match the
    exclude pattern.

    Args:
        file_path (str): The path to the file.
        compiled_include (re.Pattern[str]): Compiled regex pattern for files to include.
        compiled_exclude (re.Pattern[str] | None): Compiled regex pattern for files to
            exclude, or None to disable exclusion filtering.

    Returns:
        bool: True if the file should be formatted, False otherwise.
    """
    # Check if the file matches the include pattern
    if not compiled_include.search(file_path):
        return False

    # Check if the file matches the exclude pattern
    if compiled_exclude and compiled_exclude.search(file_path):
        return False

    return True


def collect_files(
    paths: list[str], include: re.Pattern[str], exclude: re.Pattern[str] | None
) -> list[str]:
    """Collect files that should be formatted based on include and exclude patterns.

    This function filters the provided list of file paths based on the include and
    exclude patterns. It returns a list of file paths that should be formatted.

    Args:
        paths (list[str]): List of file paths to check.
        include (re.Pattern[str]): Compiled regex pattern for files to include.
        exclude (re.Pattern[str] | None): Compiled regex pattern for files to exclude,
            or None to disable exclusion filtering.

    Returns:
        list[str]: List of file paths that should be formatted.
    """
    matched_files = []
    for path in paths:
        if os.path.isdir(path):
            for root, _, files in os.walk(path):
                for name in files:
                    full_path = os.path.join(root, name)
                    if should_format_file(full_path, include, exclude):
                        matched_files.append(full_path)
        else:
            if should_format_file(path, include, exclude):
                matched_files.append(path)

    return matched_files
