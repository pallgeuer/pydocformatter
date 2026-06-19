import pydocformatter.formatter as formatter
import pydocformatter.rules_selection as rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definitions.PDF.PDF404_section_name_trailing_colon import PDF404SectionNameTrailingColon


def format_source(source: str, *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Format source with PDF404 selected."""
    resolved_settings = CheckSettings(select=("PDF404",), docstring_convention=DocstringConvention.GOOGLE) if settings is None else settings
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=True)


def test_adds_missing_google_section_name_colon() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Args   \n        value: Description.\n    """\n'
    result = format_source(source)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    Args:\n        value: Description.\n    """\n'
    assert result.fixed_findings[PDF404SectionNameTrailingColon.meta] == 1
    assert PDF404SectionNameTrailingColon.meta.name == "section-name-trailing-colon"
    assert not format_source(result.new_source).modified


def test_adds_missing_colons_to_multiple_google_sections_in_one_docstring() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Args\n        value: Description.\n\n    Returns\t\n        int: Result.\n    """\n'
    result = format_source(source)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    Args:\n        value: Description.\n\n    Returns:\n        int: Result.\n    """\n'
    assert result.fixed_findings[PDF404SectionNameTrailingColon.meta] == 1
    assert not format_source(result.new_source).modified


def test_preserves_noncanonical_section_name_case_when_adding_colon() -> None:
    source = 'def function(value):\n    """Summary.\n\n    args\t \n        value: Description.\n    """\n'
    result = format_source(source)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    args:\n        value: Description.\n    """\n'
    assert result.fixed_findings[PDF404SectionNameTrailingColon.meta] == 1
    assert not format_source(result.new_source).modified


def test_leaves_section_name_with_colon_and_trailing_whitespace_to_whitespace_rules() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Args:   \n        value: Description.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_ignores_unrecognized_missing_colon_paragraphs() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Parameters\n    value : int\n        Description.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_reports_unsafe_missing_google_section_name_colon_without_fixing() -> None:
    source = 'def function(value):\n    ("Summary.\\n\\n"\n     "Args\\n"\n     "    value: Description.")\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2, 3, 4),)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring section 'Args' should end with a colon",)


def test_ignored_outside_google_convention() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Args\n        value: Description.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF404",), docstring_convention=DocstringConvention.NUMPY))

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings
