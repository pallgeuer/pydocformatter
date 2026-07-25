# Third-party imports
import libcst as cst
import pytest
import libcst.metadata as cst_metadata

# First-party imports
from pydocformatter import formatter, rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention, LineEnding
from pydocformatter.rules.definition import RuleCategoryContext, RuleContext
from pydocformatter.rules.definition_helpers import source_text
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.definitions.PDF.PDF101_docstring_reflow import PDF101DocstringReflow
from pydocformatter.rules.definitions.PDF.PDF110_one_line_docstring import PDF110OneLineDocstring
from pydocformatter.source_path import SourcePathContext
from tests import rule_helpers


def contexts(source: str, *, settings: CheckSettings | None = None) -> tuple[RuleCategoryContext, RuleContext]:
    """Return matching category and rule contexts for source."""
    module = cst.parse_module(source)
    wrapper = cst_metadata.MetadataWrapper(module, unsafe_skip_copy=True)
    category = RuleCategoryContext(
        path="example.py",
        source_path=SourcePathContext.for_path("example.py"),
        settings=CheckSettings(select=("PDF110",)) if settings is None else settings,
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
        source_path=category.source_path,
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


def format_pdf106(source: str, *, settings: CheckSettings | None = None, fix: bool = True) -> formatter.FormatterResult:
    """Format source with PDF110 selected."""
    resolved_settings = CheckSettings(select=("PDF110",)) if settings is None else settings
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=fix)


def test_collapses_single_summary_line_docstring() -> None:
    source = 'def function():\n    """\n    Summary.\n    """\n'
    result = format_pdf106(source)

    assert result.new_source == 'def function():\n    """Summary."""\n'
    assert result.fixed_findings[PDF110OneLineDocstring.meta] == 1
    assert not format_pdf106(result.new_source).modified


def test_removes_surrounding_space_tab_only_blank_lines() -> None:
    source = 'def function():\n    """  \n\t\n    Summary.\n      \n    """\n'
    result = format_pdf106(source)

    assert result.new_source == 'def function():\n    """Summary."""\n'
    assert result.fixed_findings[PDF110OneLineDocstring.meta] == 1
    assert not format_pdf106(result.new_source).modified


def test_preserves_same_opening_line_content_whitespace() -> None:
    source = 'def function():\n    """  Summary with leading spaces.\n    """\n'
    result = format_pdf106(source)

    assert result.new_source == 'def function():\n    """  Summary with leading spaces."""\n'
    assert result.fixed_findings[PDF110OneLineDocstring.meta] == 1


def test_collapses_module_docstring_and_preserves_closing_line_suffix() -> None:
    source = '"""\nModule summary.\n"""\n\ndef function():\n    """\n    Summary.\n    """  # retained comment\n'
    result = format_pdf106(source)

    assert result.new_source == '"""Module summary."""\n\ndef function():\n    """Summary."""  # retained comment\n'
    assert result.fixed_findings[PDF110OneLineDocstring.meta] == 2
    assert not format_pdf106(result.new_source).modified


def test_line_length_boundary_includes_complete_source_line() -> None:
    source = 'def function():\n    """\n    Summary.\n    """\n'

    fits = format_pdf106(source, settings=CheckSettings(select=("PDF110",), line_length=len('    """Summary."""')))
    too_long = format_pdf106(source, settings=CheckSettings(select=("PDF110",), line_length=len('    """Summary."""') - 1))

    assert fits.new_source == 'def function():\n    """Summary."""\n'
    assert fits.fixed_findings[PDF110OneLineDocstring.meta] == 1
    assert too_long.new_source == source
    assert not too_long.fixed_findings
    assert not too_long.unfixed_findings


def test_line_length_includes_simple_suite_suffix() -> None:
    source = 'def function(): """\n    Summary.\n    """; return None\n'

    fits = format_pdf106(source, settings=CheckSettings(select=("PDF110",), line_length=len('def function(): """Summary."""; return None')))
    too_long = format_pdf106(source, settings=CheckSettings(select=("PDF110",), line_length=len('def function(): """Summary."""; return None') - 1))

    assert fits.new_source == 'def function(): """Summary."""; return None\n'
    assert fits.fixed_findings[PDF110OneLineDocstring.meta] == 1
    assert too_long.new_source == source
    assert not too_long.fixed_findings


