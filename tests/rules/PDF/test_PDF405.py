import pydocformatter.formatter as formatter
import pydocformatter.rules_selection as rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definitions.PDF.PDF405_section_order import PDF405SectionOrder


def format_source(source: str, *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Format source with PDF405 selected."""
    resolved_settings = CheckSettings(select=("PDF405",), docstring_convention=DocstringConvention.GOOGLE) if settings is None else settings
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=True)


def test_reports_google_sections_after_later_ranked_sections() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Returns:\n        int: Result.\n\n    Args:\n        value: Description.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.rule for finding in result.unfixed_findings) == (PDF405SectionOrder.meta,)
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((7,),)


def test_allows_duplicate_and_same_rank_google_sections() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Args:\n        value: Description.\n\n    Keyword Args:\n        option: Option.\n\n    Returns:\n        int: Result.\n\n    Yields:\n        int: Streamed result.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_reports_each_google_section_after_highest_preceding_rank() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Raises:\n        ValueError: Bad value.\n\n    Returns:\n        int: Result.\n\n    Args:\n        value: Description.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((7,), (10,))


def test_unordered_google_narrative_sections_do_not_affect_order() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Examples:\n        Example text.\n\n    Args:\n        value: Description.\n\n    Returns:\n        int: Result.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_unordered_google_sections_do_not_reset_highest_order_rank() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Returns:\n        int: Result.\n\n    Examples:\n        Example text.\n\n    Args:\n        value: Description.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((10,),)


def test_google_section_order_is_case_insensitive() -> None:
    source = 'def function(value):\n    """Summary.\n\n    RETURNS:\n        int: Result.\n\n    args:\n        value: Description.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((7,),)


def test_reports_numpy_sections_after_later_ranked_sections() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Returns\n    -------\n    int\n        Result.\n\n    Parameters\n    ----------\n    value : int\n        Description.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF405",), docstring_convention=DocstringConvention.NUMPY))

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((9,),)


def test_allows_duplicate_and_same_rank_numpy_sections() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Warns\n    -----\n    RuntimeWarning\n        Warning.\n\n    Warnings\n    --------\n    UserWarning\n        Warning.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF405",), docstring_convention=DocstringConvention.NUMPY))

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_ignored_without_google_or_numpy_convention() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Returns:\n        int: Result.\n\n    Args:\n        value: Description.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF405",), docstring_convention=DocstringConvention.NONE))

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings
