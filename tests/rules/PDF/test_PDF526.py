# Future imports
from __future__ import annotations

# Standard library imports
import itertools
import dataclasses
from typing import TYPE_CHECKING

# Third-party imports
import pytest

# First-party imports
import tests.rules.PDF.helpers as pdf_helpers
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention, DocstringMissingDocumentation
from pydocformatter.rules.definition_helpers import parameter_documentation
from pydocformatter.rules.definitions.PDF.PDF import PDF, DefinitionKind
from pydocformatter.rules.definitions.PDF.PDF409_docstring_entry_spacing import PDF409DocstringEntrySpacing
from pydocformatter.rules.definitions.PDF.PDF526_parameter_documentation_order import PDF526ParameterDocumentationOrder
from tests import rule_helpers


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter import formatter


contexts = pdf_helpers.contexts_for("PDF526")
format_source = pdf_helpers.formatter_for("PDF526")


def assert_pdf526_lines(source: str, expected: tuple[tuple[int, ...], ...], *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Assert PDF526 line findings for source."""
    return pdf_helpers.assert_unfixed_lines(format_source, source, expected, meta=PDF526ParameterDocumentationOrder.meta, settings=settings)


def test_reports_swapped_google_parameters_with_signature_names() -> None:
    source = 'def combine(first, second, third):\n    """Combine values.\n\n    Args:\n        second: Second value.\n        first: First value.\n        third: Third value.\n    """\n'
    result = assert_pdf526_lines(source, ((6,),))

    assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring parameter 'first' should appear before 'second' to match the function signature",)
    assert not result.unfixed_findings[0].fixable


@pytest.mark.parametrize(
    ("documented_names", "expected_names"),
    [
        (("first", "second", "third", "fourth"), ()),
        (("third", "first", "second", "fourth"), ("first", "second")),
        (("second", "third", "first", "fourth"), ("first",)),
        (("fourth", "third", "second", "first"), ("third", "second", "first")),
        (("second", "first", "fourth", "third"), ("first", "third")),
    ],
)
def test_greatest_earlier_rank_reporting(documented_names: tuple[str, ...], expected_names: tuple[str, ...]) -> None:
    entries = "".join(f"        {name}: {name.title()} value.\n" for name in documented_names)
    source = f'def combine(first, second, third, fourth):\n    """Combine values.\n\n    Args:\n{entries}    """\n'
    result = format_source(source)

    assert tuple(finding.message.split("'")[1] for finding in result.unfixed_findings) == expected_names


def test_every_permutation_of_every_documented_signature_subset_reports_exactly_the_late_occurrences() -> None:
    signature_names = ("first", "second", "third", "fourth")
    rank_by_name = {name: rank for rank, name in enumerate(signature_names)}
    for size in range(2, len(signature_names) + 1):
        for subset in itertools.combinations(signature_names, size):
            for documented_names in itertools.permutations(subset):
                entries = "".join(f"        {name}: {name.title()} value.\n" for name in documented_names)
                source = f'def combine(first, second, third, fourth):\n    """Combine values.\n\n    Args:\n{entries}    """\n'
                result = format_source(source)
                expected_names = tuple(name for index, name in enumerate(documented_names) if any(rank_by_name[earlier] > rank_by_name[name] for earlier in documented_names[:index]))

                assert tuple(finding.message.split("'")[1] for finding in result.unfixed_findings) == expected_names, documented_names


def test_orders_every_signature_parameter_category_and_displays_variadic_stars() -> None:
    ordered = 'def configure(first, /, second, *args, mode, timeout=1.0, **kwargs):\n    """Configure the client.\n\n    Args:\n        first: First value.\n        second: Second value.\n        args: Extra positional values.\n        mode: Operating mode.\n        timeout: Timeout.\n        kwargs: Extra keyword values.\n    """\n'
    reversed_tail = 'def configure(first, /, second, *args, mode, timeout=1.0, **kwargs):\n    """Configure the client.\n\n    Args:\n        kwargs: Extra keyword values.\n        args: Extra positional values.\n        mode: Operating mode.\n    """\n'
    result = assert_pdf526_lines(reversed_tail, ((6,), (7,)))

    assert not format_source(ordered).unfixed_findings
    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Docstring parameter '*args' should appear before '**kwargs' to match the function signature",
        "Docstring parameter 'mode' should appear before '**kwargs' to match the function signature",
    )


def test_sequence_spans_google_parameter_section_aliases() -> None:
    source = 'def configure(first, *, mode, timeout):\n    """Configure the client.\n\n    Keyword Args:\n        mode: Operating mode.\n        timeout: Timeout.\n\n    Other Arguments:\n        first: First value.\n    """\n'
    result = assert_pdf526_lines(source, ((9,),))

    assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring parameter 'first' should appear before 'timeout' to match the function signature",)


def test_numpy_multi_name_entries_preserve_written_order_and_report_each_late_name() -> None:
    source = 'def combine(first, second, third):\n    """Combine values.\n\n    Parameters\n    ----------\n    third, first, second : int\n        Values.\n    """\n'
    settings = CheckSettings(select=("PDF526",), docstring_convention=DocstringConvention.NUMPY)
    result = assert_pdf526_lines(source, ((6,), (6,)), settings=settings)

    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Docstring parameter 'first' should appear before 'third' to match the function signature",
        "Docstring parameter 'second' should appear before 'third' to match the function signature",
    )


def test_sequence_spans_numpy_parameter_section_aliases() -> None:
    source = 'def combine(first, second, third):\n    """Combine values.\n\n    Other Parameters\n    ----------------\n    second : int\n        Second.\n\n    Receives\n    --------\n    third : int\n        Third.\n\n    Parameters\n    ----------\n    first : int\n        First.\n    """\n'
    settings = CheckSettings(select=("PDF526",), docstring_convention=DocstringConvention.NUMPY)

    assert_pdf526_lines(source, ((16,),), settings=settings)


def test_numpy_multi_name_entry_filters_wrong_case_extraneous_and_repeated_names_without_losing_intra_entry_order() -> None:
    source = 'def combine(first, second, third):\n    """Combine values.\n\n    Parameters\n    ----------\n    third, First, stale, third, first, second : int\n        Values.\n    """\n'
    settings = CheckSettings(select=("PDF526",), docstring_convention=DocstringConvention.NUMPY)
    result = assert_pdf526_lines(source, ((6,), (6,)), settings=settings)

    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Docstring parameter 'first' should appear before 'third' to match the function signature",
        "Docstring parameter 'second' should appear before 'third' to match the function signature",
    )


@pytest.mark.parametrize(
    ("fields", "expected_lines", "expected_name"),
    [
        ((":param second: Second.", ":type second: int", ":param first: First.", ":type first: int"), ((6,),), "first"),
        ((":type second: int", ":param first: First.", ":param second: Second.", ":type first: int"), ((5,),), "first"),
        ((":type first: int", ":type second: int", ":param first: First.", ":param second: Second."), (), None),
        ((":keyword second: Second.", ":type first: int"), ((5,),), "first"),
    ],
)
def test_rest_first_value_or_type_field_establishes_parameter_order(fields: tuple[str, ...], expected_lines: tuple[tuple[int, ...], ...], expected_name: str | None) -> None:
    body = "\n".join(f"    {field}" for field in fields)
    source = f'def combine(first, second):\n    """Combine values.\n\n{body}\n    """\n'
    settings = CheckSettings(select=("PDF526",), docstring_convention=DocstringConvention.REST)
    result = assert_pdf526_lines(source, expected_lines, settings=settings)

    assert tuple(finding.message.split("'")[1] for finding in result.unfixed_findings) == (() if expected_name is None else (expected_name,))


def test_rest_aliases_typed_arguments_and_explicit_stars_use_one_signature_order() -> None:
    source = 'def configure(first, *args, mode, **kwargs):\n    """Configure values.\n\n    :type **kwargs: dict[str, object]\n    :argument tuple[str, ...] *args: Extra positional values.\n    :key mode: Operating mode.\n    :param first: First value.\n    """\n'
    settings = CheckSettings(select=("PDF526",), docstring_convention=DocstringConvention.REST)
    result = assert_pdf526_lines(source, ((5,), (6,), (7,)), settings=settings)

    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Docstring parameter '*args' should appear before '**kwargs' to match the function signature",
        "Docstring parameter 'mode' should appear before '**kwargs' to match the function signature",
        "Docstring parameter 'first' should appear before '**kwargs' to match the function signature",
    )


def test_missing_extraneous_repeated_and_unpack_key_entries_do_not_create_order_findings() -> None:
    source = 'from typing import TypedDict, Unpack\n\n\nclass Options(TypedDict):\n    mode: str\n\n\ndef configure(first, second, **kwargs: Unpack[Options]):\n    """Configure values.\n\n    Args:\n        first: First value.\n        mode: Unpacked option.\n        stale: Obsolete value.\n        second: Second value.\n        first: Repeated first value.\n        kwargs: Complete options.\n    """\n'

    assert not format_source(source).unfixed_findings


def test_unpacked_keys_and_unknown_fields_do_not_reset_a_prior_high_rank() -> None:
    source = 'from typing import TypedDict, Unpack\n\n\nclass Options(TypedDict):\n    mode: str\n\n\ndef configure(first, second, **kwargs: Unpack[Options]):\n    """Configure values.\n\n    Args:\n        kwargs: Complete options.\n        mode: Unpacked option.\n        stale: Obsolete value.\n        first: First value.\n        second: Second value.\n    """\n'
    result = assert_pdf526_lines(source, ((15,), (16,)))

    assert tuple(finding.message.split("'")[3] for finding in result.unfixed_findings) == ("**kwargs", "**kwargs")


def test_explicit_receiver_participates_but_omitted_receiver_does_not() -> None:
    source = 'class Builder:\n    def build(self, value):\n        """Build an item.\n\n        Args:\n            value: Item value.\n            self: Builder instance.\n        """\n\n    @classmethod\n    def create(cls, value):\n        """Create an item.\n\n        Args:\n            value: Item value.\n        """\n\n    @staticmethod\n    def convert(first, second):\n        """Convert an item.\n\n        Args:\n            second: Second value.\n            first: First value.\n        """\n'
    result = assert_pdf526_lines(source, ((7,), (24,)))

    assert tuple(finding.message.split("'")[1] for finding in result.unfixed_findings) == ("self", "first")


def test_unusual_receiver_name_is_ranked_as_an_ordinary_signature_parameter() -> None:
    source = 'class Builder:\n    def build(receiver, value):\n        """Build an item.\n\n        Args:\n            value: Item value.\n            receiver: Builder instance.\n        """\n'

    assert_pdf526_lines(source, ((7,),))


def test_order_state_is_independent_across_free_async_and_class_method_definitions() -> None:
    source = 'def first(first, second):\n    """Process values.\n\n    Args:\n        second: Second value.\n        first: First value.\n    """\n\n\nasync def ordered(first, second):\n    """Process values.\n\n    Args:\n        first: First value.\n        second: Second value.\n    """\n\n\nclass Builder:\n    @classmethod\n    async def create(cls, first, second):\n        """Create a value.\n\n        Args:\n            second: Second value.\n            cls: Builder class.\n            first: First value.\n        """\n'
    result = assert_pdf526_lines(source, ((6,), (26,), (27,)))

    assert tuple(finding.message.split("'")[1] for finding in result.unfixed_findings) == ("first", "cls", "first")


@pytest.mark.parametrize("convention", [DocstringConvention.NONE, DocstringConvention.PEP257])
def test_unparsed_conventions_disable_exact_selection(convention: DocstringConvention) -> None:
    source = 'def combine(first, second):\n    """Combine values.\n\n    Args:\n        second: Second.\n        first: First.\n    """\n'

    assert_pdf526_lines(source, (), settings=CheckSettings(select=("PDF526",), docstring_convention=convention))


@pytest.mark.parametrize("selector", ["PDF526", "PDF5", "PDF", "ALL"])
def test_exact_and_broad_selectors_enable_the_rule_for_parsed_conventions(selector: str) -> None:
    source = 'def combine(first, second):\n    """Combine values.\n\n    Args:\n        second: Second.\n        first: First.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=(selector,), docstring_convention=DocstringConvention.GOOGLE), fix=False)

    assert PDF526ParameterDocumentationOrder.meta in {finding.rule for finding in result.unfixed_findings}


@pytest.mark.parametrize(
    ("convention", "body", "expected_line"),
    [
        (DocstringConvention.NUMPY, "Parameters\n    ----------\n    second : int\n        Second.\n    first : int\n        First.", 8),
        (DocstringConvention.REST, ":param second: Second.\n    :param first: First.", 5),
    ],
)
def test_broad_pdf5_selection_enables_the_rule_for_every_non_google_parsed_convention(convention: DocstringConvention, body: str, expected_line: int) -> None:
    source = f'def combine(first, second):\n    """Combine values.\n\n    {body}\n    """\n'
    settings = CheckSettings(select=("PDF5",), docstring_convention=convention)

    assert_pdf526_lines(source, ((expected_line,),), settings=settings)


@pytest.mark.parametrize("policy", list(DocstringMissingDocumentation))
@pytest.mark.parametrize("public_only", [False, True])
def test_missing_documentation_settings_do_not_change_order_checks_for_existing_private_documentation(policy: DocstringMissingDocumentation, public_only: bool) -> None:
    source = 'def _combine(first, second):\n    """Combine values.\n\n    Args:\n        second: Second value.\n        first: First value.\n    """\n'
    settings = CheckSettings(select=("PDF526",), docstring_convention=DocstringConvention.GOOGLE, docstring_missing_documentation=policy, docstring_missing_documentation_public_only=public_only)

    assert_pdf526_lines(source, ((6,),), settings=settings)


def test_selected_convention_isolates_entries_in_a_mixed_google_and_rest_docstring() -> None:
    source = 'def combine(first, second):\n    """Combine values.\n\n    Args:\n        first: First value.\n        second: Second value.\n\n    :param second: Second reST value.\n    :param first: First reST value.\n    """\n'
    google = CheckSettings(select=("PDF526",), docstring_convention=DocstringConvention.GOOGLE)
    rest = CheckSettings(select=("PDF526",), docstring_convention=DocstringConvention.REST)

    assert_pdf526_lines(source, (), settings=google)
    assert_pdf526_lines(source, ((9,),), settings=rest)


@pytest.mark.parametrize(
    ("convention", "body"),
    [
        (DocstringConvention.GOOGLE, "Args:\n        third Missing colon.\n        first: First value.\n        third: Third value."),
        (DocstringConvention.NUMPY, "Parameters\n    ----------\n    third :\n    first : int\n        First value.\n    third : int\n        Third value."),
        (DocstringConvention.REST, ":param third Missing terminator\n    :param first: First value.\n    :param third: Third value."),
    ],
)
def test_malformed_candidates_do_not_establish_order_before_later_valid_entries(convention: DocstringConvention, body: str) -> None:
    source = f'def combine(first, third):\n    """Combine values.\n\n    {body}\n    """\n'
    settings = CheckSettings(select=("PDF526",), docstring_convention=convention)
    _, context = contexts(source, settings=settings)
    data = PDF.require_data(context)
    definition = next(definition for definition in data.definitions if definition.kind is DefinitionKind.FUNCTION)
    docstring = data.docstring_for(definition)

    assert docstring is not None
    assert tuple(parameter.name for parameter in parameter_documentation.documented_parameters(docstring)) == ("first", "third")
    assert_pdf526_lines(source, (), settings=settings)


def test_literal_block_setting_controls_whether_entry_like_content_establishes_order() -> None:
    source = 'def combine(first, second):\n    """Combine values.\n\n    Args:\n        Example::\n\n            second: Example text.\n\n        first: First value.\n        second: Second value.\n    """\n'
    protected = CheckSettings(select=("PDF526",), docstring_convention=DocstringConvention.GOOGLE)
    unprotected = dataclasses.replace(protected, docstring_parse_literal_blocks=False)

    assert_pdf526_lines(source, (), settings=protected)
    assert_pdf526_lines(source, ((9,),), settings=unprotected)


def test_ignores_non_function_docstrings_absent_docstrings_and_short_sequences() -> None:
    source = '"""Module.\n\nArgs:\n    second: Second.\n    first: First.\n"""\n\nmodule_value = 1\n"""Attached value.\n\nArgs:\n    second: Second.\n    first: First.\n"""\n\n\nclass Container:\n    """Container.\n\n    Args:\n        second: Second.\n        first: First.\n    """\n\n\ndef undocumented(first, second):\n    pass\n\n\ndef one_entry(first, second):\n    """Return a value.\n\n    Args:\n        second: Second.\n    """\n\n\ndef additional_string(first, second):\n    """Return a value."""\n    """Args:\n        second: Second.\n        first: First.\n    """\n'

    assert not format_source(source).unfixed_findings


def test_entry_line_suppression_and_crlf_targeting() -> None:
    suppressed = 'def combine(first, second):\n    """Combine values.\n\n    Args:\n        second: Second.\n        first: First.\n    """  # noqa: PDF526\n'
    crlf = 'def combine(first, second):\r\n    """Combine values.\r\n\r\n    Args:\r\n        second: Second.\r\n        first: First.\r\n    """\r\n'

    assert not format_source(suppressed).unfixed_findings
    assert_pdf526_lines(crlf, ((6,),))


