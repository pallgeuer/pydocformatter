"""Tests for PDF414 malformed-convention-entry."""

# Future imports
from __future__ import annotations

# Standard library imports
import dataclasses

# Third-party imports
import pytest

# First-party imports
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
import pydocformatter.rules.definitions.PDF.PDF414_malformed_convention_entry as PDF414_definition
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention, DocstringMissingDocumentation
from pydocformatter.rules.definition_helpers import type_expressions
from pydocformatter.rules.definitions.PDF.PDF101_docstring_reflow import PDF101DocstringReflow
from pydocformatter.rules.definitions.PDF.PDF414_malformed_convention_entry import PDF414MalformedConventionEntry
from pydocformatter.rules.definitions.PDF.PDF500_missing_parameter_documentation import PDF500MissingParameterDocumentation
from pydocformatter.rules.definitions.PDF.PDF502_missing_return_documentation import PDF502MissingReturnDocumentation
from pydocformatter.rules.definitions.PDF.PDF506_missing_exception_documentation import PDF506MissingExceptionDocumentation
from tests.rules.PDF import helpers as pdf_helpers


format_source = pdf_helpers.formatter_for("PDF414")


def assert_pdf414(source: str, expected_lines: tuple[tuple[int, ...], ...], expected_messages: tuple[str, ...], *, convention: DocstringConvention) -> None:
    """Assert PDF414 findings for source under one convention."""
    result = pdf_helpers.assert_unfixed_lines(
        format_source, source, expected_lines, meta=PDF414MalformedConventionEntry.meta, settings=CheckSettings(select=("PDF414",), docstring_convention=convention)
    )
    assert tuple(finding.message for finding in result.unfixed_findings) == expected_messages


def test_metadata() -> None:
    """Expose the intended stable diagnostic-only rule identity."""
    assert PDF414MalformedConventionEntry.meta.name == "malformed-convention-entry"
    assert PDF414MalformedConventionEntry.meta.stable_since == "1.1.0"


def test_instance_message_rejects_indentation_issue_kind() -> None:
    """Fail explicitly if PDF414 receives an issue owned by PDF415."""
    issue = PDF_definition.ConventionEntryIssue(kind=PDF_definition.ConventionEntryIssueKind.GOOGLE_ENTRY_INDENTATION, start_line=0)

    with pytest.raises(AssertionError, match="Unsupported PDF414"):
        PDF414_definition._instance_message(issue)


def test_reports_google_missing_separator_and_unbalanced_type() -> None:
    """Report both supported Google syntax defect families."""
    source = 'def convert(value, option):\n    """Convert values.\n\n    Args:\n        value (int) The value.\n        option (str: The option.\n    """\n'
    assert_pdf414(
        source,
        ((5,), (6,)),
        ("Google docstring entry 'value' is missing the colon before its description", "Google docstring entry 'option' has an unbalanced parenthesized type"),
        convention=DocstringConvention.GOOGLE,
    )


def test_google_name_confidence_includes_receivers_and_variadics() -> None:
    """Use all signature parameter categories while ignoring stars for comparison."""
    source = 'class Example:\n    def convert(self, /, value, *args, option, **kwargs):\n        """Convert values.\n\n        Args:\n            self Receiver.\n            value Value.\n            *args Positional values.\n            option Option.\n            **kwargs Keyword values.\n        """\n'
    assert_pdf414(
        source,
        ((6,), (7,), (8,), (9,), (10,)),
        (
            "Google docstring entry 'self' is missing the colon before its description",
            "Google docstring entry 'value' is missing the colon before its description",
            "Google docstring entry '*args' is missing the colon before its description",
            "Google docstring entry 'option' is missing the colon before its description",
            "Google docstring entry '**kwargs' is missing the colon before its description",
        ),
        convention=DocstringConvention.GOOGLE,
    )


def test_closed_google_type_is_strong_entry_evidence() -> None:
    """Allow closed parenthesized syntax to establish parameter intent."""
    source = 'def convert():\n    """Convert values.\n\n    Args:\n        undocumented (int) The value.\n    """\n'
    assert_pdf414(source, ((5,),), ("Google docstring entry 'undocumented' is missing the colon before its description",), convention=DocstringConvention.GOOGLE)


def test_closed_google_type_is_strong_evidence_for_attributes_and_methods_but_not_exceptions() -> None:
    """Apply closed-type evidence only to entry families where it is unambiguous."""
    source = 'class Example:\n    """Describe an example.\n\n    Attributes:\n        stale_attribute (int) Stored value.\n\n    Methods:\n        stale_method (Callable) Perform work.\n\n    Raises:\n        Problem (str) Failure detail.\n    """\n'
    assert_pdf414(
        source,
        ((5,), (8,)),
        ("Google docstring entry 'stale_attribute' is missing the colon before its description", "Google docstring entry 'stale_method' is missing the colon before its description"),
        convention=DocstringConvention.GOOGLE,
    )


@pytest.mark.parametrize("name", ["ValueError", "pkg.CustomException", "RuntimeWarning"])
def test_google_exception_suffix_is_strong_evidence(name: str) -> None:
    """Recognize conventional exception suffixes without an owner inventory."""
    source = f'def convert():\n    """Convert values.\n\n    Raises:\n        {name} Failure detail.\n    """\n'
    assert_pdf414(source, ((5,),), (f"Google docstring entry '{name}' is missing the colon before its description",), convention=DocstringConvention.GOOGLE)


def test_google_exception_list_requires_every_explicit_name_to_be_exception_like() -> None:
    """Recover complete pipe/comma lists without trusting only their first name."""
    source = 'def convert():\n    """Convert values.\n\n    Raises:\n        ValueError | pkg.CustomError Failure detail.\n        TypeError, RuntimeError Other failure detail.\n        `KeyError` | `IndexError` Lookup failure detail.\n        LookupError | Problem Ambiguous prose.\n        `UnclosedError Failure detail.\n    """\n'
    assert_pdf414(
        source,
        ((5,), (6,), (7,)),
        (
            "Google docstring entry 'ValueError', 'pkg.CustomError' is missing the colon before its description",
            "Google docstring entry 'TypeError', 'RuntimeError' is missing the colon before its description",
            "Google docstring entry 'KeyError', 'IndexError' is missing the colon before its description",
        ),
        convention=DocstringConvention.GOOGLE,
    )


def test_google_exception_parenthesized_type_preserves_unbalanced_type_precedence() -> None:
    """Keep the more precise type diagnostic ahead of exception missing-separator recovery."""
    source = 'def convert():\n    """Convert values.\n\n    Raises:\n        ValueError (str: Failure detail.\n        TypeError (str) Other failure detail.\n    """\n'
    assert_pdf414(
        source,
        ((5,), (6,)),
        ("Google docstring entry 'ValueError' has an unbalanced parenthesized type", "Google docstring entry 'TypeError' is missing the colon before its description"),
        convention=DocstringConvention.GOOGLE,
    )


def test_google_balanced_type_delimiters_do_not_create_false_unbalanced_type_findings() -> None:
    """Ignore quoted delimiters while locating the outer type close."""
    source = 'def convert(value):\n    """Convert values.\n\n    Args:\n        value (Literal[":", ")"]) Missing separator.\n    """\n'
    assert_pdf414(source, ((5,),), ("Google docstring entry 'value' is missing the colon before its description",), convention=DocstringConvention.GOOGLE)


@pytest.mark.parametrize("type_text", ["list[int", "dict{str]", '"unterminated', "tuple[(int]"])
def test_google_flat_matches_require_balanced_nested_type_syntax(type_text: str) -> None:
    """Reject flat-regex matches with unbalanced delimiters or quotes."""
    source = f'def convert(value):\n    """Convert values.\n\n    Args:\n        value ({type_text}): Description.\n    """\n'
    assert_pdf414(source, ((5,),), ("Google docstring entry 'value' has an unbalanced parenthesized type",), convention=DocstringConvention.GOOGLE)


def test_unbalanced_google_type_remains_outside_semantic_parameter_entries() -> None:
    """Report malformed syntax without allowing it to satisfy parameter documentation."""
    source = 'def convert(value):\n    """Convert values.\n\n    Args:\n        value (list[int): Description.\n    """\n'
    settings = CheckSettings(select=("PDF414", "PDF500"), docstring_convention=DocstringConvention.GOOGLE, docstring_missing_documentation=DocstringMissingDocumentation.ALL_DOCSTRINGS)
    result = format_source(source, settings=settings)

    assert tuple(finding.rule for finding in result.unfixed_findings) == (PDF414MalformedConventionEntry.meta, PDF500MissingParameterDocumentation.meta)
    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Google docstring entry 'value' has an unbalanced parenthesized type",
        "Function parameter 'value' is missing docstring documentation",
    )


def test_google_prose_and_non_exception_names_are_not_reported() -> None:
    """Avoid treating weak entry-like prose as malformed syntax."""
    source = 'def convert(value):\n    """Convert values.\n\n    Args:\n        unrelated prose about conversion.\n        unknown (int: Unclosed but not inventory-backed.\n\n    Raises:\n        Problem Failure detail.\n        `not valid` Failure detail.\n    """\n'
    assert_pdf414(source, (), (), convention=DocstringConvention.GOOGLE)


def test_reports_numpy_missing_type_and_separator() -> None:
    """Report missing NumPy entry components with inventory-backed names."""
    source = 'def convert(value, option):\n    """Convert values.\n\n    Parameters\n    ----------\n    value :\n    option list[str]\n    """\n'
    assert_pdf414(
        source,
        ((6,), (7,)),
        ("NumPy docstring entry 'value' is missing its type after the colon", "NumPy docstring entry 'option' is missing the colon before its type"),
        convention=DocstringConvention.NUMPY,
    )


def test_numpy_confidence_uses_class_and_instance_attributes_and_direct_methods_without_leaking_unknown_names() -> None:
    """Use the complete owning-class inventory while keeping unrelated names out."""
    source = 'class Client:\n    """Describe the client.\n\n    Attributes\n    ----------\n    class_value int\n    instance_value str\n    foreign_value bytes\n\n    Methods\n    -------\n    run Callable[..., None]\n    foreign_method Callable\n    """\n\n    class_value = 1\n\n    def __init__(self):\n        self.instance_value = ""\n\n    def run(self):\n        pass\n'
    assert_pdf414(
        source,
        ((6,), (7,), (12,)),
        (
            "NumPy docstring entry 'class_value' is missing the colon before its type",
            "NumPy docstring entry 'instance_value' is missing the colon before its type",
            "NumPy docstring entry 'run' is missing the colon before its type",
        ),
        convention=DocstringConvention.NUMPY,
    )


def test_attached_multi_target_docstring_uses_only_its_own_attribute_targets_for_confidence() -> None:
    """Give attached docstrings confidence in every assignment target but no unrelated module attribute."""
    source = 'first = second = 1\n"""Describe stored values.\n\nAttributes:\n    first First value.\n    second Second value.\n    third Unrelated value.\n"""\n'
    assert_pdf414(
        source,
        ((5,), (6,)),
        ("Google docstring entry 'first' is missing the colon before its description", "Google docstring entry 'second' is missing the colon before its description"),
        convention=DocstringConvention.GOOGLE,
    )


def test_nested_class_members_do_not_leak_into_the_outer_class_inventory() -> None:
    """Restrict attribute and method confidence to direct members of the documented class."""
    source = 'class Outer:\n    """Describe the outer class.\n\n    Attributes:\n        nested_value Stored value.\n\n    Methods:\n        nested_method Perform work.\n    """\n\n    class Nested:\n        nested_value = 1\n\n        def nested_method(self):\n            pass\n'
    assert_pdf414(source, (), (), convention=DocstringConvention.GOOGLE)


def test_numpy_multi_name_variadics_require_all_names_to_match_the_signature() -> None:
    """Recover a complete variadic name list and reject a partially matching list."""
    source = 'def collect(*args, **kwargs):\n    """Collect values.\n\n    Parameters\n    ----------\n    *args, **kwargs tuple[object, ...]\n    *args, unknown tuple[object, ...]\n    """\n'
    assert_pdf414(source, ((6,),), ("NumPy docstring entry '*args', '**kwargs' is missing the colon before its type",), convention=DocstringConvention.NUMPY)


def test_numpy_missing_type_requires_every_name_to_match_the_owner_inventory() -> None:
    """Avoid reporting a missing type for stale names despite an explicit colon."""
    source = 'def collect():\n    """Collect values.\n\n    Parameters\n    ----------\n    stale.name, *extra :\n    """\n'
    assert_pdf414(source, (), (), convention=DocstringConvention.NUMPY)


def test_numpy_missing_separator_accepts_quoted_forward_reference() -> None:
    """Use detection-local quoted forward references as conservative types."""
    source = 'def convert(value):\n    """Convert values.\n\n    Parameters\n    ----------\n    value "pkg.Model"\n    """\n'
    assert_pdf414(source, ((6,),), ("NumPy docstring entry 'value' is missing the colon before its type",), convention=DocstringConvention.NUMPY)


def test_numpy_missing_separator_rejects_quoted_type_with_top_level_newline() -> None:
    """Avoid diagnosing quoted text that decodes to invalid top-level type syntax."""
    source = 'def convert(value):\n    r"""Convert values.\n\n    Parameters\n    ----------\n    value "int\\n| str"\n    """\n'
    assert_pdf414(source, (), (), convention=DocstringConvention.NUMPY)


def test_numpy_missing_separator_requires_inventory_and_type_confidence() -> None:
    """Reject weak NumPy prose and unknown names."""
    source = 'def convert(value):\n    """Convert values.\n\n    Parameters\n    ----------\n    unrelated int\n    value ordinary prose\n    value "ordinary prose"\n    """\n'
    assert_pdf414(source, (), (), convention=DocstringConvention.NUMPY)


def test_numpy_missing_separator_type_validation_is_iterative_and_ast_free(monkeypatch: pytest.MonkeyPatch) -> None:
    """Handle a deeply nested type candidate without invoking Python's recursive expression parser."""
    monkeypatch.setattr(type_expressions, "parse_type_like_expr", pytest.fail)
    type_text = f"{'list[' * 3000}int{']' * 3000}"
    source = f'def convert(value):\n    """Convert values.\n\n    Parameters\n    ----------\n    value {type_text}\n    """\n'
    assert_pdf414(source, ((6,),), ("NumPy docstring entry 'value' is missing the colon before its type",), convention=DocstringConvention.NUMPY)


def test_reports_rest_delimiter_and_argument_arity() -> None:
    """Report all supported standard reStructuredText field defects."""
    source = 'def convert(value):\n    """Convert a value.\n\n    :param value The value.\n    :param: The value.\n    :returns result: The result.\n    """\n'
    assert_pdf414(
        source,
        ((4,), (5,), (6,)),
        (
            "reStructuredText field ':param:' is missing its closing colon",
            "reStructuredText field ':param:' is missing its required argument",
            "reStructuredText field ':returns:' has an unexpected argument",
        ),
        convention=DocstringConvention.REST,
    )


def test_all_named_rest_field_families_require_arguments() -> None:
    """Lock in required arguments for parameter, exception, and attribute field families."""
    source = 'def convert(value):\n    """Convert a value.\n\n    :param: Value.\n    :type: int\n    :raises: Failure.\n    :ivar: Instance value.\n    :cvar: Class value.\n    :var: Value.\n    :vartype: str\n    """\n'
    assert_pdf414(
        source,
        ((4,), (5,), (6,), (7,), (8,), (9,), (10,)),
        (
            "reStructuredText field ':param:' is missing its required argument",
            "reStructuredText field ':type:' is missing its required argument",
            "reStructuredText field ':raises:' is missing its required argument",
            "reStructuredText field ':ivar:' is missing its required argument",
            "reStructuredText field ':cvar:' is missing its required argument",
            "reStructuredText field ':var:' is missing its required argument",
            "reStructuredText field ':vartype:' is missing its required argument",
        ),
        convention=DocstringConvention.REST,
    )


def test_all_owner_wide_rest_field_families_reject_arguments() -> None:
    """Lock in owner-wide arity for return value and type aliases."""
    source = 'def convert(value):\n    """Convert a value.\n\n    :return result: Value.\n    :returns result: Value.\n    :rtype result: int\n    """\n'
    assert_pdf414(
        source,
        ((4,), (5,), (6,)),
        (
            "reStructuredText field ':return:' has an unexpected argument",
            "reStructuredText field ':returns:' has an unexpected argument",
            "reStructuredText field ':rtype:' has an unexpected argument",
        ),
        convention=DocstringConvention.REST,
    )


def test_rest_yield_fields_retain_named_and_owner_wide_forms() -> None:
    """Avoid imposing return-field arity on the intentionally permissive yield families."""
    source = 'def generate():\n    """Generate values.\n\n    :yield: Value.\n    :yield item: Value.\n    :yields: Value.\n    :yields item: Value.\n    :ytype: int\n    :ytype item: int\n    """\n'
    assert_pdf414(source, (), (), convention=DocstringConvention.REST)


def test_rest_missing_delimiter_is_case_normalized_and_limited_to_standard_fields() -> None:
    """Recognize standard fields case-insensitively without consuming roles, custom fields, or double-colon text."""
    source = 'def convert(value):\n    """Convert a value.\n\n    :VARTYPE value\n\n    :unknown value\n\n    ::param value\n\n    :class:`Example`\n    """\n'
    assert_pdf414(source, ((4,),), ("reStructuredText field ':vartype:' is missing its closing colon",), convention=DocstringConvention.REST)


def test_rest_missing_delimiter_uses_field_arity_as_confidence() -> None:
    """Require a credible named argument and avoid treating owner-wide field prose as malformed syntax."""
    source = 'def convert(value):\n    """Convert a value.\n\n    :param value The value.\n\n    :raises ValueError Failure detail.\n\n    :raises Problem Failure detail.\n\n    :returns Result prose.\n\n    :rtype int\n\n    :return\n    """\n'
    assert_pdf414(
        source,
        ((4,), (6,), (14,)),
        (
            "reStructuredText field ':param:' is missing its closing colon",
            "reStructuredText field ':raises:' is missing its closing colon",
            "reStructuredText field ':return:' is missing its closing colon",
        ),
        convention=DocstringConvention.REST,
    )


def test_custom_rest_fields_are_not_subject_to_standard_arity() -> None:
    """Leave extension fields outside standard field-arity checks."""
    source = 'def convert(value):\n    """Convert a value.\n\n    :custom: Description.\n    :custom value: Description.\n    """\n'
    assert_pdf414(source, (), (), convention=DocstringConvention.REST)


def test_parseable_numpy_colon_spacing_belongs_only_to_pdf409() -> None:
    """Do not classify a parseable spacing defect as malformed syntax."""
    source = 'def convert(value):\n    """Convert a value.\n\n    Parameters\n    ----------\n    value:int\n        The value.\n    """\n'
    assert_pdf414(source, (), (), convention=DocstringConvention.NUMPY)


@pytest.mark.parametrize(
    ("settings_to_disable", "source", "line_number"),
    [
        (("docstring_parse_code_fences", "docstring_parse_headings"), 'def convert(value):\n    """Convert a value.\n\n    Args:\n        ```text\n        value Value.\n        ```\n    """\n', 6),
        (("docstring_parse_directives", "docstring_parse_literal_blocks"), 'def convert(value):\n    """Convert a value.\n\n    Args:\n        .. note::\n            value Value.\n    """\n', 6),
        (("docstring_parse_literal_blocks",), 'def convert(value):\n    """Convert a value.\n\n    Args:\n        Example::\n\n            value Value.\n    """\n', 7),
        (("docstring_parse_list_items",), 'def convert(value):\n    """Convert a value.\n\n    Args:\n        - Example\n            value Value.\n    """\n', 6),
        (("docstring_parse_doctests",), 'def convert(value):\n    """Convert a value.\n\n    Args:\n        >>> print("example")\n        value Value.\n    """\n', 6),
    ],
)
def test_protected_structure_settings_control_whether_nested_candidates_are_inspected(settings_to_disable: tuple[str, ...], source: str, line_number: int) -> None:
    """Keep candidates protected until every parser matching the surrounding structure is disabled."""
    protected = CheckSettings(select=("PDF414",), docstring_convention=DocstringConvention.GOOGLE)
    partially_unprotected = dataclasses.replace(protected, **{settings_to_disable[0]: False})
    unprotected = dataclasses.replace(protected, **dict.fromkeys(settings_to_disable, False))

    assert not format_source(source, settings=protected).unfixed_findings
    if len(settings_to_disable) > 1:
        assert not format_source(source, settings=partially_unprotected).unfixed_findings
    result = format_source(source, settings=unprotected)
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((line_number,),)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Google docstring entry 'value' is missing the colon before its description",)


