"""Validation for rule diagnostic line targets."""

from __future__ import annotations


def validate_line_numbers(line_numbers: tuple[int, ...], description: str) -> None:
    """Validate one non-empty tuple of positive one-based line numbers."""
    if not isinstance(line_numbers, tuple):
        raise TypeError(f"{description} must be a tuple")
    if not line_numbers:
        raise ValueError(f"{description} must not be empty")
    if not all(type(line_number) is int for line_number in line_numbers):
        raise TypeError(f"{description} must contain integers")
    if not all(line_number > 0 for line_number in line_numbers):
        raise ValueError(f"{description} must contain positive line numbers")


def normalize_line_numbers(line_numbers: tuple[int, ...], description: str) -> tuple[int, ...]:
    """Return validated line numbers with duplicate entries removed."""
    validate_line_numbers(line_numbers, description)
    return tuple(dict.fromkeys(line_numbers))


def validate_line_number_targets(line_number_targets: tuple[tuple[int, ...], ...], description: str, target_description: str) -> None:
    """Validate one tuple of line-number target tuples."""
    if not isinstance(line_number_targets, tuple):
        raise TypeError(f"{description} must be a tuple")
    for target in line_number_targets:
        validate_line_numbers(target, target_description)


def normalize_line_number_targets(line_number_targets: tuple[tuple[int, ...], ...], description: str, target_description: str) -> tuple[tuple[int, ...], ...]:
    """Return validated line-number targets with duplicate line entries and duplicate targets removed."""
    validate_line_number_targets(line_number_targets, description, target_description)
    return tuple(dict.fromkeys(normalize_line_numbers(target, target_description) for target in line_number_targets))
