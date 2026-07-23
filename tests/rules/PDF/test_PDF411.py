# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# First-party imports
import pydocformatter.rules.definitions.PDF.PDF411_type_like_token_spacing_normalization as PDF411_definition
from pydocformatter import formatter, rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definitions.PDF.PDF409_docstring_entry_spacing import PDF409DocstringEntrySpacing
from pydocformatter.rules.definitions.PDF.PDF410_exception_entry_normalization import PDF410ExceptionEntryNormalization
from pydocformatter.rules.definitions.PDF.PDF411_type_like_token_spacing_normalization import PDF411TypeLikeTokenSpacingNormalization


if TYPE_CHECKING:
    # Third-party imports
    import pytest


def format_source(source: str, *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Format source with PDF411 selected."""
    resolved_settings = CheckSettings(select=("PDF411",), docstring_convention=DocstringConvention.GOOGLE) if settings is None else settings
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=True)


def test_normalizes_google_parameter_return_and_yield_type_spacing() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Args:\n        value ( Mapping[ str, Sequence[int  ]] ): Description.\n\n    Returns:\n        dict[ str, Sequence[int | None  ]]: Result.\n\n    Yields:\n        Iterator[ tuple[str, int  ] ]: Item.\n    """\n'
    result = format_source(source)

    assert (
        result.new_source
        == 'def function(value):\n    """Summary.\n\n    Args:\n        value (Mapping[str, Sequence[int]]): Description.\n\n    Returns:\n        dict[str, Sequence[int | None]]: Result.\n\n    Yields:\n        Iterator[tuple[str, int]]: Item.\n    """\n'
    )
    assert result.fixed_findings[PDF411TypeLikeTokenSpacingNormalization.meta] == 1
    assert not format_source(result.new_source).modified


def test_normalizes_attribute_entry_type_spacing_in_attribute_docstring() -> None:
    source = 'value = 1\n"""Summary.\n\nAttributes:\n    child ( Mapping[ str, object ] ): Child.\n"""\n'
    result = format_source(source)

    assert result.new_source == 'value = 1\n"""Summary.\n\nAttributes:\n    child (Mapping[str, object]): Child.\n"""\n'
    assert result.fixed_findings[PDF411TypeLikeTokenSpacingNormalization.meta] == 1
    assert not result.unfixed_findings
    assert not format_source(result.new_source).modified


def test_reuses_cached_type_like_normalization_for_repeated_text(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    original_normalizer = PDF411_definition._normalized_type_like_text

    def counting_normalizer(text: str) -> str | None:
        calls.append(text)
        return original_normalizer(text)

    monkeypatch.setattr(PDF411_definition, "_normalized_type_like_text", counting_normalizer)
    source = 'def first(value):\n    """Summary.\n\n    Args:\n        value (Mapping[ str, Sequence[int  ]]): Description.\n\n    Returns:\n        dict[ str, Sequence[int | None  ]]: Result.\n    """\n\n\ndef second(value):\n    """Summary.\n\n    Args:\n        value (Mapping[ str, Sequence[int  ]]): Description.\n\n    Returns:\n        dict[ str, Sequence[int | None  ]]: Result.\n    """\n'
    settings = CheckSettings(select=("PDF411",), docstring_convention=DocstringConvention.GOOGLE)
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=False)

    assert tuple(finding.rule for finding in result.unfixed_findings) == (PDF411TypeLikeTokenSpacingNormalization.meta, PDF411TypeLikeTokenSpacingNormalization.meta)
    assert calls.count("Mapping[ str, Sequence[int  ]]") == 1
    assert calls.count("dict[ str, Sequence[int | None  ]]") == 1


def test_normalizes_numpy_parameter_return_yield_and_method_type_spacing() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Parameters\n    ----------\n    value : Mapping[ str, Sequence[int  ]]\n        Description.\n\n    Returns\n    -------\n    dict[ str, object ]\n        Result.\n\n    Yields\n    ------\n    Iterator[ tuple[str, int  ] ]\n        Item.\n\n    Methods\n    -------\n    run : Callable[[], None  ]\n        Run it.\n    """\n'
    settings = CheckSettings(select=("PDF411",), docstring_convention=DocstringConvention.NUMPY)
    result = format_source(source, settings=settings)

    assert (
        result.new_source
        == 'def function(value):\n    """Summary.\n\n    Parameters\n    ----------\n    value : Mapping[str, Sequence[int]]\n        Description.\n\n    Returns\n    -------\n    dict[str, object]\n        Result.\n\n    Yields\n    ------\n    Iterator[tuple[str, int]]\n        Item.\n\n    Methods\n    -------\n    run : Callable[[], None]\n        Run it.\n    """\n'
    )
    assert result.fixed_findings[PDF411TypeLikeTokenSpacingNormalization.meta] == 1
    assert not format_source(result.new_source, settings=settings).modified


def test_normalizes_rest_type_like_fields_and_parameter_type_arguments() -> None:
    source = 'def function(value):\n    """Summary.\n\n    :param Mapping[ str, object ]   value: Description.\n    :type value: Sequence[ int | None  ]\n    :rtype: dict[ str, Sequence[int  ]]\n    :ytype value: Iterator[ tuple[str, int  ] ]\n    :vartype timeout: Mapping[ str, object ]\n    """\n'
    settings = CheckSettings(select=("PDF411",), docstring_convention=DocstringConvention.REST)
    result = format_source(source, settings=settings)

    assert (
        result.new_source
        == 'def function(value):\n    """Summary.\n\n    :param Mapping[str, object]   value: Description.\n    :type value: Sequence[int | None]\n    :rtype: dict[str, Sequence[int]]\n    :ytype value: Iterator[tuple[str, int]]\n    :vartype timeout: Mapping[str, object]\n    """\n'
    )
    assert result.fixed_findings[PDF411TypeLikeTokenSpacingNormalization.meta] == 1
    assert not format_source(result.new_source, settings=settings).modified


def test_normalizes_dotted_names_nested_subscript_sequences_none_and_ellipsis() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Args:\n        value (pkg.types.Mapping[ str, tuple[list[int], ...] | None]): Description.\n    """\n'
    result = format_source(source)

    assert result.new_source == 'def function(value):\n    """Summary.\n\n    Args:\n        value (pkg.types.Mapping[str, tuple[list[int], ...] | None]): Description.\n    """\n'
    assert result.fixed_findings[PDF411TypeLikeTokenSpacingNormalization.meta] == 1
    assert not format_source(result.new_source).modified


def test_google_bare_return_type_uses_generic_entry_span() -> None:
    unchanged_source = 'def function(value):\n    """Summary.\n\n    Returns:\n        dict: Result.\n    """\n'
    changed_source = 'def function(value):\n    """Summary.\n\n    Returns:\n        dict[ str, object ]: Result.\n    """\n'
    unchanged_result = format_source(unchanged_source)
    changed_result = format_source(changed_source)

    assert unchanged_result.new_source == unchanged_source
    assert not unchanged_result.fixed_findings
    assert not unchanged_result.unfixed_findings
    assert changed_result.new_source == 'def function(value):\n    """Summary.\n\n    Returns:\n        dict[str, object]: Result.\n    """\n'
    assert changed_result.fixed_findings[PDF411TypeLikeTokenSpacingNormalization.meta] == 1
    assert not format_source(changed_result.new_source).modified


def test_pdf409_pdf410_and_pdf411_converge_on_overlapping_entries() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Args:\n        value   ( Mapping[ str, object ] ) : Description.\n\n    Raises:\n        `ValueError` | errors.CustomError   : Bad value.\n    """\n'
    settings = CheckSettings(select=("PDF409", "PDF410", "PDF411"), docstring_convention=DocstringConvention.GOOGLE)
    result = format_source(source, settings=settings)

    assert (
        result.new_source
        == 'def function(value):\n    """Summary.\n\n    Args:\n        value (Mapping[str, object]): Description.\n\n    Raises:\n        ValueError, errors.CustomError: Bad value.\n    """\n'
    )
    assert result.fixed_findings[PDF409DocstringEntrySpacing.meta] == 1
    assert result.fixed_findings[PDF410ExceptionEntryNormalization.meta] == 1
    assert result.fixed_findings[PDF411TypeLikeTokenSpacingNormalization.meta] == 1
    assert not format_source(result.new_source, settings=settings).modified


def test_does_not_own_exception_list_or_backtick_normalization() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Raises:\n        `ValueError` | TypeError   : Bad value.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_leaves_narrative_and_value_field_type_like_text_unchanged() -> None:
    google_source = 'def function(value):\n    """Summary.\n\n    Notes:\n        topic (Mapping[ str, object ]): Prose note.\n    """\n'
    numpy_source = 'def function(value):\n    """Summary.\n\n    Notes\n    -----\n    topic : Mapping[ str, object ]\n        Prose note.\n    """\n'
    rest_source = 'def function(value):\n    """Summary.\n\n    :returns: Mapping[ str, object ] result prose.\n    :param value: Mapping[ str, object ] parameter prose.\n    """\n'
    numpy_settings = CheckSettings(select=("PDF411",), docstring_convention=DocstringConvention.NUMPY)
    rest_settings = CheckSettings(select=("PDF411",), docstring_convention=DocstringConvention.REST)
    google_result = format_source(google_source)
    numpy_result = format_source(numpy_source, settings=numpy_settings)
    rest_result = format_source(rest_source, settings=rest_settings)

    assert google_result.new_source == google_source
    assert not google_result.fixed_findings
    assert not google_result.unfixed_findings
    assert numpy_result.new_source == numpy_source
    assert not numpy_result.fixed_findings
    assert not numpy_result.unfixed_findings
    assert rest_result.new_source == rest_source
    assert not rest_result.fixed_findings
    assert not rest_result.unfixed_findings


def test_leaves_unsupported_or_ambiguous_type_like_text_unchanged() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Args:\n        stringy ("Forward Ref"): Description.\n        called (Factory[int]()) : Description.\n        mapping ({str: int}): Description.\n        malformed (Mapping[ str): Description.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_leaves_top_level_tuple_and_list_expressions_unchanged() -> None:
    numpy_source = 'def function(value):\n    """Summary.\n\n    Returns\n    -------\n    int, str\n        Result.\n    """\n'
    google_source = 'def function(value):\n    """Summary.\n\n    Returns:\n        [ int ]: Result.\n    """\n'
    numpy_settings = CheckSettings(select=("PDF411",), docstring_convention=DocstringConvention.NUMPY)
    numpy_result = format_source(numpy_source, settings=numpy_settings)
    google_result = format_source(google_source)

    assert numpy_result.new_source == numpy_source
    assert not numpy_result.fixed_findings
    assert not numpy_result.unfixed_findings
    assert google_result.new_source == google_source
    assert not google_result.fixed_findings
    assert not google_result.unfixed_findings


def test_leaves_redundant_parentheses_unchanged_even_when_ast_equivalent() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Returns\n    -------\n    (int)\n        Result.\n\n    Yields\n    ------\n    list[(str | int)]\n        Item.\n    """\n'
    settings = CheckSettings(select=("PDF411",), docstring_convention=DocstringConvention.NUMPY)
    result = format_source(source, settings=settings)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_literal_block_parsing_setting_controls_type_like_normalization() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Args:\n        Example::\n\n            value ( Mapping[ str, object ] ): Protected text.\n    """\n'
    unprotected_settings = CheckSettings(select=("PDF411",), docstring_convention=DocstringConvention.GOOGLE, docstring_parse_literal_blocks=False)
    protected = format_source(source)
    unprotected = format_source(source, settings=unprotected_settings)

    assert protected.new_source == source
    assert not protected.fixed_findings
    assert not protected.unfixed_findings
    assert unprotected.new_source == 'def function(value):\n    """Summary.\n\n    Args:\n        Example::\n\n            value (Mapping[str, object]): Protected text.\n    """\n'
    assert unprotected.fixed_findings[PDF411TypeLikeTokenSpacingNormalization.meta] == 1
    assert not format_source(unprotected.new_source, settings=unprotected_settings).modified


def test_preserves_crlf_line_endings_when_fixing_type_like_spacing() -> None:
    source = 'def function(value):\r\n    """Summary.\r\n\r\n    Args:\r\n        value (Mapping[ str, object ]): Description.\r\n    """\r\n'
    result = format_source(source)

    assert result.new_source == 'def function(value):\r\n    """Summary.\r\n\r\n    Args:\r\n        value (Mapping[str, object]): Description.\r\n    """\r\n'
    assert result.fixed_findings[PDF411TypeLikeTokenSpacingNormalization.meta] == 1
    assert not format_source(result.new_source).modified


def test_reports_unsafe_type_like_spacing_without_fixing() -> None:
    source = 'def function(value):\n    ("Summary.\\n\\n"\n     "Args:\\n"\n     "    value (Mapping[ str, object ]): Description.")\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.rule for finding in result.unfixed_findings) == (PDF411TypeLikeTokenSpacingNormalization.meta,)
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2, 3, 4),)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring type-like token spacing should be normalized",)


def test_fixes_escaped_type_like_source_span() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Args:\n        value (Mapping[\\x20str, object ]): Description.\n    """\n'
    result = format_source(source)

    assert result.new_source == source.replace("Mapping[\\x20str, object ]", "Mapping[str, object]")
    assert result.fixed_findings[PDF411TypeLikeTokenSpacingNormalization.meta] == 1
    assert not result.unfixed_findings


def test_ignored_without_supported_convention() -> None:
    source = 'def function(value):\n    """Summary.\n\n    Args:\n        value (Mapping[ str, object ]): Description.\n    """\n'
    none_result = format_source(source, settings=CheckSettings(select=("PDF411",), docstring_convention=DocstringConvention.NONE))
    pep257_result = format_source(source, settings=CheckSettings(select=("PDF411",), docstring_convention=DocstringConvention.PEP257))

    assert none_result.new_source == source
    assert not none_result.fixed_findings
    assert not none_result.unfixed_findings
    assert pep257_result.new_source == source
    assert not pep257_result.fixed_findings
    assert not pep257_result.unfixed_findings
