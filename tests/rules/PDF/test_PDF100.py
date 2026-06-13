import libcst as cst
import libcst.metadata as cst_metadata

import pydocformatter.formatter as formatter
import pydocformatter.rules_selection as rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringBlankLineStyle, DocstringConvention, IndentStyle, LineEnding
from pydocformatter.rules.definition import RuleCategoryContext, RuleContext
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.definitions.PDF.PDF100_too_many_blank_lines import PDF100TooManyBlankLines


def contexts(source: str, *, settings: CheckSettings | None = None) -> tuple[RuleCategoryContext, RuleContext]:
    """Return matching category and rule contexts for source."""
    module = cst.parse_module(source)
    wrapper = cst_metadata.MetadataWrapper(module, unsafe_skip_copy=True)
    category = RuleCategoryContext(
        path="example.py",
        settings=CheckSettings(select=("PDF100",)) if settings is None else settings,
        module=module,
        metadata_wrapper=wrapper,
        positions=wrapper.resolve(cst_metadata.PositionProvider),
        line_ending="\r\n" if "\r\n" in source else "\n",
    )
    return category, RuleContext(**category.__dict__, category_data=PDF.prepare(category), effectively_fixable=True)


def format_pdf100(source: str, *, settings: CheckSettings | None = None, fix: bool = True) -> formatter.FormatterResult:
    """Format source with PDF100 selected."""
    resolved_settings = CheckSettings(select=("PDF100",)) if settings is None else settings
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=fix)


def test_collapses_leading_internal_and_trailing_extra_blank_lines() -> None:
    source = 'def function():\n    """\n\n    Summary.\n\n\n    Body.\n\n    """\n'
    _, context = contexts(source)
    findings = PDF100TooManyBlankLines.check(context)
    fixed = PDF100TooManyBlankLines.fix(context)
    check_only = format_pdf100(source, fix=False)

    assert fixed.module.code == 'def function():\n    """Summary.\n\n    Body.\n    """\n'
    assert tuple(finding.line_numbers for finding in findings) == ((2, 3, 6, 8),)
    assert tuple(finding.line_numbers for finding in fixed.fixed_findings) == ((2, 3, 6, 8),)
    assert tuple(finding.line_numbers for finding in check_only.unfixed_findings) == ((2, 3, 6, 8),)
    _, fixed_context = contexts(fixed.module.code)
    assert PDF100TooManyBlankLines.check(fixed_context) == ()


def test_preserves_first_line_content_whitespace_when_collapsing_later_blank_lines() -> None:
    source = 'def function():\n    """  Summary with leading spaces.\n\n\n    Body.\n    """\n'
    result = format_pdf100(source)

    assert result.new_source == 'def function():\n    """  Summary with leading spaces.\n\n    Body.\n    """\n'
    assert result.fixed_findings[PDF100TooManyBlankLines.meta] == 1


def test_does_not_insert_missing_blank_lines_or_change_single_blank_lines() -> None:
    source = 'def missing():\n    """Summary.\n    Body.\n    """\n\ndef single():\n    """Summary.\n\n    Body.\n    """\n'
    result = format_pdf100(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_collapses_blank_lines_between_google_section_children() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Args:\n\n\n        value: Description.\n\n\n        other: Other description.\n\n\n    Returns:\n        str: Result.\n    """\n'
    result = format_pdf100(source, settings=CheckSettings(select=("PDF100",), docstring_convention=DocstringConvention.GOOGLE))

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    Args:\n        value: Description.\n        other: Other description.\n    Returns:\n        str: Result.\n    """\n'
    assert result.fixed_findings[PDF100TooManyBlankLines.meta] == 1
    assert not format_pdf100(result.new_source, settings=CheckSettings(select=("PDF100",), docstring_convention=DocstringConvention.GOOGLE)).modified


def test_final_google_section_blank_line_is_removed_by_default() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Args:\n        value: Description.\n\n\n    """\n'
    settings = CheckSettings(select=("PDF100",), docstring_convention=DocstringConvention.GOOGLE)
    result = format_pdf100(source, settings=settings)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    Args:\n        value: Description.\n    """\n'
    assert result.fixed_findings[PDF100TooManyBlankLines.meta] == 1
    assert not format_pdf100(result.new_source, settings=settings).modified


def test_final_google_section_blank_line_is_preserved_when_enabled() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Args:\n        value: Description.\n\n\n    """\n'
    settings = CheckSettings(select=("PDF100",), docstring_convention=DocstringConvention.GOOGLE, docstring_blank_line_after_last_section=True)
    result = format_pdf100(source, settings=settings)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    Args:\n        value: Description.\n\n    """\n'
    assert result.fixed_findings[PDF100TooManyBlankLines.meta] == 1
    assert not format_pdf100(result.new_source, settings=settings).modified


def test_final_numpy_section_blank_line_follows_setting() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Parameters\n    ----------\n    value : int\n        Description.\n\n\n    """\n'
    default_settings = CheckSettings(select=("PDF100",), docstring_convention=DocstringConvention.NUMPY)
    enabled_settings = CheckSettings(select=("PDF100",), docstring_convention=DocstringConvention.NUMPY, docstring_blank_line_after_last_section=True)
    default_result = format_pdf100(source, settings=default_settings)
    enabled_result = format_pdf100(source, settings=enabled_settings)

    assert default_result.new_source == 'def function(value):\n    """Summary.\n\n    Parameters\n    ----------\n    value : int\n        Description.\n    """\n'
    assert enabled_result.new_source == 'def function(value):\n    """Summary.\n\n    Parameters\n    ----------\n    value : int\n        Description.\n\n    """\n'
    assert default_result.fixed_findings[PDF100TooManyBlankLines.meta] == 1
    assert enabled_result.fixed_findings[PDF100TooManyBlankLines.meta] == 1
    assert not format_pdf100(default_result.new_source, settings=default_settings).modified
    assert not format_pdf100(enabled_result.new_source, settings=enabled_settings).modified


def test_final_section_setting_does_not_preserve_convention_like_trailing_blank_without_matching_convention() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Args:\n        value: Description.\n\n\n    """\n'
    settings = CheckSettings(select=("PDF100",), docstring_convention=DocstringConvention.NONE, docstring_blank_line_after_last_section=True)
    result = format_pdf100(source, settings=settings)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    Args:\n        value: Description.\n    """\n'
    assert result.fixed_findings[PDF100TooManyBlankLines.meta] == 1
    assert not format_pdf100(result.new_source, settings=settings).modified


def test_protected_block_internal_blank_lines_are_preserved() -> None:
    source = 'def function():\n    """Summary.\n\n\n    ```text\n    first\n\n    second\n    ```\n\n\n    Body.\n    """\n'
    result = format_pdf100(source)

    assert result.new_source == 'def function():\n    """Summary.\n\n    ```text\n    first\n\n    second\n    ```\n\n    Body.\n    """\n'


def test_indented_protected_blocks_preserve_internal_blanks_but_collapse_exterior_blanks() -> None:
    source = 'def function():\n    """Summary.\n\n\n    .. note:: Title\n\n        directive first\n\n\n        directive second\n\n\n    Example::\n\n        literal first\n\n\n        literal second\n\n\n    Body.\n    """\n'
    result = format_pdf100(source)

    assert (
        result.new_source
        == 'def function():\n    """Summary.\n\n    .. note:: Title\n\n        directive first\n\n\n        directive second\n\n    Example::\n\n        literal first\n\n\n        literal second\n\n    Body.\n    """\n'
    )
    assert result.fixed_findings[PDF100TooManyBlankLines.meta] == 1
    assert not format_pdf100(result.new_source).modified


def test_verbatim_blocks_preserve_internal_blanks_but_collapse_exterior_blanks() -> None:
    source = 'def function():\n    """Summary.\n\n        verbatim first\n\n        verbatim second\n\n\n    Body.\n    """\n'
    result = format_pdf100(source)

    assert result.new_source == 'def function():\n    """Summary.\n\n        verbatim first\n\n        verbatim second\n\n    Body.\n    """\n'
    assert result.fixed_findings[PDF100TooManyBlankLines.meta] == 1
    assert not format_pdf100(result.new_source).modified


def test_mixed_generic_semantic_chunks_collapse_separator_runs_once() -> None:
    source = 'def function(value):\n    """Summary.\n\n\n    # Heading\n\n\n    >>> call()\n    result\n\n\n    - item\n      continuation\n\n\n    > quote\n    > continuation\n\n\n    :param value: description\n        continuation\n\n\n    | A | B |\n    | - | - |\n    | 1 | 2 |\n\n\n    Body.\n    """\n'
    result = format_pdf100(source)

    assert (
        result.new_source
        == 'def function(value):\n    """Summary.\n\n    # Heading\n\n    >>> call()\n    result\n\n    - item\n      continuation\n\n    > quote\n    > continuation\n\n    :param value: description\n        continuation\n\n    | A | B |\n    | - | - |\n    | 1 | 2 |\n\n    Body.\n    """\n'
    )
    assert result.fixed_findings[PDF100TooManyBlankLines.meta] == 1
    assert not format_pdf100(result.new_source).modified


def test_blank_only_docstrings_collapse_to_empty_docstrings() -> None:
    source = 'def blank():\n    """\n\n    """\n\ndef spaces():\n    """   \n\t\n    """\n'
    result = format_pdf100(source)

    assert result.new_source == 'def blank():\n    """"""\n\ndef spaces():\n    """"""\n'
    assert result.fixed_findings[PDF100TooManyBlankLines.meta] == 2
    assert not format_pdf100(result.new_source).modified


def test_one_line_whitespace_only_docstrings_collapse_to_empty_docstrings() -> None:
    source = '"""   """\n\ndef block_suite():\n    """   """\n\ndef simple_suite(): """   """\n'
    result = format_pdf100(source)

    assert result.new_source == '""""""\n\ndef block_suite():\n    """"""\n\ndef simple_suite(): """"""\n'
    assert result.fixed_findings[PDF100TooManyBlankLines.meta] == 3
    assert not format_pdf100(result.new_source).modified


def test_empty_docstrings_are_already_normalized() -> None:
    source = '""""""\n\ndef block_suite():\n    """"""\n\ndef simple_suite(): """"""\n'
    result = format_pdf100(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_trailing_extra_blank_lines_preserve_separate_closing_quotes_when_already_separate() -> None:
    source = 'def function():\n    """Summary.\n\n\n    """\n'
    result = format_pdf100(source)

    assert result.new_source == 'def function():\n    """Summary.\n    """\n'


def test_module_trailing_newline_before_closing_quotes_is_preserved() -> None:
    source = '"""Summary.\n\n\n"""\n'
    result = format_pdf100(source)

    assert result.new_source == '"""Summary.\n"""\n'
    assert not format_pdf100(result.new_source).modified


def test_simple_suite_closing_quote_prefix_uses_configured_margin() -> None:
    source = 'def function(): """Summary.\n\n\n  """\n'
    result = format_pdf100(source, settings=CheckSettings(select=("PDF100",), indent_width=2))

    assert result.new_source == 'def function(): """Summary.\n  """\n'
    assert not format_pdf100(result.new_source, settings=CheckSettings(select=("PDF100",), indent_width=2)).modified


def test_simple_suite_closing_quote_prefix_uses_configured_tab_margin() -> None:
    source = 'def function(): """Summary.\n\n\n\t"""\n'
    settings = CheckSettings(select=("PDF100",), indent_style=IndentStyle.TAB)
    result = format_pdf100(source, settings=settings)

    assert result.new_source == 'def function(): """Summary.\n\t"""\n'
    assert not format_pdf100(result.new_source, settings=settings).modified


def test_parenthesized_docstring_closing_quote_prefix_uses_quote_column_margin() -> None:
    source = 'def function():\n    (\n        """Summary.\n\n\n        """\n    )\n'
    result = format_pdf100(source)

    assert result.new_source == 'def function():\n    (\n        """Summary.\n        """\n    )\n'
    assert not format_pdf100(result.new_source).modified


def test_same_line_closing_quotes_move_to_content_line_when_blank_prefix_is_removed() -> None:
    source = 'def function():\n    """Summary.\n      """\n'
    result = format_pdf100(source)

    assert result.new_source == 'def function():\n    """Summary."""\n'


def test_preserves_crlf_for_generated_separators() -> None:
    source = 'def function():\r\n    """Summary.\r\n\r\n\r\n    Body.\r\n    """\r\n'
    result = format_pdf100(source, settings=CheckSettings(select=("PDF100",), line_ending=LineEnding.CR_LF))

    assert result.new_source == 'def function():\r\n    """Summary.\r\n\r\n    Body.\r\n    """\r\n'


def test_preserves_raw_prefix_quote_delimiter_backslashes_and_non_ascii_spellings() -> None:
    source = "def function():\n    r'''Summary with path C:\\\\temp and caf\\xe9 \\xe9.\n\n\n    Body.'''\n"
    result = format_pdf100(source)

    assert result.new_source == "def function():\n    r'''Summary with path C:\\\\temp and caf\\xe9 \\xe9.\n\n    Body.'''\n"
    assert not format_pdf100(result.new_source).modified


def test_retained_blank_line_whitespace_is_left_for_pdf004() -> None:
    source = 'def function():\n    """Summary.\n      \n        \n    Body.\n    """\n'
    settings = CheckSettings(select=("PDF100",), docstring_blank_line_style=DocstringBlankLineStyle.ALIGNED)
    result = format_pdf100(source, settings=settings)

    assert result.new_source == 'def function():\n    """Summary.\n      \n    Body.\n    """\n'
    assert result.fixed_findings[PDF100TooManyBlankLines.meta] == 1
    assert not format_pdf100(result.new_source, settings=settings).modified


def test_non_ascii_whitespace_only_lines_are_blank_for_pdf100() -> None:
    source = 'def function():\n    """Summary.\n\n\xa0\n\u2003\n    Body.\n    """\n'
    result = format_pdf100(source)

    assert result.new_source == 'def function():\n    """Summary.\n\n    Body.\n    """\n'
    assert result.fixed_findings[PDF100TooManyBlankLines.meta] == 1


def test_skips_concatenated_escaped_newline_and_non_docstring_strings() -> None:
    source = (
        'def concatenated():\n    ("Summary.\\n\\n\\n"\n     "Body.")\n\ndef escaped():\n    """Summary.\\n\\n\\nBody."""\n\ndef not_docstring():\n    value = 1\n    """Summary.\n\n\n    Body."""\n'
    )
    result = format_pdf100(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_pdf000_can_literalize_escaped_blank_lines_before_pdf100_collapses_them() -> None:
    source = 'def function():\n    """Summary.\\n\\n\\nBody."""\n'
    settings = CheckSettings(select=("PDF000", "PDF100"))
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)

    assert result.new_source == 'def function():\n    """Summary.\n\nBody."""\n'
    assert result.fixed_findings[PDF100TooManyBlankLines.meta] == 1
    assert not formatter.format_source(result.new_source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True).modified


def test_collapses_blank_lines_between_numpy_section_children() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Parameters\n    ----------\n\n\n    value : int\n        Description.\n\n\n    other : str\n        Other description.\n\n\n    Returns\n    -------\n    bool\n        Result.\n    """\n'
    settings = CheckSettings(select=("PDF100",), docstring_convention=DocstringConvention.NUMPY)
    result = format_pdf100(source, settings=settings)

    assert (
        result.new_source
        == 'def function(value):\n    """Summary.\n\n    Parameters\n    ----------\n    value : int\n        Description.\n    other : str\n        Other description.\n    Returns\n    -------\n    bool\n        Result.\n    """\n'
    )
    assert result.fixed_findings[PDF100TooManyBlankLines.meta] == 1
    assert not format_pdf100(result.new_source, settings=settings).modified


def test_convention_like_sections_keep_generic_spacing_when_convention_is_none() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Args:\n\n\n        value: Description.\n\n\n        other: Other description.\n    """\n'
    result = format_pdf100(source, settings=CheckSettings(select=("PDF100",), docstring_convention=DocstringConvention.NONE))

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    Args:\n\n        value: Description.\n\n\n        other: Other description.\n    """\n'
    assert result.fixed_findings[PDF100TooManyBlankLines.meta] == 1
    assert not format_pdf100(result.new_source, settings=CheckSettings(select=("PDF100",), docstring_convention=DocstringConvention.NONE)).modified


def test_disabled_code_fence_parsing_allows_fence_internal_blank_lines_to_collapse() -> None:
    source = 'def function():\n    """Summary.\n\n    ```text\n    first\n\n\n    second\n    ```\n    """\n'
    protected = format_pdf100(source)
    unprotected_settings = CheckSettings(select=("PDF100",), docstring_parse_code_fences=False)
    unprotected = format_pdf100(source, settings=unprotected_settings)

    assert protected.new_source == source
    assert not protected.fixed_findings
    assert unprotected.new_source == 'def function():\n    """Summary.\n\n    ```text\n    first\n\n    second\n    ```\n    """\n'
    assert unprotected.fixed_findings[PDF100TooManyBlankLines.meta] == 1
    assert not format_pdf100(unprotected.new_source, settings=unprotected_settings).modified


def test_pdf004_normalizes_retained_blank_line_after_pdf100_collapses_extras() -> None:
    source = 'def function():\n    """Summary.\n      \n        \n    Body.\n    """\n'
    settings = CheckSettings(select=("PDF004", "PDF100"))
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)

    assert result.new_source == 'def function():\n    """Summary.\n\n    Body.\n    """\n'
    assert result.fixed_findings[PDF100TooManyBlankLines.meta] == 1
