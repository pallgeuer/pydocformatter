import pytest

import pydocformatter.formatter as formatter
import pydocformatter.rules_selection as rules_selection
from pydocformatter.cli.settings_check import CheckSettings, LineEnding
from pydocformatter.rules.definitions.PDF.PDF002_docstring_backslash_raw_prefix import PDF002DocstringBackslashRawPrefix
from pydocformatter.rules.definitions.PDF.PDF003_docstring_ascii_only import PDF003DocstringAsciiOnly

pytestmark = pytest.mark.filterwarnings("ignore:invalid escape sequence.*:DeprecationWarning")


def format_pdf003(source: str, *, fix: bool = True, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    resolved_settings = CheckSettings(select=("PDF003",)) if settings is None else settings
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=fix)


def test_fixes_simple_docstring_literal_non_ascii_source() -> None:
    source = 'def function():\n    """Return caf\xe9 and \U0001f600."""\n'

    result = format_pdf003(source)

    assert result.new_source == 'def function():\n    """Return caf\\xe9 and \\U0001f600."""\n'
    assert result.fixed_findings[PDF003DocstringAsciiOnly.meta] == 1
    assert not format_pdf003(result.new_source).modified


def test_fixes_raw_docstring_without_backslashes_by_removing_raw_prefix() -> None:
    source = 'def function():\n    r"""Return caf\xe9."""\n'

    result = format_pdf003(source)

    assert result.new_source == 'def function():\n    """Return caf\\xe9."""\n'
    assert result.fixed_findings[PDF003DocstringAsciiOnly.meta] == 1


def test_fixes_u_prefixed_docstring_without_dropping_u_prefix() -> None:
    source = 'def function():\n    u"""Return caf\xe9."""\n'

    result = format_pdf003(source)

    assert result.new_source == 'def function():\n    u"""Return caf\\xe9."""\n'
    assert result.fixed_findings[PDF003DocstringAsciiOnly.meta] == 1


def test_fixes_multiline_crlf_docstring_and_reports_all_physical_lines() -> None:
    source = 'def function():\r\n    """Return caf\xe9.\r\n    Snowman \u2603."""\r\n'
    settings = CheckSettings(select=("PDF003",), line_ending=LineEnding.CR_LF)

    check_only = format_pdf003(source, fix=False, settings=settings)
    result = format_pdf003(source, settings=settings)

    assert result.new_source == 'def function():\r\n    """Return caf\\xe9.\r\n    Snowman \\u2603."""\r\n'
    assert result.fixed_findings[PDF003DocstringAsciiOnly.meta] == 1
    assert tuple(finding.line_numbers for finding in check_only.unfixed_findings) == ((2, 3),)
    assert tuple(finding.message for finding in check_only.unfixed_findings) == ("Docstring source contains non-ASCII character U+00E9",)
    assert [finding.fixable for finding in check_only.unfixed_findings] == [True]
    assert not format_pdf003(result.new_source, settings=settings).modified


def test_ignores_already_ascii_source_escapes() -> None:
    source = 'def function():\n    """Return caf\\xe9 and \\u2603."""\n'

    result = format_pdf003(source)

    assert result.new_source == source
    assert result.fixed_findings == {}
    assert result.unfixed_findings == ()


def test_reports_concatenated_docstring_as_non_fixable() -> None:
    source = 'def function():\n    ("Return caf\xe9" " soon.")\n'

    result = format_pdf003(source)

    assert result.new_source == source
    assert result.fixed_findings == {}
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2,),)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring source contains non-ASCII character U+00E9",)
    assert [finding.fixable for finding in result.unfixed_findings] == [False]


def test_reports_raw_docstring_with_backslash_as_non_fixable() -> None:
    source = 'def function():\n    r"""Return caf\xe9\\d."""\n'

    result = format_pdf003(source)

    assert result.new_source == source
    assert result.fixed_findings == {}
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2,),)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring source contains non-ASCII character U+00E9",)
    assert [finding.fixable for finding in result.unfixed_findings] == [False]


def test_reports_docstring_with_value_changing_backslash_as_non_fixable() -> None:
    source = 'def function():\n    """Return caf\xe9\\nNext."""\n'

    result = format_pdf003(source)

    assert result.new_source == source
    assert result.fixed_findings == {}
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2,),)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring source contains non-ASCII character U+00E9",)
    assert [finding.fixable for finding in result.unfixed_findings] == [False]


def test_keeps_mixed_fixable_and_nonfixable_docstrings_in_one_run() -> None:
    source = 'def fixed():\n    """Return caf\xe9."""\n\n\ndef unsafe():\n    """Return caf\xe9\\nNext."""\n'

    result = format_pdf003(source)

    assert result.new_source == 'def fixed():\n    """Return caf\\xe9."""\n\n\ndef unsafe():\n    """Return caf\xe9\\nNext."""\n'
    assert result.fixed_findings[PDF003DocstringAsciiOnly.meta] == 1
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((6,),)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring source contains non-ASCII character U+00E9",)
    assert [finding.fixable for finding in result.unfixed_findings] == [False]


def test_skips_non_docstring_strings_even_when_source_is_non_ascii() -> None:
    source = 'value = "caf\xe9"\n\ndef function(value):\n    f"caf\xe9 {value}"\n    "caf\xe9"\n'

    result = format_pdf003(source)

    assert result.new_source == source
    assert result.fixed_findings == {}
    assert result.unfixed_findings == ()


def test_does_not_block_pdf002_raw_prefix_fix_for_literal_backslash_docstring() -> None:
    source = 'def function():\n    """Return caf\xe9 and \\d."""\n'
    settings = CheckSettings(select=("PDF002", "PDF003"))

    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)

    assert result.new_source == 'def function():\n    r"""Return caf\xe9 and \\d."""\n'
    assert result.fixed_findings[PDF002DocstringBackslashRawPrefix.meta] == 1
    assert result.fixed_findings.get(PDF003DocstringAsciiOnly.meta, 0) == 0
    assert tuple(finding.rule for finding in result.unfixed_findings) == (PDF003DocstringAsciiOnly.meta,)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring source contains non-ASCII character U+00E9",)
    assert [finding.fixable for finding in result.unfixed_findings] == [False]


def test_pdf003_fix_does_not_create_pdf002_findings_for_non_ascii_character_escapes() -> None:
    source = 'def function():\n    """Return caf\xe9."""\n'
    settings = CheckSettings(select=("PDF002", "PDF003"))

    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)

    assert result.new_source == 'def function():\n    """Return caf\\xe9."""\n'
    assert result.fixed_findings[PDF003DocstringAsciiOnly.meta] == 1
    assert result.unfixed_findings == ()


def test_rule_requires_exact_selection_by_default() -> None:
    default_selection = rules_selection.select_rules(CheckSettings())
    exact_selection = rules_selection.select_rules(CheckSettings(extend_select=("PDF003",)))
    category_selection = rules_selection.select_rules(CheckSettings(select=("PDF",)))

    assert PDF003DocstringAsciiOnly.meta not in tuple(rule.rule for rule in default_selection.rules)
    assert PDF003DocstringAsciiOnly.meta in tuple(rule.rule for rule in exact_selection.rules)
    assert PDF003DocstringAsciiOnly.meta not in tuple(rule.rule for rule in category_selection.rules)
    assert next(rule for rule in exact_selection.rules if rule.rule == PDF003DocstringAsciiOnly.meta).fixable
