import libcst as cst
import libcst.metadata as cst_metadata

import pydocformatter.formatter as formatter
import pydocformatter.rules_selection as rules_selection
from pydocformatter.cli.settings_check import CheckSettings, LineEnding
from pydocformatter.rules.definition import RuleCategoryContext, RuleContext
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.definitions.PDF.PDF106_multiline_opening_quotes_same_line import PDF106MultilineOpeningQuotesSameLine
from pydocformatter.rules.definitions.PDF.PDF108_multiline_closing_quotes_same_line import PDF108MultilineClosingQuotesSameLine


def contexts(source: str, *, settings: CheckSettings | None = None) -> tuple[RuleCategoryContext, RuleContext]:
    """Return matching category and rule contexts for source."""
    module = cst.parse_module(source)
    wrapper = cst_metadata.MetadataWrapper(module, unsafe_skip_copy=True)
    category = RuleCategoryContext(
        path="example.py",
        settings=CheckSettings(select=("PDF108",)) if settings is None else settings,
        module=module,
        metadata_wrapper=wrapper,
        positions=wrapper.resolve(cst_metadata.PositionProvider),
        line_ending="\r\n" if "\r\n" in source else "\n",
    )
    return category, RuleContext(**category.__dict__, category_data=PDF.prepare(category), effectively_fixable=True)


def format_pdf104(source: str, *, settings: CheckSettings | None = None, fix: bool = True) -> formatter.FormatterResult:
    """Format source with PDF108 selected."""
    resolved_settings = CheckSettings(select=("PDF108",)) if settings is None else settings
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=fix)


def test_moves_closing_quotes_onto_final_content_line() -> None:
    source = 'def function():\n    """Summary.\n\n    Body.\n    """\n'
    result = format_pdf104(source)

    assert result.new_source == 'def function():\n    """Summary.\n\n    Body."""\n'
    assert result.fixed_findings[PDF108MultilineClosingQuotesSameLine.meta] == 1
    assert not format_pdf104(result.new_source).modified


def test_removes_multiple_trailing_space_tab_only_lines_before_closing_quotes() -> None:
    source = 'def function():\n    """Summary.\n\n    Body.\n      \n\t\n    """\n'
    result = format_pdf104(source)

    assert result.new_source == 'def function():\n    """Summary.\n\n    Body."""\n'
    assert result.fixed_findings[PDF108MultilineClosingQuotesSameLine.meta] == 1
    assert not format_pdf104(result.new_source).modified


def test_non_space_tab_whitespace_is_content_when_choosing_final_line() -> None:
    source = 'def function():\n    """Summary.\n\n    \xa0\n    """\n'
    result = format_pdf104(source)

    assert result.new_source == 'def function():\n    """Summary.\n\n    \xa0"""\n'
    assert result.fixed_findings[PDF108MultilineClosingQuotesSameLine.meta] == 1
    assert not format_pdf104(result.new_source).modified


def test_moves_closing_quotes_onto_single_content_line() -> None:
    source = 'def function():\n    """Summary.\n    """\n'
    result = format_pdf104(source)

    assert result.new_source == 'def function():\n    """Summary."""\n'
    assert result.fixed_findings[PDF108MultilineClosingQuotesSameLine.meta] == 1
    assert not format_pdf104(result.new_source).modified


def test_moves_bare_closing_quotes_after_single_content_line() -> None:
    source = '"""Summary.\n"""\n'
    result = format_pdf104(source)

    assert result.new_source == '"""Summary."""\n'
    assert result.fixed_findings[PDF108MultilineClosingQuotesSameLine.meta] == 1
    assert not format_pdf104(result.new_source).modified


def test_preserves_first_line_content_whitespace_when_moving_closing_quotes() -> None:
    source = 'def function():\n    """  Summary with leading spaces.\n    More content.\n    """\n'
    result = format_pdf104(source)

    assert result.new_source == 'def function():\n    """  Summary with leading spaces.\n    More content."""\n'
    assert result.fixed_findings[PDF108MultilineClosingQuotesSameLine.meta] == 1


def test_leaves_already_same_line_and_single_physical_line_docstrings() -> None:
    source = 'def same():\n    """Summary.\n\n    Body."""\n\ndef one_line():\n    """Summary."""\n'
    result = format_pdf104(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_removes_trailing_evaluated_newline_before_closing_quotes() -> None:
    source = '"""Summary.\nBody.\n"""\n'
    result = format_pdf104(source)

    assert result.new_source == '"""Summary.\nBody."""\n'
    assert result.fixed_findings[PDF108MultilineClosingQuotesSameLine.meta] == 1
    assert not format_pdf104(result.new_source).modified


def test_moves_simple_suite_closing_quotes_without_moving_following_statements() -> None:
    source = 'def function(): """Summary.\nBody.\n"""; return None\n'
    result = format_pdf104(source)

    assert result.new_source == 'def function(): """Summary.\nBody."""; return None\n'
    assert result.fixed_findings[PDF108MultilineClosingQuotesSameLine.meta] == 1
    assert not format_pdf104(result.new_source).modified


def test_preserves_internal_blank_lines_raw_prefix_quote_delimiter_and_crlf() -> None:
    source = "def function():\r\n    r'''Summary with path C:\\\\temp.\r\n\r\n    Body.\r\n    '''\r\n"
    settings = CheckSettings(select=("PDF108",), line_ending=LineEnding.CR_LF)
    result = format_pdf104(source, settings=settings)

    assert result.new_source == "def function():\r\n    r'''Summary with path C:\\\\temp.\r\n\r\n    Body.'''\r\n"
    assert result.fixed_findings[PDF108MultilineClosingQuotesSameLine.meta] == 1
    assert not format_pdf104(result.new_source, settings=settings).modified


def test_escapes_quote_collision_before_same_line_closing_quotes() -> None:
    source = 'def quote_one():\n    """Summary.\n\n    Body "\n    """\n\ndef quote_two():\n    """Summary.\n\n    Body ""\n    """\n\ndef raw_backslash():\n    r"""Summary.\n\n    Path \\\n    """\n'
    result = format_pdf104(source)

    assert (
        result.new_source
        == 'def quote_one():\n    """Summary.\n\n    Body \\""""\n\ndef quote_two():\n    """Summary.\n\n    Body \\"\\""""\n\ndef raw_backslash():\n    r"""Summary.\n\n    Path \\ """\n'
    )
    assert result.fixed_findings[PDF108MultilineClosingQuotesSameLine.meta] == 3
    assert not result.unfixed_findings
    assert not format_pdf104(result.new_source).modified


def test_skips_multiline_docstring_with_non_raw_escape_source_mapping() -> None:
    source = 'def function():\n    """Summary.\n\n    Body\\t.\n    """\n'
    result = format_pdf104(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_check_fix_line_numbers_and_fix_false_findings_agree() -> None:
    source = 'def first():\n    """Summary.\n\n    Body.\n    """\n\ndef second():\n    """Other.\n\n    Body.\n      """\n'
    _, context = contexts(source)
    findings = PDF108MultilineClosingQuotesSameLine.check(context)
    fixed = PDF108MultilineClosingQuotesSameLine.fix(context)
    check_only = format_pdf104(source, fix=False)

    assert tuple(finding.line_numbers for finding in findings) == ((4, 5), (10, 11))
    assert tuple(finding.line_numbers for finding in fixed.fixed_findings) == ((4, 5), (10, 11))
    assert tuple(finding.line_numbers for finding in check_only.unfixed_findings) == ((4, 5), (10, 11))
    _, fixed_context = contexts(fixed.module.code)
    assert PDF108MultilineClosingQuotesSameLine.check(fixed_context) == ()


def test_skips_concatenated_escaped_and_non_docstring_strings() -> None:
    source = (
        'def concatenated():\n    ("Summary.\\n"\n     "Body.\\n")\n\ndef escaped():\n    """Summary.\\nBody.\\n"""\n\ndef not_docstring():\n    value = 1\n    """Summary.\n\n    Body.\n    """\n'
    )
    result = format_pdf104(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_pdf000_can_literalize_escaped_newline_before_pdf104_moves_quotes() -> None:
    source = 'def function():\n    """Summary.\\nBody.\\n"""\n'
    settings = CheckSettings(select=("PDF000", "PDF108"))
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)

    assert result.new_source == 'def function():\n    """Summary.\nBody."""\n'
    assert result.fixed_findings[PDF108MultilineClosingQuotesSameLine.meta] == 1


def test_pdf102_and_pdf104_normalize_compact_opt_in_pair_together() -> None:
    source = 'def function():\n    """\n    Summary.\n\n    Body.\n    """\n'
    settings = CheckSettings(select=("PDF106", "PDF108"))
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)

    assert result.new_source == 'def function():\n    """Summary.\n\n    Body."""\n'
    assert result.fixed_findings[PDF106MultilineOpeningQuotesSameLine.meta] == 1
    assert result.fixed_findings[PDF108MultilineClosingQuotesSameLine.meta] == 1
    assert not formatter.format_source(result.new_source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True).modified
