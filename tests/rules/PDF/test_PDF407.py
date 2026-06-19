import pydocformatter.formatter as formatter
import pydocformatter.rules_selection as rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definitions.PDF.PDF407_section_order import PDF407SectionOrder


def format_source(source: str, *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Format source with PDF407 selected."""
    resolved_settings = CheckSettings(select=("PDF407",), docstring_convention=DocstringConvention.GOOGLE) if settings is None else settings
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=True)


def test_reports_google_sections_after_later_ranked_sections() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Returns:\n        int: Result.\n\n    Args:\n        value: Description.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.rule for finding in result.unfixed_findings) == (PDF407SectionOrder.meta,)
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((7,),)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring section 'Args' should appear before 'Returns'",)


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
    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Docstring section 'Returns' should appear before 'Raises'",
        "Docstring section 'Args' should appear before 'Raises'",
    )


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


def test_google_singular_ordered_aliases_use_plural_order() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Warn:\n        RuntimeWarning: Warning.\n\n    Return:\n        int: Result.\n\n    Arg:\n        value: Description.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((7,), (10,))


def test_reports_numpy_sections_after_later_ranked_sections() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Returns\n    -------\n    int\n        Result.\n\n    Parameters\n    ----------\n    value : int\n        Description.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF407",), docstring_convention=DocstringConvention.NUMPY))

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((9,),)


def test_allows_duplicate_and_same_rank_numpy_sections() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Warns\n    -----\n    RuntimeWarning\n        Warning.\n\n    Warnings\n    --------\n    UserWarning\n        Warning.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF407",), docstring_convention=DocstringConvention.NUMPY))

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_numpy_singular_ordered_aliases_use_plural_order() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Warn\n    ----\n    RuntimeWarning\n        Warning.\n\n    Return\n    ------\n    int\n        Result.\n\n    Parameter\n    ---------\n    value : int\n        Description.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF407",), docstring_convention=DocstringConvention.NUMPY))

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((9,), (14,))


def test_reports_rest_fields_after_later_ranked_fields() -> None:
    source = 'def function(value):\n    """Summary.\n\n    :returns: Result.\n    :param value: Description.\n    :raises ValueError: Bad value.\n    :rtype: str\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF407",), docstring_convention=DocstringConvention.REST))

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.rule for finding in result.unfixed_findings) == (PDF407SectionOrder.meta, PDF407SectionOrder.meta)
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((5,), (7,))
    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Docstring field ':param value:' should appear before ':returns:'",
        "Docstring field ':rtype:' should appear before ':raises ValueError:'",
    )


def test_reports_type_rest_field_after_return_field() -> None:
    source = 'def function(value):\n    """Summary.\n\n    :returns: Result.\n    :type value: int\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF407",), docstring_convention=DocstringConvention.REST))

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.rule for finding in result.unfixed_findings) == (PDF407SectionOrder.meta,)
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((5,),)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring field ':type value:' should appear before ':returns:'",)


def test_unordered_rest_fields_do_not_affect_order() -> None:
    source = 'def function(value):\n    """Summary.\n\n    :meta private: yes\n    :param value: Description.\n    :returns: Result.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF407",), docstring_convention=DocstringConvention.REST))

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_rest_unknown_fields_do_not_reset_highest_rank_and_return_yield_share_rank() -> None:
    source = 'def function(value):\n    """Summary.\n\n    :returns: Result.\n    :yields: Streamed result.\n    :meta private: yes\n    :param value: Description.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF407",), docstring_convention=DocstringConvention.REST))

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((7,),)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring field ':param value:' should appear before ':yields:'",)


def test_ignored_without_google_or_numpy_convention() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Returns:\n        int: Result.\n\n    Args:\n        value: Description.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF407",), docstring_convention=DocstringConvention.NONE))

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings
