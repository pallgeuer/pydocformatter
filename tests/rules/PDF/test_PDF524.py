# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# First-party imports
import tests.rules.PDF.helpers as pdf_helpers
from pydocformatter.rules.definitions.PDF.PDF524_private_module_attribute_docstring_must_be_owner import PDF524PrivateModuleAttributeDocstringMustBeOwner


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter import formatter
    from pydocformatter.cli.settings_check import CheckSettings


format_source = pdf_helpers.formatter_for("PDF524")


def assert_pdf524_lines(source: str, expected: tuple[tuple[int, ...], ...], *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Assert PDF524 line findings for source."""
    return pdf_helpers.assert_unfixed_lines(format_source, source, expected, meta=PDF524PrivateModuleAttributeDocstringMustBeOwner.meta, settings=settings)


def test_reports_attached_private_module_attribute_docstrings() -> None:
    source = '_token: str\n"""Internal token."""\n\ntimeout: float\n"""Request timeout."""\n'
    result = assert_pdf524_lines(source, ((2,),))

    assert tuple(finding.message for finding in result.unfixed_findings) == ("Private module attribute '_token' must use module docstring documentation, not attached docstring",)


def test_reports_each_private_tuple_unpacked_module_target() -> None:
    source = '_primary, (fallback, *_aliases) = endpoints\n"""Endpoint values."""\n'

    assert_pdf524_lines(source, ((2,), (2,)))


def test_repeated_private_module_assignment_target_reports_once_for_shared_docstring() -> None:
    source = '_token, _token = values\n"""Internal token."""\n'

    assert_pdf524_lines(source, ((2,),))


def test_reports_same_line_and_concatenated_private_module_attribute_docstrings() -> None:
    source = '_token = ""; """Internal token."""\n_cache: dict[str, object]\n"""Internal """ "cache."\n\ntimeout = 30.0\n"""Request timeout."""\n'

    assert_pdf524_lines(source, ((1,), (3,)))


def test_ignores_unsupported_private_module_attached_docstring_targets() -> None:
    source = 'items[0] = ""\n"""Subscript target."""\n\n[_name] = values\n"""List destructuring target."""\n'

    assert_pdf524_lines(source, ())
