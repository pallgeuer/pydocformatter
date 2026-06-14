import libcst as cst
import libcst.metadata as cst_metadata
import pytest

import pydocformatter.formatter as formatter
import pydocformatter.rules_selection as rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definition import RuleCategoryContext, RuleContext
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.definitions.PDF.PDF001_reflow_required import PDF001ReflowRequired
from pydocformatter.rules.definitions.PDF.PDF101_missing_blank_line import PDF101MissingBlankLine
from pydocformatter.rules.definitions.PDF.PDF107_summary_too_long import PDF107SummaryTooLong


def contexts(source: str, *, settings: CheckSettings | None = None) -> tuple[RuleCategoryContext, RuleContext]:
    """Return matching category and rule contexts for source."""
    module = cst.parse_module(source)
    wrapper = cst_metadata.MetadataWrapper(module, unsafe_skip_copy=True)
    category = RuleCategoryContext(
        path="example.py",
        settings=CheckSettings(select=("PDF107",)) if settings is None else settings,
        module=module,
        metadata_wrapper=wrapper,
        positions=wrapper.resolve(cst_metadata.PositionProvider),
        line_ending="\r\n" if "\r\n" in source else "\n",
    )
    return category, RuleContext(**category.__dict__, category_data=PDF.prepare(category), effectively_fixable=False)


def format_source(source: str, *, settings: CheckSettings | None = None, fix: bool = True) -> formatter.FormatterResult:
    """Format source with supplied settings."""
    resolved_settings = CheckSettings(select=("PDF107",)) if settings is None else settings
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=fix)


def test_reports_multiline_summary_without_changing_source() -> None:
    source = 'def function():\n    """Summary line\n    continuation line.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2, 3),)
    assert not result.unfixed_findings[0].fixable


def test_pdf001_can_reflow_short_multiline_summary_before_pdf107_checks() -> None:
    source = 'def function():\n    """Summary line\n    continuation line.\n    """\n'
    settings = CheckSettings(select=("PDF001", "PDF107"), line_length=88)
    result = format_source(source, settings=settings)

    assert result.new_source == 'def function():\n    """Summary line continuation line.\n    """\n'
    assert result.fixed_findings[PDF001ReflowRequired.meta] == 1
    assert not result.unfixed_findings


def test_pdf107_reports_summary_that_remains_multiline_after_reflow() -> None:
    source = 'def function():\n    """supercalifragilisticexpialidocious\n    words after it.\n    """\n'
    settings = CheckSettings(select=("PDF001", "PDF107"), line_length=28)
    result = format_source(source, settings=settings)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2, 3),)
    assert result.unfixed_findings[0].rule == PDF107SummaryTooLong.meta


def test_does_not_report_one_line_summary_body_or_recognized_structures() -> None:
    source = (
        'def body():\n    """Summary.\n\n    Body.\n    """\n\n'
        'def section(value):\n    """Summary.\n\n    Args:\n        value: Description.\n    """\n\n'
        'def list_item():\n    """Summary.\n\n    - item\n    """\n'
    )
    result = format_source(source, settings=CheckSettings(select=("PDF107",), docstring_convention=DocstringConvention.GOOGLE))

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_does_not_report_multiline_paragraph_or_section_entry_after_summary() -> None:
    source = (
        'def paragraph():\n    """Summary.\n\n    Body line one\n    body line two.\n    """\n\n'
        'def section(value):\n    """Summary.\n\n    Args:\n        value: Description line one\n            continuation line.\n    """\n'
    )
    result = format_source(source, settings=CheckSettings(select=("PDF107",), docstring_convention=DocstringConvention.GOOGLE))

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_reports_ambiguous_missing_blank_line_prose() -> None:
    source = 'def function():\n    """Summary.\n    Body might be a continued summary.\n    """\n'
    result = format_source(source)

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2, 3),)


def test_pdf101_can_separate_recognized_structure_before_pdf107_checks() -> None:
    source = 'def function():\n    """Summary.\n    - item\n    """\n'
    settings = CheckSettings(select=("PDF101", "PDF107"))
    result = format_source(source, settings=settings)

    assert result.new_source == 'def function():\n    """Summary.\n\n    - item\n    """\n'
    assert result.fixed_findings[PDF101MissingBlankLine.meta] == 1
    assert not result.unfixed_findings


def test_disabled_structure_parsing_can_make_structure_text_reportable() -> None:
    source = 'def function():\n    """Summary.\n    - item\n    """\n'
    settings = CheckSettings(select=("PDF101", "PDF107"), docstring_parse_list_items=False)
    result = format_source(source, settings=settings)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2, 3),)


def test_disabled_code_fence_parsing_can_make_fence_text_reportable() -> None:
    source = 'def function():\n    """```python\n    print(value)\n    ```\n    """\n'
    parsed = format_source(source)
    disabled = format_source(source, settings=CheckSettings(select=("PDF107",), docstring_parse_code_fences=False, docstring_parse_headings=False))

    assert parsed.new_source == source
    assert not parsed.unfixed_findings
    assert disabled.new_source == source
    assert tuple(finding.line_numbers for finding in disabled.unfixed_findings) == ((2, 3, 4),)


@pytest.mark.parametrize(
    ("settings", "content", "expected_lines"),
    (
        (CheckSettings(select=("PDF107",), docstring_parse_headings=False), "# Heading\n    Continuation.", (2, 3)),
        (CheckSettings(select=("PDF107",), docstring_parse_directives=False), ".. note:: Title\n    Continuation.", (2, 3)),
        (CheckSettings(select=("PDF107",), docstring_parse_sphinx_fields=False), ":param value: Description.\n    Continuation.", (2, 3)),
        (CheckSettings(select=("PDF107",), docstring_parse_list_items=False), "- item\n    Continuation.", (2, 3)),
        (CheckSettings(select=("PDF107",), docstring_parse_block_quotes=False), "> quote\n    > continuation", (2, 3)),
        (CheckSettings(select=("PDF107",), docstring_parse_tables=False), "| A | B |\n    | --- | --- |\n    | 1 | 2 |", (2, 3, 4)),
        (CheckSettings(select=("PDF107",), docstring_parse_doctests=False, docstring_parse_block_quotes=False), ">>> call()\n    result", (2, 3)),
    ),
)
def test_disabled_structure_parsing_can_make_first_block_reportable(settings: CheckSettings, content: str, expected_lines: tuple[int, ...]) -> None:
    source = f'def function():\n    """{content}\n    """\n'

    parsed = format_source(source)
    disabled = format_source(source, settings=settings)

    assert parsed.new_source == source
    assert not parsed.unfixed_findings
    assert disabled.new_source == source
    assert tuple(finding.line_numbers for finding in disabled.unfixed_findings) == (expected_lines,)
    assert not disabled.unfixed_findings[0].fixable


def test_reports_concatenated_and_escaped_newline_summary_physical_lines() -> None:
    source = 'def concatenated():\n    ("Summary line\\n"\n     "continuation line.")\n\ndef escaped():\n    """Summary line\\ncontinuation line."""\n'
    result = format_source(source)

    assert result.new_source == source
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2, 3), (6,))


def test_reports_ambiguous_escaped_body_docstring_summary_physical_lines() -> None:
    source = 'def function():\n    """Summary line\n    continuation.\n\n    Body with tab\\t escape here.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2, 3),)


def test_check_and_fix_false_findings_agree() -> None:
    source = 'def function():\n    """Summary line\n    continuation line.\n    """\n'
    _, context = contexts(source)
    findings = PDF107SummaryTooLong.check(context)
    check_only = format_source(source, fix=False)
    fix_enabled = format_source(source, fix=True)

    assert tuple(finding.line_numbers for finding in findings) == ((2, 3),)
    assert tuple(finding.line_numbers for finding in check_only.unfixed_findings) == ((2, 3),)
    assert tuple(finding.line_numbers for finding in fix_enabled.unfixed_findings) == ((2, 3),)
    assert check_only.new_source == source
    assert fix_enabled.new_source == source
