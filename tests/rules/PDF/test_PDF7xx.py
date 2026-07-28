"""Tests for PDF7xx typed docstring entry rules."""

# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# Third-party imports
import libcst as cst

# First-party imports
from pydocformatter import formatter, rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definition_helpers import type_expressions


if TYPE_CHECKING:
    # Third-party imports
    import pytest


def check(
    source: str, *, select: tuple[str, ...], convention: DocstringConvention = DocstringConvention.GOOGLE, docstring_class_attribute_no_type_base_classes: tuple[str, ...] | None = None
) -> formatter.FormatterResult:
    """Run pydocformatter on source with PDF7xx-oriented settings."""
    settings = CheckSettings(
        select=select,
        docstring_convention=convention,
        docstring_class_attribute_no_type_base_classes=(
            CheckSettings().docstring_class_attribute_no_type_base_classes if docstring_class_attribute_no_type_base_classes is None else docstring_class_attribute_no_type_base_classes
        ),
    )
    return formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=False)


def codes(result: formatter.FormatterResult) -> tuple[str, ...]:
    """Return unfixed finding rule-code tags."""
    assert not result.errors
    assert not result.fixed_findings
    return tuple(finding.rule.code.tag for finding in result.unfixed_findings)


def test_broad_selection_includes_missing_description_and_mismatch_but_not_type_policy() -> None:
    source = 'def function(value: str) -> int:\n    """Return a value.\n\n    Args:\n        value (int):\n\n    Returns:\n        str:\n    """\n    return 1\n'
    result = check(source, select=("PDF7",))

    assert codes(result) == ("PDF700", "PDF703", "PDF704", "PDF707")


def test_exact_selection_enables_required_and_forbidden_type_policy_rules() -> None:
    source = 'def function(value: int) -> int:\n    """Return a value.\n\n    Args:\n        value: Input value.\n\n    Returns:\n        int: Result value.\n    """\n    return 1\n'
    required = check(source, select=("PDF701",))
    forbidden = check(source, select=("PDF706",))

    assert codes(required) == ("PDF701",)
    assert codes(forbidden) == ("PDF706",)


def test_ignored_under_none_and_pep257_even_when_selected_broadly() -> None:
    source = 'def function(value: str):\n    """Return a value.\n\n    Args:\n        value (int):\n    """\n'
    none_result = check(source, select=("PDF7",), convention=DocstringConvention.NONE)
    pep257_result = check(source, select=("PDF7",), convention=DocstringConvention.PEP257)

    assert codes(none_result) == ()
    assert codes(pep257_result) == ()


def test_rest_type_only_fields_provide_types_without_value_entry_descriptions() -> None:
    source = 'def function(value: int) -> str:\n    """Return a value.\n\n    :type value: int\n    :rtype: str\n    """\n    return "value"\n'
    missing_description = check(source, select=("PDF700", "PDF704"), convention=DocstringConvention.REST)
    required_type = check(source, select=("PDF701", "PDF705"), convention=DocstringConvention.REST)

    assert codes(missing_description) == ()
    assert codes(required_type) == ()


def test_rest_type_only_fields_skip_every_missing_description_family() -> None:
    source = '"""Module.\n\n:vartype module_value: int\n"""\nmodule_value: int = 1\n\n\nclass Client:\n    """Client.\n\n    :vartype timeout: int\n    """\n\n    timeout: int = 1\n\n\ndef generate(value: int) -> typing.Iterator[str]:\n    """Generate values.\n\n    :type value: int\n    :ytype: str\n    """\n    yield "value"\n'
    description_result = check(source, select=("PDF700", "PDF708", "PDF712", "PDF716"), convention=DocstringConvention.REST)
    type_result = check(source, select=("PDF701", "PDF709", "PDF713", "PDF717"), convention=DocstringConvention.REST)

    assert codes(description_result) == ()
    assert codes(type_result) == ()


def test_rest_type_fields_before_empty_value_fields_target_each_value_entry() -> None:
    source = '"""Module.\n\n:vartype module_value: int\n:var module_value:\n"""\nmodule_value: int = 1\n\n\nclass Client:\n    """Client.\n\n    :vartype timeout: int\n    :var timeout:\n    """\n\n    timeout: int = 1\n\n\ndef transform(value: int) -> str:\n    """Transform a value.\n\n    :type value: int\n    :param value:\n    :rtype: str\n    :return:\n    """\n    return str(value)\n\n\ndef generate() -> typing.Iterator[str]:\n    """Generate values.\n\n    :ytype: str\n    :yield:\n    """\n    yield "value"\n'
    result = check(source, select=("PDF700", "PDF704", "PDF708", "PDF712", "PDF716"), convention=DocstringConvention.REST)

    assert codes(result) == ("PDF700", "PDF704", "PDF708", "PDF712", "PDF716")
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((23,), (25,), (34,), (13,), (4,))


def test_rest_surplus_value_entries_remain_independent_for_description_and_type_rules() -> None:
    source = 'def function(value: int):\n    """Process a value.\n\n    :param value: First value.\n    :param value:\n    :type value: int\n    """\n'
    result = check(source, select=("PDF700", "PDF701", "PDF722"), convention=DocstringConvention.REST)

    assert codes(result) == ("PDF700", "PDF701")
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((5,), (5,))


def test_rest_surplus_type_entry_is_description_silent_but_keeps_type_and_orphan_diagnostics() -> None:
    source = 'def function(value: int):\n    """Process a value.\n\n    :type value: int\n    :param value:\n    :type value: str\n    """\n'
    result = check(source, select=("PDF700", "PDF703", "PDF722"), convention=DocstringConvention.REST)

    assert codes(result) == ("PDF700", "PDF703", "PDF722")
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((5,), (6,), (6,))


def test_empty_orphan_type_entry_is_missing_a_type_but_not_a_description() -> None:
    source = 'def function(value: int):\n    """Process a value.\n\n    :type value:\n    """\n'
    result = check(source, select=("PDF700", "PDF701", "PDF722"), convention=DocstringConvention.REST)

    assert codes(result) == ("PDF701", "PDF722")
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((4,), (4,))


def test_rest_value_and_type_fields_merge_without_double_counting() -> None:
    source = '"""Module.\n\n:var module_value: Module value.\n:vartype module_value: int\n"""\nmodule_value: int = 1\n\n\ndef function(value: str) -> int:\n    """Return a value.\n\n    :param value: Input value.\n    :type value: str\n    :returns: Result value.\n    :rtype: int\n    """\n    return 1\n'
    result = check(source, select=("PDF700", "PDF701", "PDF703", "PDF704", "PDF705", "PDF707", "PDF716", "PDF717", "PDF719"), convention=DocstringConvention.REST)

    assert codes(result) == ()


def test_rest_repeated_value_fields_are_checked_individually() -> None:
    source = 'def function(value: int):\n    """Process a value.\n\n    :param value: First value.\n    :param value:\n    """\n'
    result = check(source, select=("PDF700",), convention=DocstringConvention.REST)

    assert codes(result) == ("PDF700",)
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((5,),)


def test_rest_repeated_type_fields_are_checked_individually() -> None:
    source = 'def function(value: int):\n    """Process a value.\n\n    :param value: Input value.\n    :type value: int\n    :type value: str\n    """\n'
    result = check(source, select=("PDF703",), convention=DocstringConvention.REST)

    assert codes(result) == ("PDF703",)
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((6,),)


def test_rest_inline_and_paired_parameter_types_are_checked_independently() -> None:
    source = 'def function(value: int):\n    """Process a value.\n\n    :param str value: Input value.\n    :type value: int\n    """\n'
    result = check(source, select=("PDF703",), convention=DocstringConvention.REST)

    assert codes(result) == ("PDF703",)
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((4,),)


def test_rest_paired_type_mismatches_report_type_field_lines() -> None:
    source = 'def function(value: int) -> str:\n    """Return a value.\n\n    :param value: Input value.\n    :type value: str\n    :returns: Result value.\n    :rtype: int\n    """\n    return str(value)\n'
    result = check(source, select=("PDF703", "PDF707"), convention=DocstringConvention.REST)

    assert codes(result) == ("PDF703", "PDF707")
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((5,), (7,))


def test_rest_type_diagnostics_are_reported_in_source_order() -> None:
    source = 'def function(a: int, b: int):\n    """Process values.\n\n    :type b: str\n    :param a: A.\n    :param b: B.\n    :type a: str\n    """\n'
    result = check(source, select=("PDF703",), convention=DocstringConvention.REST)

    assert codes(result) == ("PDF703", "PDF703")
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((4,), (7,))


def test_rest_forbidden_type_rules_report_each_type_source() -> None:
    source = 'def function(value: int) -> int:\n    """Return a value.\n\n    :param str value: Input value.\n    :type value: int\n    :returns: Result value.\n    :rtype: int\n    """\n    return value\n'
    result = check(source, select=("PDF702", "PDF706"), convention=DocstringConvention.REST)

    assert codes(result) == ("PDF702", "PDF702", "PDF706")
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((4,), (5,), (7,))


def test_rest_required_type_rules_accept_inline_or_paired_type_sources() -> None:
    inline_source = 'def function(value: int):\n    """Process a value.\n\n    :param int value: Input value.\n    """\n'
    paired_source = 'def function(value: int):\n    """Process a value.\n\n    :param value: Input value.\n    :type value: int\n    """\n'

    assert codes(check(inline_source, select=("PDF701",), convention=DocstringConvention.REST)) == ()
    assert codes(check(paired_source, select=("PDF701",), convention=DocstringConvention.REST)) == ()


def test_rest_required_type_rules_accept_continued_type_fields() -> None:
    """Treat continuation-only reStructuredText field descriptions as types."""
    source = 'def function(value: int) -> str:\n    """Process a value.\n\n    :param value: Input value.\n    :type value:\n        int\n    :returns: Result value.\n    :rtype:\n        str\n    """\n    return str(value)\n'
    result = check(source, select=("PDF701", "PDF703", "PDF705", "PDF707"), convention=DocstringConvention.REST)

    assert codes(result) == ()


def test_rest_mismatch_rules_use_complete_multiline_type_fields() -> None:
    """Compare complete mixed inline and continued reStructuredText types."""
    source = 'def function(value: list[int]):\n    """Process a value.\n\n    :param value: Input value.\n    :type value: list[\n        str]\n    """\n'
    result = check(source, select=("PDF701", "PDF703"), convention=DocstringConvention.REST)

    assert codes(result) == ("PDF703",)
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((5,),)


def test_rest_variadic_parameter_value_and_type_fields_pair_by_comparison_name() -> None:
    source = 'def function(*items: int):\n    """Process values.\n\n    :param *items: Items.\n    :type items: int\n    """\n'
    result = check(source, select=("PDF700", "PDF701", "PDF703"), convention=DocstringConvention.REST)

    assert codes(result) == ()


def test_variadic_parameter_entries_match_signature_names_and_annotations() -> None:
    source = 'def function(*items: int, **options: str):\n    """Process values.\n\n    Args:\n        *items (int):\n        **options (int): Option values.\n    """\n'
    result = check(source, select=("PDF700", "PDF703"))

    assert codes(result) == ("PDF700", "PDF703")
    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Function parameter '*items' docstring entry is missing a description",
        "Function parameter '**options' docstring type does not match the annotation",
    )


def test_equivalent_stringized_and_complex_type_expressions_do_not_mismatch() -> None:
    source = 'from typing import Iterator\n\n\ndef function(value: "list[str | None]") -> "tuple[str, ...]":\n    """Return values.\n\n    Args:\n        value (list[str | None]): Input value.\n\n    Returns:\n        tuple[str, ...]: Result values.\n    """\n    return ("value",)\n\n\ndef generate() -> Iterator[dict[str, int]]:\n    """Yield values.\n\n    Yields:\n        dict[str, int]: Result values.\n    """\n    yield {"value": 1}\n'
    result = check(source, select=("PDF703", "PDF707", "PDF711"))

    assert codes(result) == ()


def test_equivalent_import_alias_type_expressions_do_not_mismatch() -> None:
    source = 'from typing import Iterator\nimport typing as t\nimport collections.abc as cabc\n\n"""Module.\n\nAttributes:\n    module_value (Iterator[int]): Module value.\n"""\nmodule_value: t.Iterator[int] = iter(())\n\n\nclass Client:\n    """Client.\n\n    Attributes:\n        timeout (Iterator[int]): Timeout values.\n    """\n\n    timeout: t.Iterator[int]\n\n\ndef function(value: Iterator[int]) -> cabc.Iterator[int]:\n    """Return values.\n\n    Args:\n        value (t.Iterator[int]): Input value.\n\n    Returns:\n        collections.abc.Iterator[int]: Result value.\n    """\n    return value\n\n\ndef generate() -> "Iterator[int]":\n    """Yield values.\n\n    Yields:\n        int: Result value.\n    """\n    yield 1\n'
    result = check(source, select=("PDF703", "PDF707", "PDF711", "PDF715", "PDF719"))

    assert codes(result) == ()


def test_quoted_yield_import_aliases_report_mismatches() -> None:
    source = 'from typing import Iterator\nfrom collections.abc import Iterator as CIterator\nimport typing as t\n\n\ndef imported() -> "Iterator[int]":\n    """Yield values.\n\n    Yields:\n        str: Value.\n    """\n    yield 1\n\n\ndef imported_alias() -> "CIterator[int]":\n    """Yield values.\n\n    Yields:\n        str: Value.\n    """\n    yield 1\n\n\ndef module_alias() -> "t.Iterator[int]":\n    """Yield values.\n\n    Yields:\n        str: Value.\n    """\n    yield 1\n'
    result = check(source, select=("PDF711",))

    assert codes(result) == ("PDF711", "PDF711", "PDF711")


def test_module_type_aliases_are_cached_across_typed_mismatch_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0
    original = type_expressions.module_type_aliases

    def counted_module_type_aliases(module: cst.Module) -> type_expressions.TypeAliasMap:
        nonlocal calls
        calls += 1
        return original(module)

    monkeypatch.setattr(type_expressions, "module_type_aliases", counted_module_type_aliases)
    source = 'from typing import Iterator\n\n\ndef function(value: Iterator[int]) -> "Iterator[int]":\n    """Yield values.\n\n    Args:\n        value (typing.Iterator[int]): Input value.\n\n    Returns:\n        typing.Iterator[int]: Result value.\n\n    Yields:\n        int: Yielded value.\n    """\n    yield 1\n'
    result = check(source, select=("PDF703", "PDF707", "PDF711"))

    assert codes(result) == ()
    assert calls == 1


def test_module_type_aliases_treat_top_level_compound_bindings_as_shadowing() -> None:
    source = "from typing import Iterator, Mapping, Sequence\nfor Iterator in []:\n    pass\nwith manager as Mapping:\n    pass\ntry:\n    pass\nexcept Exception as Sequence:\n    pass\n"

    assert type_expressions.module_type_aliases(cst.parse_module(source)) == {}


def test_shadowed_import_alias_type_expressions_remain_conservative() -> None:
    source = (
        'from typing import Iterator\nIterator = object\n\n\ndef function(value: Iterator[int]):\n    """Process values.\n\n    Args:\n        value (typing.Iterator[int]): Input value.\n    """\n'
    )
    result = check(source, select=("PDF703",))

    assert codes(result) == ("PDF703",)


def test_uncomparable_type_expression_shapes_do_not_report_mismatches() -> None:
    source = 'def function(value: Callable[[int], str]) -> Literal["ok"]:\n    """Return values.\n\n    Args:\n        value (Callable[[int], str]): Input value.\n\n    Returns:\n        Literal["ok"]: Result value.\n    """\n    return "ok"\n'
    result = check(source, select=("PDF703", "PDF707"))

    assert codes(result) == ()


def test_numpy_parameter_return_yield_and_attribute_rules() -> None:
    source = '"""Module.\n\nAttributes\n----------\nmodule_value : str\n\n"""\nmodule_value: int = 1\n\n\nclass Client:\n    """Client.\n\n    Attributes\n    ----------\n    timeout : str\n\n    """\n\n    timeout: int = 1\n\n\ndef function(value: str) -> typing.Iterator[str]:\n    """Yield values.\n\n    Parameters\n    ----------\n    value : int\n\n    Yields\n    ------\n    int\n\n    """\n    yield "value"\n'
    result = check(source, select=("PDF7",), convention=DocstringConvention.NUMPY)

    assert codes(result) == ("PDF700", "PDF703", "PDF708", "PDF711", "PDF712", "PDF715", "PDF716", "PDF719")


def test_protected_only_descriptions_are_missing_for_every_typed_description_rule() -> None:
    source = (
        '"""Module.\n\nAttributes:\n    module_value:\n        ```text\n        protected only\n        ```\n"""\nmodule_value = 1\n\n\n'
        'class Client:\n    """Client.\n\n    Attributes:\n        class_value:\n            ```text\n            protected only\n            ```\n    """\n\n    class_value = 1\n\n\n'
        'def transform(parameter) -> int:\n    """Transform a value.\n\n    Args:\n        parameter:\n            ```text\n            protected only\n            ```\n\n    Returns:\n        int:\n            ```text\n            protected only\n            ```\n    """\n    return 1\n\n\n'
        'def generate() -> Iterator[int]:\n    """Generate values.\n\n    Yields:\n        int:\n            ```text\n            protected only\n            ```\n    """\n    yield 1\n'
    )
    selected = ("PDF700", "PDF704", "PDF708", "PDF712", "PDF716")
    protected = check(source, select=selected)
    settings = CheckSettings(select=selected, docstring_convention=DocstringConvention.GOOGLE, docstring_parse_code_fences=False)
    unprotected = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=False)

    assert codes(protected) == selected
    assert codes(unprotected) == ()


def test_numpy_multi_name_parameter_entries_check_each_signature_annotation() -> None:
    source = 'def function(x: int, y: str):\n    """Process values.\n\n    Parameters\n    ----------\n    x, y : int\n        Values.\n    """\n'
    result = check(source, select=("PDF703",), convention=DocstringConvention.NUMPY)

    assert codes(result) == ("PDF703",)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Function parameter 'y' docstring type does not match the annotation",)


def test_numpy_multi_name_attribute_entries_check_each_assignment_annotation() -> None:
    source = '"""Client defaults.\n\nAttributes\n----------\nmodule_primary, module_fallback : str\n    Module endpoints.\n"""\n\nmodule_primary: str\nmodule_fallback: int\n\n\nclass Client:\n    """Client.\n\n    Attributes\n    ----------\n    primary, fallback : str\n        Request endpoints.\n    """\n\n    primary: str\n    fallback: int\n'
    result = check(source, select=("PDF715", "PDF719"), convention=DocstringConvention.NUMPY)

    assert codes(result) == ("PDF715", "PDF719")
    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Class attribute 'fallback' docstring type does not match the annotation",
        "Module attribute 'module_fallback' docstring type does not match the annotation",
    )


def test_return_mismatch_skips_generator_return_annotations_and_yield_mismatch_uses_yield_type() -> None:
    source = 'from typing import Generator\n\n\ndef function() -> Generator[str, None, None]:\n    """Yield values.\n\n    Returns:\n        int: Wrong but ignored for generators.\n\n    Yields:\n        int: Wrong yield type.\n    """\n    yield "value"\n'
    result = check(source, select=("PDF707", "PDF711"))

    assert codes(result) == ("PDF711",)


def test_mismatch_skips_unparseable_docstring_or_code_types() -> None:
    source = (
        'def function(value: "list[") -> int:\n    """Return a value.\n\n    Args:\n        value (Factory[int]()): Input value.\n\n    Returns:\n        int: Result value.\n    """\n    return 1\n'
    )
    result = check(source, select=("PDF703", "PDF707"))

    assert codes(result) == ()


def test_stub_and_abstract_functions_are_not_checked_for_return_or_yield_entries() -> None:
    source = 'import abc\nfrom typing import Iterator\n\n\n@abc.abstractmethod\ndef abstract() -> int:\n    """Return a value.\n\n    Returns:\n        str:\n    """\n    raise NotImplementedError\n\n\ndef stub() -> Iterator[int]:\n    """Yield values.\n\n    Yields:\n        str:\n    """\n    ...\n'
    result = check(source, select=("PDF704", "PDF707", "PDF708", "PDF711"))

    assert codes(result) == ()


def test_class_attribute_enum_inversion_affects_only_pdf713() -> None:
    source = 'from enum import Enum\n\n\nclass Color(Enum):\n    """Color.\n\n    Attributes:\n        RED (int): Red value.\n        BLUE: Blue value.\n    """\n\n    RED = 1\n    BLUE = 2\n'
    required = check(source, select=("PDF713",))
    mismatch = check(source, select=("PDF715",))
    empty_config = check(source, select=("PDF713",), docstring_class_attribute_no_type_base_classes=())

    assert codes(required) == ("PDF713",)
    assert tuple(finding.message for finding in required.unfixed_findings) == ("Class attribute 'RED' docstring entry should not include a type",)
    assert codes(mismatch) == ()
    assert codes(empty_config) == ("PDF713",)
    assert tuple(finding.message for finding in empty_config.unfixed_findings) == ("Class attribute 'BLUE' docstring entry is missing a type",)


def test_class_attribute_enum_inversion_matches_import_aliases() -> None:
    source = 'import enum as e\nfrom enum import Flag as F\n\n\nclass Color(e.Enum):\n    """Color.\n\n    Attributes:\n        RED (int): Red value.\n    """\n\n    RED = 1\n\n\nclass Permission(F):\n    """Permission.\n\n    Attributes:\n        READ (int): Read value.\n    """\n\n    READ = 1\n'
    result = check(source, select=("PDF713",))

    assert codes(result) == ("PDF713", "PDF713")
    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Class attribute 'RED' docstring entry should not include a type",
        "Class attribute 'READ' docstring entry should not include a type",
    )


def test_class_attribute_enum_inversion_reports_in_source_order() -> None:
    source = 'from enum import Enum\n\n\nclass Regular:\n    """Regular.\n\n    Attributes:\n        timeout: Timeout.\n    """\n\n    timeout = 1\n\n\nclass Color(Enum):\n    """Color.\n\n    Attributes:\n        RED (int): Red value.\n    """\n\n    RED = 1\n'
    result = check(source, select=("PDF713",))

    assert codes(result) == ("PDF713", "PDF713")
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((8,), (18,))


def test_class_attribute_unqualified_base_configuration_is_syntactic_only() -> None:
    source = 'from enum import Enum as E\n\n\nclass Enum:\n    """Local base."""\n\n\nclass Imported(E):\n    """Imported.\n\n    Attributes:\n        VALUE (int): Value.\n    """\n\n    VALUE = 1\n\n\nclass Local(Enum):\n    """Local.\n\n    Attributes:\n        VALUE (int): Value.\n    """\n\n    VALUE = 1\n'
    result = check(source, select=("PDF713",), docstring_class_attribute_no_type_base_classes=("Enum",))

    assert codes(result) == ("PDF713",)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Class attribute 'VALUE' docstring entry should not include a type",)


def test_shadowed_enum_import_alias_is_not_treated_as_imported_enum_base() -> None:
    source = 'from enum import Enum as E\nE = object\n\n\nclass Color(E):\n    """Color.\n\n    Attributes:\n        RED: Red value.\n    """\n\n    RED = 1\n'
    result = check(source, select=("PDF713",))

    assert codes(result) == ("PDF713",)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Class attribute 'RED' docstring entry is missing a type",)


def test_later_enum_import_alias_rebinding_does_not_affect_prior_base() -> None:
    source = 'import enum as e\n\n\nclass Color(e.Enum):\n    """Color.\n\n    Attributes:\n        RED (int): Red value.\n    """\n\n    RED = 1\n\n\ne = object\n'
    result = check(source, select=("PDF713",))

    assert codes(result) == ("PDF713",)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Class attribute 'RED' docstring entry should not include a type",)


def test_guarded_enum_import_alias_matches_enum_like_base() -> None:
    source = 'if enabled:\n    import enum as e\n\n\nclass Color(e.Enum):\n    """Color.\n\n    Attributes:\n        RED (int): Red value.\n    """\n\n    RED = 1\n'
    result = check(source, select=("PDF713",))

    assert codes(result) == ("PDF713",)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Class attribute 'RED' docstring entry should not include a type",)


def test_shadowed_dotted_enum_base_is_not_treated_as_imported_enum_base() -> None:
    source = 'class E:\n    Enum = object\n\nenum = E()\n\n\nclass Color(enum.Enum):\n    """Color.\n\n    Attributes:\n        RED: Red value.\n    """\n\n    RED = 1\n'
    result = check(source, select=("PDF713",))

    assert codes(result) == ("PDF713",)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Class attribute 'RED' docstring entry is missing a type",)


def test_local_yield_container_name_is_not_treated_as_recognized_typing_container() -> None:
    source = 'class Iterator:\n    """Local container."""\n\n\ndef function() -> Iterator[int]:\n    """Yield values.\n\n    Yields:\n        str: Value.\n    """\n    yield 1\n'
    result = check(source, select=("PDF711",))

    assert codes(result) == ()


def test_later_yield_container_import_alias_rebinding_does_not_affect_prior_annotation() -> None:
    source = 'from typing import Iterator\n\n\ndef function() -> Iterator[int]:\n    """Yield values.\n\n    Yields:\n        str: Value.\n    """\n    yield 1\n\n\nIterator = object\n'
    result = check(source, select=("PDF711",))

    assert codes(result) == ("PDF711",)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Function yield 'yield' docstring type does not match the annotation",)


def test_guarded_yield_container_import_alias_matches_annotation_container() -> None:
    source = 'if enabled:\n    from typing import Iterator\n\n\ndef function() -> Iterator[int]:\n    """Yield values.\n\n    Yields:\n        str: Value.\n    """\n    yield 1\n'
    result = check(source, select=("PDF711",))

    assert codes(result) == ("PDF711",)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Function yield 'yield' docstring type does not match the annotation",)


def test_attached_attribute_docstrings_are_not_checked_by_pdf7xx() -> None:
    source = 'class Client:\n    timeout: int = 1\n    """Timeout.\n\n    Attributes:\n        timeout (str):\n    """\n\nmodule_value: int = 1\n"""Module value.\n\nAttributes:\n    module_value (str):\n"""\n'
    result = check(source, select=("PDF7",))

    assert codes(result) == ()
