import pydocformatter.formatter as formatter
import pydocformatter.rules_selection as rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definitions.PDF.PDF409_docstring_entry_spacing import PDF409DocstringEntrySpacing


def format_source(source: str, *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Format source with PDF409 selected."""
    resolved_settings = CheckSettings(select=("PDF409",), docstring_convention=DocstringConvention.GOOGLE) if settings is None else settings
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=True)


def test_normalizes_google_entry_spacing() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Args:\n        value   ( int ) : Description.\n\n    Returns:\n        list[ str ] : Result.\n    """\n'
    result = format_source(source)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    Args:\n        value (int): Description.\n\n    Returns:\n        list[ str ]: Result.\n    """\n'
    assert result.fixed_findings[PDF409DocstringEntrySpacing.meta] == 1
    assert not format_source(result.new_source).modified


def test_normalizes_google_star_dotted_yield_and_exception_entries() -> None:
    source = 'def function(*args, **kwargs):\n    """Summary.\n\n    Args:\n        *args   ( tuple[str, ...] ) : Positional values.\n        **kwargs   ( dict[str, object] ) :\n        model.value : Dotted value.\n\n    Yields:\n        tuple[ int, int ] : Pair.\n\n    Raises:\n        ValueError   : Bad value.\n    """\n'
    result = format_source(source)

    assert (
        result.new_source
        == 'def function(*args, **kwargs):\n    """Summary.\n\n    Args:\n        *args (tuple[str, ...]): Positional values.\n        **kwargs (dict[str, object]):\n        model.value: Dotted value.\n\n    Yields:\n        tuple[ int, int ]: Pair.\n\n    Raises:\n        ValueError: Bad value.\n    """\n'
    )
    assert result.fixed_findings[PDF409DocstringEntrySpacing.meta] == 1
    assert not format_source(result.new_source).modified


def test_preserves_google_exception_list_spelling_while_normalizing_spacing() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Raises:\n        `ValueError` | TypeError   : Bad value.\n    """\n'
    result = format_source(source)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    Raises:\n        `ValueError` | TypeError: Bad value.\n    """\n'
    assert result.fixed_findings[PDF409DocstringEntrySpacing.meta] == 1
    assert not format_source(result.new_source).modified


def test_preserves_google_exception_parenthetical_while_normalizing_spacing() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Raises:\n        ValueError (when bad)   : Bad value.\n    """\n'
    result = format_source(source)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    Raises:\n        ValueError (when bad): Bad value.\n    """\n'
    assert result.fixed_findings[PDF409DocstringEntrySpacing.meta] == 1
    assert not format_source(result.new_source).modified


def test_preserves_numpy_and_rest_exception_list_spelling_while_normalizing_spacing() -> None:
    numpy_source = 'def function(value):\n    """Summary.\n\n    Raises\n    ------\n    `ValueError` | TypeError  :  Bad value.\n    """\n'
    rest_source = 'def function(value):\n    """Summary.\n\n    :raises   `ValueError` | TypeError : Bad value.\n    """\n'
    numpy_settings = CheckSettings(select=("PDF409",), docstring_convention=DocstringConvention.NUMPY)
    rest_settings = CheckSettings(select=("PDF409",), docstring_convention=DocstringConvention.REST)
    numpy_result = format_source(numpy_source, settings=numpy_settings)
    rest_result = format_source(rest_source, settings=rest_settings)

    assert numpy_result.new_source == 'def function(value):\n    """Summary.\n\n    Raises\n    ------\n    `ValueError` | TypeError: Bad value.\n    """\n'
    assert rest_result.new_source == 'def function(value):\n    """Summary.\n\n    :raises `ValueError` | TypeError: Bad value.\n    """\n'
    assert numpy_result.fixed_findings[PDF409DocstringEntrySpacing.meta] == 1
    assert rest_result.fixed_findings[PDF409DocstringEntrySpacing.meta] == 1
    assert not format_source(numpy_result.new_source, settings=numpy_settings).modified
    assert not format_source(rest_result.new_source, settings=rest_settings).modified


def test_normalizes_google_entry_prefix_without_rewriting_continuation_lines() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Args:\n        value   ( int ) :\n            Keep   internal   spacing.\n            And trailing prefix behavior.\n    """\n'
    result = format_source(source)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    Args:\n        value (int):\n            Keep   internal   spacing.\n            And trailing prefix behavior.\n    """\n'
    assert result.fixed_findings[PDF409DocstringEntrySpacing.meta] == 1
    assert not format_source(result.new_source).modified


def test_normalizes_numpy_entry_spacing() -> None:
    source = 'def function(first, second):\n    """Summary.\n\n    Parameters\n    ----------\n    first,second:int\n        Values.\n    """\n'
    settings = CheckSettings(select=("PDF409",), docstring_convention=DocstringConvention.NUMPY)
    result = format_source(source, settings=settings)

    assert result.new_source == 'def function(first, second):\n    """Summary.\n\n    Parameters\n    ----------\n    first, second : int\n        Values.\n    """\n'
    assert result.fixed_findings[PDF409DocstringEntrySpacing.meta] == 1
    assert not format_source(result.new_source, settings=settings).modified


def test_normalizes_numpy_multiple_sections_and_preserves_descriptions() -> None:
    source = 'def function(first, second):\n    """Summary.\n\n    Parameters\n    ----------\n    first,second  :  tuple[ int, int ]\n        Values stay as written.\n\n    Returns\n    -------\n    dict[ str, int ]\n        Mapping values.\n\n    Raises\n    ------\n    ValueError\n        Bad value.\n    """\n'
    settings = CheckSettings(select=("PDF409",), docstring_convention=DocstringConvention.NUMPY)
    result = format_source(source, settings=settings)

    assert (
        result.new_source
        == 'def function(first, second):\n    """Summary.\n\n    Parameters\n    ----------\n    first, second : tuple[ int, int ]\n        Values stay as written.\n\n    Returns\n    -------\n    dict[ str, int ]\n        Mapping values.\n\n    Raises\n    ------\n    ValueError\n        Bad value.\n    """\n'
    )
    assert result.fixed_findings[PDF409DocstringEntrySpacing.meta] == 1
    assert not format_source(result.new_source, settings=settings).modified


def test_normalizes_rest_field_spacing() -> None:
    source = 'def function(value):\n    """Summary.\n\n    :param   int   value : Description.\n    :type value:int\n    :raises   ValueError : Bad value.\n    """\n'
    settings = CheckSettings(select=("PDF409",), docstring_convention=DocstringConvention.REST)
    result = format_source(source, settings=settings)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    :param int value: Description.\n    :type value: int\n    :raises ValueError: Bad value.\n    """\n'
    assert result.fixed_findings[PDF409DocstringEntrySpacing.meta] == 1
    assert not format_source(result.new_source, settings=settings).modified


def test_normalizes_rest_return_yield_and_argumentless_type_fields() -> None:
    source = 'def function(value):\n    """Summary.\n\n    :returns  : Result.\n    :rtype:list[str]\n    :yield   value :\n    :ytype value: Iterator[int]\n    """\n'
    settings = CheckSettings(select=("PDF409",), docstring_convention=DocstringConvention.REST)
    result = format_source(source, settings=settings)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    :returns: Result.\n    :rtype: list[str]\n    :yield value:\n    :ytype value: Iterator[int]\n    """\n'
    assert result.fixed_findings[PDF409DocstringEntrySpacing.meta] == 1
    assert not format_source(result.new_source, settings=settings).modified


def test_normalizes_rest_no_argument_field_with_space_before_colon() -> None:
    source = 'def function(value):\n    """Summary.\n\n    :rtype : list[str]\n    """\n'
    settings = CheckSettings(select=("PDF409",), docstring_convention=DocstringConvention.REST)
    result = format_source(source, settings=settings)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    :rtype: list[str]\n    """\n'
    assert result.fixed_findings[PDF409DocstringEntrySpacing.meta] == 1
    assert not result.unfixed_findings
    assert not format_source(result.new_source, settings=settings).modified


def test_leaves_malformed_and_protected_google_text_unchanged() -> None:
    source = (
        'def function(value):\n    """Summary.\n\n    Args:\n        value   ( int ) Description missing colon.\n\n        ```text\n        protected   ( int ) : Not an entry.\n        ```\n    """\n'
    )
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_literal_block_parsing_setting_controls_entry_spacing_inside_literal_blocks() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Args:\n        Example::\n\n            literal   ( int ) : Entry-like text.\n    """\n'
    unprotected_settings = CheckSettings(select=("PDF409",), docstring_convention=DocstringConvention.GOOGLE, docstring_parse_literal_blocks=False)
    protected = format_source(source)
    unprotected = format_source(source, settings=unprotected_settings)

    assert protected.new_source == source
    assert not protected.fixed_findings
    assert not protected.unfixed_findings
    assert unprotected.new_source == 'def function(value):\n    """Summary.\n\n    Args:\n        Example::\n\n            literal (int): Entry-like text.\n    """\n'
    assert unprotected.fixed_findings[PDF409DocstringEntrySpacing.meta] == 1
    assert not format_source(unprotected.new_source, settings=unprotected_settings).modified


def test_reports_unsafe_entry_spacing_without_fixing() -> None:
    source = 'def function(value):\n    ("Summary.\\n\\n"\n     "Args:\\n"\n     "    value   (int) : Description.")\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2, 3, 4),)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring convention entry spacing should be normalized",)


def test_ignored_without_supported_convention() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Args:\n        value   (int) : Description.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF409",), docstring_convention=DocstringConvention.NONE))

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings
