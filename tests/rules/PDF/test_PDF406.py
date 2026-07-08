# First-party imports
from pydocformatter import formatter, rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definitions.PDF.PDF406_empty_section import PDF406EmptySection


def format_source(source: str, *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Format source with PDF406 selected."""
    resolved_settings = CheckSettings(select=("PDF406",), docstring_convention=DocstringConvention.GOOGLE) if settings is None else settings
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=True)


def test_reports_empty_google_sections_without_fixing() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Args:\n\n    Returns:\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.rule for finding in result.unfixed_findings) == (PDF406EmptySection.meta, PDF406EmptySection.meta)
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((4,), (6,))
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring section 'Args' should not be empty", "Docstring section 'Returns' should not be empty")


def test_reports_adjacent_header_only_google_sections() -> None:
    source = 'def function(value):\n    """Args:\n    Returns:\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2,), (3,))


def test_accepts_section_with_nonblank_body_content() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Args:\n        value: Description.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_reports_empty_numpy_section_after_underline() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Parameters\n    ----------\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF406",), docstring_convention=DocstringConvention.NUMPY))

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((4,),)


def test_protected_structure_inside_section_counts_as_content() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Examples:\n        ```python\n        call(value)\n        ```\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_rest_like_field_inside_google_section_counts_as_plain_content() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Args:\n        :param value: Description.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_reports_empty_rest_fields() -> None:
    source = 'def function(value):\n    """Summary.\n\n    :param value:\n    :rtype:\n    :raises ValueError: Bad value.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF406",), docstring_convention=DocstringConvention.REST))

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.rule for finding in result.unfixed_findings) == (PDF406EmptySection.meta, PDF406EmptySection.meta)
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((4,), (5,))
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring field ':param value:' should not be empty", "Docstring field ':rtype:' should not be empty")


def test_accepts_rest_fields_with_only_continuation_body_content() -> None:
    source = 'def function(value):\n    """Summary.\n\n    :param value:\n        Description on continuation.\n    :returns:\n        Result on continuation.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF406",), docstring_convention=DocstringConvention.REST))

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_accepts_rest_fields_with_only_protected_continuation_body_content() -> None:
    source = 'def function(value):\n    """Summary.\n\n    :param value:\n        - First choice.\n          Continued choice.\n        - Second choice.\n    :returns:\n        Result.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF406",), docstring_convention=DocstringConvention.REST))

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_rest_fields_are_not_checked_without_rest_convention() -> None:
    source = 'def function(value):\n    """Summary.\n\n    :param value:\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF406",), docstring_convention=DocstringConvention.NONE))

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_ignored_without_google_or_numpy_convention() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Args:\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF406",), docstring_convention=DocstringConvention.NONE))

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings
