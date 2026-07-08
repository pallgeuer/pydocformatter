# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# First-party imports
import tests.rules.PDF.helpers as pdf_helpers
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definitions.PDF.PDF523_private_class_attribute_docstring_must_be_attached import PDF523PrivateClassAttributeDocstringMustBeAttached


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter import formatter


format_source = pdf_helpers.formatter_for("PDF523")


def assert_pdf523_lines(source: str, expected: tuple[tuple[int, ...], ...], *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Assert PDF523 line findings for source."""
    return pdf_helpers.assert_unfixed_lines(format_source, source, expected, meta=PDF523PrivateClassAttributeDocstringMustBeAttached.meta, settings=settings)


def test_reports_google_private_class_attribute_owner_documentation() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    Attributes:\n        _token: Internal token.\n        timeout: Request timeout.\n        _stale: Stale docs.\n    """\n\n    _token: str\n    timeout: float\n'
    result = assert_pdf523_lines(source, ((5,),))

    assert tuple(finding.message for finding in result.unfixed_findings) == ("Private class attribute '_token' must use attached docstring, not class docstring documentation",)


def test_reports_private_init_attribute_owner_documentation() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    Attributes:\n        _token: Internal token.\n    """\n\n    def __init__(self):\n        self._token = ""\n'

    assert_pdf523_lines(source, ((5,),))


def test_reports_repeated_private_class_owner_entries_and_ignores_stale_entries() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    Attributes:\n        _token: Internal token.\n        _missing: Stale docs.\n        _token: Repeated token docs.\n    """\n\n    _token: str\n'

    assert_pdf523_lines(source, ((5,), (7,)))


def test_reports_numpy_mixed_private_class_owner_entries_by_name() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    Attributes\n    ----------\n    _token, timeout, _cache : object\n        Client state.\n    """\n\n    _token: str\n    timeout: float\n    _cache: dict[str, object]\n'

    assert_pdf523_lines(source, ((6,), (6,)), settings=CheckSettings(select=("PDF523",), docstring_convention=DocstringConvention.NUMPY))


def test_none_and_pep257_conventions_do_not_parse_private_class_attribute_entries() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    Attributes:\n        _token: Internal token.\n    """\n\n    _token: str\n'

    for convention in (DocstringConvention.NONE, DocstringConvention.PEP257):
        assert_pdf523_lines(source, (), settings=CheckSettings(select=("PDF523",), docstring_convention=convention))
