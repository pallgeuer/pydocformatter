import libcst as cst
import libcst.metadata as cst_metadata
import pytest

import pydocformatter.formatter as formatter
import pydocformatter.rules.definition_helpers.source_text as source_text
import pydocformatter.rules_selection as rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definition import RuleCategoryContext, RuleContext
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.definitions.PDF.PDF305_summary_starts_with_this import PDF305SummaryStartsWithThis


def contexts(source: str, *, settings: CheckSettings | None = None) -> tuple[RuleCategoryContext, RuleContext]:
    """Return matching category and rule contexts for source."""
    module = cst.parse_module(source)
    wrapper = cst_metadata.MetadataWrapper(module, unsafe_skip_copy=True)
    category = RuleCategoryContext(
        path="example.py",
        settings=CheckSettings(select=("PDF305",)) if settings is None else settings,
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
        effectively_fixable=False,
    )


def format_source(source: str, *, settings: CheckSettings | None = None, fix: bool = True) -> formatter.FormatterResult:
    """Format source with supplied settings."""
    resolved_settings = CheckSettings(select=("PDF305",)) if settings is None else settings
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=fix)


@pytest.mark.parametrize("summary", ("This returns value.", "This. Returns value.", '"This" returns value.', "(This) returns value.", "This: returns value.", "`This` returns value."))
def test_reports_summaries_starting_with_this(summary: str) -> None:
    source = f'def function():\n    """{summary}"""\n'
    result = format_source(source)

    assert result.new_source == source
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2,),)
    assert not result.unfixed_findings[0].fixable


@pytest.mark.parametrize("summary", ("this returns value.", "THIS returns value.", "'this' returns value."))
def test_this_detection_is_case_insensitive_after_normalization(summary: str) -> None:
    source = f'def function():\n    """{summary}"""\n'
    result = format_source(source)

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2,),)


@pytest.mark.parametrize("summary", ("This\\treturns value.", "This\nreturns value.", "This\\u00a0returns value."))
def test_reports_this_separated_by_non_space_whitespace(summary: str) -> None:
    source = f'def function():\n    """{summary}"""\n'
    result = format_source(source)

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2,),)


@pytest.mark.parametrize("summary", ("Return this value.", "ThisReturns value.", "this_module value.", "This\\u00e9 returns value."))
def test_does_not_report_other_first_words(summary: str) -> None:
    source = f'def function():\n    """{summary}"""\n'
    result = format_source(source)

    assert not result.unfixed_findings


def test_applies_to_modules_classes_and_functions_but_respects_summary_parsing() -> None:
    source = '"""This module returns value."""\n\nclass Example:\n    """This class returns value."""\n\n\ndef field():\n    """:return: This field returns value"""\n\n\ndef function():\n    """This function returns value."""\n'
    result = format_source(source)

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((1,), (4,), (12,))


def test_recognized_first_blocks_are_not_summary_targets() -> None:
    source = 'def list_item():\n    """- This item"""\n\n\ndef doctest():\n    """>>> This()"""\n\n\ndef fenced():\n    """```python\n    This()\n    ```\n    """\n\n\ndef quote():\n    """> This quote"""\n\n\ndef table():\n    """| This | Value |\n    | --- | --- |\n    """\n\n\ndef directive():\n    """.. note:: This value"""\n\n\ndef literal():\n    """This::\n        value\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.unfixed_findings


def test_disabled_literal_block_parsing_can_make_literal_marker_reportable() -> None:
    source = 'def literal():\n    """This::\n        value\n    """\n'
    protected = format_source(source)
    disabled = format_source(source, settings=CheckSettings(select=("PDF305",), docstring_parse_literal_blocks=False))

    assert not protected.unfixed_findings
    assert tuple(finding.line_numbers for finding in disabled.unfixed_findings) == ((2,),)


def test_underlined_title_style_summary_obeys_heading_parsing_setting() -> None:
    source = 'def function():\n    """This\n    ====\n    """\n'
    protected = format_source(source)
    disabled = format_source(source, settings=CheckSettings(select=("PDF305",), docstring_parse_headings=False))

    assert not protected.unfixed_findings
    assert tuple(finding.line_numbers for finding in disabled.unfixed_findings) == ((2,),)


def test_lone_adornment_summary_has_no_first_word_target() -> None:
    source = 'def function():\n    """===="""\n'
    result = format_source(source, settings=CheckSettings(select=("PDF305",), docstring_parse_headings=False))

    assert result.new_source == source
    assert not result.unfixed_findings


def test_leading_blank_and_adornment_lines_are_not_this_targets() -> None:
    source = 'def function():\n    """\n    ====\n    This returns value.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF305",), docstring_parse_headings=False))

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((4,),)


def test_reports_concatenated_and_escaped_newline_physical_lines() -> None:
    source = 'def concatenated():\n    ("This "\n     "returns value.")\n\n\ndef escaped():\n    """This returns value\\ncontinued."""\n'
    result = format_source(source)

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2, 3), (7,))


@pytest.mark.parametrize("convention", (DocstringConvention.GOOGLE, DocstringConvention.PEP257))
def test_google_and_pep257_conventions_ignore_broad_selection_but_exact_selection_still_applies(convention: DocstringConvention) -> None:
    broad = rules_selection.select_rules(CheckSettings(select=("PDF3",), docstring_convention=convention))
    active_codes = tuple(rule.rule.code.tag for rule in broad.rules)

    assert "PDF305" not in active_codes

    exact = format_source('def function():\n    """This returns value."""\n', settings=CheckSettings(select=("PDF305",), docstring_convention=convention))

    assert tuple(finding.line_numbers for finding in exact.unfixed_findings) == ((2,),)


def test_check_and_fix_false_findings_agree() -> None:
    source = 'def function():\n    """This returns value."""\n'
    _, context = contexts(source)
    findings = PDF305SummaryStartsWithThis.check(context)
    fixed = PDF305SummaryStartsWithThis.fix(context)
    check_only = format_source(source, fix=False)

    assert tuple(finding.line_numbers for finding in findings) == ((2,),)
    assert fixed.module.code == source
    assert not fixed.fixed_findings
    assert tuple(finding.line_numbers for finding in check_only.unfixed_findings) == ((2,),)
