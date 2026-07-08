# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# First-party imports
import tests.rules.PDF.helpers as pdf_helpers
from pydocformatter import rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definitions.PDF.PDF518_public_class_attribute_docstring_must_be_owner import PDF518PublicClassAttributeDocstringMustBeOwner


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter import formatter


format_source = pdf_helpers.formatter_for("PDF518")


def assert_pdf518_lines(source: str, expected: tuple[tuple[int, ...], ...], *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Assert PDF518 line findings for source."""
    return pdf_helpers.assert_unfixed_lines(format_source, source, expected, meta=PDF518PublicClassAttributeDocstringMustBeOwner.meta, settings=settings)


def test_reports_attached_public_class_attribute_docstrings() -> None:
    source = 'class Client:\n    timeout: float\n    """Request timeout."""\n\n    _token: str\n    """Internal token."""\n'
    result = assert_pdf518_lines(source, ((3,),))

    assert tuple(finding.message for finding in result.unfixed_findings) == ("Public class attribute 'timeout' must use class docstring documentation, not attached docstring",)


def test_reports_public_init_attribute_docstrings() -> None:
    source = 'class Client:\n    def __init__(self):\n        self.timeout = 30.0\n        """Request timeout."""\n\n    def configure(self):\n        self.retries = 3\n        """Ignored non-init attribute."""\n'

    assert_pdf518_lines(source, ((4,),))


def test_reports_each_public_tuple_unpacked_class_target() -> None:
    source = 'class Client:\n    primary, (_fallback, *aliases) = endpoints\n    """Endpoint values."""\n'

    assert_pdf518_lines(source, ((3,), (3,)))


def test_repeated_public_class_assignment_target_reports_once_for_shared_docstring() -> None:
    source = 'class Client:\n    timeout, timeout = values\n    """Request timeout."""\n'

    assert_pdf518_lines(source, ((3,),))


def test_public_attribute_in_private_class_still_uses_public_class_policy() -> None:
    source = 'class _Client:\n    timeout: float\n    """Request timeout."""\n'

    assert_pdf518_lines(source, ((3,),))


def test_reports_same_line_and_concatenated_public_class_attribute_docstrings() -> None:
    source = 'class Client:\n    timeout = 30.0; """Request timeout."""\n    retries: int\n    """Retry """ "count."\n\n    items[0] = 1\n    """Ignored subscript target."""\n'

    assert_pdf518_lines(source, ((2,), (4,)))


def test_suppression_on_attached_docstring_suppresses_public_class_owner_preference() -> None:
    source = 'class Client:\n    timeout: float\n    """Request timeout."""  # pydocfmt: ignore[PDF518]\n\n    retries: int\n    """Retry count."""\n'

    assert_pdf518_lines(source, ((6,),))


def test_broad_selection_keeps_pdf518_over_incompatible_pdf519_when_require_explicit_is_empty() -> None:
    selection = rules_selection.select_rules(CheckSettings(select=("PDF5",), require_explicit=(), docstring_convention=DocstringConvention.GOOGLE))

    assert "PDF518" in tuple(rule.rule.code.tag for rule in selection.rules)
    assert "PDF519" not in tuple(rule.rule.code.tag for rule in selection.rules)
    assert "Selected rule PDF519 is incompatible with earlier selected rule PDF518; PDF519 has been disabled" in selection.errors
