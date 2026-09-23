"""Tests for line-ending detection and rendering."""

# Future imports
from __future__ import annotations

# Standard library imports
import os
import typing

# Third-party imports
import pytest

# First-party imports
from pydocformatter.cli.settings_check import LineEnding
from pydocformatter.rules import line_endings


@pytest.mark.parametrize(("setting", "expected"), [(LineEnding.AUTO, "\r\n"), (LineEnding.LF, "\n"), (LineEnding.CR_LF, "\r\n"), (LineEnding.NATIVE, os.linesep)])
def test_resolve_line_ending_honors_every_supported_mode(setting: LineEnding, expected: str) -> None:
    """Resolve automatic, explicit, and platform-native line endings."""
    assert line_endings.resolve_line_ending("first\r\nsecond\n", line_ending=setting) == expected


def test_resolve_line_ending_rejects_an_unknown_mode() -> None:
    """Reject values outside the validated line-ending enumeration."""
    invalid = typing.cast("LineEnding", object())

    with pytest.raises(ValueError, match="Unexpected line ending specification"):
        line_endings.resolve_line_ending("source", line_ending=invalid)


@pytest.mark.parametrize("replacement", ["\n", "\r\n", "\r"])
def test_normalize_line_endings_converts_mixed_physical_endings(replacement: str) -> None:
    """Normalize CRLF, CR, and LF without changing line contents."""
    assert line_endings.normalize_line_endings("first\r\nsecond\rthird\nfourth", line_ending=replacement) == replacement.join(("first", "second", "third", "fourth"))
