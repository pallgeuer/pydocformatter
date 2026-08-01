"""Tests for PDF527 parameter-variadic-marker-style."""

# Third-party imports
import pytest

# First-party imports
import tests.rules.PDF.helpers as pdf_helpers
from pydocformatter import formatter, rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definitions.PDF.PDF527_parameter_variadic_marker_style import PDF527ParameterVariadicMarkerStyle
from pydocformatter.rules.models import FixAvailability


format_source = pdf_helpers.formatter_for("PDF527")


def assert_pdf527_lines(source: str, expected: tuple[tuple[int, ...], ...], *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Assert PDF527 findings without applying available fixes."""
    result = format_source(source, settings=settings, fix=False)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.rule for finding in result.unfixed_findings) == (PDF527ParameterVariadicMarkerStyle.meta,) * len(expected)
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == expected
    return result


def assert_pdf527_fix(source: str, expected: str, count: int, *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Assert a complete idempotent PDF527 fix."""
    result = format_source(source, settings=settings)

    assert result.new_source == expected
    assert result.fixed_findings[PDF527ParameterVariadicMarkerStyle.meta] == count
    assert not result.unfixed_findings
    assert not format_source(expected, settings=settings).modified
    return result


def test_metadata() -> None:
    """Expose the stable usually-fixable rule identity."""
    assert PDF527ParameterVariadicMarkerStyle.meta.name == "parameter-variadic-marker-style"
    assert PDF527ParameterVariadicMarkerStyle.meta.message == "Docstring parameter variadic markers do not use the canonical spelling"
    assert PDF527ParameterVariadicMarkerStyle.meta.fix_availability is FixAvailability.USUALLY
    assert PDF527ParameterVariadicMarkerStyle.meta.stable_since == "1.1.0"


def test_google_fixes_missing_wrong_count_and_spurious_variadic_markers() -> None:
    source = (
        'def function(value, *args, **kwargs):\n    """Collect values.\n\n    Args:\n        *value: Ordinary value.\n        args: Positional values.\n        *kwargs: Keyword values.\n    """\n'
    )
    expected = source.replace("*value: Ordinary", "value: Ordinary").replace("        args: Positional", "        *args: Positional").replace("*kwargs: Keyword", "**kwargs: Keyword")
    result = assert_pdf527_lines(source, ((5,), (6,), (7,)))

    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Docstring parameter '*value' should be written as 'value' to match the function signature",
        "Docstring parameter 'args' should be written as '*args' to match the function signature",
        "Docstring parameter '*kwargs' should be written as '**kwargs' to match the function signature",
    )
    assert_pdf527_fix(source, expected, 3)


def test_google_fixes_every_other_noncanonical_marker_count() -> None:
    source = (
        'def function(value, *args, **kwargs):\n    """Collect values.\n\n    Args:\n        **value: Ordinary value.\n        **args: Positional values.\n        kwargs: Keyword values.\n    """\n'
    )
    expected = source.replace("**value", "value").replace("**args", "*args").replace("        kwargs:", "        **kwargs:")

    assert_pdf527_fix(source, expected, 3)


def test_correct_google_variadic_markers_are_valid() -> None:
    source = (
        'def function(value, *args, **kwargs):\n    """Collect values.\n\n    Args:\n        value: Ordinary value.\n        *args: Positional values.\n        **kwargs: Keyword values.\n    """\n'
    )

    assert_pdf527_lines(source, ())


def test_numpy_fixes_each_name_in_multi_name_and_duplicate_entries() -> None:
    source = 'def function(value, *args, **kwargs):\n    """Collect values.\n\n    Parameters\n    ----------\n    *value, args, *kwargs : object\n        Values.\n    args : object\n        Repeated values.\n    """\n'
    expected = source.replace("*value, args, *kwargs", "value, *args, **kwargs").replace("    args : object", "    *args : object")
    settings = CheckSettings(select=("PDF527",), docstring_convention=DocstringConvention.NUMPY)

    assert_pdf527_lines(source, ((6,), (6,), (6,), (8,)), settings=settings)
    assert_pdf527_fix(source, expected, 4, settings=settings)


def test_correct_numpy_variadic_markers_are_valid() -> None:
    source = 'def function(value, *args, **kwargs):\n    """Collect values.\n\n    Parameters\n    ----------\n    value, *args, **kwargs : object\n        Values.\n    """\n'
    settings = CheckSettings(select=("PDF527",), docstring_convention=DocstringConvention.NUMPY)

    assert_pdf527_lines(source, (), settings=settings)


