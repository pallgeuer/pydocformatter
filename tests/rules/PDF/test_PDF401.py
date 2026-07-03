import pydocformatter.formatter as formatter
import pydocformatter.rules_selection as rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definitions.PDF.PDF401_section_name_pluralization import PDF401SectionNamePluralization


def format_source(source: str, *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Format source with PDF401 selected."""
    resolved_settings = CheckSettings(select=("PDF401",), docstring_convention=DocstringConvention.GOOGLE) if settings is None else settings
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=True)


def test_pluralizes_google_section_names() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Arg:\n        value: Description.\n\n    Raise:\n        ValueError: Bad value.\n\n    Attribute:\n        name (str): Name.\n\n    Return:\n        int: Result.\n\n    Yield:\n        int: Item.\n\n    Example:\n        function(1)\n\n    Method:\n        run: Run it.\n\n    Note:\n        Worth noting.\n\n    Reference:\n        docs.\n\n    Warning:\n        Be careful.\n\n    Warn:\n        RuntimeWarning: May warn.\n    """\n'
    result = format_source(source)

    assert (
        result.new_source
        == 'def function(value):\n    """Summary.\n\n    Args:\n        value: Description.\n\n    Raises:\n        ValueError: Bad value.\n\n    Attributes:\n        name (str): Name.\n\n    Returns:\n        int: Result.\n\n    Yields:\n        int: Item.\n\n    Examples:\n        function(1)\n\n    Methods:\n        run: Run it.\n\n    Notes:\n        Worth noting.\n\n    References:\n        docs.\n\n    Warnings:\n        Be careful.\n\n    Warns:\n        RuntimeWarning: May warn.\n    """\n'
    )
    assert result.fixed_findings[PDF401SectionNamePluralization.meta] == 1
    assert not format_source(result.new_source).modified


def test_pluralizes_long_google_section_names_without_term_normalization() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Keyword Argument:\n        value: Description.\n\n    Other Arg:\n        value: More detail.\n    """\n'
    result = format_source(source)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    Keyword Arguments:\n        value: Description.\n\n    Other Args:\n        value: More detail.\n    """\n'
    assert result.fixed_findings[PDF401SectionNamePluralization.meta] == 1
    assert not format_source(result.new_source).modified


def test_pluralizes_colonless_google_section_names_without_changing_suffix() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Return   \n        int: Result.\n\n    Example\n        function(1)\n    """\n'
    result = format_source(source)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    Returns   \n        int: Result.\n\n    Examples\n        function(1)\n    """\n'
    assert result.fixed_findings[PDF401SectionNamePluralization.meta] == 1
    assert not format_source(result.new_source).modified


def test_pluralizes_numpy_section_names() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Parameter\n    ---------\n    value : int\n        Description.\n\n    Receive\n    -------\n    event : str\n        Event.\n\n    Return\n    ------\n    int\n        Result.\n\n    Yield\n    -----\n    int\n        Item.\n\n    Raise\n    -----\n    ValueError\n        Bad value.\n\n    Warning\n    -------\n    RuntimeWarning\n        May warn.\n\n    Warn\n    ----\n    UserWarning\n        May warn.\n\n    Attribute\n    ---------\n    name : str\n        Name.\n\n    Method\n    ------\n    run : Callable[[], None]\n        Run it.\n\n    Note\n    ----\n    Worth noting.\n\n    Example\n    -------\n    function(1)\n\n    Reference\n    ---------\n    docs.\n    """\n'
    settings = CheckSettings(select=("PDF401",), docstring_convention=DocstringConvention.NUMPY)
    result = format_source(source, settings=settings)

    assert (
        result.new_source
        == 'def function(value):\n    """Summary.\n\n    Parameters\n    ---------\n    value : int\n        Description.\n\n    Receives\n    -------\n    event : str\n        Event.\n\n    Returns\n    ------\n    int\n        Result.\n\n    Yields\n    -----\n    int\n        Item.\n\n    Raises\n    -----\n    ValueError\n        Bad value.\n\n    Warnings\n    -------\n    RuntimeWarning\n        May warn.\n\n    Warns\n    ----\n    UserWarning\n        May warn.\n\n    Attributes\n    ---------\n    name : str\n        Name.\n\n    Methods\n    ------\n    run : Callable[[], None]\n        Run it.\n\n    Notes\n    ----\n    Worth noting.\n\n    Examples\n    -------\n    function(1)\n\n    References\n    ---------\n    docs.\n    """\n'
    )
    assert result.fixed_findings[PDF401SectionNamePluralization.meta] == 1
    assert not format_source(result.new_source, settings=settings).modified


def test_pluralizes_numpy_other_parameter_terms_without_term_normalization() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Other Param\n    -----------\n    value : int\n        Description.\n    """\n'
    settings = CheckSettings(select=("PDF401",), docstring_convention=DocstringConvention.NUMPY)
    result = format_source(source, settings=settings)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    Other Params\n    -----------\n    value : int\n        Description.\n    """\n'
    assert result.fixed_findings[PDF401SectionNamePluralization.meta] == 1
    assert not format_source(result.new_source, settings=settings).modified


def test_ordered_section_name_rules_converge_from_lowercase_singular_equivalent_term() -> None:
    source = 'def function(value):\n    """Summary.\n\n    keyword argument:\n        value: Description.\n    """\n'
    settings = CheckSettings(select=("PDF400", "PDF401", "PDF402"), docstring_convention=DocstringConvention.GOOGLE)
    result = format_source(source, settings=settings)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    Keyword Args:\n        value: Description.\n    """\n'
    assert result.fixed_findings[PDF401SectionNamePluralization.meta] == 1
    assert not format_source(result.new_source, settings=settings).modified


def test_ordered_numpy_section_name_rules_converge_from_singular_equivalent_term() -> None:
    source = 'def function(value):\n    """Summary.\n\n    other param\n    -----------\n    value : int\n        Description.\n    """\n'
    settings = CheckSettings(select=("PDF400", "PDF401", "PDF402"), docstring_convention=DocstringConvention.NUMPY)
    result = format_source(source, settings=settings)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    Other Parameters\n    -----------\n    value : int\n        Description.\n    """\n'
    assert result.fixed_findings[PDF401SectionNamePluralization.meta] == 1
    assert not format_source(result.new_source, settings=settings).modified


def test_reports_unsafe_section_name_pluralization_without_fixing() -> None:
    source = 'def function(value):\n    ("Summary.\\n\\n"\n     "Return:\\n"\n     "    int: Result.")\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2, 3, 4),)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring section name 'Return' should use plural form 'Returns'",)


def test_ignored_without_google_or_numpy_convention() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Return:\n        int: Result.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF401",), docstring_convention=DocstringConvention.NONE))

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_normalizes_rest_singular_and_plural_field_spellings() -> None:
    source = 'def function(value):\n    """Summary.\n\n    :returns: Result.\n    :yields: Item.\n    :raise ValueError: Bad value.\n    """\n'
    settings = CheckSettings(select=("PDF401",), docstring_convention=DocstringConvention.REST)
    result = format_source(source, settings=settings)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    :return: Result.\n    :yield: Item.\n    :raises ValueError: Bad value.\n    """\n'
    assert result.fixed_findings[PDF401SectionNamePluralization.meta] == 1
    assert not format_source(result.new_source, settings=settings).modified


def test_normalizes_mixed_case_rest_plural_field_spellings_to_preferred_spelling() -> None:
    source = 'def function(value):\n    """Summary.\n\n    :RETURNS: Result.\n    :YIELDS: Item.\n    :Raise ValueError: Bad value.\n    """\n'
    settings = CheckSettings(select=("PDF401",), docstring_convention=DocstringConvention.REST)
    result = format_source(source, settings=settings)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    :return: Result.\n    :yield: Item.\n    :raises ValueError: Bad value.\n    """\n'
    assert result.fixed_findings[PDF401SectionNamePluralization.meta] == 1
    assert not format_source(result.new_source, settings=settings).modified


def test_preserves_rest_field_arguments_spacing_and_continuation_content() -> None:
    source = 'def function(value):\n    """Summary.\n\n    :returns  : Result.\n        Continued result.\n    """\n'
    settings = CheckSettings(select=("PDF401",), docstring_convention=DocstringConvention.REST)
    result = format_source(source, settings=settings)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    :return  : Result.\n        Continued result.\n    """\n'
    assert result.fixed_findings[PDF401SectionNamePluralization.meta] == 1


def test_reports_unsafe_rest_field_pluralization_without_fixing() -> None:
    source = 'def function(value):\n    ("Summary.\\n\\n"\n     ":returns: Result.")\n'
    settings = CheckSettings(select=("PDF401",), docstring_convention=DocstringConvention.REST)
    result = format_source(source, settings=settings)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2, 3),)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring reStructuredText field name 'returns' should use preferred spelling 'return'",)
