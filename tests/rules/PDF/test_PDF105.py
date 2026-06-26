import libcst as cst
import libcst.metadata as cst_metadata
import pytest

import pydocformatter.formatter as formatter
import pydocformatter.rules.definition_helpers.source_text as source_text
import pydocformatter.rules_selection as rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention, IndentStyle, LineEnding
from pydocformatter.rules.definition import RuleCategoryContext, RuleContext
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.definitions.PDF.PDF105_closing_quotes_whitespace import PDF105ClosingQuotesWhitespace


def contexts(source: str, *, settings: CheckSettings | None = None) -> tuple[RuleCategoryContext, RuleContext]:
    """Return matching category and rule contexts for source."""
    module = cst.parse_module(source)
    wrapper = cst_metadata.MetadataWrapper(module, unsafe_skip_copy=True)
    category = RuleCategoryContext(
        path="example.py",
        settings=CheckSettings(select=("PDF105",)) if settings is None else settings,
        module=module,
        metadata_wrapper=wrapper,
        positions=wrapper.resolve(cst_metadata.PositionProvider),
        line_ending="\r\n" if "\r\n" in source else "\n",
        source=source,
        source_lines=tuple(source_text.source_lines(source)),
        line_bounds=None,
        suppression_index=None,
    )
    return category, RuleContext(
        path=category.path,
        settings=category.settings,
        module=category.module,
        metadata_wrapper=category.metadata_wrapper,
        positions=category.positions,
        line_ending=category.line_ending,
        source=category.source,
        source_lines=category.source_lines,
        line_bounds=category.line_bounds,
        suppression_index=category.suppression_index,
        category_data=PDF.prepare(category),
        effectively_fixable=True,
    )


def format_pdf006(source: str, *, settings: CheckSettings | None = None, fix: bool = True) -> formatter.FormatterResult:
    """Format source with PDF105 selected."""
    resolved_settings = CheckSettings(select=("PDF105",)) if settings is None else settings
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=fix)


def test_removes_closing_whitespace_from_one_line_and_multiline_docstrings() -> None:
    source = 'def one_line():\n    """Summary.  """\n\ndef multi_line():\n    """Summary.\n    Body.\t """\n'
    result = format_pdf006(source)

    assert result.new_source == 'def one_line():\n    """Summary."""\n\ndef multi_line():\n    """Summary.\n    Body."""\n'
    assert result.fixed_findings[PDF105ClosingQuotesWhitespace.meta] == 2
    assert not format_pdf006(result.new_source).modified


def test_escapes_quote_collision_before_closing_quotes() -> None:
    source = 'def quote_one():\n    """Summary "  """\n\ndef quote_two():\n    """Summary ""  """\n\ndef backslash():\n    r"""Path \\  """\n'
    result = format_pdf006(source)

    assert result.new_source == 'def quote_one():\n    """Summary \\""""\n\ndef quote_two():\n    """Summary \\"\\""""\n\ndef backslash():\n    r"""Path \\ """\n'
    assert result.fixed_findings[PDF105ClosingQuotesWhitespace.meta] == 3
    assert not format_pdf006(result.new_source).modified


def test_single_separator_quote_collision_is_escaped_when_possible() -> None:
    source = 'def quote_one():\n    """Summary " """\n\ndef quote_two():\n    """Summary "" """\n\ndef backslash():\n    r"""Path \\ """\n'
    result = format_pdf006(source)

    assert result.new_source == 'def quote_one():\n    """Summary \\""""\n\ndef quote_two():\n    """Summary \\"\\""""\n\ndef backslash():\n    r"""Path \\ """\n'
    assert result.fixed_findings[PDF105ClosingQuotesWhitespace.meta] == 2
    assert not result.unfixed_findings


def test_single_quote_delimiter_escapes_and_escaped_backslash_trim() -> None:
    source = "def quote_one():\n    '''Summary '  '''\n\ndef quote_two():\n    '''Summary ''  '''\n\ndef backslash():\n    \"\"\"Path \\\\  \"\"\"\n"
    result = format_pdf006(source)

    assert result.new_source == "def quote_one():\n    '''Summary \\''''\n\ndef quote_two():\n    '''Summary \\'\\''''\n\ndef backslash():\n    \"\"\"Path \\\\\"\"\"\n"
    assert result.fixed_findings[PDF105ClosingQuotesWhitespace.meta] == 3
    assert not result.errors
    assert not format_pdf006(result.new_source).modified


def test_single_quote_single_separator_is_escaped_when_possible() -> None:
    source = "def quote_one():\n    '''Summary ' '''\n\ndef quote_two():\n    '''Summary '' '''\n"
    result = format_pdf006(source)

    assert result.new_source == "def quote_one():\n    '''Summary \\''''\n\ndef quote_two():\n    '''Summary \\'\\''''\n"
    assert result.fixed_findings[PDF105ClosingQuotesWhitespace.meta] == 2
    assert not result.unfixed_findings


def test_single_character_quote_delimiter_with_escaped_quote_trims_safely() -> None:
    source = "def function():\n    'Summary \\'  '\n"
    result = format_pdf006(source)

    assert result.new_source == "def function():\n    'Summary \\''\n"
    assert result.fixed_findings[PDF105ClosingQuotesWhitespace.meta] == 1
    assert not result.unfixed_findings


@pytest.mark.filterwarnings("ignore:invalid escape sequence.*:DeprecationWarning")
def test_unsupported_non_raw_backslash_escape_is_skipped() -> None:
    source = 'def backslash():\n    """Path \\  """\n'
    result = format_pdf006(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_module_parenthesized_simple_suite_and_neutral_settings() -> None:
    source = '"""Module.  """\n\nclass Parenthesized:\n    ("""Class.\t""")\n\ndef simple(): """Summary.  """; return None\n'
    settings = CheckSettings(select=("PDF105",), docstring_convention=DocstringConvention.NUMPY, indent_style=IndentStyle.TAB, indent_width=8)
    result = format_pdf006(source, settings=settings)

    assert result.new_source == '"""Module."""\n\nclass Parenthesized:\n    ("""Class.""")\n\ndef simple(): """Summary."""; return None\n'
    assert result.fixed_findings[PDF105ClosingQuotesWhitespace.meta] == 3
    assert not format_pdf006(result.new_source, settings=settings).modified


def test_trailing_whitespace_before_evaluated_newline_belongs_to_pdf003() -> None:
    source = 'def function():\n    """Summary.  \n    """\n'
    result = format_pdf006(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_whitespace_only_closing_quote_line_belongs_to_pdf004() -> None:
    source = 'def function():\n    """Summary.\n      """\n'
    result = format_pdf006(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_non_space_tab_whitespace_counts_as_content() -> None:
    source = 'def function():\n    """Summary.\xa0 \t """\n'
    result = format_pdf006(source)

    assert result.new_source == 'def function():\n    """Summary.\xa0"""\n'
    assert result.fixed_findings[PDF105ClosingQuotesWhitespace.meta] == 1


def test_check_fix_line_numbers_and_fix_false_findings_agree() -> None:
    source = 'def first():\n    """Summary.  """\n\ndef second():\n    """Other.\t"""\n'
    _, context = contexts(source)
    findings = PDF105ClosingQuotesWhitespace.check(context)
    fixed = PDF105ClosingQuotesWhitespace.fix(context)
    check_only = format_pdf006(source, fix=False)

    assert tuple(finding.line_numbers for finding in findings) == ((2,), (5,))
    assert tuple(finding.line_numbers for finding in fixed.fixed_findings) == ((2,), (5,))
    assert tuple(finding.line_numbers for finding in check_only.unfixed_findings) == ((2,), (5,))
    _, fixed_context = contexts(fixed.module.code)
    assert PDF105ClosingQuotesWhitespace.check(fixed_context) == ()


def test_skips_empty_concatenated_escaped_and_non_docstring_strings() -> None:
    source = 'def empty():\n    """"""\n\ndef concatenated():\n    ("Summary.\\n"\n     "Body.  ")\n\ndef escaped():\n    """Summary.\\nBody.  """\n\ndef not_docstring():\n    value = 1\n    """Summary.  """\n'
    result = format_pdf006(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_preserves_raw_prefix_quote_delimiter_non_ascii_and_crlf_line_endings() -> None:
    source = "def function():\r\n    r'''Path C:\\\\temp and caf\xe9.\t '''\r\n"
    result = format_pdf006(source, settings=CheckSettings(select=("PDF105",), line_ending=LineEnding.CR_LF))

    assert result.new_source == "def function():\r\n    r'''Path C:\\\\temp and caf\xe9.'''\r\n"
    assert not format_pdf006(result.new_source, settings=CheckSettings(select=("PDF105",), line_ending=LineEnding.CR_LF)).modified


def test_pdf000_can_literalize_escaped_newline_before_pdf006_trims_it() -> None:
    source = 'def function():\n    """Summary.\\nBody.  """\n'
    settings = CheckSettings(select=("PDF000", "PDF105"))
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)

    assert result.new_source == 'def function():\n    """Summary.\nBody."""\n'
    assert result.fixed_findings[PDF105ClosingQuotesWhitespace.meta] == 1
    assert not formatter.format_source(result.new_source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True).modified


def test_pdf005_and_pdf006_can_normalize_both_sides() -> None:
    source = 'def function():\n    """  Summary.  """\n'
    settings = CheckSettings(select=("PDF104", "PDF105"))
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)

    assert result.new_source == 'def function():\n    """Summary."""\n'
    assert result.fixed_findings[PDF105ClosingQuotesWhitespace.meta] == 1
