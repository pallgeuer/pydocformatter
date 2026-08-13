"""Tests for PDF529 module-attribute-documentation-order."""

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
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definition_helpers import attribute_documentation
from pydocformatter.rules.definitions.PDF.PDF import PDF, DefinitionKind
from pydocformatter.rules.definitions.PDF.PDF529_module_attribute_documentation_order import PDF529ModuleAttributeDocumentationOrder
from pydocformatter.rules.models import MODULE_SOURCE_CONTEXTS, FixAvailability, SourceContext
from tests import rule_helpers


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter import formatter


contexts = pdf_helpers.contexts_for("PDF529")
format_source = pdf_helpers.formatter_for("PDF529")


def assert_pdf529_lines(source: str, expected: tuple[tuple[int, ...], ...], *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Assert PDF529 line findings for source."""
    return pdf_helpers.assert_unfixed_lines(format_source, source, expected, meta=PDF529ModuleAttributeDocumentationOrder.meta, settings=settings)


def test_metadata() -> None:
    assert PDF529ModuleAttributeDocumentationOrder.meta.name == "module-attribute-documentation-order"
    assert PDF529ModuleAttributeDocumentationOrder.meta.message == "Module docstring attributes are not in declaration order"
    assert PDF529ModuleAttributeDocumentationOrder.meta.fix_availability is FixAvailability.NEVER
    assert PDF529ModuleAttributeDocumentationOrder.meta.stable_since == "1.2.0"
    assert PDF529ModuleAttributeDocumentationOrder.meta.source_contexts == MODULE_SOURCE_CONTEXTS


def test_reports_swapped_module_attributes_with_source_names() -> None:
    source = '"""Module values.\n\nAttributes:\n    high: Upper limit.\n    low: Lower limit.\n"""\n\nlow = 0\nhigh = 100\n'
    result = assert_pdf529_lines(source, ((5,),))

    assert tuple(finding.message for finding in result.unfixed_findings) == ("Module docstring attribute 'low' should appear before 'high' to match the source declaration order",)
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


def test_multi_target_assignments_use_written_left_to_right_depth_first_order() -> None:
    source = '"""Module values.\n\nAttributes:\n    fourth: Fourth.\n    third: Third.\n    second: Second.\n    first: First.\n"""\n\nfirst = second = 1\nthird, (fourth, *rest) = values\n'
    result = assert_pdf529_lines(source, ((5,), (6,), (7,)))

    assert tuple(finding.message.split("'")[1] for finding in result.unfixed_findings) == ("third", "second", "first")
    assert tuple(finding.message.split("'")[3] for finding in result.unfixed_findings) == ("fourth",) * 3


def test_first_source_declaration_sets_rank_and_later_assignments_do_not_move_it() -> None:
    source = '"""Module values.\n\nAttributes:\n    second: Second.\n    first: First.\n"""\n\nfirst = 1\nsecond = 2\nfirst = 3\n'

    assert_pdf529_lines(source, ((5,),))


def test_partial_unknown_wrong_case_and_repeated_documentation_do_not_reset_order() -> None:
    source = '"""Module values.\n\nAttributes:\n    third: Third.\n    stale: Stale.\n    First: Wrong case.\n    first: First.\n    third: Repeated third.\n    second: Second.\n"""\n\nfirst = 1\nsecond = 2\nthird = 3\n'
    result = assert_pdf529_lines(source, ((7,), (9,)))

    assert tuple(finding.message.split("'")[1] for finding in result.unfixed_findings) == ("first", "second")
    assert tuple(finding.message.split("'")[3] for finding in result.unfixed_findings) == ("third", "third")


@pytest.mark.parametrize(
    ("convention", "source", "expected"),
    [
        (DocstringConvention.NUMPY, '"""Module values.\n\nAttributes\n----------\nthird, first, second : int\n    Values.\n"""\n\nfirst = 1\nsecond = 2\nthird = 3\n', ((5,), (5,))),
        (DocstringConvention.REST, '"""Module values.\n\n:vartype first: int\n:var second: Second.\n:vartype second: int\n:var first: First.\n"""\n\nfirst = 1\nsecond = 2\n', ((6,),)),
    ],
)
def test_supported_conventions_preserve_documented_order(convention: DocstringConvention, source: str, expected: tuple[tuple[int, ...], ...]) -> None:
    assert_pdf529_lines(source, expected, settings=CheckSettings(select=("PDF529",), docstring_convention=convention))


def test_rest_type_only_fields_do_not_establish_order_or_create_findings() -> None:
    source = '"""Module values.\n\n:vartype second: int\n:var first: First.\n"""\n\nfirst = 1\nsecond = 2\n'
    settings = CheckSettings(select=("PDF529",), docstring_convention=DocstringConvention.REST)

    assert_pdf529_lines(source, (), settings=settings)


def test_attached_attribute_docstrings_are_not_checked() -> None:
    source = 'first = 1\n"""First value.\n\nAttributes:\n    second: Second.\n    first: First.\n"""\nsecond = 2\n'

    assert_pdf529_lines(source, ())


def test_class_and_function_docstrings_are_not_checked() -> None:
    source = 'class Values:\n    """Store values.\n\n    Attributes:\n        second: Second.\n        first: First.\n    """\n\n    first = 1\n    second = 2\n'

    assert_pdf529_lines(source, ())


@pytest.mark.parametrize("convention", [DocstringConvention.NONE, DocstringConvention.PEP257])
def test_unparsed_conventions_disable_exact_selection(convention: DocstringConvention) -> None:
    source = '"""Module values.\n\nAttributes:\n    second: Second.\n    first: First.\n"""\n\nfirst = 1\nsecond = 2\n'

    assert_pdf529_lines(source, (), settings=CheckSettings(select=("PDF529",), docstring_convention=convention))


@pytest.mark.parametrize("selector", ["PDF5", "PDF", "ALL"])
@pytest.mark.parametrize("convention", [DocstringConvention.GOOGLE, DocstringConvention.NUMPY, DocstringConvention.REST])
def test_broad_selectors_ignore_pdf529_for_parsed_conventions(selector: str, convention: DocstringConvention) -> None:
    selected = rules_selection.select_rules(CheckSettings(select=(selector,), docstring_convention=convention))

    assert "PDF529" not in tuple(rule.rule.code.tag for rule in selected.rules)


@pytest.mark.parametrize("convention", [DocstringConvention.GOOGLE, DocstringConvention.NUMPY, DocstringConvention.REST])
def test_exact_selection_restores_pdf529_for_parsed_conventions(convention: DocstringConvention) -> None:
    selected = rules_selection.select_rules(CheckSettings(select=("PDF",), extend_select=("PDF529",), docstring_convention=convention))

    assert "PDF529" in tuple(rule.rule.code.tag for rule in selected.rules)


def test_fragment_context_disables_exact_selection() -> None:
    selected = rules_selection.select_rules(CheckSettings(select=("PDF529",), source_context=SourceContext.FRAGMENT))

    assert not selected.rules


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


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ('"""Module values.\r\n\r\nAttributes:\r\n    second: Second.\r\n    first: First.\r\n"""\r\n\r\nfirst = 1\r\nsecond = 2\r\n', ((5,),)),
        ('"""Module values.\\n\\nAttributes:\\n    second: Second.\\n    first: First."""\n\nfirst = 1\nsecond = 2\n', ((1,),)),
        ('("Module values.\\n\\n"\n "Attributes:\\n"\n "    second: Second.\\n"\n "    \\x66irst: First.\\n")\n\nfirst = 1\nsecond = 2\n', ((1, 2, 3, 4),)),
    ],
)
def test_docstring_source_forms_target_the_physical_attribute_entry(source: str, expected: tuple[tuple[int, ...], ...]) -> None:
    assert_pdf529_lines(source, expected)


def test_direct_rule_hook_returns_valid_diagnostics() -> None:
    source = '"""Module values.\n\nAttributes:\n    second: Second.\n    first: First.\n"""\n\nfirst = 1\nsecond = 2\n'
    _, context = contexts(source)
    findings = rule_helpers.rule_findings(PDF529ModuleAttributeDocumentationOrder, context)

    assert tuple(finding.line_numbers for finding in findings) == ((5,),)
