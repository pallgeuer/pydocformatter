"""Validation for rule diagnostic line targets."""

from __future__ import annotations


def validate_line_numbers(line_numbers: tuple[int, ...], description: str) -> None:
    """Validate one non-empty tuple of positive one-based line numbers.

    Args:
        line_numbers (tuple[int, ...]): Candidate diagnostic target lines.
        description (str): Label used in validation error messages.

    Raises:
        TypeError: If the target is not a tuple of integers.
        ValueError: If the target is empty or contains non-positive line numbers.
    """
    if not isinstance(line_numbers, tuple):
        raise TypeError(f"{description} must be a tuple")
    if not line_numbers:
        raise ValueError(f"{description} must not be empty")
    if not all(type(line_number) is int for line_number in line_numbers):
        raise TypeError(f"{description} must contain integers")
    if not all(line_number > 0 for line_number in line_numbers):
        raise ValueError(f"{description} must contain positive line numbers")


def normalize_line_numbers(line_numbers: tuple[int, ...], description: str) -> tuple[int, ...]:
    """Return validated line numbers with duplicate entries removed.

    Args:
        line_numbers (tuple[int, ...]): Candidate diagnostic target lines.
        description (str): Label used in validation error messages.

    Returns:
        tuple[int, ...]: Validated one-based line numbers in first-seen order.
    """
    validate_line_numbers(line_numbers, description)
    return tuple(dict.fromkeys(line_numbers))


def validate_line_number_targets(line_number_targets: tuple[tuple[int, ...], ...], description: str, target_description: str) -> None:
    """Validate one tuple of line-number target tuples.

    Args:
        line_number_targets (tuple[tuple[int, ...], ...]): Candidate suppression or grouping targets.
        description (str): Label used when the outer value is invalid.
        target_description (str): Label used when an inner line-number tuple is invalid.

    Raises:
        TypeError: If the outer value or an inner target has the wrong type.
        ValueError: If an inner target is empty or contains non-positive line numbers.
    """
    if not isinstance(line_number_targets, tuple):
        raise TypeError(f"{description} must be a tuple")
    for target in line_number_targets:
        validate_line_numbers(target, target_description)


def normalize_line_number_targets(line_number_targets: tuple[tuple[int, ...], ...], description: str, target_description: str) -> tuple[tuple[int, ...], ...]:
    """Return validated line-number targets with duplicate line entries and duplicate targets removed.

    Args:
        line_number_targets (tuple[tuple[int, ...], ...]): Candidate suppression or grouping targets.
        description (str): Label used when the outer value is invalid.
        target_description (str): Label used when an inner line-number tuple is invalid.

    Returns:
        tuple[tuple[int, ...], ...]: Normalized targets in first-seen order.
    """
    validate_line_number_targets(line_number_targets, description, target_description)
    return tuple(dict.fromkeys(normalize_line_numbers(target, target_description) for target in line_number_targets))
