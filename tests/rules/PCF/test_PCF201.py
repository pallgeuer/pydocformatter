# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# Third-party imports
import pytest

# First-party imports
import tests.rules.PCF.helpers as pcf_helpers
from pydocformatter import rules_selection
from pydocformatter.cli.settings_check import CheckSettings
from pydocformatter.rules.definitions.PCF.PCF201_comment_suspicious_unicode import PCF201CommentSuspiciousUnicode


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter import formatter


def format_pcf201(source: str, *, fix: bool = True) -> formatter.FormatterResult:
    settings = CheckSettings(select=("PCF201",))
    return pcf_helpers.format_pcf_settings(source, settings=settings, fix=fix)


@pytest.mark.parametrize("char", ["\u00a0", "\u2007", "\u202f"])
def test_fixes_nonbreaking_comment_indentation(char: str) -> None:
    source = f"#{char}Comment.\nvalue = 1  #{char}Trailing.\n"

    result = format_pcf201(source)

    assert result.new_source == "# Comment.\nvalue = 1  # Trailing.\n"
    assert result.fixed_findings[PCF201CommentSuspiciousUnicode.meta] == 2
    assert result.unfixed_findings == ()


def test_reports_diagnostic_only_characters_without_interpreting_ascii_escapes() -> None:
    source = "# abc\u202edef\u202e\n# \\u202e is notation\nvalue = 1  # x\u200by\n"

    result = format_pcf201(source)

    assert result.new_source == source
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((1,), (3,))
    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Comment contains suspicious Unicode character U+202E RIGHT-TO-LEFT OVERRIDE",
        "Comment contains suspicious Unicode character U+200B ZERO WIDTH SPACE",
    )
    assert all(not finding.fixable for finding in result.unfixed_findings)


def test_groups_repeated_characters_per_comment_but_not_across_comments() -> None:
    source = "#\u00a0\u00a0first\n#\u00a0second\n# a\u202eb\u202ec\n"

    checked = format_pcf201(source, fix=False)
    fixed = format_pcf201(source)

    assert tuple((finding.line_numbers, finding.message, finding.fixable) for finding in checked.unfixed_findings) == (
        ((1,), "Comment contains suspicious Unicode character U+00A0 NO-BREAK SPACE", True),
        ((2,), "Comment contains suspicious Unicode character U+00A0 NO-BREAK SPACE", True),
        ((3,), "Comment contains suspicious Unicode character U+202E RIGHT-TO-LEFT OVERRIDE", False),
    )
    assert fixed.new_source == "#  first\n# second\n# a\u202eb\u202ec\n"
    assert fixed.fixed_findings[PCF201CommentSuspiciousUnicode.meta] == 2
    assert tuple(finding.line_numbers for finding in fixed.unfixed_findings) == ((3,),)


def test_whitespace_only_payload_remains_indentation_until_line_end() -> None:
    source = "#\u00a0\u2007\u202f\n#\t\u00a0\n"

    result = format_pcf201(source)

    assert result.new_source == "#   \n#\t \n"
    assert result.fixed_findings[PCF201CommentSuspiciousUnicode.meta] == 4


def test_nonbreaking_space_after_prose_is_not_reclassified_by_later_line_break_characters() -> None:
    source = "# prose\u00a0\r\n#\u00a0indent\r\n"

    result = format_pcf201(source)

    assert result.new_source == "# prose\u00a0\r\n# indent\r\n"
    assert result.fixed_findings[PCF201CommentSuspiciousUnicode.meta] == 1


def test_handles_eof_without_a_final_newline() -> None:
    source = "#\u00a0comment"

    result = format_pcf201(source)

    assert result.new_source == "# comment"
    assert result.fixed_findings[PCF201CommentSuspiciousUnicode.meta] == 1


def test_uses_only_the_first_hash_as_syntax() -> None:
    source = "#\u00a0fixed\n##\u00a0accepted\n# \u00a0also fixed\n"

    result = format_pcf201(source)

    assert result.new_source == "# fixed\n##\u00a0accepted\n#  also fixed\n"
    assert result.fixed_findings[PCF201CommentSuspiciousUnicode.meta] == 2


def test_checks_special_comment_kinds() -> None:
    source = "#!/usr/bin/env\u202epython\n# coding: utf-8\u200b\nvalue = 1  # type: int\u2060\n# noqa\u00ad\n"

    result = format_pcf201(source)

    assert result.new_source == source
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((1,), (2,), (3,), (4,))


def test_rule_is_selected_broadly_and_is_sometimes_fixable() -> None:
    default_selection = rules_selection.select_rules(CheckSettings())
    category_selection = rules_selection.select_rules(CheckSettings(select=("PCF",)))

    assert PCF201CommentSuspiciousUnicode.meta in tuple(rule.rule for rule in default_selection.rules)
    selected = next(rule for rule in category_selection.rules if rule.rule == PCF201CommentSuspiciousUnicode.meta)
    assert selected.fixable


def test_unfixable_selection_reports_fixable_occurrences_without_editing() -> None:
    source = "#\u00a0Comment.\n"
    settings = CheckSettings(select=("PCF201",), unfixable=("PCF201",))

    result = pcf_helpers.format_pcf_settings(source, settings=settings)

    assert result.new_source == source
    assert result.fixed_findings == {}
    assert tuple((finding.line_numbers, finding.fixable) for finding in result.unfixed_findings) == (((1,), False),)


@pytest.mark.parametrize("payload", ["\u00a0Comment.", "Comment\u202epayload."])
def test_local_suppression_hides_fixable_and_diagnostic_occurrences(payload: str) -> None:
    source = f"# pydocfmt: ignore[PCF201]\n# {payload}\n"

    result = format_pcf201(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_comment_formatters_preserve_hazards_until_pcf201_reports_or_fixes_them() -> None:
    source = "#\u00a0Fix indentation.\n# Keep  abc\u202edef unchanged.\nvalue = 1# Keep\u200bpayload\n# noqa : F401\u2060\n"
    settings = CheckSettings(select=("PCF",))

    result = pcf_helpers.format_pcf_settings(source, settings=settings)

    assert result.new_source == "# Fix indentation.\n# Keep  abc\u202edef unchanged.\nvalue = 1  # Keep\u200bpayload\n# noqa : F401\u2060\n"
    assert result.fixed_findings[PCF201CommentSuspiciousUnicode.meta] == 1
    assert tuple(finding.rule for finding in result.unfixed_findings).count(PCF201CommentSuspiciousUnicode.meta) == 3


def test_pcf001_and_pcf201_apply_overlapping_trailing_comment_fixes_convergently() -> None:
    source = "value = 1#\u00a0Comment.\n"
    settings = CheckSettings(select=("PCF001", "PCF201"))

    result = pcf_helpers.format_pcf_settings(source, settings=settings)

    assert result.new_source == "value = 1  # Comment.\n"
    assert {rule.code.tag: count for rule, count in result.fixed_findings.items()} == {"PCF001": 1, "PCF201": 1}
    assert result.new_source is not None
    assert not pcf_helpers.format_pcf_settings(result.new_source, settings=settings).modified
