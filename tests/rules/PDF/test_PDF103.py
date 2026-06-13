import libcst as cst
import libcst.metadata as cst_metadata

import pydocformatter.formatter as formatter
import pydocformatter.rules_selection as rules_selection
from pydocformatter.cli.settings_check import CheckSettings, IndentStyle, LineEnding
from pydocformatter.rules.definition import RuleCategoryContext, RuleContext
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.definitions.PDF.PDF103_multiline_opening_quotes_sep_line import PDF103MultilineOpeningQuotesSepLine
from pydocformatter.rules.definitions.PDF.PDF105_multiline_closing_quotes_sep_line import PDF105MultilineClosingQuotesSepLine


def contexts(source: str, *, settings: CheckSettings | None = None) -> tuple[RuleCategoryContext, RuleContext]:
    """Return matching category and rule contexts for source."""
    module = cst.parse_module(source)
    wrapper = cst_metadata.MetadataWrapper(module, unsafe_skip_copy=True)
    category = RuleCategoryContext(
        path="example.py",
        settings=CheckSettings(select=("PDF103",)) if settings is None else settings,
        module=module,
        metadata_wrapper=wrapper,
        positions=wrapper.resolve(cst_metadata.PositionProvider),
        line_ending="\r\n" if "\r\n" in source else "\n",
    )
    return category, RuleContext(**category.__dict__, category_data=PDF.prepare(category), effectively_fixable=True)


def format_pdf103(source: str, *, settings: CheckSettings | None = None, fix: bool = True) -> formatter.FormatterResult:
    """Format source with PDF103 selected."""
    resolved_settings = CheckSettings(select=("PDF103",)) if settings is None else settings
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=fix)


def test_moves_first_content_line_below_opening_quotes() -> None:
    source = 'def function():\n    """Summary.\n\n    Body.\n    """\n'
    result = format_pdf103(source)

    assert result.new_source == 'def function():\n    """\n    Summary.\n\n    Body.\n    """\n'
    assert result.fixed_findings[PDF103MultilineOpeningQuotesSepLine.meta] == 1
    assert not format_pdf103(result.new_source).modified


def test_strips_quote_adjacent_space_tabs_from_moved_first_line() -> None:
    source = 'def function():\n    """ \t Summary.\n\n    Body.\n    """\n'
    result = format_pdf103(source)

    assert result.new_source == 'def function():\n    """\n    Summary.\n\n    Body.\n    """\n'
    assert result.fixed_findings[PDF103MultilineOpeningQuotesSepLine.meta] == 1
    assert not format_pdf103(result.new_source).modified


def test_preserves_quote_adjacent_non_space_tab_whitespace_on_moved_first_line() -> None:
    source = 'def function():\n    """\xa0Summary.\n\n    Body.\n    """\n'
    result = format_pdf103(source)

    assert result.new_source == 'def function():\n    """\n    \xa0Summary.\n\n    Body.\n    """\n'
    assert result.fixed_findings[PDF103MultilineOpeningQuotesSepLine.meta] == 1
    assert not format_pdf103(result.new_source).modified


def test_moves_single_content_line_below_opening_quotes() -> None:
    source = 'def function():\n    """Summary.\n    """\n'
    result = format_pdf103(source)

    assert result.new_source == 'def function():\n    """\n    Summary.\n    """\n'
    assert result.fixed_findings[PDF103MultilineOpeningQuotesSepLine.meta] == 1
    assert not format_pdf103(result.new_source).modified


