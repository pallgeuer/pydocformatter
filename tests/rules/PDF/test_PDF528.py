"""Tests for PDF528 attribute-documentation-order."""

# Future imports
from __future__ import annotations

# Standard library imports
import itertools
from typing import TYPE_CHECKING

# Third-party imports
import pytest

# First-party imports
import tests.rules.PDF.helpers as pdf_helpers
from pydocformatter import rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention, DocstringMissingDocumentation
from pydocformatter.rules.definition_helpers import attribute_documentation
from pydocformatter.rules.definitions.PDF.PDF import PDF, DefinitionKind
from pydocformatter.rules.definitions.PDF.PDF528_attribute_documentation_order import PDF528AttributeDocumentationOrder
from pydocformatter.rules.models import FixAvailability
from tests import rule_helpers


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter import formatter


contexts = pdf_helpers.contexts_for("PDF528")
format_source = pdf_helpers.formatter_for("PDF528")


def assert_pdf528_lines(source: str, expected: tuple[tuple[int, ...], ...], *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Assert PDF528 line findings for source."""
    return pdf_helpers.assert_unfixed_lines(format_source, source, expected, meta=PDF528AttributeDocumentationOrder.meta, settings=settings)


def test_metadata() -> None:
    assert PDF528AttributeDocumentationOrder.meta.name == "attribute-documentation-order"
    assert PDF528AttributeDocumentationOrder.meta.message == "Docstring attributes are not in declaration order"
    assert PDF528AttributeDocumentationOrder.meta.fix_availability is FixAvailability.NEVER
    assert PDF528AttributeDocumentationOrder.meta.stable_since == "1.1.0"


def test_reports_swapped_module_attributes_with_source_names() -> None:
    source = '"""Module values.\n\nAttributes:\n    high: Upper limit.\n    low: Lower limit.\n"""\n\nlow = 0\nhigh = 100\n'
    result = assert_pdf528_lines(source, ((5,),))

    assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring attribute 'low' should appear before 'high' to match the source declaration order",)
    assert not result.unfixed_findings[0].fixable


def test_every_permutation_of_documented_subsets_reports_each_late_occurrence() -> None:
    declaration_names = ("first", "second", "third", "fourth")
    rank_by_name = {name: rank for rank, name in enumerate(declaration_names)}
    declarations = "".join(f"{name} = {rank}\n" for rank, name in enumerate(declaration_names))
    for size in range(2, len(declaration_names) + 1):
        for subset in itertools.combinations(declaration_names, size):
            for documented_names in itertools.permutations(subset):
                entries = "".join(f"    {name}: {name.title()} value.\n" for name in documented_names)
                source = f'"""Module values.\n\nAttributes:\n{entries}"""\n\n{declarations}'
                result = format_source(source)
                expected_names = tuple(name for index, name in enumerate(documented_names) if any(rank_by_name[earlier] > rank_by_name[name] for earlier in documented_names[:index]))

                assert tuple(finding.message.split("'")[1] for finding in result.unfixed_findings) == expected_names, documented_names


def test_class_inventory_uses_unified_source_order_across_direct_slots_initializer_and_later_direct_attributes() -> None:
    source = 'class Limits:\n    """Store limits.\n\n    Attributes:\n        later: Later class value.\n        instance: Instance value.\n        slot_second: Second slot.\n        slot_first: First slot.\n        __slots__: Slot declaration.\n        direct: Direct class value.\n    """\n\n    direct = 1\n    __slots__ = ("slot_first", "slot_second")\n\n    def __init__(self):\n        self.instance = 2\n\n    later = 3\n'
    result = assert_pdf528_lines(source, ((6,), (7,), (8,), (9,), (10,)))

    assert tuple(finding.message.split("'")[1] for finding in result.unfixed_findings) == ("instance", "slot_second", "slot_first", "__slots__", "direct")
    assert tuple(finding.message.split("'")[3] for finding in result.unfixed_findings) == ("later",) * 5


def test_multi_target_assignments_use_written_left_to_right_depth_first_order() -> None:
    source = '"""Module values.\n\nAttributes:\n    fourth: Fourth.\n    third: Third.\n    second: Second.\n    first: First.\n"""\n\nfirst = second = 1\nthird, (fourth, *rest) = values\n'
    result = assert_pdf528_lines(source, ((5,), (6,), (7,)))

    assert tuple(finding.message.split("'")[1] for finding in result.unfixed_findings) == ("third", "second", "first")
    assert tuple(finding.message.split("'")[3] for finding in result.unfixed_findings) == ("fourth",) * 3


def test_first_source_declaration_sets_rank_and_later_assignments_do_not_move_it() -> None:
    source = 'class Values:\n    """Store values.\n\n    Attributes:\n        second: Second.\n        first: First.\n    """\n\n    first = 1\n    second = 2\n    first = 3\n'

    assert_pdf528_lines(source, ((6,),))


def test_nested_classes_use_independent_inventories() -> None:
    source = 'class Outer:\n    """Outer values.\n\n    Attributes:\n        second: Second.\n        first: First.\n    """\n\n    first = 1\n    second = 2\n\n    class Inner:\n        """Inner values.\n\n        Attributes:\n            first: First.\n            second: Second.\n        """\n\n        first = 1\n        second = 2\n'

    assert_pdf528_lines(source, ((6,),))


def test_private_dunder_and_slot_members_participate_when_documented() -> None:
    source = 'class State:\n    """Store state.\n\n    Attributes:\n        _private: Private state.\n        slot: Slotted state.\n        __slots__: Slots declaration.\n    """\n\n    __slots__ = ("slot",)\n    _private = 1\n'
    result = assert_pdf528_lines(source, ((6,), (7,)))

    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Docstring attribute 'slot' should appear before '_private' to match the source declaration order",
        "Docstring attribute '__slots__' should appear before '_private' to match the source declaration order",
    )


def test_final_effective_slot_members_use_their_binding_position_without_moving_the_slots_attribute() -> None:
    source = 'class State:\n    """Store state.\n\n    Attributes:\n        recovered: Recovered slot.\n        direct: Direct value.\n        stale: Stale slot.\n        __slots__: Slot declaration.\n    """\n\n    __slots__ = ("stale",)\n    direct = 1\n    __slots__ = ("recovered",)\n'
    result = assert_pdf528_lines(source, ((6,), (8,)))

    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Docstring attribute 'direct' should appear before 'recovered' to match the source declaration order",
        "Docstring attribute '__slots__' should appear before 'recovered' to match the source declaration order",
    )


def test_partial_unknown_wrong_case_and_repeated_documentation_do_not_reset_order() -> None:
    source = '"""Module values.\n\nAttributes:\n    third: Third.\n    stale: Stale.\n    First: Wrong case.\n    first: First.\n    third: Repeated third.\n    second: Second.\n"""\n\nfirst = 1\nsecond = 2\nthird = 3\n'
    result = assert_pdf528_lines(source, ((7,), (9,)))

    assert tuple(finding.message.split("'")[1] for finding in result.unfixed_findings) == ("first", "second")
    assert tuple(finding.message.split("'")[3] for finding in result.unfixed_findings) == ("third", "third")


def test_repeated_late_known_attribute_does_not_create_another_order_finding() -> None:
    source = '"""Module values.\n\nAttributes:\n    first: First.\n    third: Third.\n    second: Second.\n    first: Repeated first.\n"""\n\nfirst = 1\nsecond = 2\nthird = 3\n'
    result = assert_pdf528_lines(source, ((6,),))

    assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring attribute 'second' should appear before 'third' to match the source declaration order",)


def test_numpy_multi_name_entries_preserve_written_order() -> None:
    source = '"""Module values.\n\nAttributes\n----------\nthird, first, second : int\n    Values.\n"""\n\nfirst = 1\nsecond = 2\nthird = 3\n'
    settings = CheckSettings(select=("PDF528",), docstring_convention=DocstringConvention.NUMPY)
    result = assert_pdf528_lines(source, ((5,), (5,)), settings=settings)

    assert tuple(finding.message.split("'")[1] for finding in result.unfixed_findings) == ("first", "second")


def test_rest_only_value_fields_establish_order() -> None:
    source = '"""Module values.\n\n:vartype first: int\n:var second: Second.\n:vartype second: int\n:var first: First.\n"""\n\nfirst = 1\nsecond = 2\n'
    settings = CheckSettings(select=("PDF528",), docstring_convention=DocstringConvention.REST)
    result = assert_pdf528_lines(source, ((6,),), settings=settings)

    assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring attribute 'first' should appear before 'second' to match the source declaration order",)


def test_type_only_fields_do_not_establish_order_or_create_findings() -> None:
    source = '"""Module values.\n\n:vartype second: int\n:var first: First.\n"""\n\nfirst = 1\nsecond = 2\n'
    settings = CheckSettings(select=("PDF528",), docstring_convention=DocstringConvention.REST)

    assert_pdf528_lines(source, (), settings=settings)


def test_attached_attribute_docstrings_are_not_checked() -> None:
    source = 'first = 1\n"""First value.\n\nAttributes:\n    second: Second.\n    first: First.\n"""\nsecond = 2\n'

    assert_pdf528_lines(source, ())


def test_function_docstrings_are_not_checked() -> None:
    source = 'def function():\n    """Function.\n\n    Attributes:\n        second: Second.\n        first: First.\n    """\n'

    assert_pdf528_lines(source, ())


@pytest.mark.parametrize("convention", [DocstringConvention.NONE, DocstringConvention.PEP257])
def test_unparsed_conventions_disable_exact_selection(convention: DocstringConvention) -> None:
    source = '"""Module values.\n\nAttributes:\n    second: Second.\n    first: First.\n"""\n\nfirst = 1\nsecond = 2\n'

    assert_pdf528_lines(source, (), settings=CheckSettings(select=("PDF528",), docstring_convention=convention))


@pytest.mark.parametrize("selector", ["PDF5", "PDF", "ALL"])
@pytest.mark.parametrize("convention", [DocstringConvention.GOOGLE, DocstringConvention.NUMPY, DocstringConvention.REST])
def test_broad_selectors_ignore_pdf528_for_parsed_conventions(selector: str, convention: DocstringConvention) -> None:
    selected = rules_selection.select_rules(CheckSettings(select=(selector,), docstring_convention=convention))
    assert "PDF528" not in tuple(rule.rule.code.tag for rule in selected.rules)


@pytest.mark.parametrize("convention", [DocstringConvention.GOOGLE, DocstringConvention.NUMPY, DocstringConvention.REST])
def test_exact_selection_restores_pdf528_for_parsed_conventions(convention: DocstringConvention) -> None:
    selected = rules_selection.select_rules(CheckSettings(select=("PDF",), extend_select=("PDF528",), docstring_convention=convention))
    assert "PDF528" in tuple(rule.rule.code.tag for rule in selected.rules)


@pytest.mark.parametrize("policy", list(DocstringMissingDocumentation))
@pytest.mark.parametrize("public_only", [False, True])
@pytest.mark.parametrize("require_instance", [False, True])
def test_missing_documentation_settings_do_not_change_existing_attribute_order(policy: DocstringMissingDocumentation, public_only: bool, require_instance: bool) -> None:
    source = (
        'class Values:\n    """Store values.\n\n    Attributes:\n        second: Second.\n        first: First.\n    """\n\n    def __init__(self):\n        self.first = 1\n        self.second = 2\n'
    )
    settings = CheckSettings(
        select=("PDF528",),
        docstring_convention=DocstringConvention.GOOGLE,
        docstring_missing_documentation=policy,
        docstring_missing_documentation_public_only=public_only,
        docstring_require_init_attribute_documentation=require_instance,
    )

    assert_pdf528_lines(source, ((6,),), settings=settings)


def test_docstring_suppression_covers_attribute_order_findings() -> None:
    source = '"""Module values.\n\nAttributes:\n    second: Second.\n    first: First.\n"""  # noqa: PDF528\n\nfirst = 1\nsecond = 2\n'

    assert not format_source(source).unfixed_findings


def test_crlf_docstring_targets_attribute_entry_line() -> None:
    source = '"""Module values.\r\n\r\nAttributes:\r\n    second: Second.\r\n    first: First.\r\n"""\r\n\r\nfirst = 1\r\nsecond = 2\r\n'

    assert_pdf528_lines(source, ((5,),))


def test_escaped_newline_docstring_uses_evaluated_attribute_entries() -> None:
    source = '"""Module values.\\n\\nAttributes:\\n    second: Second.\\n    first: First."""\n\nfirst = 1\nsecond = 2\n'

    assert_pdf528_lines(source, ((1,),))


def test_concatenated_docstring_matches_escape_spelled_names_and_targets_the_expression() -> None:
    source = '("Module values.\\n\\n"\n "Attributes:\\n"\n "    second: Second.\\n"\n "    \\x66irst: First.\\n")\n\nfirst = 1\nsecond = 2\n'
    result = assert_pdf528_lines(source, ((1, 2, 3, 4),))

    assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring attribute 'first' should appear before 'second' to match the source declaration order",)


def test_attribute_order_helper_returns_typed_issue_payloads() -> None:
    source = '"""Module values.\n\nAttributes:\n    third: Third.\n    stale: Stale.\n    first: First.\n    third: Repeated third.\n    second: Second.\n"""\n\nfirst = 1\nsecond = 2\nthird = 3\n'
    _, context = contexts(source)
    data = PDF.require_data(context)
    owner = next(definition for definition in data.definitions if definition.kind is DefinitionKind.MODULE)
    docstring = data.docstring_for(owner)

    assert docstring is not None
    issues = attribute_documentation.attribute_order_issues(data, owner, docstring)
    assert all(isinstance(issue, attribute_documentation.AttributeOrderIssue) for issue in issues)
    assert tuple((issue.documented_attribute.name, issue.inventory_attribute.name, issue.preceding_inventory_attribute.name) for issue in issues) == (
        ("first", "first", "third"),
        ("second", "second", "third"),
    )


def test_direct_rule_hook_returns_valid_diagnostics() -> None:
    source = '"""Module values.\n\nAttributes:\n    second: Second.\n    first: First.\n"""\n\nfirst = 1\nsecond = 2\n'
    _, context = contexts(source)
    findings = rule_helpers.rule_findings(PDF528AttributeDocumentationOrder, context)

    assert tuple(finding.line_numbers for finding in findings) == ((5,),)
