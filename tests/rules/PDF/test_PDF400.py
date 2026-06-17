import pydocformatter.formatter as formatter
import pydocformatter.rules_selection as rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definitions.PDF.PDF400_section_name_capitalization import PDF400SectionNameCapitalization


def format_source(source: str, *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Format source with PDF400 selected."""
    resolved_settings = CheckSettings(select=("PDF400",), docstring_convention=DocstringConvention.GOOGLE) if settings is None else settings
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=True)


def test_capitalizes_google_section_names() -> None:
    source = 'def function(value):\n    """Summary.\n\n    args:\n        value: Description.\n\n    keyword arguments:\n        option: Option.\n    """\n'
    result = format_source(source)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    Args:\n        value: Description.\n\n    Keyword Arguments:\n        option: Option.\n    """\n'
    assert result.fixed_findings[PDF400SectionNameCapitalization.meta] == 1
    assert not format_source(result.new_source).modified


def test_capitalizes_numpy_section_names_and_preserves_underlines() -> None:
    source = 'def function(value):\n    """Summary.\n\n    parameters\n    ----------\n    value : int\n        Description.\n    """\n'
    settings = CheckSettings(select=("PDF400",), docstring_convention=DocstringConvention.NUMPY)
    result = format_source(source, settings=settings)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    Parameters\n    ----------\n    value : int\n        Description.\n    """\n'
    assert result.fixed_findings[PDF400SectionNameCapitalization.meta] == 1
    assert not format_source(result.new_source, settings=settings).modified


def test_capitalizes_section_name_without_adding_missing_colon() -> None:
    source = 'def function(value):\n    """Summary.\n\n    args\n        value: Description.\n    """\n'
    result = format_source(source)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    Args\n        value: Description.\n    """\n'
    assert result.fixed_findings[PDF400SectionNameCapitalization.meta] == 1
    assert not format_source(result.new_source).modified


def test_capitalizes_indented_malformed_section_name_without_changing_indentation() -> None:
    source = 'def function(value):\n    """Summary.\n\n      args:\n          value: Description.\n    """\n'
    result = format_source(source)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n      Args:\n          value: Description.\n    """\n'
    assert result.fixed_findings[PDF400SectionNameCapitalization.meta] == 1
    assert not format_source(result.new_source).modified


def test_google_convention_does_not_capitalize_numpy_only_section_names() -> None:
    source = 'def function(value):\n    """Summary.\n\n    parameters\n    ----------\n    value : int\n        Description.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_reports_unsafe_section_name_capitalization_without_fixing() -> None:
    source = 'def function(value):\n    ("Summary.\\n\\n"\n     "args:\\n"\n     "    value: Description.")\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2, 3, 4),)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring section name 'args' should be capitalized as 'Args'",)


def test_ignored_without_google_or_numpy_convention() -> None:
    source = 'def function(value):\n    """Summary.\n\n    args:\n        value: Description.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF400",), docstring_convention=DocstringConvention.NONE))

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings
