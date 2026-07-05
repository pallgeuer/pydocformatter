import pydocformatter.formatter as formatter
import tests.rules.PDF.helpers as pdf_helpers
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definitions.PDF.PDF521_public_module_attribute_docstring_must_be_attached import PDF521PublicModuleAttributeDocstringMustBeAttached

format_source = pdf_helpers.formatter_for("PDF521")


def assert_pdf521_lines(source: str, expected: tuple[tuple[int, ...], ...], *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Assert PDF521 line findings for source."""
    return pdf_helpers.assert_unfixed_lines(format_source, source, expected, meta=PDF521PublicModuleAttributeDocstringMustBeAttached.meta, settings=settings)


def test_reports_google_public_module_attribute_owner_documentation() -> None:
    source = '"""Module constants.\n\nAttributes:\n    timeout: Request timeout.\n    _token: Internal token.\n    stale: Stale docs.\n"""\n\ntimeout: float\n_token: str\n'
    result = assert_pdf521_lines(source, ((4,),))

    assert tuple(finding.message for finding in result.unfixed_findings) == ("Public module attribute 'timeout' must use attached docstring, not module docstring documentation",)


def test_reports_rest_public_module_attribute_owner_documentation() -> None:
    source = '"""Module constants.\n\n:var timeout: Request timeout.\n:vartype retries: int\n"""\n\ntimeout: float\nretries: int\n'

    assert_pdf521_lines(source, ((3,), (4,)), settings=CheckSettings(select=("PDF521",), docstring_convention=DocstringConvention.REST))


def test_reports_repeated_public_module_owner_entries_and_ignores_stale_entries() -> None:
    source = '"""Module constants.\n\nAttributes:\n    timeout: Request timeout.\n    missing: Stale docs.\n    timeout: Repeated timeout docs.\n"""\n\ntimeout: float\n'

    assert_pdf521_lines(source, ((4,), (6,)))


def test_none_and_pep257_conventions_do_not_parse_public_module_attribute_entries() -> None:
    source = '"""Module constants.\n\nAttributes:\n    timeout: Request timeout.\n"""\n\ntimeout: float\n'

    for convention in (DocstringConvention.NONE, DocstringConvention.PEP257):
        assert_pdf521_lines(source, (), settings=CheckSettings(select=("PDF521",), docstring_convention=convention))
