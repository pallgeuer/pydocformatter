import pydocformatter.formatter as formatter
import pydocformatter.rules_selection as rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definitions.PDF.PDF402_section_name_term_normalization import PDF402SectionNameTermNormalization


def format_source(source: str, *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Format source with PDF402 selected."""
    resolved_settings = CheckSettings(select=("PDF402",), docstring_convention=DocstringConvention.GOOGLE) if settings is None else settings
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=True)


def test_normalizes_google_section_name_terms() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Arguments:\n        value: Description.\n\n    Keyword Arguments:\n        option: Option.\n\n    Other Arguments:\n        other: Other value.\n    """\n'
    result = format_source(source)

    assert (
        result.new_source
        == 'def function(value):\n    """Summary.\n\n    Args:\n        value: Description.\n\n    Keyword Args:\n        option: Option.\n\n    Other Args:\n        other: Other value.\n    """\n'
    )
    assert result.fixed_findings[PDF402SectionNameTermNormalization.meta] == 1
    assert not format_source(result.new_source).modified


def test_normalizes_numpy_section_name_terms_without_rewriting_underline() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Other Params\n    ------------\n    value : int\n        Description.\n    """\n'
    settings = CheckSettings(select=("PDF402",), docstring_convention=DocstringConvention.NUMPY)
    result = format_source(source, settings=settings)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    Other Parameters\n    ------------\n    value : int\n        Description.\n    """\n'
    assert result.fixed_findings[PDF402SectionNameTermNormalization.meta] == 1
    assert not format_source(result.new_source, settings=settings).modified


def test_normalizes_colonless_google_section_name_terms_without_changing_suffix() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Other Arguments   \n        value: Description.\n    """\n'
    result = format_source(source)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    Other Args   \n        value: Description.\n    """\n'
    assert result.fixed_findings[PDF402SectionNameTermNormalization.meta] == 1
    assert not format_source(result.new_source).modified


def test_does_not_term_normalize_singular_google_names_owned_by_pluralization_rule() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Argument:\n        value: Description.\n\n    Keyword Argument:\n        option: Option.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_preserves_distinct_google_warning_section_terms() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Warning:\n        Be careful.\n\n    Warnings:\n        Also be careful.\n\n    Warns:\n        RuntimeWarning: May warn.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_reports_unsafe_section_name_term_normalization_without_fixing() -> None:
    source = 'def function(value):\n    ("Summary.\\n\\n"\n     "Arguments:\\n"\n     "    value: Description.")\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2, 3, 4),)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring section name 'Arguments' should use equivalent term 'Args'",)


def test_ignored_without_google_or_numpy_convention() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Arguments:\n        value: Description.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF402",), docstring_convention=DocstringConvention.NONE))

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_normalizes_rest_field_terms() -> None:
    source = 'def function(value):\n    """Summary.\n\n    :parameter value: Description.\n    :arg other: Other value.\n    :argument third: Third value.\n    :key option: Option.\n    :keyword name: Name.\n    :kwarg flag: Flag.\n    :except ValueError: Bad value.\n    :exception RuntimeError: Worse value.\n    """\n'
    settings = CheckSettings(select=("PDF402",), docstring_convention=DocstringConvention.REST)
    result = format_source(source, settings=settings)

    assert (
        result.new_source
        == 'def function(value):\n    """Summary.\n\n    :param value: Description.\n    :param other: Other value.\n    :param third: Third value.\n    :param option: Option.\n    :param name: Name.\n    :param flag: Flag.\n    :raises ValueError: Bad value.\n    :raises RuntimeError: Worse value.\n    """\n'
    )
    assert result.fixed_findings[PDF402SectionNameTermNormalization.meta] == 1
    assert not format_source(result.new_source, settings=settings).modified


def test_ordered_rest_field_name_rules_converge_from_mixed_case_plural_equivalent_terms() -> None:
    source = 'def function(value):\n    """Summary.\n\n    :PARAMETER value: Description.\n    :RETURNS: Result.\n    :Exception ValueError: Bad value.\n    :KEY option: Option.\n    """\n'
    settings = CheckSettings(select=("PDF400", "PDF401", "PDF402"), docstring_convention=DocstringConvention.REST)
    result = format_source(source, settings=settings)

    assert (
        result.new_source == 'def function(value):\n    """Summary.\n\n    :param value: Description.\n    :return: Result.\n    :raises ValueError: Bad value.\n    :param option: Option.\n    """\n'
    )
    assert result.fixed_findings[PDF402SectionNameTermNormalization.meta] == 1
    assert not format_source(result.new_source, settings=settings).modified


def test_does_not_term_normalize_distinct_rest_fields() -> None:
    source = 'def function(value):\n    """Summary.\n\n    :type value: int\n    :rtype: str\n    :ytype: Iterator[str]\n    :meta private: yes\n    """\n'
    settings = CheckSettings(select=("PDF402",), docstring_convention=DocstringConvention.REST)
    result = format_source(source, settings=settings)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_reports_unsafe_rest_field_term_normalization_without_fixing() -> None:
    source = 'def function(value):\n    ("Summary.\\n\\n"\n     ":parameter value: Description.")\n'
    settings = CheckSettings(select=("PDF402",), docstring_convention=DocstringConvention.REST)
    result = format_source(source, settings=settings)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2, 3),)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring reStructuredText field name 'parameter' should use equivalent term 'param'",)
