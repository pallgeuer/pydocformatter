# Third-party imports
import libcst as cst
import pytest
import libcst.metadata as cst_metadata

# First-party imports
from pydocformatter import formatter, rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringBlankLineStyle, DocstringConvention, IndentStyle, LineEnding
from pydocformatter.rules.definition import RuleCategoryContext, RuleContext
from pydocformatter.rules.definition_helpers import source_text
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.definitions.PDF.PDF201_missing_blank_line import PDF201MissingBlankLine
from pydocformatter.source_path import SourcePathContext
from tests import rule_helpers


def contexts(source: str, *, settings: CheckSettings | None = None) -> tuple[RuleCategoryContext, RuleContext]:
    """Return matching category and rule contexts for source."""
    module = cst.parse_module(source)
    wrapper = cst_metadata.MetadataWrapper(module, unsafe_skip_copy=True)
    category = RuleCategoryContext(
        path="example.py",
        source_path=SourcePathContext.for_path("example.py"),
        settings=CheckSettings(select=("PDF201",)) if settings is None else settings,
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
    resolved_settings = CheckSettings(select=("PDF201",)) if settings is None else settings
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=fix)


def test_inserts_blank_line_between_summary_and_google_section() -> None:
    source = 'def function(value):\n    """Summary.\n    Args:\n        value: Description.\n    """\n'
    settings = CheckSettings(select=("PDF201",), docstring_convention=DocstringConvention.GOOGLE)
    result = format_source(source, settings=settings)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    Args:\n        value: Description.\n    """\n'
    assert result.fixed_findings[PDF201MissingBlankLine.meta] == 1
    assert not format_source(result.new_source, settings=settings).modified


def test_preserves_first_line_content_whitespace_when_inserting_separator() -> None:
    source = 'def function(value):\n    """  Summary with leading spaces.\n    Args:\n        value: Description.\n    """\n'
    settings = CheckSettings(select=("PDF201",), docstring_convention=DocstringConvention.GOOGLE)
    result = format_source(source, settings=settings)

    assert result.new_source == 'def function(value):\n    """  Summary with leading spaces.\n\n    Args:\n        value: Description.\n    """\n'
    assert result.fixed_findings[PDF201MissingBlankLine.meta] == 1


def test_inserts_blank_line_between_summary_and_recognized_structure() -> None:
    source = 'def function():\n    """Summary.\n    - item\n      detail\n    """\n'
    result = format_source(source)

    assert result.new_source == 'def function():\n    """Summary.\n\n    - item\n      detail\n    """\n'
    assert result.fixed_findings[PDF201MissingBlankLine.meta] == 1
    assert not format_source(result.new_source).modified


@pytest.mark.parametrize(
    "structure_source",
    [
        "    # Heading",
        "    >>> call()\n    result",
        "    ```text\n    value\n    ```",
        "    > quote\n    > continuation",
        "    | A | B |\n    | --- | --- |\n    | 1 | 2 |",
        "    .. note:: Title\n\n        detail",
        "    .. custom:\n        detail",
        "    Example::\n\n        code",
        "    Accepted values:",
        "        verbatim line",
    ],
)
def test_inserts_blank_line_between_summary_and_each_recognized_structure_kind(structure_source: str) -> None:
    source = f'def function():\n    """Summary.\n{structure_source}\n    """\n'
    result = format_source(source)

    assert result.new_source == f'def function():\n    """Summary.\n\n{structure_source}\n    """\n'
    assert result.fixed_findings[PDF201MissingBlankLine.meta] == 1
    assert result.new_source is not None
    assert not format_source(result.new_source).modified


def test_inserts_blank_line_between_summary_and_rest_field_only_under_rest_convention() -> None:
    source = 'def function():\n    """Summary.\n    :param value: Description.\n    """\n'
    rest_settings = CheckSettings(select=("PDF201",), docstring_convention=DocstringConvention.REST)
    none_settings = CheckSettings(select=("PDF201",), docstring_convention=DocstringConvention.NONE)
    rest = format_source(source, settings=rest_settings)
    inactive = format_source(source, settings=none_settings)

    assert rest.new_source == 'def function():\n    """Summary.\n\n    :param value: Description.\n    """\n'
    assert rest.fixed_findings[PDF201MissingBlankLine.meta] == 1
    assert inactive.new_source == source
    assert not inactive.fixed_findings


def test_disabled_structure_parsing_prevents_summary_separator_insertion() -> None:
    source = 'def function():\n    """Summary.\n    ```text\n    value\n    ```\n    """\n'
    settings = CheckSettings(select=("PDF201",), docstring_parse_code_fences=False)
    result = format_source(source, settings=settings)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_directive_setting_controls_malformed_namespaced_structure_separator() -> None:
    source = 'def function():\n    """Summary.\n    .. py:function: signature\n    """\n'
    enabled = format_source(source)
    disabled = format_source(source, settings=CheckSettings(select=("PDF201",), docstring_parse_directives=False))

    assert enabled.new_source == source.replace("Summary.\n", "Summary.\n\n")
    assert enabled.fixed_findings[PDF201MissingBlankLine.meta] == 1
    assert disabled.new_source == source
    assert not disabled.fixed_findings
    assert not disabled.unfixed_findings


def test_does_not_split_ambiguous_multiline_summary_or_plain_prose() -> None:
    source = 'def function():\n    """Summary line\n    continuation line.\n    """\n\ndef other():\n    """Summary.\n    Body.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_existing_whitespace_only_separator_prevents_duplicate_insertion() -> None:
    source = 'def function(value):\n    """Summary.\n      \n    Args:\n        value: Description.\n    """\n'
    settings = CheckSettings(select=("PDF201",), docstring_convention=DocstringConvention.GOOGLE)
    result = format_source(source, settings=settings)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


@pytest.mark.parametrize("convention", [DocstringConvention.NONE, DocstringConvention.NUMPY, DocstringConvention.PEP257])
def test_google_section_syntax_is_separated_as_colon_header_without_google_convention(convention: DocstringConvention) -> None:
    source = 'def function(value):\n    """Summary.\n    Args:\n        value: Description.\n    """\n'
    settings = CheckSettings(select=("PDF201",), docstring_convention=convention)
    result = format_source(source, settings=settings)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    Args:\n        value: Description.\n    """\n'
    assert result.fixed_findings[PDF201MissingBlankLine.meta] == 1


@pytest.mark.parametrize("convention", [DocstringConvention.NONE, DocstringConvention.PEP257, DocstringConvention.GOOGLE])
def test_numpy_section_syntax_is_separated_as_heading_without_numpy_convention(convention: DocstringConvention) -> None:
    source = 'def function(value):\n    """Summary.\n    Parameters\n    ----------\n    value : int\n        Description.\n    """\n'
    settings = CheckSettings(select=("PDF201",), docstring_convention=convention, docstring_blank_line_after_last_section=True)
    result = format_source(source, settings=settings)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    Parameters\n    ----------\n    value : int\n        Description.\n    """\n'
    assert result.fixed_findings[PDF201MissingBlankLine.meta] == 1
    assert not format_source(result.new_source, settings=settings).modified


def test_final_section_setting_does_not_add_trailing_blank_after_non_section_structure() -> None:
    source = 'def function():\n    """Summary.\n\n    - item\n      detail\n    """\n'
    settings = CheckSettings(select=("PDF201",), docstring_convention=DocstringConvention.GOOGLE, docstring_blank_line_after_last_section=True)
    result = format_source(source, settings=settings)

    assert result.new_source == source
    assert not result.fixed_findings


def test_inserts_blank_line_between_paragraph_and_following_section() -> None:
    source = 'def function(value):\n    """Summary.\n\n    More details.\n    Args:\n        value: Description.\n    """\n'
    settings = CheckSettings(select=("PDF201",), docstring_convention=DocstringConvention.GOOGLE)
    result = format_source(source, settings=settings)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    More details.\n\n    Args:\n        value: Description.\n    """\n'
    assert result.fixed_findings[PDF201MissingBlankLine.meta] == 1
    assert not format_source(result.new_source, settings=settings).modified


def test_inserts_blank_line_between_summary_and_numpy_section() -> None:
    source = 'def function(value):\n    """Summary.\n    Parameters\n    ----------\n    value : int\n        Description.\n    """\n'
    settings = CheckSettings(select=("PDF201",), docstring_convention=DocstringConvention.NUMPY)
    result = format_source(source, settings=settings)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    Parameters\n    ----------\n    value : int\n        Description.\n    """\n'
    assert result.fixed_findings[PDF201MissingBlankLine.meta] == 1
    assert not format_source(result.new_source, settings=settings).modified


def test_parenthesized_docstring_uses_quote_column_margin_for_aligned_insertions() -> None:
    source = 'def function(value):\n    (\n        """Summary.\n        Args:\n            value: Description.\n        """\n    )\n'
    settings = CheckSettings(select=("PDF201",), docstring_convention=DocstringConvention.GOOGLE, docstring_blank_line_style=DocstringBlankLineStyle.ALIGNED)
    result = format_source(source, settings=settings)

    assert result.new_source == 'def function(value):\n    (\n        """Summary.\n        \n        Args:\n            value: Description.\n        """\n    )\n'
    assert result.fixed_findings[PDF201MissingBlankLine.meta] == 1
    assert not format_source(result.new_source, settings=settings).modified


def test_preserves_raw_prefix_quote_delimiter_backslashes_and_non_ascii_spellings() -> None:
    source = "def function(value):\n    r'''Summary with path C:\\\\temp and caf\\xe9 \\xe9.\n    Args:\n        value: Description.'''\n"
    settings = CheckSettings(select=("PDF201",), docstring_convention=DocstringConvention.GOOGLE)
    result = format_source(source, settings=settings)

    assert result.new_source == "def function(value):\n    r'''Summary with path C:\\\\temp and caf\\xe9 \\xe9.\n\n    Args:\n        value: Description.'''\n"
    assert result.fixed_findings[PDF201MissingBlankLine.meta] == 1
    assert not format_source(result.new_source, settings=settings).modified


def test_inserts_blank_line_before_adjacent_google_sections() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Args:\n        value: Description.\n    Returns:\n        bool: Result.\n    """\n'
    settings = CheckSettings(select=("PDF201",), docstring_convention=DocstringConvention.GOOGLE)
    result = format_source(source, settings=settings)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    Args:\n        value: Description.\n\n    Returns:\n        bool: Result.\n    """\n'
    assert result.fixed_findings[PDF201MissingBlankLine.meta] == 1
    assert not format_source(result.new_source, settings=settings).modified


def test_inserts_blank_line_before_adjacent_numpy_sections() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Parameters\n    ----------\n    value : int\n        Description.\n    Returns\n    -------\n    bool\n        Result.\n    """\n'
    settings = CheckSettings(select=("PDF201",), docstring_convention=DocstringConvention.NUMPY)
    result = format_source(source, settings=settings)

    assert (
        result.new_source
        == 'def function(value):\n    """Summary.\n\n    Parameters\n    ----------\n    value : int\n        Description.\n\n    Returns\n    -------\n    bool\n        Result.\n    """\n'
    )
    assert result.fixed_findings[PDF201MissingBlankLine.meta] == 1
    assert not format_source(result.new_source, settings=settings).modified


def test_multiple_missing_blank_lines_are_inserted_in_one_docstring() -> None:
    source = 'def function(value):\n    """Summary.\n    Args:\n        value: Description.\n    Returns:\n        bool: Result.\n    """\n'
    settings = CheckSettings(select=("PDF201",), docstring_convention=DocstringConvention.GOOGLE, docstring_blank_line_after_last_section=True)
    _, context = contexts(source, settings=settings)
    findings = rule_helpers.rule_findings(PDF201MissingBlankLine, context)
    result = format_source(source, settings=settings)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    Args:\n        value: Description.\n\n    Returns:\n        bool: Result.\n\n    """\n'
    assert tuple(finding.line_numbers for finding in findings) == ((3, 5, 6),)
    assert result.fixed_findings[PDF201MissingBlankLine.meta] == 1
    assert not format_source(result.new_source, settings=settings).modified


def test_does_not_insert_section_internal_blank_lines() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Args:\n        value: Description.\n        other: Other description.\n    """\n'
    settings = CheckSettings(select=("PDF201",), docstring_convention=DocstringConvention.GOOGLE)
    result = format_source(source, settings=settings)

    assert result.new_source == source
    assert not result.fixed_findings


def test_final_section_blank_line_is_disabled_by_default() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Args:\n        value: Description.\n    """\n'
    settings = CheckSettings(select=("PDF201",), docstring_convention=DocstringConvention.GOOGLE)
    result = format_source(source, settings=settings)

    assert result.new_source == source
    assert not result.fixed_findings


def test_final_section_setting_does_not_apply_without_matching_convention() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Args:\n        value: Description."""\n'
    settings = CheckSettings(select=("PDF201",), docstring_convention=DocstringConvention.NONE, docstring_blank_line_after_last_section=True)
    result = format_source(source, settings=settings)

    assert result.new_source == source
    assert not result.fixed_findings


def test_final_section_blank_line_is_inserted_when_enabled() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Args:\n        value: Description.\n    """\n'
    settings = CheckSettings(select=("PDF201",), docstring_convention=DocstringConvention.GOOGLE, docstring_blank_line_after_last_section=True)
    result = format_source(source, settings=settings)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    Args:\n        value: Description.\n\n    """\n'
    assert result.fixed_findings[PDF201MissingBlankLine.meta] == 1
    assert not format_source(result.new_source, settings=settings).modified


def test_final_section_blank_line_is_not_inserted_after_header_only_section() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Examples:\n    """\n'
    settings = CheckSettings(select=("PDF201",), docstring_convention=DocstringConvention.GOOGLE, docstring_blank_line_after_last_section=True)
    result = format_source(source, settings=settings)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_first_line_section_only_gets_configured_final_blank() -> None:
    source = 'def function(value):\n    """Args:\n        value: Description."""\n'
    settings = CheckSettings(select=("PDF201",), docstring_convention=DocstringConvention.GOOGLE, docstring_blank_line_after_last_section=True)
    result = format_source(source, settings=settings)

    assert result.new_source == 'def function(value):\n    """Args:\n        value: Description.\n\n    """\n'
    assert result.fixed_findings[PDF201MissingBlankLine.meta] == 1
    assert not format_source(result.new_source, settings=settings).modified


def test_final_section_blank_line_insertion_separates_same_line_closing_quotes() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Args:\n        value: Description."""\n'
    settings = CheckSettings(select=("PDF201",), docstring_convention=DocstringConvention.GOOGLE, docstring_blank_line_after_last_section=True)
    result = format_source(source, settings=settings)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    Args:\n        value: Description.\n\n    """\n'
    assert result.fixed_findings[PDF201MissingBlankLine.meta] == 1
    assert not format_source(result.new_source, settings=settings).modified


def test_aligned_style_controls_final_section_blank_line_source() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Args:\n        value: Description."""\n'
    settings = CheckSettings(
        select=("PDF201",), docstring_convention=DocstringConvention.GOOGLE, docstring_blank_line_after_last_section=True, docstring_blank_line_style=DocstringBlankLineStyle.ALIGNED
    )
    result = format_source(source, settings=settings)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    Args:\n        value: Description.\n    \n    """\n'
    assert result.fixed_findings[PDF201MissingBlankLine.meta] == 1
    assert not format_source(result.new_source, settings=settings).modified


def test_aligned_style_controls_inserted_blank_line_source() -> None:
    source = 'def function(value):\n    """Summary.\n    Args:\n        value: Description.\n    """\n'
    settings = CheckSettings(select=("PDF201",), docstring_convention=DocstringConvention.GOOGLE, docstring_blank_line_style=DocstringBlankLineStyle.ALIGNED)
    result = format_source(source, settings=settings)

    assert result.new_source == 'def function(value):\n    """Summary.\n    \n    Args:\n        value: Description.\n    """\n'
    assert not format_source(result.new_source, settings=settings).modified


def test_preserves_crlf_for_generated_blank_lines() -> None:
    source = 'def function(value):\r\n    """Summary.\r\n    Args:\r\n        value: Description.\r\n    """\r\n'
    settings = CheckSettings(select=("PDF201",), docstring_convention=DocstringConvention.GOOGLE, line_ending=LineEnding.CR_LF)
    result = format_source(source, settings=settings)

    assert result.new_source == 'def function(value):\r\n    """Summary.\r\n\r\n    Args:\r\n        value: Description.\r\n    """\r\n'


def test_simple_suite_tab_margin_is_used_for_aligned_insertions() -> None:
    source = 'def function(value): """Summary.\nArgs:\n\tvalue: Description.\n"""\n'
    settings = CheckSettings(select=("PDF201",), docstring_convention=DocstringConvention.GOOGLE, docstring_blank_line_style=DocstringBlankLineStyle.ALIGNED, indent_style=IndentStyle.TAB)
    result = format_source(source, settings=settings)

    assert result.new_source == 'def function(value): """Summary.\n\t\nArgs:\n\tvalue: Description.\n"""\n'


def test_check_fix_and_fix_false_findings_agree() -> None:
    source = 'def first():\n    """Summary.\n    Args:\n        value: Description.\n    """\n\ndef second():\n    """Summary.\n    - item\n    """\n'
    settings = CheckSettings(select=("PDF201",), docstring_convention=DocstringConvention.GOOGLE)
    _, context = contexts(source, settings=settings)
    findings = rule_helpers.rule_findings(PDF201MissingBlankLine, context)
    fixed = rule_helpers.rule_fix_result(PDF201MissingBlankLine, context)
    check_only = format_source(source, settings=settings, fix=False)

    assert tuple(finding.line_numbers for finding in findings) == ((3,), (9,))
    assert tuple(finding.line_numbers for finding in fixed.fixed_findings) == ((3,), (9,))
    assert tuple(finding.line_numbers for finding in check_only.unfixed_findings) == ((3,), (9,))
    _, fixed_context = contexts(fixed.module.code, settings=settings)
    assert rule_helpers.rule_findings(PDF201MissingBlankLine, fixed_context) == ()


def test_skips_concatenated_escaped_and_non_docstring_strings() -> None:
    source = 'def concatenated():\n    ("Summary.\\n"\n     "Args:\\n"\n     "    value: Description.")\n\ndef escaped():\n    """Summary.\\nArgs:\\n    value: Description."""\n\ndef not_docstring():\n    value = 1\n    """Summary.\n    Args:\n        value: Description.\n    """\n'
    settings = CheckSettings(select=("PDF201",), docstring_convention=DocstringConvention.GOOGLE)
    result = format_source(source, settings=settings)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_pdf100_and_pdf101_converge_with_configured_final_section_blank() -> None:
    source = 'def function(value):\n    """Summary.\n    Args:\n        value: Description.\n\n\n    """\n'
    settings = CheckSettings(select=("PDF200", "PDF201"), docstring_convention=DocstringConvention.GOOGLE, docstring_blank_line_after_last_section=True)
    result = format_source(source, settings=settings)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    Args:\n        value: Description.\n\n    """\n'
    assert not format_source(result.new_source, settings=settings).modified


def test_pdf100_and_pdf101_converge_with_default_final_section_blank_disabled() -> None:
    source = 'def function(value):\n    """Summary.\n    Args:\n        value: Description.\n\n\n    """\n'
    settings = CheckSettings(select=("PDF200", "PDF201"), docstring_convention=DocstringConvention.GOOGLE)
    result = format_source(source, settings=settings)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    Args:\n        value: Description.\n    """\n'
    assert not format_source(result.new_source, settings=settings).modified


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ('def function(value):\n    """Summary.\n    Args:\n        value: Description."""\n', 'def function(value):\n    """Summary.\n\n    Args:\n        value: Description.\n\n    """\n'),
        (
            'def function(value):\n    """Summary.\n    Args:\n        value: Description.\n\n\n    """\n',
            'def function(value):\n    """Summary.\n\n    Args:\n        value: Description.\n\n    """\n',
        ),
        ('def function(value):\n    """Summary.\n    Examples:\n    """\n', 'def function(value):\n    """Summary.\n\n    Examples:\n    """\n'),
        ('def function(value):\n    """Summary.\n    Examples:\n\n\n    """\n', 'def function(value):\n    """Summary.\n\n    Examples:\n    """\n'),
    ],
)
def test_pdf100_and_pdf101_converge_with_configured_final_section_blank_cases(source: str, expected: str) -> None:
    settings = CheckSettings(select=("PDF200", "PDF201"), docstring_convention=DocstringConvention.GOOGLE, docstring_blank_line_after_last_section=True)
    result = format_source(source, settings=settings)

    assert result.new_source == expected
    assert result.new_source is not None
    assert not format_source(result.new_source, settings=settings).modified


def test_suspicious_unicode_blocks_inserting_section_separator() -> None:
    source = 'def function(value):\n    """Summary\u202e.\n    Args:\n        value: Description.\n    """\n'
    settings = CheckSettings(select=("PDF201",), docstring_convention=DocstringConvention.GOOGLE)

    result = format_source(source, settings=settings)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings
