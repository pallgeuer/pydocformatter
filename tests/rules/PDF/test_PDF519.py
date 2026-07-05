import pydocformatter.formatter as formatter
import tests.rules.PDF.helpers as pdf_helpers
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definitions.PDF.PDF519_public_class_attribute_docstring_must_be_attached import PDF519PublicClassAttributeDocstringMustBeAttached

format_source = pdf_helpers.formatter_for("PDF519")


def assert_pdf519_lines(source: str, expected: tuple[tuple[int, ...], ...], *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Assert PDF519 line findings for source."""
    return pdf_helpers.assert_unfixed_lines(format_source, source, expected, meta=PDF519PublicClassAttributeDocstringMustBeAttached.meta, settings=settings)


def test_reports_google_public_class_attribute_owner_documentation() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    Attributes:\n        timeout: Request timeout.\n        _token: Internal token.\n        stale: Stale docs.\n    """\n\n    timeout: float\n    _token: str\n'
    result = assert_pdf519_lines(source, ((5,),))

    assert tuple(finding.message for finding in result.unfixed_findings) == ("Public class attribute 'timeout' must use attached docstring, not class docstring documentation",)


def test_reports_numpy_public_class_attribute_owner_documentation_by_name() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    Attributes\n    ----------\n    primary, fallback : str\n        Endpoint values.\n    """\n\n    primary = fallback = ""\n'

    assert_pdf519_lines(source, ((6,), (6,)), settings=CheckSettings(select=("PDF519",), docstring_convention=DocstringConvention.NUMPY))


def test_reports_public_init_attribute_owner_documentation() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    Attributes:\n        timeout: Request timeout.\n    """\n\n    def __init__(self):\n        self.timeout = 30.0\n'

    assert_pdf519_lines(source, ((5,),))


def test_reports_repeated_public_class_owner_entries_and_ignores_stale_entries() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    Attributes:\n        timeout: Request timeout.\n        missing: Stale docs.\n        timeout: Repeated timeout docs.\n    """\n\n    timeout: float\n'

    assert_pdf519_lines(source, ((5,), (7,)))


def test_reports_rest_public_class_attribute_owner_documentation() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    :ivar timeout: Request timeout.\n    :vartype retries: int\n    """\n\n    timeout: float\n    retries: int\n'

    assert_pdf519_lines(source, ((4,), (5,)), settings=CheckSettings(select=("PDF519",), docstring_convention=DocstringConvention.REST))


def test_none_and_pep257_conventions_do_not_parse_public_class_attribute_entries() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    Attributes:\n        timeout: Request timeout.\n    """\n\n    timeout: float\n'

    for convention in (DocstringConvention.NONE, DocstringConvention.PEP257):
        assert_pdf519_lines(source, (), settings=CheckSettings(select=("PDF519",), docstring_convention=convention))
