"""Tests for colon-ended prose boundaries."""

# Third-party imports
import pytest

# First-party imports
from pydocformatter.rules.definition_helpers import colon_boundaries


@pytest.mark.parametrize(("text", "require_unindented", "expected"), [("Heading:", False, True), (" Heading:", False, True), (" Heading:", True, False), ("Heading", False, False), ("", False, False)])
def test_is_colon_header_text_respects_shape_and_indentation(text: str, require_unindented: bool, expected: bool) -> None:
    """Classify non-empty colon endings with the requested indentation policy."""
    assert colon_boundaries.is_colon_header_text(text, require_unindented=require_unindented) is expected


@pytest.mark.parametrize(
    ("previous", "current", "expected"),
    [
        ("Continue the thought", "with another phrase:", True),
        ("Sentence complete.", "with another phrase:", False),
        ('Sentence complete.)"', "with another phrase:", False),
        ("", "with another phrase:", False),
        ("Continue the thought", "Without a colon", False),
        ("Continue the thought", "Uppercase continuation:", False),
        ("Continue the thought", "label:", False),
    ],
)
def test_allows_colon_continuation_distinguishes_prose_from_boundaries(previous: str, current: str, expected: bool) -> None:
    """Join lowercase prose continuations but not sentences, labels, or headers."""
    assert colon_boundaries.allows_colon_continuation(previous, current) is expected