def test_rest_fixes_value_and_type_fields_to_bare_names() -> None:
    source = 'def function(value, *args, **kwargs):\n    """Collect values.\n\n    :param *value: Ordinary value.\n    :type *value: object\n    :param *args: Positional values.\n    :type *args: tuple[object, ...]\n    :param **kwargs: Keyword values.\n    :type **kwargs: dict[str, object]\n    """\n'
    expected = source.replace("*value", "value").replace("*args", "args").replace("**kwargs", "kwargs").replace("def function(value, args, kwargs):", "def function(value, *args, **kwargs):")
    settings = CheckSettings(select=("PDF527",), docstring_convention=DocstringConvention.REST)
    result = assert_pdf527_lines(source, ((4,), (5,), (6,), (7,), (8,), (9,)), settings=settings)

    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Docstring parameter '*value' should be written as 'value' without variadic markers under the reStructuredText convention",
        "Docstring parameter '*value' should be written as 'value' without variadic markers under the reStructuredText convention",
        "Docstring parameter '*args' should be written as 'args' without variadic markers under the reStructuredText convention",
        "Docstring parameter '*args' should be written as 'args' without variadic markers under the reStructuredText convention",
        "Docstring parameter '**kwargs' should be written as 'kwargs' without variadic markers under the reStructuredText convention",
        "Docstring parameter '**kwargs' should be written as 'kwargs' without variadic markers under the reStructuredText convention",
    )
    assert_pdf527_fix(source, expected, 6, settings=settings)


def test_rest_fixes_inline_typed_aliases_and_preserves_types() -> None:
    source = 'def function(*args):\n    """Collect values.\n\n    :param tuple[object, ...] *args: Values.\n    :parameter *args: Values.\n    :arg *args: Values.\n    :argument *args: Values.\n    :key *args: Values.\n    :keyword *args: Values.\n    :kwarg *args: Values.\n    :type *args: tuple[object, ...]\n    """\n'
    expected = source.replace("*args", "args").replace("def function(args):", "def function(*args):")
    settings = CheckSettings(select=("PDF527",), docstring_convention=DocstringConvention.REST)

    assert_pdf527_fix(source, expected, 8, settings=settings)
    assert ":param tuple[object, ...] args:" in expected


def test_rest_fixes_orphan_type_field_independently() -> None:
    source = 'def function(*args):\n    """Collect values.\n\n    :type *args: tuple[object, ...]\n    """\n'
    expected = source.replace("*args", "args").replace("def function(args):", "def function(*args):")
    settings = CheckSettings(select=("PDF527",), docstring_convention=DocstringConvention.REST)

    assert_pdf527_fix(source, expected, 1, settings=settings)


def test_rest_accepts_bare_value_and_type_fields() -> None:
    source = 'def function(*args, **kwargs):\n    """Collect values.\n\n    :argument tuple[object, ...] args: Positional values.\n    :kwarg Mapping[str, object] kwargs: Keyword values.\n    :type args: tuple[object, ...]\n    :type kwargs: Mapping[str, object]\n    """\n'
    settings = CheckSettings(select=("PDF527",), docstring_convention=DocstringConvention.REST)

    assert_pdf527_lines(source, (), settings=settings)


def test_unknown_value_and_type_names_remain_exclusively_pdf501_responsibility() -> None:
    google = 'def function(*args):\n    """Collect values.\n\n    Args:\n        **stale: Stale values.\n        *args: Positional values.\n    """\n'
    rest = 'def function(*args):\n    """Collect values.\n\n    :param *stale: Stale values.\n    :type **stale: object\n    :param args: Positional values.\n    """\n'

    assert_pdf527_lines(google, ())
    assert_pdf527_lines(rest, (), settings=CheckSettings(select=("PDF527",), docstring_convention=DocstringConvention.REST))


def test_unpack_typed_dict_keys_are_ignored_but_explicit_container_is_fixed() -> None:
    source = 'from typing import TypedDict, Unpack\n\n\nclass Options(TypedDict):\n    mode: str\n\n\ndef function(**kwargs: Unpack[Options]):\n    """Configure values.\n\n    Args:\n        mode: Operating mode.\n        kwargs: Complete options.\n    """\n'
    expected = source.replace("        kwargs: Complete", "        **kwargs: Complete")

    assert_pdf527_fix(source, expected, 1)


def test_protected_entry_like_content_is_ignored() -> None:
    source = 'def function(*args):\n    """Collect values.\n\n    Args:\n        Example::\n\n            args: Example text.\n\n        *args: Positional values.\n    """\n'

    assert_pdf527_lines(source, ())


