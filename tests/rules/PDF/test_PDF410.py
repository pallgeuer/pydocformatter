import pydocformatter.formatter as formatter
import pydocformatter.rules_selection as rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definitions.PDF.PDF409_convention_entry_spacing import PDF409ConventionEntrySpacing
from pydocformatter.rules.definitions.PDF.PDF410_exception_entry_normalization import PDF410ExceptionEntryNormalization


def format_source(source: str, *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Format source with PDF410 selected."""
    resolved_settings = CheckSettings(select=("PDF410",), docstring_convention=DocstringConvention.GOOGLE) if settings is None else settings
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=True)


def test_normalizes_google_raises_and_warns_exception_entries() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Raises:\n        `ValueError` | mypkg.CustomError , TypeError   : Bad value.\n\n    Warns:\n        `RuntimeWarning`|UserWarning : Bad warning.\n    """\n'
    result = format_source(source)

    assert (
        result.new_source
        == 'def function(value):\n    """Summary.\n\n    Raises:\n        ValueError, mypkg.CustomError, TypeError: Bad value.\n\n    Warns:\n        RuntimeWarning, UserWarning: Bad warning.\n    """\n'
    )
    assert result.fixed_findings[PDF410ExceptionEntryNormalization.meta] == 1
    assert not format_source(result.new_source).modified


def test_leaves_canonical_google_exception_with_parenthetical_unchanged() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Raises:\n        ConnectionError (network): Cannot connect.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_leaves_google_warning_admonition_entries_unchanged() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Warning:\n        `RuntimeWarning` | UserWarning : Be careful.\n\n    Warnings:\n        `DeprecationWarning`|FutureWarning : Also be careful.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_pdf409_and_pdf410_converge_on_overlapping_google_exception_entry() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Raises:\n        `ValueError` | TypeError   :\n            Keep   continuation   spacing.\n    """\n'
    settings = CheckSettings(select=("PDF409", "PDF410"), docstring_convention=DocstringConvention.GOOGLE)
    result = format_source(source, settings=settings)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    Raises:\n        ValueError, TypeError:\n            Keep   continuation   spacing.\n    """\n'
    assert result.fixed_findings[PDF409ConventionEntrySpacing.meta] == 1
    assert result.fixed_findings[PDF410ExceptionEntryNormalization.meta] == 1
    assert not format_source(result.new_source, settings=settings).modified


def test_normalizes_numpy_raises_and_warning_entries() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Raises\n    ------\n    `ValueError` | errors.CustomError\n        Bad value.\n\n    Warnings\n    --------\n    `RuntimeWarning`,UserWarning\n        Bad warning.\n    """\n'
    settings = CheckSettings(select=("PDF410",), docstring_convention=DocstringConvention.NUMPY)
    result = format_source(source, settings=settings)

    assert (
        result.new_source
        == 'def function(value):\n    """Summary.\n\n    Raises\n    ------\n    ValueError, errors.CustomError\n        Bad value.\n\n    Warnings\n    --------\n    RuntimeWarning, UserWarning\n        Bad warning.\n    """\n'
    )
    assert result.fixed_findings[PDF410ExceptionEntryNormalization.meta] == 1
    assert not format_source(result.new_source, settings=settings).modified


def test_normalizes_numpy_colon_style_exception_name_list() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Raises\n    ------\n    ValueError,TypeError : Bad value.\n    """\n'
    settings = CheckSettings(select=("PDF410",), docstring_convention=DocstringConvention.NUMPY)
    result = format_source(source, settings=settings)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    Raises\n    ------\n    ValueError, TypeError: Bad value.\n    """\n'
    assert result.fixed_findings[PDF410ExceptionEntryNormalization.meta] == 1
    assert not format_source(result.new_source, settings=settings).modified


def test_normalizes_rest_exception_field_entries() -> None:
    source = 'def function(value):\n    """Summary.\n\n    :raises   `ValueError` | errors.CustomError : Bad value.\n    :exception `RuntimeError`,TypeError:\n    """\n'
    settings = CheckSettings(select=("PDF410",), docstring_convention=DocstringConvention.REST)
    result = format_source(source, settings=settings)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    :raises ValueError, errors.CustomError: Bad value.\n    :exception RuntimeError, TypeError:\n    """\n'
    assert result.fixed_findings[PDF410ExceptionEntryNormalization.meta] == 1
    assert not format_source(result.new_source, settings=settings).modified


def test_normalizes_rest_exception_field_aliases_and_whole_list_code_span() -> None:
    source = 'def function(value):\n    """Summary.\n\n    :raise `ValueError | errors.CustomError` : Bad value.\n    :except RuntimeError|TypeError:\n    """\n'
    settings = CheckSettings(select=("PDF410",), docstring_convention=DocstringConvention.REST)
    result = format_source(source, settings=settings)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    :raise ValueError, errors.CustomError: Bad value.\n    :except RuntimeError, TypeError:\n    """\n'
    assert result.fixed_findings[PDF410ExceptionEntryNormalization.meta] == 1
    assert not format_source(result.new_source, settings=settings).modified


def test_leaves_malformed_and_protected_exception_like_text_unchanged() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Raises:\n        If the value is bad: explain the condition.\n\n        ```text\n        `ValueError` | TypeError : Protected text.\n        ```\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_leaves_ambiguous_exception_lists_unchanged() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Raises:\n        ValueError or TypeError: Bad value.\n        ValueError || TypeError: Bad value.\n        ``RuntimeError``: Bad value.\n\n    :raises ValueError || TypeError: Bad value.\n    """\n'
    result = format_source(source)
    rest_result = format_source(source, settings=CheckSettings(select=("PDF410",), docstring_convention=DocstringConvention.REST))

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings
    assert rest_result.new_source == source
    assert not rest_result.fixed_findings
    assert not rest_result.unfixed_findings


def test_skips_malformed_google_exception_block_before_later_valid_entry() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Raises:\n        If the value is bad: explain the condition.\n            `ValueError` | TypeError : prose continuation.\n        `RuntimeError` | LookupError : Bad runtime.\n    """\n'
    result = format_source(source)

    assert (
        result.new_source
        == 'def function(value):\n    """Summary.\n\n    Raises:\n        If the value is bad: explain the condition.\n            `ValueError` | TypeError : prose continuation.\n        RuntimeError, LookupError: Bad runtime.\n    """\n'
    )
    assert result.fixed_findings[PDF410ExceptionEntryNormalization.meta] == 1
    assert not result.unfixed_findings
    assert not format_source(result.new_source).modified


def test_skips_malformed_numpy_exception_block_before_later_valid_entry() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Raises\n    ------\n    If the value is bad: explain the condition.\n        `ValueError` | TypeError : prose continuation.\n    `RuntimeError` | LookupError\n        Bad runtime.\n    """\n'
    settings = CheckSettings(select=("PDF410",), docstring_convention=DocstringConvention.NUMPY)
    result = format_source(source, settings=settings)

    assert (
        result.new_source
        == 'def function(value):\n    """Summary.\n\n    Raises\n    ------\n    If the value is bad: explain the condition.\n        `ValueError` | TypeError : prose continuation.\n    RuntimeError, LookupError\n        Bad runtime.\n    """\n'
    )
    assert result.fixed_findings[PDF410ExceptionEntryNormalization.meta] == 1
    assert not result.unfixed_findings
    assert not format_source(result.new_source, settings=settings).modified


def test_skips_malformed_exception_entries_without_blocking_later_valid_entries() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Raises:\n        ValueError || TypeError: Ambiguous separator.\n        `RuntimeError`: Bad runtime.\n        ValueError,: Trailing separator.\n        `LookupError` | KeyError : Bad lookup.\n    """\n'
    result = format_source(source)

    assert (
        result.new_source
        == 'def function(value):\n    """Summary.\n\n    Raises:\n        ValueError || TypeError: Ambiguous separator.\n        RuntimeError: Bad runtime.\n        ValueError,: Trailing separator.\n        LookupError, KeyError: Bad lookup.\n    """\n'
    )
    assert result.fixed_findings[PDF410ExceptionEntryNormalization.meta] == 1
    assert not result.unfixed_findings
    assert not format_source(result.new_source).modified


def test_leaves_nameless_rest_exception_fields_unchanged() -> None:
    source = 'def function(value):\n    """Summary.\n\n    :raises: `ValueError` | TypeError if parsing fails.\n    """\n'
    settings = CheckSettings(select=("PDF410",), docstring_convention=DocstringConvention.REST)
    result = format_source(source, settings=settings)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_literal_block_parsing_setting_controls_exception_entry_normalization() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Raises:\n        Example::\n\n            `ValueError` | TypeError : Entry-like text.\n    """\n'
    unprotected_settings = CheckSettings(select=("PDF410",), docstring_convention=DocstringConvention.GOOGLE, docstring_parse_literal_blocks=False)
    protected = format_source(source)
    unprotected = format_source(source, settings=unprotected_settings)

    assert protected.new_source == source
    assert not protected.fixed_findings
    assert not protected.unfixed_findings
    assert unprotected.new_source == 'def function(value):\n    """Summary.\n\n    Raises:\n        Example::\n\n            ValueError, TypeError: Entry-like text.\n    """\n'
    assert unprotected.fixed_findings[PDF410ExceptionEntryNormalization.meta] == 1
    assert not format_source(unprotected.new_source, settings=unprotected_settings).modified


def test_reports_unsafe_exception_entry_without_fixing() -> None:
    source = 'def function(value):\n    ("Summary.\\n\\n"\n     "Raises:\\n"\n     "    `ValueError` | TypeError : Bad value.")\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.rule for finding in result.unfixed_findings) == (PDF410ExceptionEntryNormalization.meta,)
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2, 3, 4),)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring exception entry should use canonical spelling",)


def test_ignored_without_supported_convention() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Raises:\n        `ValueError` | TypeError : Bad value.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF410",), docstring_convention=DocstringConvention.NONE))

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings
