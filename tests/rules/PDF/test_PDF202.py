# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# First-party imports
from pydocformatter import formatter, rules_selection
from pydocformatter.cli.settings_check import CheckSettings
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.definitions.PDF.PDF202_empty_docstring import PDF202EmptyDocstring
from tests import rule_helpers


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.definition import RuleCategoryContext, RuleContext


def contexts(source: str, *, settings: CheckSettings | None = None) -> tuple[RuleCategoryContext, RuleContext]:
    """Return matching category and rule contexts for source."""
    resolved_settings = CheckSettings(select=("PDF202",)) if settings is None else settings
    return rule_helpers.prepared_direct_rule_contexts(PDF, source, settings=resolved_settings)


def format_source(source: str, *, settings: CheckSettings | None = None, fix: bool = True) -> formatter.FormatterResult:
    """Format source with supplied settings."""
    resolved_settings = CheckSettings(select=("PDF202",)) if settings is None else settings
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=fix)


def test_reports_empty_and_whitespace_only_docstrings_without_fixing() -> None:
    source = '""""""\n\n\ndef function():\n    """   """\n\n\nclass Example:\n    """\n    \n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((1,), (5,), (9, 10, 11))
    assert [finding.fixable for finding in result.unfixed_findings] == [False, False, False]


def test_reports_empty_concatenated_docstring_on_physical_lines() -> None:
    source = 'def function():\n    (""\n     "")\n'
    result = format_source(source)

    assert result.new_source == source
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2, 3),)


def test_reports_delimiter_only_closing_line_as_part_of_empty_docstring() -> None:
    source = '"""\n"""\n'
    result = format_source(source)

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((1, 2),)


def test_closing_line_suppression_covers_the_whole_empty_docstring() -> None:
    source = '"""\n"""  # noqa: PDF202\n'

    assert not format_source(source).unfixed_findings


def test_reports_simple_suite_and_concatenated_whitespace_docstrings() -> None:
    source = 'def inline(): ""\n\n\ndef concatenated():\n    (" "\n     "\\t")\n'
    result = format_source(source)

    assert result.new_source == source
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((1,), (5, 6))


def test_reports_supported_empty_attached_attribute_docstrings() -> None:
    source = 'module_value = 1\n""""""\n\n\nclass Client:\n    class_value = 1\n    """   """\n\n    def __init__(self):\n        self.instance_value = 1\n        (""\n         "")\n'
    result = format_source(source)

    assert result.new_source == source
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2,), (7,), (11, 12))


def test_does_not_report_content_absent_docstrings_or_non_docstring_strings() -> None:
    source = 'def documented():\n    """Value."""\n\n\ndef undocumented():\n    pass\n\n\ndef not_docstring():\n    value = 1\n    """"""\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_reports_escaped_whitespace_but_skips_bytes_and_fstring_first_expressions() -> None:
    source = 'def escaped():\n    """\\t\\n"""\n\n\ndef bytes_expression():\n    b""\n\n\ndef fstring_expression(value):\n    f"{value}"\n'
    result = format_source(source)

    assert result.new_source == source
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2,),)


def test_unicode_whitespace_is_empty_but_zero_width_content_is_not() -> None:
    source = 'def non_breaking_space():\n    """\\u00a0"""\n\n\ndef zero_width_space():\n    """\\u200b"""\n'
    result = format_source(source)

    assert result.new_source == source
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2,),)


def test_check_and_fix_false_findings_agree() -> None:
    source = 'def function():\n    """   """\n'
    _, context = contexts(source)
    findings = rule_helpers.rule_findings(PDF202EmptyDocstring, context)
    check_only = format_source(source, fix=False)
    fix_enabled = format_source(source, fix=True)

    assert tuple(finding.line_numbers for finding in findings) == ((2,),)
    assert tuple(finding.line_numbers for finding in check_only.unfixed_findings) == ((2,),)
    assert tuple(finding.line_numbers for finding in fix_enabled.unfixed_findings) == ((2,),)
    assert check_only.new_source == source
    assert fix_enabled.new_source == source