def test_implicitly_concatenated_docstring_uses_whole_expression_line_fallback() -> None:
    """Report unmapped evaluated lines against the complete concatenated expression."""
    source = 'def convert(value):\n    (\n        "Convert a value.\\n\\n"\n        "Args:\\n"\n        "    value Value."\n    )\n'
    result = format_source(source)

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((3, 4, 5),)


def test_arity_invalid_rest_fields_do_not_satisfy_parameter_or_return_documentation() -> None:
    """Keep malformed fields outside semantic completeness checks while reporting both facts."""
    source = 'def convert(value):\n    """Convert a value.\n\n    :param: Value.\n    :returns result: Result.\n    """\n    return value\n'
    settings = CheckSettings(select=("PDF414", "PDF500", "PDF502"), docstring_convention=DocstringConvention.REST, docstring_missing_documentation=DocstringMissingDocumentation.ALL_DOCSTRINGS)
    result = format_source(source, settings=settings)

    assert tuple(finding.rule for finding in result.unfixed_findings) == (
        PDF414MalformedConventionEntry.meta,
        PDF414MalformedConventionEntry.meta,
        PDF500MissingParameterDocumentation.meta,
        PDF502MissingReturnDocumentation.meta,
    )
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((4,), (5,), (1,), (7,))


def test_malformed_google_exception_does_not_satisfy_raised_exception_documentation() -> None:
    """Report malformed syntax and the independently missing semantic exception entry."""
    source = 'def convert():\n    """Convert a value.\n\n    Raises:\n        ValueError Failure detail.\n    """\n    raise ValueError\n'
    settings = CheckSettings(select=("PDF414", "PDF506"), docstring_convention=DocstringConvention.GOOGLE, docstring_missing_documentation=DocstringMissingDocumentation.ALL_DOCSTRINGS)
    result = format_source(source, settings=settings)

    assert tuple(finding.rule for finding in result.unfixed_findings) == (PDF414MalformedConventionEntry.meta, PDF506MissingExceptionDocumentation.meta)
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((5,), (7,))


def test_mixed_valid_and_malformed_numpy_entries_preserve_only_valid_semantics() -> None:
    """Keep valid peers available to completeness checks without promoting a malformed entry."""
    source = 'def combine(first, second):\n    """Combine values.\n\n    Parameters\n    ----------\n    first int\n    second : str\n        Second value.\n    """\n'
    settings = CheckSettings(select=("PDF414", "PDF500"), docstring_convention=DocstringConvention.NUMPY, docstring_missing_documentation=DocstringMissingDocumentation.ALL_DOCSTRINGS)
    result = format_source(source, settings=settings)

    assert tuple(finding.rule for finding in result.unfixed_findings) == (PDF414MalformedConventionEntry.meta, PDF500MissingParameterDocumentation.meta)
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((6,), (1,))
    assert result.unfixed_findings[1].message == "Function parameter 'first' is missing docstring documentation"


def test_pdf101_does_not_merge_adjacent_malformed_numpy_entries() -> None:
    """Keep diagnosed NumPy candidates unchanged and independently visible."""
    source = 'def combine(first, second):\n    """Combine values.\n\n    Parameters\n    ----------\n    first tuple[int, int]\n    second list[str]\n    """\n'
    settings = CheckSettings(select=("PDF101", "PDF414"), docstring_convention=DocstringConvention.NUMPY)
    result = format_source(source, settings=settings)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "NumPy docstring entry 'first' is missing the colon before its type",
        "NumPy docstring entry 'second' is missing the colon before its type",
    )


