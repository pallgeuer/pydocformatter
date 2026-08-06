# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# Third-party imports
import pytest

# First-party imports
from pydocformatter import formatter, rules_selection
from pydocformatter.cli.settings_check import CheckSettings, LineEnding
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.definitions.PDF.PDF001_docstring_quote_style import PDF001DocstringQuoteStyle
from tests import rule_helpers


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.definition import RuleCategoryContext, RuleContext


def contexts(source: str, *, settings: CheckSettings | None = None) -> tuple[RuleCategoryContext, RuleContext]:
    """Return matching category and rule contexts for source."""
    resolved_settings = CheckSettings(select=("PDF001",)) if settings is None else settings
    return rule_helpers.prepared_direct_rule_contexts(PDF, source, settings=resolved_settings)


def format_pdf001(source: str, *, settings: CheckSettings | None = None, fix: bool = True) -> formatter.FormatterResult:
    """Format source with PDF001 selected."""
    resolved_settings = CheckSettings(select=("PDF001",)) if settings is None else settings
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=fix)


def test_rewrites_simple_docstring_quote_styles() -> None:
    source = "\"module doc\"\n\nclass Client:\n    'client doc'\n\n    def close(self): '''close client'''\n"
    result = format_pdf001(source)

    assert result.new_source == '"""module doc"""\n\nclass Client:\n    """client doc"""\n\n    def close(self): """close client"""\n'
    assert result.fixed_findings[PDF001DocstringQuoteStyle.meta] == 3
    assert not format_pdf001(result.new_source).modified


def test_rewrites_attribute_docstring_quote_styles() -> None:
    source = "module_value = 1\n'module attr'\n\nclass Client:\n    class_value = 1\n    'class attr'\n\n    def __init__(self): self.instance_value = 1; 'instance attr'\n"
    result = format_pdf001(source)

    assert (
        result.new_source == 'module_value = 1\n"""module attr"""\n\nclass Client:\n    class_value = 1\n    """class attr"""\n\n    def __init__(self): self.instance_value = 1; """instance attr"""\n'
    )
    assert result.fixed_findings[PDF001DocstringQuoteStyle.meta] == 3
    assert not format_pdf001(result.new_source).modified


def test_ignores_attribute_like_strings_after_blank_or_comment_lines() -> None:
    source = (
        "module_blank = 1\n\n'separated module string without period and enough words to reflow'\nmodule_comment = 1\n# comment\n'separated comment string without period and enough words to reflow'\n"
    )
    settings = CheckSettings(select=("PDF001", "PDF101", "PDF300"), line_length=32)
    result = format_pdf001(source, settings=settings)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_preserves_raw_prefix_when_requoting_is_value_preserving() -> None:
    source = "def path():\n    r'''Return C:\\\\temp.'''\n"
    result = format_pdf001(source)

    assert result.new_source == 'def path():\n    r"""Return C:\\\\temp."""\n'
    assert result.fixed_findings[PDF001DocstringQuoteStyle.meta] == 1


def test_preserves_source_continuation_when_requoting() -> None:
    source = "def joined():\n    '''Return alpha\\\nbeta.'''\n"
    result = format_pdf001(source)

    assert result.new_source == 'def joined():\n    """Return alpha\\\nbeta."""\n'
    assert result.fixed_findings[PDF001DocstringQuoteStyle.meta] == 1


def test_requotes_empty_u_prefixed_and_simple_suite_docstrings() -> None:
    source = "''\n\nclass Empty:\n    ''''''\n\n\ndef inline(): 'Inline doc.'\n\n\ndef unicode_prefix():\n    u'''Caf\\xe9.'''\n"
    result = format_pdf001(source)

    assert result.new_source == '""""""\n\nclass Empty:\n    """"""\n\n\ndef inline(): """Inline doc."""\n\n\ndef unicode_prefix():\n    u"""Caf\\xe9."""\n'
    assert result.fixed_findings[PDF001DocstringQuoteStyle.meta] == 4
    _, fixed_context = contexts(result.new_source)
    assert tuple(docstring.value for docstring in PDF.require_data(fixed_context).docstrings) == ("", "", "Inline doc.", "Caf\xe9.")
    assert not format_pdf001(result.new_source).modified


def test_escapes_target_delimiter_collision_for_non_raw_docstring() -> None:
    source = "def quoted():\n    '''Contains \"\"\" inside.'''\n"
    result = format_pdf001(source)

    assert result.new_source == 'def quoted():\n    """Contains \\"\\"\\" inside."""\n'
    _, fixed_context = contexts(result.new_source)
    assert PDF.require_data(fixed_context).docstrings[0].value == 'Contains """ inside.'
    assert not format_pdf001(result.new_source).modified


def test_reports_raw_target_delimiter_collision_as_non_fixable() -> None:
    source = "def quoted():\n    r'''Contains \"\"\" inside.'''\n"
    _, context = contexts(source)
    findings = rule_helpers.rule_findings(PDF001DocstringQuoteStyle, context)
    result = rule_helpers.rule_fix_result(PDF001DocstringQuoteStyle, context)
    check_only = format_pdf001(source, fix=False)

    assert tuple(finding.line_numbers for finding in findings) == ((2,),)
    assert [finding.fixable for finding in findings] == [False]
    assert result.module is context.module
    assert result.fixed_findings == ()
    assert tuple(finding.line_numbers for finding in check_only.unfixed_findings) == ((2,),)
    assert [finding.fixable for finding in check_only.unfixed_findings] == [False]


def test_keeps_mixed_fixable_and_nonfixable_findings_in_one_run() -> None:
    source = "def fixed():\n    'Summary.'\n\ndef unsafe():\n    r'''Contains \"\"\" delimiter.'''\n"
    result = format_pdf001(source)

    assert result.new_source == 'def fixed():\n    """Summary."""\n\ndef unsafe():\n    r\'\'\'Contains """ delimiter.\'\'\'\n'
    assert result.fixed_findings[PDF001DocstringQuoteStyle.meta] == 1
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((5,),)
    assert [finding.fixable for finding in result.unfixed_findings] == [False]


def test_reports_multiline_uppercase_raw_target_delimiter_collision_as_non_fixable() -> None:
    source = "def quoted():\n    R'''First line.\n    Contains \"\"\" delimiter.\n    Done.'''\n"
    result = format_pdf001(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2, 3, 4),)
    assert [finding.fixable for finding in result.unfixed_findings] == [False]


def test_requotes_multiline_crlf_docstring_with_target_delimiter_collision() -> None:
    source = "def function():\r\n    '''First line.\r\n    Contains \"\"\" delimiter.\r\n    Done.'''\r\n"
    result = format_pdf001(source, settings=CheckSettings(select=("PDF001",), line_ending=LineEnding.CR_LF))

    assert result.new_source == 'def function():\r\n    """First line.\r\n    Contains \\"\\"\\" delimiter.\r\n    Done."""\r\n'
    assert result.fixed_findings[PDF001DocstringQuoteStyle.meta] == 1
    _, fixed_context = contexts(result.new_source, settings=CheckSettings(select=("PDF001",), line_ending=LineEnding.CR_LF))
    assert PDF.require_data(fixed_context).docstrings[0].value == 'First line.\n    Contains """ delimiter.\n    Done.'
    assert not format_pdf001(result.new_source, settings=CheckSettings(select=("PDF001",), line_ending=LineEnding.CR_LF)).modified


@pytest.mark.filterwarnings("ignore:invalid escape sequence.*:DeprecationWarning")
def test_unsupported_escape_with_target_delimiter_collision_is_non_fixable() -> None:
    source = "def function():\n    '''Contains \\z and \"\"\" delimiter.'''\n"
    result = format_pdf001(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2,),)
    assert [finding.fixable for finding in result.unfixed_findings] == [False]


@pytest.mark.filterwarnings("ignore:invalid escape sequence.*:DeprecationWarning")
def test_requotes_unsupported_escape_when_body_spelling_is_value_preserving() -> None:
    source = "def function():\n    '''Contains \\z literally.'''\n"
    result = format_pdf001(source)

    assert result.new_source == 'def function():\n    """Contains \\z literally."""\n'
    assert result.fixed_findings[PDF001DocstringQuoteStyle.meta] == 1
    _, fixed_context = contexts(result.new_source)
    assert PDF.require_data(fixed_context).docstrings[0].value == "Contains \\z literally."
    assert not format_pdf001(result.new_source).modified


def test_skips_triple_double_concatenated_and_non_docstring_strings() -> None:
    source = '"""module doc"""\n\n\ndef concatenated():\n    ("first " "second")\n\n\ndef not_docstring():\n    value = 1\n    \'not a docstring\'\n'
    result = format_pdf001(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_skips_bytes_and_fstring_first_expressions() -> None:
    source = 'def bytes_expression():\n    b"bytes are not docstrings"\n\n\ndef fstring_expression(value):\n    f"formatted {value} strings are not docstrings"\n'
    result = format_pdf001(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_check_fix_line_numbers_and_fix_false_findings_agree() -> None:
    source = "def first():\n    'Summary.'\n\ndef second():\n    '''Other.'''\n"
    _, context = contexts(source)
    findings = rule_helpers.rule_findings(PDF001DocstringQuoteStyle, context)
    fixed = rule_helpers.rule_fix_result(PDF001DocstringQuoteStyle, context)
    check_only = format_pdf001(source, fix=False)

    assert tuple(finding.line_numbers for finding in findings) == ((2,), (5,))
    assert [finding.fixable for finding in findings] == [True, True]
    assert tuple(finding.line_numbers for finding in fixed.fixed_findings) == ((2,), (5,))
    assert tuple(finding.line_numbers for finding in check_only.unfixed_findings) == ((2,), (5,))
    _, fixed_context = contexts(fixed.module.code)
    assert rule_helpers.rule_findings(PDF001DocstringQuoteStyle, fixed_context) == ()


def test_pdf000_normalizes_concatenation_before_pdf001() -> None:
    source = "def function():\n    (\"first \" 'second')\n"
    settings = CheckSettings(select=("PDF000", "PDF001"))
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)

    assert result.new_source == 'def function():\n    ("""first second""")\n'
    assert not result.unfixed_findings
