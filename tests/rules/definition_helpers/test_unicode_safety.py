# Third-party imports
import pytest

# First-party imports
from pydocformatter.rules.definition_helpers import unicode_safety


@pytest.mark.parametrize(("text", "expected"), [("plain text\t", False), ("line\nbreak", True), ("word\u00a0word", True), ("hazard\u202e", True), ("accepted\u200dformat", False)])
def test_normalization_safety_guard_matches_shared_unicode_policy(text: str, expected: bool) -> None:
    """Classify normalization barriers without producing diagnostic details."""
    assert unicode_safety.has_nonstandard_whitespace_or_control(text) is expected


def test_normalization_safety_guard_does_not_materialize_occurrences(monkeypatch: pytest.MonkeyPatch) -> None:
    """Avoid the detailed occurrence classifier for a Boolean safety check."""

    def unexpected_classifier(text: str) -> tuple[unicode_safety.SuspiciousUnicodeOccurrence, ...]:
        raise AssertionError(text)

    monkeypatch.setattr(unicode_safety, "suspicious_unicode_occurrences", unexpected_classifier)

    assert unicode_safety.has_nonstandard_whitespace_or_control("\x00")


def test_every_reportable_code_point_has_exactly_one_stable_label() -> None:
    reportable = unicode_safety.INDENTATION_ONLY_CODE_POINTS | unicode_safety.EVERYWHERE_CODE_POINTS

    assert unicode_safety.CODE_POINT_LABELS.keys() == reportable
    assert all(unicode_safety.suspicious_unicode_occurrences(chr(code_point))[0].label == unicode_safety.CODE_POINT_LABELS[code_point] for code_point in unicode_safety.EVERYWHERE_CODE_POINTS)
    assert all(
        unicode_safety.suspicious_unicode_occurrences(f"{chr(code_point)}text")[0].label == unicode_safety.CODE_POINT_LABELS[code_point] for code_point in unicode_safety.INDENTATION_ONLY_CODE_POINTS
    )


@pytest.mark.parametrize(
    ("code_point", "label"),
    [
        (0x0000, "NULL"),
        (0x0007, "ALERT"),
        (0x001F, "INFORMATION SEPARATOR ONE"),
        (0x007F, "DELETE"),
        (0x0080, "PADDING CHARACTER"),
        (0x009F, "APPLICATION PROGRAM COMMAND"),
        (0x061C, "ARABIC LETTER MARK"),
        (0x202E, "RIGHT-TO-LEFT OVERRIDE"),
        (0x206A, "INHIBIT SYMMETRIC SWAPPING"),
        (0x206F, "NOMINAL DIGIT SHAPES"),
        (0xFEFF, "ZERO WIDTH NO-BREAK SPACE"),
    ],
)
def test_reports_everywhere_characters_with_stable_labels(code_point: int, label: str) -> None:
    occurrence = unicode_safety.suspicious_unicode_occurrences(f"a{chr(code_point)}b")[0]

    assert occurrence.offset == 1
    assert occurrence.code_point == code_point
    assert occurrence.label == label
    assert occurrence.code_point_text == f"U+{code_point:04X} {label}"
    assert not occurrence.can_fix


@pytest.mark.parametrize("char", ["\u00a0", "\u2007", "\u202f"])
def test_nonbreaking_spaces_are_fixable_only_in_indentation(char: str) -> None:
    occurrences = unicode_safety.suspicious_unicode_occurrences(f"{char}first\r{char}\n{char}blank\nword{char}word")
    space_occurrences = tuple(occurrence for occurrence in occurrences if occurrence.code_point == ord(char))

    assert tuple(occurrence.offset for occurrence in space_occurrences) == (0, 7, 9)
    assert all(occurrence.can_fix for occurrence in space_occurrences)


def test_tabs_and_line_feeds_are_accepted_but_other_control_characters_are_reported() -> None:
    occurrences = unicode_safety.suspicious_unicode_occurrences("\ttext\nnext\rmore")

    assert tuple(occurrence.code_point for occurrence in occurrences) == (0x000D,)


def test_indentation_state_resets_for_crlf_cr_and_lf_without_double_counting() -> None:
    text = "prose\u00a0\r\n\u00a0crlf\r\u2007cr\n\u202flf"

    occurrences = unicode_safety.suspicious_unicode_occurrences(text)

    assert tuple((occurrence.code_point, occurrence.indentation) for occurrence in occurrences) == ((0x000D, False), (0x00A0, True), (0x000D, False), (0x2007, True), (0x202F, True))


def test_everywhere_character_in_indentation_does_not_end_indentation_prefix() -> None:
    occurrences = unicode_safety.suspicious_unicode_occurrences("\v\u00a0text")

    assert tuple((occurrence.code_point, occurrence.indentation, occurrence.can_fix) for occurrence in occurrences) == ((0x000B, False, False), (0x00A0, True, True))


@pytest.mark.parametrize("char", ["\u200c", "\u200d", "\u0301", "\ufe0f"])
def test_deliberate_exclusions_are_accepted(char: str) -> None:
    assert unicode_safety.suspicious_unicode_occurrences(f"a{char}b") == ()


def test_layout_separator_preserves_nonbreaking_prose_spaces() -> None:
    assert unicode_safety.is_layout_separator(" ")
    assert unicode_safety.is_layout_separator("\t")
    assert not unicode_safety.is_layout_separator("\v")
    assert not unicode_safety.is_layout_separator("\u0085")
    assert not unicode_safety.is_layout_separator("\u00a0")
    assert not unicode_safety.is_layout_separator("\u2007")
    assert not unicode_safety.is_layout_separator("\u202f")