def test_malformed_numpy_entry_splits_reflowable_surrounding_prose() -> None:
    """Reflow ordinary section prose without consuming the diagnosed entry line."""
    source = 'def convert(first):\n    """Convert values.\n\n    Parameters\n    ----------\n    Narrative section prose that is intentionally long enough to wrap.\n    first int\n    """\n'
    settings = CheckSettings(select=("PDF101", "PDF414"), docstring_convention=DocstringConvention.NUMPY, line_length=45)
    result = format_source(source, settings=settings)

    assert (
        result.new_source
        == 'def convert(first):\n    """Convert values.\n\n    Parameters\n    ----------\n    Narrative section prose that is\n    intentionally long enough to wrap.\n    first int\n    """\n'
    )
    assert result.fixed_findings == {PDF101DocstringReflow.meta: 1}
    assert tuple(finding.message for finding in result.unfixed_findings) == ("NumPy docstring entry 'first' is missing the colon before its type",)


@pytest.mark.parametrize("separator", ["", "\n"])
def test_malformed_rest_fields_preserve_layout_and_remain_individually_diagnosed(separator: str) -> None:
    """Keep adjacent or blank-separated malformed fields outside layout fixes."""
    source = f'def convert(value):\n    """Convert values.\n:param value Missing delimiter.{separator}\n:type value Missing delimiter.\n    """\n'
    settings = CheckSettings(select=("PDF101", "PDF200", "PDF201", "PDF414"), docstring_convention=DocstringConvention.REST)
    result = format_source(source, settings=settings)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "reStructuredText field ':param:' is missing its closing colon",
        "reStructuredText field ':type:' is missing its closing colon",
    )


@pytest.mark.parametrize(
    ("convention", "body"),
    [
        (DocstringConvention.GOOGLE, "Parameters\n    ----------\n    value int"),
        (DocstringConvention.NUMPY, "Args:\n        value Value."),
        (DocstringConvention.REST, "Args:\n        value Value."),
        (DocstringConvention.GOOGLE, ":param value Value."),
    ],
)
def test_mismatched_convention_syntax_is_not_diagnosed(convention: DocstringConvention, body: str) -> None:
    """Follow only the configured convention instead of detecting a different syntax."""
    source = f'def convert(value):\n    """Convert a value.\n\n    {body}\n    """\n'
    assert_pdf414(source, (), (), convention=convention)


def test_docstring_suppression_hides_findings() -> None:
    """Honor whole-docstring suppression from the closing delimiter line."""
    source = 'def convert(value):\n    """Convert a value.\n\n    Args:\n        value Value.\n    """  # noqa: PDF414\n'
    result = format_source(source)
    assert not result.unfixed_findings


def test_signature_line_suppression_does_not_hide_docstring_syntax_findings() -> None:
    """Keep suppression attachment on the malformed docstring rather than its owner signature."""
    source = 'def convert(value):  # noqa: PDF414\n    """Convert a value.\n\n    Args:\n        value Value.\n    """\n'
    result = format_source(source)
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((5,),)


@pytest.mark.parametrize("selector", ["PDF414", "PDF4", "PDF", "ALL"])
def test_normal_selectors_include_rule(selector: str) -> None:
    """Keep the objective diagnostic in normal broad selection."""
    source = 'def convert(value):\n    """Convert a value.\n\n    Args:\n        value Value.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=(selector,), docstring_convention=DocstringConvention.GOOGLE), fix=False)
    assert PDF414MalformedConventionEntry.meta in {finding.rule for finding in result.unfixed_findings}


@pytest.mark.parametrize("convention", [DocstringConvention.NONE, DocstringConvention.PEP257])
def test_rule_is_disabled_for_unparsed_conventions(convention: DocstringConvention) -> None:
    """Disable exact selection where convention entries are not parsed."""
    source = 'def convert(value):\n    """Convert a value.\n\n    Args:\n        value Value.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF414",), docstring_convention=convention))
    assert not result.unfixed_findings
