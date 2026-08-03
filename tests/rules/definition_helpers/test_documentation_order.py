"""Tests for shared documentation-order comparison."""

# First-party imports
from pydocformatter.rules.definition_helpers import documentation_order


def test_reports_every_inversion_against_the_highest_rank_documented_earlier() -> None:
    issues = documentation_order.order_issues(
        ("first", "second", "third", "fourth"),
        ("third", "first", "second", "fourth"),
        ordered_key=lambda item: item,
        documented_key=lambda item: item,
        issue_factory=lambda documented, ordered, preceding: (documented, ordered, preceding),
    )

    assert issues == (("first", "first", "third"), ("second", "second", "third"))


def test_ignores_unknown_and_repeated_keys_after_normalization() -> None:
    issues = documentation_order.order_issues(
        ("First", "Second", "Third"),
        ("THIRD", "stale", "third", "FIRST", "SECOND"),
        ordered_key=str.lower,
        documented_key=str.lower,
        issue_factory=lambda documented, ordered, preceding: (documented, ordered, preceding),
    )

    assert issues == (("FIRST", "First", "Third"), ("SECOND", "Second", "Third"))


def test_accepts_ordered_partial_documentation() -> None:
    issues = documentation_order.order_issues(
        ("first", "second", "third", "fourth"),
        ("first", "third"),
        ordered_key=lambda item: item,
        documented_key=lambda item: item,
        issue_factory=lambda documented, ordered, preceding: (documented, ordered, preceding),
    )

    assert not issues