def test_leaves_already_separate_and_single_physical_line_docstrings() -> None:
    source = 'def separate():\n    """\n    Summary.\n\n    Body.\n    """\n\ndef one_line():\n    """Summary."""\n'
    result = format_pdf103(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_parenthesized_and_simple_suite_docstrings_use_canonical_margin() -> None:
    source = 'class Parenthesized:\n    (\n        """Class.\n\n        Body.\n        """\n    )\n\ndef simple(): """Summary.\nBody.\n"""; return None\n'
    result = format_pdf103(source, settings=CheckSettings(select=("PDF103",), indent_width=2))

    assert result.new_source == 'class Parenthesized:\n    (\n        """\n        Class.\n\n        Body.\n        """\n    )\n\ndef simple(): """\n  Summary.\nBody.\n"""; return None\n'
    assert result.fixed_findings[PDF103MultilineOpeningQuotesSepLine.meta] == 2
    assert not format_pdf103(result.new_source, settings=CheckSettings(select=("PDF103",), indent_width=2)).modified


def test_tab_simple_suite_uses_configured_tab_margin() -> None:
    source = 'def function(): """Summary.\nBody.\n"""\n'
    settings = CheckSettings(select=("PDF103",), indent_style=IndentStyle.TAB)
    result = format_pdf103(source, settings=settings)

    assert result.new_source == 'def function(): """\n\tSummary.\nBody.\n"""\n'
    assert result.fixed_findings[PDF103MultilineOpeningQuotesSepLine.meta] == 1


def test_preserves_crlf_for_generated_opening_separator() -> None:
    source = 'def function():\r\n    """Summary.\r\n\r\n    Body.\r\n    """\r\n'
    settings = CheckSettings(select=("PDF103",), line_ending=LineEnding.CR_LF)
    result = format_pdf103(source, settings=settings)

    assert result.new_source == 'def function():\r\n    """\r\n    Summary.\r\n\r\n    Body.\r\n    """\r\n'
    assert result.fixed_findings[PDF103MultilineOpeningQuotesSepLine.meta] == 1
    assert not format_pdf103(result.new_source, settings=settings).modified


def test_check_fix_line_numbers_and_fix_false_findings_agree() -> None:
    source = 'def first():\n    """Summary.\n\n    Body.\n    """\n\ndef second():\n    """  Other.\n\n    Body.\n    """\n'
    _, context = contexts(source)
    findings = PDF103MultilineOpeningQuotesSepLine.check(context)
    fixed = PDF103MultilineOpeningQuotesSepLine.fix(context)
    check_only = format_pdf103(source, fix=False)

    assert tuple(finding.line_numbers for finding in findings) == ((2,), (8,))
    assert tuple(finding.line_numbers for finding in fixed.fixed_findings) == ((2,), (8,))
    assert tuple(finding.line_numbers for finding in check_only.unfixed_findings) == ((2,), (8,))
    _, fixed_context = contexts(fixed.module.code)
    assert PDF103MultilineOpeningQuotesSepLine.check(fixed_context) == ()


def test_preserves_raw_prefix_quote_delimiter_and_skips_unsafe_shapes() -> None:
    source = "def raw():\n    r'''Path C:\\\\temp.\n    Body.'''\n\ndef escaped():\n    '''Summary.\\nBody.'''\n\ndef concatenated():\n    ('Summary.\\n'\n     'Body.')\n"
    result = format_pdf103(source)

    assert result.new_source == "def raw():\n    r'''\n    Path C:\\\\temp.\n    Body.'''\n\ndef escaped():\n    '''Summary.\\nBody.'''\n\ndef concatenated():\n    ('Summary.\\n'\n     'Body.')\n"
    assert result.fixed_findings[PDF103MultilineOpeningQuotesSepLine.meta] == 1


def test_pdf103_and_pdf104_normalize_compact_opt_in_pair_together() -> None:
    source = 'def function():\n    """Summary.\n\n    Body.\n    """\n'
    settings = CheckSettings(select=("PDF103", "PDF104"))
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)

    assert result.new_source == 'def function():\n    """\n    Summary.\n\n    Body."""\n'
    assert result.fixed_findings[PDF103MultilineOpeningQuotesSepLine.meta] == 1
    assert not formatter.format_source(result.new_source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True).modified


def test_pdf103_and_pdf105_normalize_expanded_opt_in_pair_together() -> None:
    source = 'def function():\n    """Summary.\n\n    Body."""\n'
    settings = CheckSettings(select=("PDF103", "PDF105"))
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)

    assert result.new_source == 'def function():\n    """\n    Summary.\n\n    Body.\n    """\n'
    assert result.fixed_findings[PDF103MultilineOpeningQuotesSepLine.meta] == 1
    assert result.fixed_findings[PDF105MultilineClosingQuotesSepLine.meta] == 1
    assert not formatter.format_source(result.new_source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True).modified


def test_pdf103_and_pdf105_leave_single_physical_line_docstring_unchanged() -> None:
    source = 'def function():\n    """Summary."""\n'
    settings = CheckSettings(select=("PDF103", "PDF105"))
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings
