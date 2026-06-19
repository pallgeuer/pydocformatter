import pydocformatter.formatter as formatter
import pydocformatter.rules_selection as rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention, IndentStyle, LineEnding
from pydocformatter.rules.definitions.PDF.PDF403_section_name_trailing_content import PDF403SectionNameTrailingContent


def format_source(source: str, *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Format source with PDF403 selected."""
    resolved_settings = CheckSettings(select=("PDF403",), docstring_convention=DocstringConvention.GOOGLE) if settings is None else settings
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=True)


def test_moves_google_section_trailing_content_to_next_line() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Args: value: Description.\n    """\n'
    result = format_source(source)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    Args:\n        value: Description.\n    """\n'
    assert result.fixed_findings[PDF403SectionNameTrailingContent.meta] == 1
    assert PDF403SectionNameTrailingContent.meta.name == "section-name-trailing-content"
    assert not format_source(result.new_source).modified


def test_moves_google_section_trailing_content_with_space_before_colon() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Args : value: Description.\n    """\n'
    result = format_source(source)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    Args:\n        value: Description.\n    """\n'
    assert result.fixed_findings[PDF403SectionNameTrailingContent.meta] == 1
    assert not format_source(result.new_source).modified


def test_moves_multiple_google_section_trailing_content_lines_in_one_docstring() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Args: value: Description.\n\n    Returns: int: Result.\n\n    Raises: ValueError: Bad value.\n    """\n'
    result = format_source(source)

    assert (
        result.new_source
        == 'def function(value):\n    """Summary.\n\n    Args:\n        value: Description.\n\n    Returns:\n        int: Result.\n\n    Raises:\n        ValueError: Bad value.\n    """\n'
    )
    assert result.fixed_findings[PDF403SectionNameTrailingContent.meta] == 1
    assert not format_source(result.new_source).modified


def test_preserves_noncanonical_section_name_case_when_moving_trailing_content() -> None:
    source = 'def function(value):\n    """Summary.\n\n    args: value: Description.\n    """\n'
    result = format_source(source)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    args:\n        value: Description.\n    """\n'
    assert result.fixed_findings[PDF403SectionNameTrailingContent.meta] == 1
    assert not format_source(result.new_source).modified


def test_does_not_treat_summary_with_section_like_prefix_as_trailing_section_content() -> None:
    source = 'def function(value):\n    """Returns: True when the value is enabled."""\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_reports_unsafe_google_section_trailing_content_without_fixing() -> None:
    source = 'def function(value):\n    ("Summary.\\n\\n"\n     "Args: value: Description.")\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2, 3),)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring section 'Args' should be followed by a line break",)


def test_uses_configured_indentation_when_moving_trailing_content() -> None:
    source = 'def function(value):\n\t"""Summary.\n\n\tArgs: value: Description.\n\t"""\n'
    settings = CheckSettings(select=("PDF403",), docstring_convention=DocstringConvention.GOOGLE, indent_style=IndentStyle.TAB)
    result = format_source(source, settings=settings)

    assert result.new_source == 'def function(value):\n\t"""Summary.\n\n\tArgs:\n\t\tvalue: Description.\n\t"""\n'
    assert result.fixed_findings[PDF403SectionNameTrailingContent.meta] == 1
    assert not format_source(result.new_source, settings=settings).modified


def test_preserves_configured_crlf_line_endings_when_moving_trailing_content() -> None:
    source = 'def function(value):\r\n    """Summary.\r\n\r\n    Args: value: Description.\r\n    """\r\n'
    settings = CheckSettings(select=("PDF403",), docstring_convention=DocstringConvention.GOOGLE, line_ending=LineEnding.CR_LF)
    result = format_source(source, settings=settings)

    assert result.new_source == 'def function(value):\r\n    """Summary.\r\n\r\n    Args:\r\n        value: Description.\r\n    """\r\n'
    assert result.fixed_findings[PDF403SectionNameTrailingContent.meta] == 1
    assert not format_source(result.new_source, settings=settings).modified


def test_ignores_section_like_trailing_content_inside_code_fences() -> None:
    source = 'def function(value):\n    """Summary.\n\n    ```text\n    Args: fake content.\n    ```\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_ignores_section_like_trailing_content_inside_existing_section_body() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Args:\n        value: Description.\n            Returns: embedded text.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_ignores_unrecognized_same_line_colon_paragraphs() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Parameters: value : int.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_ignores_ordinary_paragraph_lines_after_summary() -> None:
    source = 'def function(value):\n    """Summary.\n\n    More detail without a section header.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_ignored_outside_google_convention() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Args: value: Description.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF403",), docstring_convention=DocstringConvention.NUMPY))

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings
