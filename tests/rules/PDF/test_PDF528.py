"""Tests for PDF528 class-attribute-documentation-order."""

# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# Third-party imports
import pytest

# First-party imports
import tests.rules.PDF.helpers as pdf_helpers
from pydocformatter import rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention, DocstringMissingDocumentation
from pydocformatter.rules.definitions.PDF.PDF528_class_attribute_documentation_order import PDF528ClassAttributeDocumentationOrder
from pydocformatter.rules.models import FixAvailability, SourceContext
from tests import rule_helpers


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter import formatter


contexts = pdf_helpers.contexts_for("PDF528")
format_source = pdf_helpers.formatter_for("PDF528")


def assert_pdf528_lines(source: str, expected: tuple[tuple[int, ...], ...], *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Assert PDF528 line findings for source."""
    return pdf_helpers.assert_unfixed_lines(format_source, source, expected, meta=PDF528ClassAttributeDocumentationOrder.meta, settings=settings)


def test_metadata() -> None:
    assert PDF528ClassAttributeDocumentationOrder.meta.name == "class-attribute-documentation-order"
    assert PDF528ClassAttributeDocumentationOrder.meta.message == "Class docstring attributes are not in declaration order"
    assert PDF528ClassAttributeDocumentationOrder.meta.fix_availability is FixAvailability.NEVER
    assert PDF528ClassAttributeDocumentationOrder.meta.stable_since == "1.2.0"


def test_class_inventory_uses_unified_source_order_across_direct_slots_initializer_and_later_direct_attributes() -> None:
    source = 'class Limits:\n    """Store limits.\n\n    Attributes:\n        later: Later class value.\n        instance: Instance value.\n        slot_second: Second slot.\n        slot_first: First slot.\n        __slots__: Slot declaration.\n        direct: Direct class value.\n    """\n\n    direct = 1\n    __slots__ = ("slot_first", "slot_second")\n\n    def __init__(self):\n        self.instance = 2\n\n    later = 3\n'
    result = assert_pdf528_lines(source, ((6,), (7,), (8,), (9,), (10,)))

    assert tuple(finding.message.split("'")[1] for finding in result.unfixed_findings) == ("instance", "slot_second", "slot_first", "__slots__", "direct")
    assert tuple(finding.message.split("'")[3] for finding in result.unfixed_findings) == ("later",) * 5
    assert all(finding.message.startswith("Class docstring attribute") for finding in result.unfixed_findings)


def test_nested_classes_use_independent_inventories() -> None:
    source = 'class Outer:\n    """Outer values.\n\n    Attributes:\n        second: Second.\n        first: First.\n    """\n\n    first = 1\n    second = 2\n\n    class Inner:\n        """Inner values.\n\n        Attributes:\n            first: First.\n            second: Second.\n        """\n\n        first = 1\n        second = 2\n'

    assert_pdf528_lines(source, ((6,),))


def test_first_source_declaration_sets_rank_and_later_assignments_do_not_move_it() -> None:
    source = 'class Values:\n    """Store values.\n\n    Attributes:\n        second: Second.\n        first: First.\n    """\n\n    first = 1\n    second = 2\n    first = 3\n'

    assert_pdf528_lines(source, ((6,),))


def test_final_effective_slot_members_use_their_binding_position_without_moving_the_slots_attribute() -> None:
    source = 'class State:\n    """Store state.\n\n    Attributes:\n        recovered: Recovered slot.\n        direct: Direct value.\n        stale: Stale slot.\n        __slots__: Slot declaration.\n    """\n\n    __slots__ = ("stale",)\n    direct = 1\n    __slots__ = ("recovered",)\n'
    result = assert_pdf528_lines(source, ((6,), (8,)))

    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Class docstring attribute 'direct' should appear before 'recovered' to match the source declaration order",
        "Class docstring attribute '__slots__' should appear before 'recovered' to match the source declaration order",
    )


def test_partial_unknown_wrong_case_and_repeated_documentation_do_not_reset_order() -> None:
    source = 'class Values:\n    """Store values.\n\n    Attributes:\n        third: Third.\n        stale: Stale.\n        First: Wrong case.\n        first: First.\n        third: Repeated third.\n        second: Second.\n    """\n\n    first = 1\n    second = 2\n    third = 3\n'
    result = assert_pdf528_lines(source, ((8,), (10,)))

    assert tuple(finding.message.split("'")[1] for finding in result.unfixed_findings) == ("first", "second")
    assert tuple(finding.message.split("'")[3] for finding in result.unfixed_findings) == ("third", "third")


def test_class_without_owner_docstring_ignores_attached_attribute_docstrings() -> None:
    source = 'class Values:\n    first = 1\n    """First value.\n\n    Attributes:\n        second: Second.\n        first: First.\n    """\n    second = 2\n'

    assert_pdf528_lines(source, ())


def test_module_and_function_docstrings_are_not_checked() -> None:
    source = '"""Module values.\n\nAttributes:\n    second: Second.\n    first: First.\n"""\n\nfirst = 1\nsecond = 2\n\ndef function():\n    """Function.\n\n    Attributes:\n        second: Second.\n        first: First.\n    """\n'

    assert_pdf528_lines(source, ())


@pytest.mark.parametrize("convention", [DocstringConvention.NONE, DocstringConvention.PEP257])
def test_unparsed_conventions_disable_exact_selection(convention: DocstringConvention) -> None:
    source = 'class Values:\n    """Store values.\n\n    Attributes:\n        second: Second.\n        first: First.\n    """\n\n    first = 1\n    second = 2\n'

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


@pytest.mark.parametrize(
    ("convention", "source", "expected"),
    [
        (
            DocstringConvention.NUMPY,
            'class Values:\n    """Store values.\n\n    Attributes\n    ----------\n    third, first, second : int\n        Values.\n    """\n\n    first = 1\n    second = 2\n    third = 3\n',
            ((6,), (6,)),
        ),
        (
            DocstringConvention.REST,
            'class Values:\n    """Store values.\n\n    :vartype first: int\n    :var second: Second.\n    :vartype second: int\n    :var first: First.\n    """\n\n    first = 1\n    second = 2\n',
            ((7,),),
        ),
    ],
)
def test_supported_conventions_preserve_documented_order(convention: DocstringConvention, source: str, expected: tuple[tuple[int, ...], ...]) -> None:
    assert_pdf528_lines(source, expected, settings=CheckSettings(select=("PDF528",), docstring_convention=convention))


def test_fragment_context_retains_class_order_check() -> None:
    source = 'class Values:\n    """Store values.\n\n    Attributes:\n        second: Second.\n        first: First.\n    """\n\n    first = 1\n    second = 2\n'
    settings = CheckSettings(select=("PDF528",), docstring_convention=DocstringConvention.GOOGLE, source_context=SourceContext.FRAGMENT)

    assert_pdf528_lines(source, ((6,),), settings=settings)


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
    source = 'class Values:\n    """Store values.\n\n    Attributes:\n        second: Second.\n        first: First.\n    """  # noqa: PDF528\n\n    first = 1\n    second = 2\n'

    assert not format_source(source).unfixed_findings


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ('class Values:\r\n    """Store values.\r\n\r\n    Attributes:\r\n        second: Second.\r\n        first: First.\r\n    """\r\n\r\n    first = 1\r\n    second = 2\r\n', ((6,),)),
        ('class Values:\n    """Store values.\\n\\n    Attributes:\\n        second: Second.\\n        first: First."""\n\n    first = 1\n    second = 2\n', ((2,),)),
        ('class Values:\n    ("Store values.\\n\\n"\n     "Attributes:\\n"\n     "    second: Second.\\n"\n     "    \\x66irst: First.\\n")\n\n    first = 1\n    second = 2\n', ((2, 3, 4, 5),)),
    ],
)
def test_docstring_source_forms_target_the_physical_attribute_entry(source: str, expected: tuple[tuple[int, ...], ...]) -> None:
    assert_pdf528_lines(source, expected)


def test_direct_rule_hook_returns_valid_diagnostics() -> None:
    source = 'class Values:\n    """Store values.\n\n    Attributes:\n        second: Second.\n        first: First.\n    """\n\n    first = 1\n    second = 2\n'
    _, context = contexts(source)
    findings = rule_helpers.rule_findings(PDF528ClassAttributeDocumentationOrder, context)

    assert tuple(finding.line_numbers for finding in findings) == ((6,),)