def test_fixes_escape_spelled_parameter_name_when_source_mapping_is_safe() -> None:
    source = 'def function(value):\n    """Collect a value.\n\n    Args:\n        \\x2avalue: Ordinary value.\n    """\n'
    expected = source.replace("\\x2avalue", "value")

    assert_pdf527_fix(source, expected, 1)


def test_fixes_parameter_name_on_exact_escaped_logical_line() -> None:
    """Use the parser-owned name slot when an escaped logical line has no physical line mapping."""
    source = 'def function(*args):\n    """Summary.\\n\\nArgs:\\n        args: Values."""\n'
    expected = source.replace("args: Values", "*args: Values")

    assert_pdf527_fix(source, expected, 1)


def test_rest_fixes_escaped_variadic_value_and_type_fields_without_extraneous_findings() -> None:
    """Decode one reStructuredText escape while preserving the raw replacement span."""
    source = 'def function(*args):\n    r"""Collect values.\n\n    :param \\*args: Values.\n    :type \\*args: tuple[object, ...]\n    """\n'
    expected = source.replace("\\*args", "args")
    settings = CheckSettings(select=("PDF500", "PDF501", "PDF527"), docstring_convention=DocstringConvention.REST)
    result = format_source(source, settings=settings)

    assert result.new_source == expected
    assert result.fixed_findings[PDF527ParameterVariadicMarkerStyle.meta] == 2
    assert not result.unfixed_findings
    assert not format_source(expected, settings=settings).modified


@pytest.mark.filterwarnings("ignore:invalid escape sequence.*:DeprecationWarning")
def test_rest_ordinary_literal_escaped_variadic_is_matched_without_an_unsafe_fix() -> None:
    """Recognize an escaped name even when its ordinary-literal source mapping cannot be rewritten."""
    source = 'def function(*args):\n    """Collect values.\n\n    :param \\*args: Values.\n    """\n'
    settings = CheckSettings(select=("PDF501", "PDF527"), docstring_convention=DocstringConvention.REST)
    result = format_source(source, settings=settings, fix=False)

    assert result.new_source == source
    assert not result.errors
    assert not result.fixed_findings
    assert tuple(finding.rule for finding in result.unfixed_findings) == (PDF527ParameterVariadicMarkerStyle.meta,)


@pytest.mark.parametrize("documented_name", [r"\\*args", r"\***args", r"\args"])
def test_rest_does_not_normalize_unsupported_parameter_escapes(documented_name: str) -> None:
    """Restrict semantic unescaping to one slash before one or two variadic stars."""
    source = f'def function(*args):\n    r"""Collect values.\n\n    :param {documented_name}: Values.\n    """\n'
    settings = CheckSettings(select=("PDF527",), docstring_convention=DocstringConvention.REST)

    assert_pdf527_lines(source, (), settings=settings)


def test_reports_concatenated_docstring_without_fixing() -> None:
    source = 'def function(*args):\n    ("Collect values.\\n\\n"\n     "Args:\\n"\n     "    args: Positional values.")\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.rule for finding in result.unfixed_findings) == (PDF527ParameterVariadicMarkerStyle.meta,)
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2, 3, 4),)


def test_fixes_crlf_source_and_preserves_line_endings() -> None:
    source = 'def function(*args):\r\n    """Collect values.\r\n\r\n    Args:\r\n        args: Positional values.\r\n    """\r\n'
    expected = source.replace("        args:", "        *args:")

    assert_pdf527_fix(source, expected, 1)
    assert "\r\n" in expected


@pytest.mark.parametrize("convention", [DocstringConvention.NONE, DocstringConvention.PEP257])
def test_unparsed_conventions_disable_rule_even_for_exact_selection(convention: DocstringConvention) -> None:
    selected = rules_selection.select_rules(CheckSettings(select=("PDF527",), docstring_convention=convention))

    assert "PDF527" not in tuple(rule.rule.code.tag for rule in selected.rules)


@pytest.mark.parametrize("convention", [DocstringConvention.GOOGLE, DocstringConvention.NUMPY, DocstringConvention.REST])
def test_parsed_conventions_enable_rule_through_broad_selection(convention: DocstringConvention) -> None:
    selected = rules_selection.select_rules(CheckSettings(select=("PDF",), docstring_convention=convention))

    assert "PDF527" in tuple(rule.rule.code.tag for rule in selected.rules)


def test_rule_respects_suppression_before_fixing() -> None:
    source = 'def function(*args):\n    # pydocfmt: ignore[PDF527]\n    """Collect values.\n\n    Args:\n        args: Positional values.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings
