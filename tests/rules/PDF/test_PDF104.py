# Third-party imports
import libcst as cst
import libcst.metadata as cst_metadata

# First-party imports
from pydocformatter import formatter, rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention, IndentStyle, LineEnding
from pydocformatter.rules.definition import RuleCategoryContext, RuleContext
from pydocformatter.rules.definition_helpers import source_text
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.definitions.PDF.PDF104_opening_quotes_whitespace import PDF104OpeningQuotesWhitespace
from tests import rule_helpers


def contexts(source: str, *, settings: CheckSettings | None = None) -> tuple[RuleCategoryContext, RuleContext]:
    """Return matching category and rule contexts for source."""
    module = cst.parse_module(source)
    wrapper = cst_metadata.MetadataWrapper(module, unsafe_skip_copy=True)
    category = RuleCategoryContext(
        path="example.py",
        settings=CheckSettings(select=("PDF104",)) if settings is None else settings,
        module=module,
        metadata_wrapper=wrapper,
        positions=wrapper.resolve(cst_metadata.PositionProvider),
        line_ending="\r\n" if "\r\n" in source else "\n",
        source=source,
        source_lines=tuple(source_text.source_lines(source)),
        line_bounds=None,
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
        category_data=PDF.prepare(category),
    )


def format_pdf005(source: str, *, settings: CheckSettings | None = None, fix: bool = True) -> formatter.FormatterResult:
    """Format source with PDF104 selected."""
    resolved_settings = CheckSettings(select=("PDF104",)) if settings is None else settings
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=fix)


def test_removes_opening_whitespace_from_one_line_and_multiline_docstrings() -> None:
    source = 'def one_line():\n    """  Summary.  """\n\ndef multi_line():\n    """\t Summary.\n    Body.\n    """\n'
    result = format_pdf005(source)

    assert result.new_source == 'def one_line():\n    """Summary.  """\n\ndef multi_line():\n    """Summary.\n    Body.\n    """\n'
    assert result.fixed_findings[PDF104OpeningQuotesWhitespace.meta] == 2
    assert not format_pdf005(result.new_source).modified


def test_leaves_trailing_whitespace_for_other_rules() -> None:
    source = 'def function():\n    """Summary.  """\n'
    result = format_pdf005(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_whitespace_only_opening_quote_line_belongs_to_pdf004() -> None:
    source = 'def function():\n    """   \n    Summary.\n    """\n'
    result = format_pdf005(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_non_space_tab_whitespace_counts_as_content() -> None:
    source = 'def function():\n    """ \t\xa0  Summary."""\n'
    result = format_pdf005(source)

    assert result.new_source == 'def function():\n    """\xa0  Summary."""\n'
    assert result.fixed_findings[PDF104OpeningQuotesWhitespace.meta] == 1


def test_trims_before_leading_delimiter_quotes() -> None:
    source = (
        "def double_one():\n    \"\"\"  \"quoted.\"\"\"\n\ndef double_two():\n    \"\"\"  \"\"quoted.\"\"\"\n\ndef single_one():\n    '''  'quoted.'''\n\ndef single_two():\n    '''  ''quoted.'''\n"
    )
    result = format_pdf005(source)

    assert (
        result.new_source
        == "def double_one():\n    \"\"\"\"quoted.\"\"\"\n\ndef double_two():\n    \"\"\"\"\"quoted.\"\"\"\n\ndef single_one():\n    ''''quoted.'''\n\ndef single_two():\n    '''''quoted.'''\n"
    )
    assert result.fixed_findings[PDF104OpeningQuotesWhitespace.meta] == 4
    assert not result.errors
    assert not format_pdf005(result.new_source).modified


def test_module_parenthesized_simple_suite_and_neutral_settings() -> None:
    source = '"""  Module."""\n\nclass Parenthesized:\n    ("""  Class.""")\n\ndef simple(): """  Summary."""; return None\n'
    settings = CheckSettings(select=("PDF104",), docstring_convention=DocstringConvention.GOOGLE, indent_style=IndentStyle.TAB, indent_width=8)
    result = format_pdf005(source, settings=settings)

    assert result.new_source == '"""Module."""\n\nclass Parenthesized:\n    ("""Class.""")\n\ndef simple(): """Summary."""; return None\n'
    assert result.fixed_findings[PDF104OpeningQuotesWhitespace.meta] == 3
    assert not format_pdf005(result.new_source, settings=settings).modified


def test_check_fix_line_numbers_and_fix_false_findings_agree() -> None:
    source = 'def first():\n    """  Summary."""\n\ndef second():\n    """\tOther."""\n'
    _, context = contexts(source)
    findings = rule_helpers.rule_findings(PDF104OpeningQuotesWhitespace, context)
    fixed = rule_helpers.rule_fix_result(PDF104OpeningQuotesWhitespace, context)
    check_only = format_pdf005(source, fix=False)

    assert tuple(finding.line_numbers for finding in findings) == ((2,), (5,))
    assert tuple(finding.line_numbers for finding in fixed.fixed_findings) == ((2,), (5,))
    assert tuple(finding.line_numbers for finding in check_only.unfixed_findings) == ((2,), (5,))
    _, fixed_context = contexts(fixed.module.code)
    assert rule_helpers.rule_findings(PDF104OpeningQuotesWhitespace, fixed_context) == ()


def test_skips_empty_concatenated_escaped_and_non_docstring_strings() -> None:
    source = 'def empty():\n    """"""\n\ndef concatenated():\n    ("  Summary.\\n"\n     "Body.")\n\ndef escaped():\n    """  Summary.\\nBody."""\n\ndef not_docstring():\n    value = 1\n    """  Summary."""\n'
    result = format_pdf005(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_preserves_raw_prefix_quote_delimiter_non_ascii_and_crlf_line_endings() -> None:
    source = "def function():\r\n    r''' \tPath C:\\\\temp and caf\xe9.'''\r\n"
    result = format_pdf005(source, settings=CheckSettings(select=("PDF104",), line_ending=LineEnding.CR_LF))

    assert result.new_source == "def function():\r\n    r'''Path C:\\\\temp and caf\xe9.'''\r\n"
    assert not format_pdf005(result.new_source, settings=CheckSettings(select=("PDF104",), line_ending=LineEnding.CR_LF)).modified


def test_pdf000_can_literalize_escaped_newline_before_pdf005_trims_it() -> None:
    source = 'def function():\n    """  Summary.\\nBody."""\n'
    settings = CheckSettings(select=("PDF000", "PDF104"))
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)

    assert result.new_source == 'def function():\n    """Summary.\nBody."""\n'
    assert result.fixed_findings[PDF104OpeningQuotesWhitespace.meta] == 1
    assert not formatter.format_source(result.new_source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True).modified
