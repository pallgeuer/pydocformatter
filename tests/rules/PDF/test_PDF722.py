"""Tests for PDF722 orphan-rest-type-field."""

# Future imports
from __future__ import annotations

# Third-party imports
import pytest

# First-party imports
import tests.rules.PDF.helpers as pdf_helpers
from pydocformatter import formatter, rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definitions.PDF.PDF722_orphan_rest_type_field import PDF722OrphanRestTypeField
from tests import rule_helpers


contexts = pdf_helpers.contexts_for("PDF722", convention=DocstringConvention.REST)
format_source = pdf_helpers.formatter_for("PDF722", convention=DocstringConvention.REST)


def assert_pdf722(source: str, expected_lines: tuple[tuple[int, ...], ...], *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Assert PDF722 findings for source."""
    return pdf_helpers.assert_unfixed_lines(format_source, source, expected_lines, meta=PDF722OrphanRestTypeField.meta, settings=settings)


def codes(result: formatter.FormatterResult) -> tuple[str, ...]:
    """Return unfixed rule-code tags."""
    return tuple(finding.rule.code.tag for finding in result.unfixed_findings)


def test_metadata() -> None:
    """Expose the stable diagnostic-only rule identity."""
    assert PDF722OrphanRestTypeField.meta.name == "orphan-rest-type-field"
    assert PDF722OrphanRestTypeField.meta.stable_since == "1.1.0"
    assert PDF722OrphanRestTypeField.meta.message == "reST type field has no corresponding value field"


def test_reports_every_supported_orphan_family_with_specific_messages() -> None:
    source = 'def convert(value):\n    """Convert a value.\n\n    :type value: int\n    :rtype: str\n    :ytype item: bytes\n    :vartype timeout: float\n    """\n'
    result = assert_pdf722(source, ((4,), (5,), (6,), (7,)))

    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "reST type field ':type value:' has no corresponding parameter value field",
        "reST type field ':rtype:' has no corresponding return value field",
        "reST type field ':ytype item:' has no corresponding yield value field",
        "reST type field ':vartype timeout:' has no corresponding attribute value field",
    )


def test_reports_interleaved_orphan_families_in_source_order() -> None:
    source = 'def convert(value):\n    """Convert a value.\n\n    :vartype timeout: float\n    :ytype item: bytes\n    :rtype: str\n    :type value: int\n    """\n'
    result = assert_pdf722(source, ((4,), (5,), (6,), (7,)))

    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "reST type field ':vartype timeout:' has no corresponding attribute value field",
        "reST type field ':ytype item:' has no corresponding yield value field",
        "reST type field ':rtype:' has no corresponding return value field",
        "reST type field ':type value:' has no corresponding parameter value field",
    )


def test_pairs_aliases_variadics_named_yields_and_attributes_regardless_of_order() -> None:
    source = 'def collect(*args, **kwargs):\n    """Collect values.\n\n    :type args: tuple[object, ...]\n    :argument *args: Positional values.\n    :kwarg **kwargs: Keyword values.\n    :type kwargs: dict[str, object]\n    :rtype: int\n    :returns: Count.\n    :yield: Value.\n    :ytype: object\n    :ytype item: str\n    :yields item: Named value.\n    :vartype timeout: float\n    :cvar timeout: Timeout.\n    """\n'

    assert_pdf722(source, ())


def test_named_yields_and_attributes_match_exactly() -> None:
    source = '"""Values.\n\n:ytype item: str\n:yield other: Value.\n:vartype Timeout: float\n:var timeout: Timeout.\n"""\n'
    result = assert_pdf722(source, ((3,), (5,)))

    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "reST type field ':ytype item:' has no corresponding yield value field",
        "reST type field ':vartype Timeout:' has no corresponding attribute value field",
    )


def test_identical_names_do_not_pair_across_semantic_field_families() -> None:
    source = 'def convert(value):\n    """Convert a value.\n\n    :type value: int\n    :param value: Value.\n    :vartype value: str\n    :yield value: Yielded value.\n    """\n'
    result = assert_pdf722(source, ((6,),))

    assert tuple(finding.message for finding in result.unfixed_findings) == ("reST type field ':vartype value:' has no corresponding attribute value field",)


def test_pairing_is_fifo_one_to_one() -> None:
    source = 'def convert(value):\n    """Convert a value.\n\n    :type value: int\n    :param value: Value.\n    :type value: str\n    """\n'

    assert_pdf722(source, ((6,),))


def test_surplus_value_fields_are_not_orphans_and_names_remain_case_sensitive() -> None:
    source = 'def convert(first, second, third):\n    """Convert values.\n\n    :type first: int\n    :param first: First value.\n    :param second: Second value.\n    :type Third: str\n    :param third: Third value.\n    """\n'
    result = assert_pdf722(source, ((7,),))

    assert tuple(finding.message for finding in result.unfixed_findings) == ("reST type field ':type Third:' has no corresponding parameter value field",)


def test_empty_value_fields_still_pair_structurally_with_type_fields() -> None:
    source = 'def generate(value):\n    """Generate values.\n\n    :type value: int\n    :param value:\n    :rtype: str\n    :return:\n    :ytype item: bytes\n    :yield item:\n    :vartype timeout: float\n    :var timeout:\n    """\n    yield value\n'

    assert_pdf722(source, ())


def test_valid_empty_type_is_orphan_but_malformed_and_custom_fields_are_not() -> None:
    source = 'def convert(value):\n    """Convert a value.\n\n    :type value:\n    :type: int\n    :rtype result: int\n    :custom-type value: int\n    """\n'

    assert_pdf722(source, ((4,),))


def test_pairing_does_not_cross_primary_and_attached_docstrings() -> None:
    source = '"""Module values.\n\n:vartype timeout: float\n"""\n\ntimeout = 1.0\n""":var timeout: Timeout value."""\n'

    assert_pdf722(source, ((3,),))


def test_checks_supported_attached_attribute_docstrings() -> None:
    source = 'timeout = 1.0\n"""Timeout value.\n\n:vartype timeout: float\n"""\n'

    assert_pdf722(source, ((4,),))


def test_checks_class_and_instance_attached_docstrings_in_source_order() -> None:
    source = 'class Client:\n    timeout = 1.0\n    """Timeout.\n\n    :vartype timeout: float\n    """\n\n    def __init__(self):\n        self.retries = 3\n        """Retries.\n\n        :vartype retries: int\n        """\n'

    assert_pdf722(source, ((5,), (12,)))


def test_ignores_additional_unattached_string_literals() -> None:
    source = 'def convert(value):\n    """Convert a value."""\n    """:type value: int"""\n\n\nclass Client:\n    """Client."""\n    """:vartype timeout: float"""\n'

    assert_pdf722(source, ())


@pytest.mark.parametrize("selector", ["PDF722", "PDF7", "PDF", "ALL"])
def test_normal_selectors_include_rule_under_rest(selector: str) -> None:
    settings = CheckSettings(select=(selector,), docstring_convention=DocstringConvention.REST)
    active_codes = {selected.rule.code.tag for selected in rules_selection.select_rules(settings).rules}

    assert "PDF722" in active_codes


@pytest.mark.parametrize("convention", [DocstringConvention.NONE, DocstringConvention.PEP257, DocstringConvention.GOOGLE, DocstringConvention.NUMPY])
def test_rule_is_disabled_outside_rest(convention: DocstringConvention) -> None:
    source = 'def convert(value):\n    """Convert a value.\n\n    :type value: int\n    """\n'
    settings = CheckSettings(select=("PDF722",), docstring_convention=convention)

    assert_pdf722(source, (), settings=settings)


def test_protected_directive_fence_and_literal_block_fields_follow_parser_settings() -> None:
    directive = 'def convert(value):\n    """Convert.\n\n    .. note::\n        :type value: int\n    """\n'
    fence = 'def convert(value):\n    """Convert.\n\n    ```text\n    :type value: int\n    ```\n    """\n'
    literal = 'def convert(value):\n    """Convert.\n\n    Example::\n\n        :type value: int\n    """\n'

    assert_pdf722(directive, ())
    assert_pdf722(fence, ())
    assert_pdf722(literal, ())
    assert_pdf722(directive, (), settings=CheckSettings(select=("PDF722",), docstring_convention=DocstringConvention.REST, docstring_parse_directives=False))
    assert_pdf722(fence, (), settings=CheckSettings(select=("PDF722",), docstring_convention=DocstringConvention.REST, docstring_parse_code_fences=False))
    assert_pdf722(literal, ((6,),), settings=CheckSettings(select=("PDF722",), docstring_convention=DocstringConvention.REST, docstring_parse_literal_blocks=False))


@pytest.mark.parametrize(
    ("source", "unprotected_settings", "expected_lines"),
    [
        pytest.param(
            'def convert(value):\n    """Convert.\n\n    >>> print(":type value: int")\n    :type value: int\n    """\n',
            CheckSettings(select=("PDF722",), docstring_convention=DocstringConvention.REST, docstring_parse_doctests=False),
            ((5,),),
            id="doctest",
        ),
        pytest.param(
            'def convert(value):\n    """Convert.\n\n    - Example:\n        :type value: int\n    """\n',
            CheckSettings(select=("PDF722",), docstring_convention=DocstringConvention.REST, docstring_parse_list_items=False),
            ((5,),),
            id="list-item",
        ),
        pytest.param(
            'def convert(value):\n    """Convert.\n\n    ===== =====\n    :type value: int\n    ===== =====\n    """\n',
            CheckSettings(select=("PDF722",), docstring_convention=DocstringConvention.REST, docstring_parse_tables=False),
            ((5,),),
            id="table",
        ),
        pytest.param(
            'def convert(value):\n    """Convert.\n\n    :type value: int\n    ----------------\n    """\n',
            CheckSettings(select=("PDF722",), docstring_convention=DocstringConvention.REST, docstring_parse_headings=False),
            ((4,),),
            id="heading",
        ),
    ],
)
def test_additional_parser_protection_settings_control_orphan_visibility(source: str, unprotected_settings: CheckSettings, expected_lines: tuple[tuple[int, ...], ...]) -> None:
    assert_pdf722(source, ())
    assert_pdf722(source, expected_lines, settings=unprotected_settings)


def test_indented_field_syntax_inside_value_field_content_is_not_a_separate_type_field() -> None:
    source = 'def convert(value):\n    """Convert a value.\n\n    :param value:\n        :type value: int\n    """\n'

    assert_pdf722(source, ())


def test_docstring_suppression_hides_findings() -> None:
    source = 'def convert(value):\n    """Convert a value.\n\n    :type value: int\n    """  # noqa: PDF722\n'

    assert not format_source(source).unfixed_findings


def test_direct_rule_and_formatter_findings_agree_without_fixes() -> None:
    source = 'def convert(value):\n    """Convert a value.\n\n    :type value: int\n    """\n'
    _, context = contexts(source)
    direct = rule_helpers.rule_findings(PDF722OrphanRestTypeField, context)
    formatted = format_source(source)

    assert tuple(finding.line_numbers for finding in direct) == ((4,),)
    assert tuple(finding.line_numbers for finding in formatted.unfixed_findings) == ((4,),)
    assert not rule_helpers.rule_fix_result(PDF722OrphanRestTypeField, context).fixed_findings


def test_escaped_and_concatenated_docstrings_use_existing_source_mapping_fallbacks() -> None:
    escaped = 'def convert(value):\n    """Convert.\\n\\n:type value: int"""\n'
    concatenated = 'def convert(value):\n    ("Convert.\\n\\n"\n     ":type value: int")\n'

    assert_pdf722(escaped, ((2,),))
    assert_pdf722(concatenated, ((2, 3),))


def test_crlf_source_reports_the_field_head_line() -> None:
    source = 'def convert(value):\r\n    """Convert.\r\n\r\n    :type value: int\r\n    """\r\n'

    assert_pdf722(source, ((4,),))


def test_type_only_fields_trigger_missing_value_rules_but_not_missing_description_rules() -> None:
    source = 'def convert(value: int) -> str:\n    """Convert a value.\n\n    :type value: int\n    :rtype: str\n    """\n    return str(value)\n'
    settings = CheckSettings(select=("PDF500", "PDF502", "PDF700", "PDF704", "PDF722"), docstring_convention=DocstringConvention.REST)
    result = format_source(source, settings=settings)

    assert codes(result) == ("PDF500", "PDF502", "PDF722", "PDF722")


def test_orphans_remain_available_to_extraneous_mismatch_and_forbidden_type_rules() -> None:
    stale_source = 'def convert():\n    """Convert.\n\n    :type stale: int\n    """\n'
    mismatch_source = 'def convert(value: int):\n    """Convert.\n\n    :type value: str\n    """\n'
    stale_settings = CheckSettings(select=("PDF501", "PDF722"), docstring_convention=DocstringConvention.REST)
    mismatch_settings = CheckSettings(select=("PDF703", "PDF722"), docstring_convention=DocstringConvention.REST)
    forbidden_settings = CheckSettings(select=("PDF702", "PDF722"), docstring_convention=DocstringConvention.REST)

    assert codes(format_source(stale_source, settings=stale_settings)) == ("PDF501", "PDF722")
    assert codes(format_source(mismatch_source, settings=mismatch_settings, fix=False)) == ("PDF703", "PDF722")
    assert codes(format_source(mismatch_source, settings=forbidden_settings)) == ("PDF702", "PDF722")


def test_empty_and_repeated_type_fields_keep_independent_diagnostics() -> None:
    empty_source = 'def convert(value):\n    """Convert.\n\n    :type value:\n    """\n'
    repeated_source = 'def convert(value):\n    """Convert.\n\n    :type value: int\n    :param value: Value.\n    :type value: str\n    """\n'
    empty_settings = CheckSettings(select=("PDF406", "PDF722"), docstring_convention=DocstringConvention.REST)
    repeated_settings = CheckSettings(select=("PDF412", "PDF722"), docstring_convention=DocstringConvention.REST)

    assert codes(format_source(empty_source, settings=empty_settings)) == ("PDF406", "PDF722")
    assert codes(format_source(repeated_source, settings=repeated_settings)) == ("PDF412", "PDF722")


def test_malformed_type_field_remains_pdf414_only() -> None:
    source = 'def convert(value):\n    """Convert.\n\n    :type: int\n    """\n'
    settings = CheckSettings(select=("PDF414", "PDF722"), docstring_convention=DocstringConvention.REST)

    assert codes(format_source(source, settings=settings)) == ("PDF414",)


def test_field_normalization_fixes_preserve_pairing_and_converge() -> None:
    source = 'def convert(value):\n    """Convert.\n\n    :argument   value : Value.\n    :type value:int\n    :returns  : Result.\n    :rtype:int\n    """\n    return 1\n'
    settings = CheckSettings(select=("PDF401", "PDF402", "PDF409", "PDF722"), docstring_convention=DocstringConvention.REST)
    first = format_source(source, settings=settings)
    new_source = first.new_source

    assert new_source == 'def convert(value):\n    """Convert.\n\n    :param value: Value.\n    :type value: int\n    :return: Result.\n    :rtype: int\n    """\n    return 1\n'
    assert not first.unfixed_findings

    second = format_source(new_source, settings=settings)

    assert not second.fixed_findings
    assert not second.unfixed_findings