def test_line_length_includes_parenthesized_prefix_and_tab_width() -> None:
    parenthesized = 'class Example:\n    ("""\n    Summary.\n    """)\n'
    tabs = 'def function():\n\t"""\n\tSummary.\n\t"""\n'

    parenthesized_too_long = format_pdf106(parenthesized, settings=CheckSettings(select=("PDF110",), line_length=len('    """Summary."""')))
    tab_width_four = format_pdf106(tabs, settings=CheckSettings(select=("PDF110",), line_length=len('    """Summary."""'), indent_width=4))
    tab_width_eight = format_pdf106(tabs, settings=CheckSettings(select=("PDF110",), line_length=len('    """Summary."""'), indent_width=8))

    assert parenthesized_too_long.new_source == parenthesized
    assert not parenthesized_too_long.fixed_findings
    assert tab_width_four.new_source == 'def function():\n\t"""Summary."""\n'
    assert tab_width_four.fixed_findings[PDF110OneLineDocstring.meta] == 1
    assert tab_width_eight.new_source == tabs
    assert not tab_width_eight.fixed_findings


def test_preserves_raw_prefix_quote_delimiter_nested_async_and_crlf() -> None:
    source = "class Example:\r\n    @decorator\r\n    async def method(self):\r\n        r'''\r\n        Path C:\\\\temp.\r\n        '''\r\n"
    settings = CheckSettings(select=("PDF110",), line_ending=LineEnding.CR_LF)
    result = format_pdf106(source, settings=settings)

    assert result.new_source == "class Example:\r\n    @decorator\r\n    async def method(self):\r\n        r'''Path C:\\\\temp.'''\r\n"
    assert result.fixed_findings[PDF110OneLineDocstring.meta] == 1
    assert not format_pdf106(result.new_source, settings=settings).modified


def test_escapes_quote_collisions_before_using_separator_fallback() -> None:
    source = 'def quoted():\n    """\n    "quoted"\n    """\n\ndef trailing():\n    """\n    trailing "\n    """\n\ndef quote_pair():\n    """\n    ""\n    """\n'
    result = format_pdf106(source)

    assert result.new_source == 'def quoted():\n    """\\"quoted\\""""\n\ndef trailing():\n    """trailing \\""""\n\ndef quote_pair():\n    """\\"\\""""\n'
    assert result.fixed_findings[PDF110OneLineDocstring.meta] == 3
    assert not format_pdf106(result.new_source).modified


def test_uses_separator_fallback_for_raw_backslash_collision() -> None:
    source = 'def raw():\n    r"""\n    Path \\\n    """\n'
    result = format_pdf106(source)

    assert result.new_source == 'def raw():\n    r"""Path \\ """\n'
    assert result.fixed_findings[PDF110OneLineDocstring.meta] == 1
    assert not result.unfixed_findings


def test_skips_docstrings_that_are_not_single_line_summaries() -> None:
    source = (
        'def already():\n    """Summary."""\n\n'
        'def blank():\n    """\n    """\n\n'
        'def body():\n    """Summary.\n\n    Body.\n    """\n\n'
        'def section(value):\n    """Summary.\n\n    Args:\n        value: Description.\n    """\n\n'
        'def wrapped():\n    """Summary line\n    continuation.\n    """\n'
    )
    result = format_pdf106(source, settings=CheckSettings(select=("PDF110",), docstring_convention=DocstringConvention.GOOGLE))

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_disabled_structure_parsing_can_make_structural_line_collapsible() -> None:
    source = 'def function():\n    """\n    - item\n    """\n'

    parsed = format_pdf106(source)
    disabled = format_pdf106(source, settings=CheckSettings(select=("PDF110",), docstring_parse_list_items=False))

    assert parsed.new_source == source
    assert not parsed.fixed_findings
    assert disabled.new_source == 'def function():\n    """- item"""\n'
    assert disabled.fixed_findings[PDF110OneLineDocstring.meta] == 1


@pytest.mark.parametrize(
    ("settings", "content", "expected"),
    [
        (CheckSettings(select=("PDF110",), docstring_parse_headings=False), "# Heading", 'def function():\n    """# Heading"""\n'),
        (CheckSettings(select=("PDF110",), docstring_parse_directives=False), ".. note:: Title", 'def function():\n    """.. note:: Title"""\n'),
        (CheckSettings(select=("PDF110",), docstring_parse_block_quotes=False), "> quote", 'def function():\n    """> quote"""\n'),
        (CheckSettings(select=("PDF110",), docstring_parse_doctests=False, docstring_parse_block_quotes=False), ">>> call()", 'def function():\n    """>>> call()"""\n'),
    ],
)
def test_disabled_single_line_structure_parsing_can_make_structure_collapsible(settings: CheckSettings, content: str, expected: str) -> None:
    source = f'def function():\n    """\n    {content}\n    """\n'

    parsed = format_pdf106(source)
    disabled = format_pdf106(source, settings=settings)

    assert parsed.new_source == source
    assert not parsed.fixed_findings
    assert disabled.new_source == expected
    assert disabled.fixed_findings[PDF110OneLineDocstring.meta] == 1


def test_collapses_multiline_simple_docstring_with_safely_mapped_escape() -> None:
    source = 'def function():\n    """\n    Summary with tab\\t escape.\n    """\n'
    result = format_pdf106(source)

    assert result.new_source == 'def function():\n    """Summary with tab\\t escape."""\n'
    assert result.fixed_findings[PDF110OneLineDocstring.meta] == 1
    assert not result.unfixed_findings


def test_skips_concatenated_escaped_and_non_docstring_strings() -> None:
    source = 'def concatenated():\n    ("Summary.")\n\ndef escaped():\n    """Summary\\n"""\n\ndef not_docstring():\n    value = 1\n    """\n    Summary.\n    """\n'
    result = format_pdf106(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_pdf001_can_reflow_multiline_summary_before_pdf106_collapses_it() -> None:
    source = 'def function():\n    """Summary line\n    continuation line.\n    """\n'
    settings = CheckSettings(select=("PDF101", "PDF110"), line_length=88)
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)

    assert result.new_source == 'def function():\n    """Summary line continuation line."""\n'
    assert result.fixed_findings[PDF101DocstringReflow.meta] == 1
    assert result.fixed_findings[PDF110OneLineDocstring.meta] == 1
    assert not formatter.format_source(result.new_source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True).modified


def test_pdf_family_selection_converges_after_pdf106_collapse() -> None:
    source = 'def function():\n    """\n    Summary.\n    """\n'
    settings = CheckSettings(select=("PDF",), line_length=88)
    selection = rules_selection.select_rules(settings)
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=selection, fix=True)

    assert result.new_source == 'def function():\n    """Summary."""\n'
    second_pass = formatter.format_source(result.new_source, "example.py", settings=settings, rule_selection=selection, fix=True)
    assert result.fixed_findings[PDF110OneLineDocstring.meta] == 1
    assert not second_pass.modified
    assert not result.errors
    assert not second_pass.errors


def test_check_fix_line_numbers_and_fix_false_findings_agree() -> None:
    source = 'def first():\n    """\n    Summary.\n    """\n\ndef second():\n    """Other.\n    """\n'
    _, context = contexts(source)
    findings = rule_helpers.rule_findings(PDF110OneLineDocstring, context)
    fixed = rule_helpers.rule_fix_result(PDF110OneLineDocstring, context)
    check_only = format_pdf106(source, fix=False)

    assert tuple(finding.line_numbers for finding in findings) == ((2, 3, 4), (7, 8))
    assert tuple(finding.line_numbers for finding in fixed.fixed_findings) == ((2, 3, 4), (7, 8))
    assert tuple(finding.line_numbers for finding in check_only.unfixed_findings) == ((2, 3, 4), (7, 8))
    _, fixed_context = contexts(fixed.module.code)
    assert rule_helpers.rule_findings(PDF110OneLineDocstring, fixed_context) == ()


def test_suspicious_unicode_blocks_collapsing_multiline_docstring() -> None:
    source = 'def function():\n    """\n    Summary\u202e.\n    """\n'

    result = format_pdf106(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings
