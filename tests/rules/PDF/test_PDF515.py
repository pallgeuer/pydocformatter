import pydocformatter.formatter as formatter
import tests.rules.PDF.helpers as pdf_helpers
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definitions.PDF.PDF515_private_module_attribute_owner_documentation import PDF515PrivateModuleAttributeOwnerDocumentation

format_source = pdf_helpers.formatter_for("PDF515")


def assert_pdf515_lines(source: str, expected: tuple[tuple[int, ...], ...], *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Assert PDF515 line findings for source."""
    return pdf_helpers.assert_unfixed_lines(format_source, source, expected, meta=PDF515PrivateModuleAttributeOwnerDocumentation.meta, settings=settings)


def test_reports_google_private_module_attribute_owner_documentation() -> None:
    source = '"""Client defaults.\n\nAttributes:\n    _token (str): Internal token.\n    timeout (float): Request timeout.\n"""\n\n_token: str\ntimeout: float\n'
    result = assert_pdf515_lines(source, ((4,),))

    assert tuple(finding.message for finding in result.unfixed_findings) == ("Module docstring documents private attribute '_token'",)


def test_reports_numpy_private_module_attribute_names_individually() -> None:
    source = '"""Client defaults.\n\nAttributes\n----------\n_token, timeout, _cache : object\n    Client state.\n"""\n'

    result = assert_pdf515_lines(source, ((5,), (5,)), settings=CheckSettings(select=("PDF515",), docstring_convention=DocstringConvention.NUMPY))

    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Module docstring documents private attribute '_token'",
        "Module docstring documents private attribute '_cache'",
    )


def test_reports_rest_private_module_attribute_entries() -> None:
    source = '"""Client defaults.\n\n:ivar _token: Internal token.\n:vartype _cache: dict[str, object]\n:ivar timeout: Request timeout.\n"""\n'

    assert_pdf515_lines(source, ((3,), (4,)), settings=CheckSettings(select=("PDF515",), docstring_convention=DocstringConvention.REST))


def test_reports_repeated_and_dunder_private_module_attribute_entries() -> None:
    source = '"""Client defaults.\n\nAttributes:\n    _token: Internal token.\n    __all__: Export names.\n    _token: Repeated token docs.\n"""\n'
    result = assert_pdf515_lines(source, ((4,), (5,), (6,)))

    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Module docstring documents private attribute '_token'",
        "Module docstring documents private attribute '__all__'",
        "Module docstring documents private attribute '_token'",
    )


def test_none_and_pep257_conventions_do_not_parse_module_attribute_entries() -> None:
    source = '"""Client defaults.\n\nAttributes:\n    _token (str): Internal token.\n"""\n'

    for convention in (DocstringConvention.NONE, DocstringConvention.PEP257):
        assert_pdf515_lines(source, (), settings=CheckSettings(select=("PDF515",), docstring_convention=convention))


def test_broad_pdf5_selection_includes_module_private_owner_rule_under_parsed_conventions() -> None:
    source = '"""Client defaults.\n\nAttributes:\n    _token (str): Internal token.\n"""\n\n_token: str\n'

    active = format_source(source, settings=CheckSettings(select=("PDF5",), docstring_convention=DocstringConvention.GOOGLE))
    inert = format_source(source, settings=CheckSettings(select=("PDF5",), docstring_convention=DocstringConvention.PEP257))

    assert tuple(finding.rule for finding in active.unfixed_findings) == (PDF515PrivateModuleAttributeOwnerDocumentation.meta,)
    assert not inert.unfixed_findings


def test_class_attribute_entries_are_ignored() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    Attributes:\n        _token: Internal token.\n    """\n'

    assert_pdf515_lines(source, ())


def test_additional_module_string_literals_are_not_owner_docstrings() -> None:
    source = '"""Client defaults."""\n\n"""Attributes:\n_token: Internal token.\n"""\n'

    assert_pdf515_lines(source, ())


def test_local_docstring_suppression_suppresses_module_attribute_entries() -> None:
    source = '# pydocfmt: ignore[PDF515]\n"""Client defaults.\n\nAttributes:\n    _token: Internal token.\n    _cache: Internal cache.\n"""\n'

    assert_pdf515_lines(source, ())
