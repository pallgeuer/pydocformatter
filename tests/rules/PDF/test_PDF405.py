import pydocformatter.formatter as formatter
import pydocformatter.rules_selection as rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definitions.PDF.PDF405_section_underline_format import PDF405SectionUnderlineFormat


def format_source(source: str, *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Format source with PDF405 selected."""
    resolved_settings = CheckSettings(select=("PDF405",), docstring_convention=DocstringConvention.NUMPY) if settings is None else settings
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=True)


def test_replaces_malformed_numpy_section_underline() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Parameters\n    ===\n    value : int\n        Description.\n    """\n'
    result = format_source(source)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    Parameters\n    ----------\n    value : int\n        Description.\n    """\n'
    assert result.fixed_findings[PDF405SectionUnderlineFormat.meta] == 1
    assert PDF405SectionUnderlineFormat.meta.name == "section-underline-format"
    assert not format_source(result.new_source).modified


def test_replaces_too_short_hyphen_numpy_section_underline() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Parameters\n    -----\n    value : int\n        Description.\n    """\n'
    result = format_source(source)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    Parameters\n    ----------\n    value : int\n        Description.\n    """\n'
    assert result.fixed_findings[PDF405SectionUnderlineFormat.meta] == 1
    assert not format_source(result.new_source).modified


def test_inserts_missing_numpy_section_underline() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Parameters\n    value : int\n        Description.\n    """\n'
    result = format_source(source)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    Parameters\n    ----------\n    value : int\n        Description.\n    """\n'
    assert result.fixed_findings[PDF405SectionUnderlineFormat.meta] == 1


def test_inserts_missing_underline_for_header_only_numpy_section() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Returns\n    """\n'
    result = format_source(source)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    Returns\n    -------\n    """\n'
    assert result.fixed_findings[PDF405SectionUnderlineFormat.meta] == 1
    assert not format_source(result.new_source).modified


def test_inserts_missing_underline_before_same_line_closing_quotes() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Returns"""\n'
    result = format_source(source)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    Returns\n    -------"""\n'
    assert result.fixed_findings[PDF405SectionUnderlineFormat.meta] == 1
    assert not format_source(result.new_source).modified


def test_moves_misplaced_numpy_section_underline_past_blank_lines() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Parameters\n\n    ----------\n    value : int\n        Description.\n    """\n'
    result = format_source(source)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    Parameters\n    ----------\n    value : int\n        Description.\n    """\n'
    assert result.fixed_findings[PDF405SectionUnderlineFormat.meta] == 1


def test_normalizes_multiple_numpy_section_underlines_in_one_docstring() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Parameters\n    ===\n    value : int\n        Description.\n\n    Returns\n    int\n        Result.\n    """\n'
    result = format_source(source)

    assert (
        result.new_source
        == 'def function(value):\n    """Summary.\n\n    Parameters\n    ----------\n    value : int\n        Description.\n\n    Returns\n    -------\n    int\n        Result.\n    """\n'
    )
    assert result.fixed_findings[PDF405SectionUnderlineFormat.meta] == 1
    assert not format_source(result.new_source).modified


def test_numpy_section_underline_uses_section_name_indentation() -> None:
    source = 'def function(value):\n    """Summary.\n\n      Parameters\n    ----------\n      value : int\n          Description.\n    """\n'
    result = format_source(source)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n      Parameters\n      ----------\n      value : int\n          Description.\n    """\n'
    assert result.fixed_findings[PDF405SectionUnderlineFormat.meta] == 1
    assert not format_source(result.new_source).modified


def test_correct_numpy_section_underline_is_unchanged() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Parameters\n    ----------\n    value : int\n        Description.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_reports_unsafe_numpy_section_underline_without_fixing() -> None:
    source = 'def function(value):\n    ("Summary.\\n\\n"\n     "Parameters\\n"\n     "===\\n"\n     "value : int\\n"\n     "    Description.")\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2, 3, 4, 5, 6),)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring section 'Parameters' underline should be normalized",)


def test_ignored_outside_numpy_convention() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Parameters\n    ===\n    value : int\n        Description.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF405",), docstring_convention=DocstringConvention.GOOGLE))

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings
