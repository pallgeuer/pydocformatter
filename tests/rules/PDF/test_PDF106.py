# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# First-party imports
from pydocformatter import formatter, rules_selection
from pydocformatter.cli.settings_check import CheckSettings, LineEnding
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.definitions.PDF.PDF106_multiline_opening_quotes_same_line import PDF106MultilineOpeningQuotesSameLine
from pydocformatter.rules.definitions.PDF.PDF108_multiline_closing_quotes_same_line import PDF108MultilineClosingQuotesSameLine
from tests import rule_helpers


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.definition import RuleCategoryContext, RuleContext


def contexts(source: str, *, settings: CheckSettings | None = None) -> tuple[RuleCategoryContext, RuleContext]:
    """Return matching category and rule contexts for source."""
    resolved_settings = CheckSettings(select=("PDF106",)) if settings is None else settings
    return rule_helpers.prepared_direct_rule_contexts(PDF, source, settings=resolved_settings)


def format_pdf102(source: str, *, settings: CheckSettings | None = None, fix: bool = True) -> formatter.FormatterResult:
    """Format source with PDF106 selected."""
    resolved_settings = CheckSettings(select=("PDF106",)) if settings is None else settings
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=fix)


def test_moves_first_content_line_onto_opening_quotes() -> None:
    source = 'def function():\n    """\n\n    Summary.\n\n    Body.\n    """\n'
    result = format_pdf102(source)

    assert result.new_source == 'def function():\n    """Summary.\n\n    Body.\n    """\n'
    assert result.fixed_findings[PDF106MultilineOpeningQuotesSameLine.meta] == 1
    assert not format_pdf102(result.new_source).modified


def test_removes_space_tab_only_lines_before_first_content() -> None:
    source = 'def function():\n    """  \n\t\n    Summary.\n\n    Body.\n    """\n'
    result = format_pdf102(source)

    assert result.new_source == 'def function():\n    """Summary.\n\n    Body.\n    """\n'
    assert result.fixed_findings[PDF106MultilineOpeningQuotesSameLine.meta] == 1
    assert not format_pdf102(result.new_source).modified


def test_suspicious_unicode_defers_moving_summary_to_first_line() -> None:
    source = 'def function():\n    """\n    \xa0\n    Body.\n    """\n'
    result = format_pdf102(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_preserves_raw_prefix_quote_delimiter_and_rewrites_nested_decorated_async_docstrings() -> None:
    source = "def outer():\n    r'''\n    Path C:\\\\temp.\n\n    Body.\n    '''\n\n    @decorator\n    async def inner():\n        \"\"\"\n        Inner.\n\n        Body.\n        \"\"\"\n"
    result = format_pdf102(source)

    assert result.new_source == "def outer():\n    r'''Path C:\\\\temp.\n\n    Body.\n    '''\n\n    @decorator\n    async def inner():\n        \"\"\"Inner.\n\n        Body.\n        \"\"\"\n"
    assert result.fixed_findings[PDF106MultilineOpeningQuotesSameLine.meta] == 2
    assert not format_pdf102(result.new_source).modified


def test_moves_single_content_line_onto_opening_quotes() -> None:
    source = 'def function():\n    """\n    Summary.\n    """\n'
    result = format_pdf102(source)

    assert result.new_source == 'def function():\n    """Summary.\n    """\n'
    assert result.fixed_findings[PDF106MultilineOpeningQuotesSameLine.meta] == 1
    assert not format_pdf102(result.new_source).modified


def test_escapes_leading_content_quote_when_moving_onto_opening_quotes() -> None:
    source = 'def function():\n    """\n    "quoted start.\n    Body.\n    """\n'
    result = format_pdf102(source)

    assert result.new_source == 'def function():\n    """\\"quoted start.\n    Body.\n    """\n'
    assert result.fixed_findings[PDF106MultilineOpeningQuotesSameLine.meta] == 1
    assert not format_pdf102(result.new_source).modified


def test_leaves_already_same_line_and_single_physical_line_docstrings() -> None:
    source = 'def same():\n    """Summary.\n\n    Body.\n    """\n\ndef one_line():\n    """Summary."""\n'
    result = format_pdf102(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_module_parenthesized_simple_suite_and_crlf_line_endings() -> None:
    source = '"""\r\nModule.\r\n\r\nBody.\r\n"""\r\n\r\nclass Parenthesized:\r\n    ("""\r\n    Class.\r\n\r\n    Body.\r\n    """)\r\n\r\ndef simple(): """\r\n    Summary.\r\n\r\n    Body.\r\n    """; return None\r\n'
    settings = CheckSettings(select=("PDF106",), line_ending=LineEnding.CR_LF)
    result = format_pdf102(source, settings=settings)

    assert (
        result.new_source
        == '"""Module.\r\n\r\nBody.\r\n"""\r\n\r\nclass Parenthesized:\r\n    ("""Class.\r\n\r\n    Body.\r\n    """)\r\n\r\ndef simple(): """Summary.\r\n\r\n    Body.\r\n    """; return None\r\n'
    )
    assert result.fixed_findings[PDF106MultilineOpeningQuotesSameLine.meta] == 3
    assert not format_pdf102(result.new_source, settings=settings).modified


def test_check_fix_line_numbers_and_fix_false_findings_agree() -> None:
    source = 'def first():\n    """\n    Summary.\n\n    Body.\n    """\n\ndef second():\n    """\n\n    Other.\n\n    Body.\n    """\n'
    _, context = contexts(source)
    findings = rule_helpers.rule_findings(PDF106MultilineOpeningQuotesSameLine, context)
    fixed = rule_helpers.rule_fix_result(PDF106MultilineOpeningQuotesSameLine, context)
    check_only = format_pdf102(source, fix=False)

    assert tuple(finding.line_numbers for finding in findings) == ((2, 3), (9, 10, 11))
    assert tuple(finding.line_numbers for finding in fixed.fixed_findings) == ((2, 3), (9, 10, 11))
    assert tuple(finding.line_numbers for finding in check_only.unfixed_findings) == ((2, 3), (9, 10, 11))
    _, fixed_context = contexts(fixed.module.code)
    assert rule_helpers.rule_findings(PDF106MultilineOpeningQuotesSameLine, fixed_context) == ()


def test_skips_concatenated_escaped_and_non_docstring_strings() -> None:
    source = 'def concatenated():\n    ("\\n"\n     "Summary.\\n"\n     "Body.")\n\ndef escaped():\n    """\\nSummary.\\nBody."""\n\ndef not_docstring():\n    value = 1\n    """\n    Summary.\n\n    Body.\n    """\n'
    result = format_pdf102(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_moves_opening_quotes_with_non_raw_escape_source_mapping() -> None:
    source = 'def function():\n    """\n    Summary\\t.\n\n    Body.\n    """\n'
    result = format_pdf102(source)

    assert result.new_source == 'def function():\n    """Summary\\t.\n\n    Body.\n    """\n'
    assert result.fixed_findings[PDF106MultilineOpeningQuotesSameLine.meta] == 1
    assert not result.unfixed_findings


def test_pdf000_can_literalize_escaped_newline_before_pdf102_moves_content() -> None:
    source = 'def function():\n    """\\nSummary.\\nBody."""\n'
    settings = CheckSettings(select=("PDF000", "PDF106"))
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)

    assert result.new_source == 'def function():\n    """Summary.\nBody."""\n'
    assert result.fixed_findings[PDF106MultilineOpeningQuotesSameLine.meta] == 1


def test_pdf102_and_pdf105_normalize_both_quote_placements_together() -> None:
    source = 'def function():\n    """\n    Summary.\n\n    Body."""\n'
    settings = CheckSettings(select=("PDF106", "PDF109"))
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)

    assert result.new_source == 'def function():\n    """Summary.\n\n    Body.\n    """\n'
    assert result.fixed_findings[PDF106MultilineOpeningQuotesSameLine.meta] == 1
    assert not formatter.format_source(result.new_source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True).modified


def test_pdf102_and_pdf104_can_collapse_single_content_line_multiline_docstring() -> None:
    source = 'def function():\n    """\n    Summary.\n    """\n'
    settings = CheckSettings(select=("PDF106", "PDF108"))
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)

    assert result.new_source == 'def function():\n    """Summary."""\n'
    assert result.fixed_findings[PDF106MultilineOpeningQuotesSameLine.meta] == 1
    assert result.fixed_findings[PDF108MultilineClosingQuotesSameLine.meta] == 1
    assert not formatter.format_source(result.new_source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True).modified
