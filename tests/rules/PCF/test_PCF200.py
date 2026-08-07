# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# First-party imports
import tests.rules.PCF.helpers as pcf_helpers
from pydocformatter import rules_selection
from pydocformatter.cli.settings_check import CheckSettings
from pydocformatter.rules.definitions.PCF.PCF200_comment_ascii_only import PCF200CommentAsciiOnly


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter import formatter


def format_pcf200(source: str, *, fix: bool = True) -> formatter.FormatterResult:
    settings = CheckSettings(select=("PCF200",))
    return pcf_helpers.format_pcf_settings(source, settings=settings, fix=fix)


def test_reports_non_ascii_comments_without_fixing() -> None:
    source = "# caf\xe9\nvalue = 1  # na\xefve\n# noqa: caf\xe9\n"

    result = format_pcf200(source)

    assert result.new_source == source
    assert result.fixed_findings == {}
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((1,), (2,), (3,))
    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Comment contains non-ASCII character U+00E9",
        "Comment contains non-ASCII character U+00EF",
        "Comment contains non-ASCII character U+00E9",
    )
    assert all(not finding.fixable for finding in result.unfixed_findings)


def test_ignores_ascii_comments() -> None:
    result = format_pcf200("# cafe\nvalue = 1  # naive\n")

    assert result.new_source == "# cafe\nvalue = 1  # naive\n"
    assert result.fixed_findings == {}
    assert result.unfixed_findings == ()


def test_ignores_non_ascii_outside_comments_and_ascii_escape_spellings() -> None:
    source = 'text = "# caf\xe9 is data"\n# caf\\xe9 is ASCII source\n# caf\xe9 is a comment\n'

    result = format_pcf200(source)

    assert result.new_source == source
    assert result.fixed_findings == {}
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((3,),)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Comment contains non-ASCII character U+00E9",)
    assert all(not finding.fixable for finding in result.unfixed_findings)


def test_rule_requires_exact_selection_by_default() -> None:
    default_selection = rules_selection.select_rules(CheckSettings())
    exact_selection = rules_selection.select_rules(CheckSettings(extend_select=("PCF200",)))
    category_selection = rules_selection.select_rules(CheckSettings(select=("PCF",)))

    assert PCF200CommentAsciiOnly.meta not in tuple(rule.rule for rule in default_selection.rules)
    assert PCF200CommentAsciiOnly.meta in tuple(rule.rule for rule in exact_selection.rules)
    assert PCF200CommentAsciiOnly.meta not in tuple(rule.rule for rule in category_selection.rules)
    assert not next(rule for rule in exact_selection.rules if rule.rule == PCF200CommentAsciiOnly.meta).fixable
