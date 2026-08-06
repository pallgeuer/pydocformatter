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
from pydocformatter.rules.definitions.PDF.PDF002_docstring_backslash_raw_prefix import PDF002DocstringBackslashRawPrefix
from tests import rule_helpers


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.definition import RuleCategoryContext, RuleContext


def contexts(source: str, *, settings: CheckSettings | None = None) -> tuple[RuleCategoryContext, RuleContext]:
    """Return matching category and rule contexts for source."""
    resolved_settings = CheckSettings(select=("PDF002",)) if settings is None else settings
    return rule_helpers.prepared_direct_rule_contexts(PDF, source, settings=resolved_settings)


def format_pdf002(source: str, *, settings: CheckSettings | None = None, fix: bool = True) -> formatter.FormatterResult:
    """Format source with PDF002 selected."""
    resolved_settings = CheckSettings(select=("PDF002",)) if settings is None else settings
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=fix)


@pytest.mark.filterwarnings("ignore:invalid escape sequence.*:DeprecationWarning")
def test_adds_raw_prefix_for_value_preserving_invalid_escape() -> None:
    source = 'def regex():\n    """Match \\d+ values."""\n'
    result = format_pdf002(source)

    assert result.new_source == 'def regex():\n    r"""Match \\d+ values."""\n'
    assert result.fixed_findings[PDF002DocstringBackslashRawPrefix.meta] == 1
    assert not format_pdf002(result.new_source).modified


@pytest.mark.filterwarnings("ignore:invalid escape sequence.*:DeprecationWarning")
def test_preserves_quote_style_when_adding_raw_prefix() -> None:
    source = "def regex():\n    '''Match \\d+ values.'''\n"
    result = format_pdf002(source)

    assert result.new_source == "def regex():\n    r'''Match \\d+ values.'''\n"
    assert result.fixed_findings[PDF002DocstringBackslashRawPrefix.meta] == 1


@pytest.mark.filterwarnings("ignore:invalid escape sequence.*:DeprecationWarning")
def test_adds_raw_prefix_to_simple_suite_docstring() -> None:
    source = 'def regex(): """Match \\d+ values."""\n'
    result = format_pdf002(source)

    assert result.new_source == 'def regex(): r"""Match \\d+ values."""\n'
    assert result.fixed_findings[PDF002DocstringBackslashRawPrefix.meta] == 1
    assert not format_pdf002(result.new_source).modified


def test_skips_raw_no_backslash_concatenated_and_non_docstring_strings() -> None:
    source = 'def raw():\n    r"""Match \\d+ values."""\n\n\ndef plain():\n    """No escapes."""\n\n\ndef concatenated():\n    ("Match " "\\\\d+")\n\n\ndef not_docstring():\n    value = 1\n    """Match \\d+ values."""\n'
    result = format_pdf002(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_skips_uppercase_raw_prefix() -> None:
    source = 'def raw():\n    R"""Match \\d+ values."""\n'
    result = format_pdf002(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_reports_recognized_escapes_as_non_fixable() -> None:
    source = 'def line():\n    """First\\nSecond."""\n\ndef tab():\n    """First\\tSecond."""\n\ndef unicode():\n    """Value \\u00e9."""\n'
    _, context = contexts(source)
    findings = rule_helpers.rule_findings(PDF002DocstringBackslashRawPrefix, context)
    result = rule_helpers.rule_fix_result(PDF002DocstringBackslashRawPrefix, context)
    check_only = format_pdf002(source, fix=False)

    assert tuple(finding.line_numbers for finding in findings) == ((2,), (5,))
    assert [finding.fixable for finding in findings] == [False, False]
    assert result.module is context.module
    assert result.fixed_findings == ()
    assert tuple(finding.line_numbers for finding in check_only.unfixed_findings) == ((2,), (5,))
    assert [finding.fixable for finding in check_only.unfixed_findings] == [False, False]


def test_skips_non_ascii_character_escapes_when_they_are_the_only_backslashes() -> None:
    source = 'def hex_escape():\n    """Letter \\xe9."""\n\ndef unicode_escape():\n    """Letter \\u00e9."""\n\ndef large_unicode_escape():\n    """Face \\U0001f600."""\n\ndef named_escape():\n    """Snowman \\N{SNOWMAN}."""\n\ndef octal_escape():\n    """No-break space \\240."""\n\ndef unicode_prefix():\n    u"""Letter \\u00e9."""\n'
    result = format_pdf002(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_reports_hex_octal_and_named_unicode_escapes_as_non_fixable() -> None:
    source = 'def hex_escape():\n    """Letter \\x41."""\n\ndef octal_escape():\n    """Letter \\101."""\n\ndef named_escape():\n    """Letter \\N{LATIN CAPITAL LETTER A}."""\n'
    result = format_pdf002(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2,), (5,), (8,))
    assert [finding.fixable for finding in result.unfixed_findings] == [False, False, False]


@pytest.mark.filterwarnings("ignore:invalid escape sequence.*:DeprecationWarning")
def test_keeps_mixed_fixable_and_nonfixable_findings_in_one_run() -> None:
    source = 'def fixed():\n    """Match \\d+."""\n\ndef unsafe():\n    """First\\nSecond."""\n'
    result = format_pdf002(source)

    assert result.new_source == 'def fixed():\n    r"""Match \\d+."""\n\ndef unsafe():\n    """First\\nSecond."""\n'
    assert result.fixed_findings[PDF002DocstringBackslashRawPrefix.meta] == 1
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((5,),)
    assert [finding.fixable for finding in result.unfixed_findings] == [False]


@pytest.mark.filterwarnings("ignore:invalid escape sequence.*:DeprecationWarning")
def test_reports_literal_and_recognized_escape_in_same_docstring_as_non_fixable() -> None:
    source = 'def mixed():\n    """Match \\d+ then\\nNext."""\n'
    result = format_pdf002(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2,),)
    assert [finding.fixable for finding in result.unfixed_findings] == [False]


@pytest.mark.filterwarnings("ignore:invalid escape sequence.*:DeprecationWarning")
def test_mixed_non_ascii_character_escapes_report_only_other_problem_lines() -> None:
    source = 'def mixed():\n    """Letter \\u00e9.\n    Match \\d+.\n    First\\nSecond."""\n'
    result = format_pdf002(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((3, 4),)
    assert [finding.fixable for finding in result.unfixed_findings] == [False]


@pytest.mark.filterwarnings("ignore:invalid escape sequence.*:DeprecationWarning")
def test_adds_raw_prefix_to_multiline_crlf_docstring_when_all_backslashes_are_literal() -> None:
    source = 'def regex():\r\n    """First line \\d+\r\n    second line \\w+."""\r\n'
    result = format_pdf002(source, settings=CheckSettings(select=("PDF002",), line_ending=LineEnding.CR_LF))

    assert result.new_source == 'def regex():\r\n    r"""First line \\d+\r\n    second line \\w+."""\r\n'
    assert result.fixed_findings[PDF002DocstringBackslashRawPrefix.meta] == 1
    _, fixed_context = contexts(result.new_source, settings=CheckSettings(select=("PDF002",), line_ending=LineEnding.CR_LF))
    assert PDF.require_data(fixed_context).docstrings[0].value == "First line \\d+\n    second line \\w+."
    assert not format_pdf002(result.new_source, settings=CheckSettings(select=("PDF002",), line_ending=LineEnding.CR_LF)).modified


def test_reports_escaped_backslash_delimiter_and_line_continuation_as_non_fixable() -> None:
    source = 'def backslash():\n    """C:\\\\temp."""\n\ndef delimiter():\n    """Contains \\"quote\\"."""\n\ndef continuation():\n    """first\\\nsecond"""\n'
    result = format_pdf002(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2,), (5,), (8,))
    assert [finding.fixable for finding in result.unfixed_findings] == [False, False, False]


def test_skips_bytes_and_fstring_first_expressions() -> None:
    source = 'def bytes_expression():\n    b"bytes with \\\\d are not docstrings"\n\n\ndef fstring_expression(value):\n    f"formatted {value} strings with \\\\d are not docstrings"\n'
    result = format_pdf002(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


@pytest.mark.filterwarnings("ignore:invalid escape sequence.*:DeprecationWarning")
def test_u_prefixed_backslash_docstring_is_non_fixable() -> None:
    source = 'def regex():\n    u"""Match \\d+ values."""\n'
    result = format_pdf002(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2,),)
    assert [finding.fixable for finding in result.unfixed_findings] == [False]


@pytest.mark.filterwarnings("ignore:invalid escape sequence.*:DeprecationWarning")
def test_check_fix_line_numbers_and_fix_false_findings_agree() -> None:
    source = 'def first():\n    """Match \\d+."""\n\ndef second():\n    """Match \\w+."""\n'
    _, context = contexts(source)
    findings = rule_helpers.rule_findings(PDF002DocstringBackslashRawPrefix, context)
    fixed = rule_helpers.rule_fix_result(PDF002DocstringBackslashRawPrefix, context)
    check_only = format_pdf002(source, fix=False)

    assert tuple(finding.line_numbers for finding in findings) == ((2,), (5,))
    assert [finding.fixable for finding in findings] == [True, True]
    assert tuple(finding.line_numbers for finding in fixed.fixed_findings) == ((2,), (5,))
    assert fixed.module.code == 'def first():\n    r"""Match \\d+."""\n\ndef second():\n    r"""Match \\w+."""\n'
    assert tuple(finding.line_numbers for finding in check_only.unfixed_findings) == ((2,), (5,))
    _, fixed_context = contexts(fixed.module.code)
    assert rule_helpers.rule_findings(PDF002DocstringBackslashRawPrefix, fixed_context) == ()


@pytest.mark.filterwarnings("ignore:invalid escape sequence.*:DeprecationWarning")
def test_pdf001_requotes_before_pdf002_adds_raw_prefix() -> None:
    source = "def regex():\n    '''Match \\d+ values.'''\n"
    settings = CheckSettings(select=("PDF001", "PDF002"))
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)

    assert result.new_source == 'def regex():\n    r"""Match \\d+ values."""\n'
    assert not result.unfixed_findings


def test_pdf000_normalized_raw_concatenation_can_leave_pdf002_nonfixable() -> None:
    source = 'def regex():\n    ("Match " r"\\d+ values.")\n'
    settings = CheckSettings(select=("PDF000", "PDF002"))
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)

    assert result.new_source == 'def regex():\n    ("""Match \\\\d+ values.""")\n'
    assert result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2,),)
    assert [finding.rule for finding in result.unfixed_findings] == [PDF002DocstringBackslashRawPrefix.meta]
    assert [finding.fixable for finding in result.unfixed_findings] == [False]
