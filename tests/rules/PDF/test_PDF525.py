# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# First-party imports
import tests.rules.PDF.helpers as pdf_helpers
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definitions.PDF.PDF525_private_module_attribute_docstring_must_be_attached import PDF525PrivateModuleAttributeDocstringMustBeAttached


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter import formatter


format_source = pdf_helpers.formatter_for("PDF525")


def assert_pdf525_lines(source: str, expected: tuple[tuple[int, ...], ...], *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Assert PDF525 line findings for source."""
    return pdf_helpers.assert_unfixed_lines(format_source, source, expected, meta=PDF525PrivateModuleAttributeDocstringMustBeAttached.meta, settings=settings)


def test_reports_google_private_module_attribute_owner_documentation() -> None:
    source = '"""Module constants.\n\nAttributes:\n    _token: Internal token.\n    timeout: Request timeout.\n    _stale: Stale docs.\n"""\n\n_token: str\ntimeout: float\n'
    result = assert_pdf525_lines(source, ((4,),))

    assert tuple(finding.message for finding in result.unfixed_findings) == ("Private module attribute '_token' must use attached docstring, not module docstring documentation",)


def test_reports_numpy_private_module_attribute_owner_documentation() -> None:
    source = '"""Module constants.\n\nAttributes\n----------\n_token, timeout : object\n    State.\n"""\n\n_token: str\ntimeout: float\n'

    assert_pdf525_lines(source, ((5,),), settings=CheckSettings(select=("PDF525",), docstring_convention=DocstringConvention.NUMPY))


def test_reports_repeated_private_module_owner_entries_and_ignores_stale_entries() -> None:
    source = '"""Module constants.\n\nAttributes:\n    _token: Internal token.\n    _missing: Stale docs.\n    _token: Repeated token docs.\n"""\n\n_token: str\n'

    assert_pdf525_lines(source, ((4,), (6,)))


def test_none_and_pep257_conventions_do_not_parse_private_module_attribute_entries() -> None:
    source = '"""Module constants.\n\nAttributes:\n    _token: Internal token.\n"""\n\n_token: str\n'

    for convention in (DocstringConvention.NONE, DocstringConvention.PEP257):
        assert_pdf525_lines(source, (), settings=CheckSettings(select=("PDF525",), docstring_convention=convention))
