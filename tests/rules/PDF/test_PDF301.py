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
from pydocformatter.rules.definitions.PDF.PDF301_summary_terminal_punctuation import PDF301SummaryTerminalPunctuation
from pydocformatter.source_path import SourcePathContext
from tests import rule_helpers


def contexts(source: str, *, settings: CheckSettings | None = None) -> tuple[RuleCategoryContext, RuleContext]:
    """Return matching category and rule contexts for source."""
    module = cst.parse_module(source)
    wrapper = cst_metadata.MetadataWrapper(module, unsafe_skip_copy=True)
    category = RuleCategoryContext(
        path="example.py",
        source_path=SourcePathContext.for_path("example.py"),
        settings=CheckSettings(select=("PDF301",)) if settings is None else settings,
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


def format_source(source: str, *, settings: CheckSettings | None = None, fix: bool = True) -> formatter.FormatterResult:
    """Format source with supplied settings."""
    resolved_settings = CheckSettings(select=("PDF301",)) if settings is None else settings
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=fix)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ('def function():\n    """Return value"""\n', 'def function():\n    """Return value."""\n'),
        ("def function():\n    '''Return value'''\n", "def function():\n    '''Return value.'''\n"),
        ('def function(): """Return value"""\n', 'def function(): """Return value."""\n'),
        ('def function():\n    r"""Return \\d+ values"""\n', 'def function():\n    r"""Return \\d+ values."""\n'),
        ('def function():\n    """Return value   """\n', 'def function():\n    """Return value.   """\n'),
        ('def function():\n    """Return value\n    continued\n    """\n', 'def function():\n    """Return value\n    continued.\n    """\n'),
        ('def function():\n    """\n    Return value\n    """\n', 'def function():\n    """\n    Return value.\n    """\n'),
    ],
)
def test_inserts_period_for_safe_missing_terminal_punctuation(source: str, expected: str) -> None:
    result = format_source(source)

    assert result.new_source == expected
    assert result.fixed_findings[PDF301SummaryTerminalPunctuation.meta] == 1
    assert not result.unfixed_findings
    assert result.new_source is not None
    assert not format_source(result.new_source).modified


def test_inserts_terminal_punctuation_for_attribute_docstring_summary() -> None:
    source = 'value = 1\n"""summary without punctuation"""\n'
    result = format_source(source)

    assert result.new_source == 'value = 1\n"""summary without punctuation."""\n'
    assert result.fixed_findings[PDF301SummaryTerminalPunctuation.meta] == 1
    assert not result.unfixed_findings
    assert not format_source(result.new_source).modified


@pytest.mark.parametrize("punctuation", [".", "?", "!"])
def test_accepts_existing_terminal_punctuation(punctuation: str) -> None:
    source = f'def function():\n    """Return value{punctuation}"""\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


@pytest.mark.parametrize("punctuation", [",", ";"])
def test_replaces_comma_and_semicolon_with_period(punctuation: str) -> None:
    source = f'def function():\n    """Return value{punctuation}"""\n'
    result = format_source(source)

    assert result.new_source == 'def function():\n    """Return value."""\n'
    assert result.fixed_findings[PDF301SummaryTerminalPunctuation.meta] == 1
    assert not result.unfixed_findings
    assert not format_source(result.new_source).modified


@pytest.mark.parametrize(
    "structured_content",
    [
        "    - red\n    - blue",
        "    ```text\n    red\n    ```",
        "    >>> choose()",
        "    .. note::\n        red",
        "    .. warning:\n        red",
        "    Example::\n\n        red",
        "    | Color | Value |\n    | --- | --- |\n    | red | 1 |",
        "    Colors\n    ------",
        "    > red",
        "    Colors:\n    red",
        "        raw text",
    ],
)
def test_reports_comma_before_every_structured_content_kind_without_fixing(structured_content: str) -> None:
    """Keep a comma that may introduce recognized structured content."""
    source = f'def function():\n    """Choose one,\n\n{structured_content}\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2,),)
    assert not result.unfixed_findings[0].fixable


def test_fixes_comma_before_convention_section() -> None:
    """Treat a following convention section as independent from the summary."""
    source = 'def function(value):\n    """Return value,\n\n    Args:\n        value: Input value.\n    """\n'
    settings = CheckSettings(select=("PDF301",), docstring_convention=DocstringConvention.GOOGLE)
    result = format_source(source, settings=settings)

    assert result.new_source == source.replace("Return value,", "Return value.")
    assert result.fixed_findings[PDF301SummaryTerminalPunctuation.meta] == 1
    assert not result.unfixed_findings


def test_disabled_structure_parser_allows_comma_fix() -> None:
    """Guard commas only when the following syntax is parsed as structure."""
    source = 'def function():\n    """Choose one,\n\n    - red\n    - blue\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF301",), docstring_parse_list_items=False))

    assert result.new_source == source.replace("Choose one,", "Choose one.")
    assert result.fixed_findings[PDF301SummaryTerminalPunctuation.meta] == 1
    assert not result.unfixed_findings


def test_replacement_preserves_raw_prefix_trailing_whitespace_and_crlf_line_endings() -> None:
    source = 'def function():\r\n    r"""Return \\d+ values; \t"""\r\n'
    settings = CheckSettings(select=("PDF301",), line_ending=LineEnding.CR_LF)
    result = format_source(source, settings=settings)

    assert result.new_source == 'def function():\r\n    r"""Return \\d+ values. \t"""\r\n'
    assert result.fixed_findings[PDF301SummaryTerminalPunctuation.meta] == 1
    assert not result.unfixed_findings
    assert not format_source(result.new_source, settings=settings).modified


def test_reports_but_does_not_fix_final_colon() -> None:
    source = 'def function():\n    """Return value:"""\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2,),)
    assert [finding.fixable for finding in result.unfixed_findings] == [False]


def test_reports_escaped_semicolon_as_nonfixable() -> None:
    source = 'def function():\n    """Return value\\x3b"""\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2,),)
    assert not result.unfixed_findings[0].fixable


def test_summary_punctuation_rules_are_incompatible() -> None:
    settings = CheckSettings(select=("PDF300", "PDF301"))
    selection = rules_selection.select_rules(settings)

    assert tuple(rule.rule.code.tag for rule in selection.rules) == ("PDF300",)
    assert selection.errors == ("Selected rule PDF301 is incompatible with earlier selected rule PDF300; PDF301 has been disabled",)


def test_skips_empty_sections_fields_and_backslash_ending_targets() -> None:
    source = 'def empty():\n    """"""\n\n\ndef section():\n    """Args:\n        value: Description\n    """\n\n\ndef field():\n    """:param value: Description."""\n\n\ndef backslash():\n    """Path C:\\\\\\\\"""\n'
    result = format_source(source, settings=CheckSettings(select=("PDF301",), docstring_convention=DocstringConvention.GOOGLE))

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_skips_rest_fields_under_rest_convention() -> None:
    source = 'def field():\n    """:param value: Description"""\n'
    result = format_source(source, settings=CheckSettings(select=("PDF301",), docstring_convention=DocstringConvention.REST))

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_skips_numpy_section_only_docstring() -> None:
    source = 'def function(value):\n    """Parameters\n    ----------\n    value : int\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF301",), docstring_convention=DocstringConvention.NUMPY))

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


@pytest.mark.parametrize("summary", ["Parameters", "Extended summary"])
def test_google_convention_punctuates_numpy_only_section_names_as_summaries(summary: str) -> None:
    source = f'def function():\n    """{summary}"""\n'
    result = format_source(source, settings=CheckSettings(select=("PDF301",), docstring_convention=DocstringConvention.GOOGLE))

    assert result.new_source == f'def function():\n    """{summary}."""\n'
    assert result.fixed_findings[PDF301SummaryTerminalPunctuation.meta] == 1


def test_default_convention_punctuates_section_name_as_summary() -> None:
    source = 'def function():\n    """Returns"""\n'
    result = format_source(source)

    assert result.new_source == 'def function():\n    """Returns."""\n'
    assert result.fixed_findings[PDF301SummaryTerminalPunctuation.meta] == 1


def test_numpy_convention_skips_parser_recognized_bare_section_header() -> None:
    source = 'def function():\n    """Returns"""\n'
    result = format_source(source, settings=CheckSettings(select=("PDF301",), docstring_convention=DocstringConvention.NUMPY))

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_first_atx_heading_is_protected_unless_heading_parsing_is_disabled() -> None:
    source = 'def function():\n    """# Heading"""\n'
    protected = format_source(source)
    unprotected = format_source(source, settings=CheckSettings(select=("PDF301",), docstring_parse_headings=False))

    assert protected.new_source == source
    assert not protected.fixed_findings
    assert not protected.unfixed_findings
    assert unprotected.new_source == 'def function():\n    """# Heading."""\n'
    assert unprotected.fixed_findings[PDF301SummaryTerminalPunctuation.meta] == 1


def test_underlined_title_style_summary_obeys_heading_parsing_setting() -> None:
    source = 'def function():\n    """Title\n    =====\n    """\n'
    default = format_source(source)
    disabled = format_source(source, settings=CheckSettings(select=("PDF301",), docstring_parse_headings=False))

    assert default.new_source == source
    assert disabled.new_source == 'def function():\n    """Title.\n    =====\n    """\n'
    assert not default.fixed_findings
    assert disabled.fixed_findings[PDF301SummaryTerminalPunctuation.meta] == 1
    assert not default.unfixed_findings
    assert not disabled.unfixed_findings


def test_disabled_heading_parsing_punctuates_final_content_line_before_trailing_adornment() -> None:
    source = 'def function():\n    """Title\n    detail\n    =====\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF301",), docstring_parse_headings=False))

    assert result.new_source == 'def function():\n    """Title\n    detail.\n    =====\n    """\n'
    assert result.fixed_findings[PDF301SummaryTerminalPunctuation.meta] == 1
    assert not result.unfixed_findings


def test_rest_field_skip_requires_actual_field_marker() -> None:
    source = 'def field():\n    """:return: Description"""\n\n\ndef prose():\n    """:returning value"""\n'
    result = format_source(source, settings=CheckSettings(select=("PDF301",), docstring_convention=DocstringConvention.REST))

    assert result.new_source == 'def field():\n    """:return: Description"""\n\n\ndef prose():\n    """:returning value."""\n'
    assert result.fixed_findings[PDF301SummaryTerminalPunctuation.meta] == 1


def test_rest_like_summary_is_punctuated_when_field_marker_is_invalid_or_convention_is_inactive() -> None:
    source = 'def malformed():\n    """:param x"""\n\n\ndef inactive():\n    """:param x: value"""\n'
    result = format_source(source, settings=CheckSettings(select=("PDF301",), docstring_convention=DocstringConvention.NONE))

    assert result.new_source == 'def malformed():\n    """:param x."""\n\n\ndef inactive():\n    """:param x: value."""\n'
    assert result.fixed_findings[PDF301SummaryTerminalPunctuation.meta] == 2


@pytest.mark.parametrize("adornment", ["===", "---"])
def test_lone_adornment_line_is_not_punctuated(adornment: str) -> None:
    source = f'def function():\n    """{adornment}"""\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_unicode_ellipsis_is_accepted_as_terminal_punctuation() -> None:
    ellipsis = "\u2026"
    sources = ('def function():\n    """Done\\u2026"""\n', f'def function():\n    """Done{ellipsis}"""\n')

    for source in sources:
        result = format_source(source)

        assert result.new_source == source
        assert not result.fixed_findings
        assert not result.unfixed_findings


def test_reports_concatenated_and_escaped_newline_targets_as_nonfixable() -> None:
    source = 'def concatenated():\n    ("Return " "value")\n\n\ndef escaped():\n    """Return value\\ncontinued"""\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2,), (6,))
    assert [finding.fixable for finding in result.unfixed_findings] == [False, False]


def test_preserves_crlf_line_endings() -> None:
    source = 'def function():\r\n    """Return value\r\n    continued\r\n    """\r\n'
    result = format_source(source, settings=CheckSettings(select=("PDF301",), line_ending=LineEnding.CR_LF))

    assert result.new_source == 'def function():\r\n    """Return value\r\n    continued.\r\n    """\r\n'
    assert result.fixed_findings[PDF301SummaryTerminalPunctuation.meta] == 1


def test_unfixable_selection_reports_fixable_instance_without_changing_source() -> None:
    source = 'def function():\n    """Return value"""\n'
    result = format_source(source, settings=CheckSettings(select=("PDF301",), unfixable=("PDF301",)))

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2,),)
    assert [finding.fixable for finding in result.unfixed_findings] == [False]


@pytest.mark.parametrize("convention", [DocstringConvention.NUMPY, DocstringConvention.PEP257])
def test_numpy_and_pep257_conventions_ignore_broad_selection_but_exact_selection_still_applies(convention: DocstringConvention) -> None:
    broad = rules_selection.select_rules(CheckSettings(select=("PDF3",), docstring_convention=convention))
    active_codes = tuple(rule.rule.code.tag for rule in broad.rules)

    assert "PDF300" in active_codes
    assert "PDF301" not in active_codes

    source = 'def function():\n    """Return value"""\n'
    exact = format_source(source, settings=CheckSettings(select=("PDF301",), docstring_convention=convention))

    assert exact.new_source == 'def function():\n    """Return value."""\n'
    assert exact.fixed_findings[PDF301SummaryTerminalPunctuation.meta] == 1


def test_google_convention_keeps_broad_pdf301_selection_active() -> None:
    broad = rules_selection.select_rules(CheckSettings(select=("PDF3",), docstring_convention=DocstringConvention.GOOGLE))
    active_codes = tuple(rule.rule.code.tag for rule in broad.rules)

    assert "PDF300" not in active_codes
    assert "PDF301" in active_codes

    source = 'def function():\n    """Return value"""\n'
    result = format_source(source, settings=CheckSettings(select=("PDF301",), docstring_convention=DocstringConvention.GOOGLE))
    assert result.new_source == 'def function():\n    """Return value."""\n'
    assert result.fixed_findings[PDF301SummaryTerminalPunctuation.meta] == 1


def test_pdf101_reflows_before_pdf301_adds_period() -> None:
    source = 'def function():\n    """Return value\n    continued\n    """\n'
    settings = CheckSettings(select=("PDF101", "PDF301"), line_length=88)
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)

    assert result.new_source == 'def function():\n    """Return value continued.\n    """\n'
    assert result.fixed_findings[PDF101DocstringReflow.meta] == 1
    assert result.fixed_findings[PDF301SummaryTerminalPunctuation.meta] == 1
    assert not result.unfixed_findings


def test_pdf301_runs_before_pdf110_so_single_summary_can_be_collapsed_after_period_insertion() -> None:
    source = 'def function():\n    """Return value\n    """\n'
    settings = CheckSettings(select=("PDF110", "PDF301"))
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)

    assert result.new_source == 'def function():\n    """Return value."""\n'
    assert result.fixed_findings[PDF301SummaryTerminalPunctuation.meta] == 1


@pytest.mark.parametrize("convention", [DocstringConvention.NONE, DocstringConvention.REST])
def test_none_and_rest_broad_selection_prefers_pdf300(convention: DocstringConvention) -> None:
    selection = rules_selection.select_rules(CheckSettings(select=("PDF3",), docstring_convention=convention))
    active_codes = {rule.rule.code.tag for rule in selection.rules}

    assert selection.errors == ()
    assert "PDF300" in active_codes
    assert "PDF301" not in active_codes


def test_check_and_fix_false_findings_agree() -> None:
    source = 'def function():\n    """Return value"""\n'
    _, context = contexts(source)
    findings = rule_helpers.rule_findings(PDF301SummaryTerminalPunctuation, context)
    fixed = rule_helpers.rule_fix_result(PDF301SummaryTerminalPunctuation, context)
    check_only = format_source(source, fix=False)

    assert tuple(finding.line_numbers for finding in findings) == ((2,),)
    assert [finding.fixable for finding in findings] == [True]
    assert tuple(finding.line_numbers for finding in fixed.fixed_findings) == ((2,),)
    assert fixed.module.code == 'def function():\n    """Return value."""\n'
    assert tuple(finding.line_numbers for finding in check_only.unfixed_findings) == ((2,),)