def test_signature_line_suppression_does_not_hide_docstring_entry_diagnostic() -> None:
    source = 'def combine(first, second):  # noqa: PDF526\n    """Combine values.\n\n    Args:\n        second: Second.\n        first: First.\n    """\n'

    assert_pdf526_lines(source, ((6,),))


def test_escaped_newline_docstring_uses_evaluated_entries_and_raw_spelling_remains_plain_text() -> None:
    escaped = 'def combine(first, second, third):\n    """Combine values.\\n\\n    Args:\\n        third: Third.\\n        first: First.\\n        second: Second."""\n'
    raw = 'def combine(first, second, third):\n    r"""Combine values.\\n\\n    Args:\\n        third: Third.\\n        first: First.\\n        second: Second."""\n'

    assert_pdf526_lines(escaped, ((2,), (2,)))
    assert_pdf526_lines(raw, ())


def test_concatenated_docstring_maps_entry_lines_and_accepts_component_suppression() -> None:
    source = 'def combine(first, second):\n    (\n        "Combine values.\\n\\n"\n        "Args:\\n"\n        "    second: Second value.\\n"\n        "    first: First value."\n    )\n'
    suppressed = (
        'def combine(first, second):\n    (\n        "Combine values.\\n\\n"  # noqa: PDF526\n        "Args:\\n"\n        "    second: Second value.\\n"\n        "    first: First value."\n    )\n'
    )

    assert_pdf526_lines(source, ((3, 4, 5, 6),))
    assert not format_source(suppressed).unfixed_findings


def test_nested_function_uses_its_own_signature_order() -> None:
    source = 'def outer(first, second):\n    """Return a nested function."""\n\n    def inner(third, fourth):\n        """Process nested values.\n\n        Args:\n            fourth: Fourth value.\n            third: Third value.\n        """\n'
    result = assert_pdf526_lines(source, ((9,),))

    assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring parameter 'third' should appear before 'fourth' to match the function signature",)


def test_uses_reparsed_entries_after_an_earlier_spacing_fix() -> None:
    source = 'def combine(first, second):\n    """Combine values.\n\n    Args:\n        second : Second.\n        first : First.\n    """\n'
    settings = CheckSettings(select=("PDF409", "PDF526"), docstring_convention=DocstringConvention.GOOGLE)
    result = format_source(source, settings=settings)

    assert result.new_source == 'def combine(first, second):\n    """Combine values.\n\n    Args:\n        second: Second.\n        first: First.\n    """\n'
    assert result.fixed_findings[PDF409DocstringEntrySpacing.meta] == 1
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((6,),)


def test_co_selected_consistency_rules_retain_distinct_diagnostic_ownership() -> None:
    source = 'def combine(first, second, third):\n    """Combine values.\n\n    Args:\n        third: Third value.\n        stale: Obsolete value.\n        first: First value.\n        first: Repeated first value.\n    """\n'
    settings = CheckSettings(select=("PDF412", "PDF500", "PDF501", "PDF526"), docstring_convention=DocstringConvention.GOOGLE)
    result = format_source(source, settings=settings)

    assert {(finding.rule.code.tag, finding.line_numbers) for finding in result.unfixed_findings} == {("PDF412", (8,)), ("PDF500", (1,)), ("PDF501", (6,)), ("PDF526", (7,))}


def test_parameter_order_helper_returns_typed_issue_payloads() -> None:
    source = 'def combine(first, second, third):\n    """Combine values.\n\n    Args:\n        third: Third.\n        stale: Stale.\n        first: First.\n        third: Repeated third.\n        second: Second.\n    """\n'
    _, context = contexts(source)
    data = PDF.require_data(context)
    definition = next(definition for definition in data.definitions if definition.kind is DefinitionKind.FUNCTION)
    docstring = data.docstring_for(definition)

    assert docstring is not None
    issues = parameter_documentation.parameter_order_issues(definition, docstring, context=context)
    assert tuple(dataclasses.astuple(issue) for issue in issues)
    assert tuple((issue.documented_parameter.name, issue.signature_parameter.display_name, issue.preceding_signature_parameter.display_name) for issue in issues) == (
        ("first", "first", "third"),
        ("second", "second", "third"),
    )


def test_direct_rule_hook_returns_valid_diagnostics() -> None:
    source = 'def combine(first, second):\n    """Combine values.\n\n    Args:\n        second: Second.\n        first: First.\n    """\n'
    _, context = contexts(source)
    findings = rule_helpers.rule_findings(PDF526ParameterDocumentationOrder, context)

    assert tuple(finding.line_numbers for finding in findings) == ((6,),)
