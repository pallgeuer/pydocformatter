# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# First-party imports
import tests.rules.PDF.helpers as pdf_helpers
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definitions.PDF.PDF514_private_class_attribute_owner_docstring_forbidden import PDF514PrivateClassAttributeOwnerDocstringForbidden


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter import formatter


format_source = pdf_helpers.formatter_for("PDF514")


def assert_pdf514_lines(source: str, expected: tuple[tuple[int, ...], ...], *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Assert PDF514 line findings for source."""
    return pdf_helpers.assert_unfixed_lines(format_source, source, expected, meta=PDF514PrivateClassAttributeOwnerDocstringForbidden.meta, settings=settings)


def test_reports_google_private_class_attribute_owner_documentation() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    Attributes:\n        _token (str): Internal token.\n        timeout (float): Request timeout.\n    """\n\n    _token: str\n    timeout: float\n'
    result = assert_pdf514_lines(source, ((5,),))

    assert tuple(finding.message for finding in result.unfixed_findings) == ("Class docstring documents private attribute '_token'",)


def test_reports_numpy_private_class_attribute_names_individually() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    Attributes\n    ----------\n    _token, timeout, _cache : object\n        Client state.\n    """\n'

    result = assert_pdf514_lines(source, ((6,), (6,)), settings=CheckSettings(select=("PDF514",), docstring_convention=DocstringConvention.NUMPY))

    assert tuple(finding.message for finding in result.unfixed_findings) == ("Class docstring documents private attribute '_token'", "Class docstring documents private attribute '_cache'")


def test_reports_rest_private_class_attribute_entries() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    :ivar _token: Internal token.\n    :vartype _cache: dict[str, object]\n    :ivar timeout: Request timeout.\n    """\n'

    assert_pdf514_lines(source, ((4,), (5,)), settings=CheckSettings(select=("PDF514",), docstring_convention=DocstringConvention.REST))


def test_reports_repeated_and_dunder_private_class_attribute_entries() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    Attributes:\n        _token: Internal token.\n        __slots__: Slot names.\n        _token: Repeated token docs.\n    """\n'
    result = assert_pdf514_lines(source, ((5,), (6,), (7,)))

    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Class docstring documents private attribute '_token'",
        "Class docstring documents private attribute '__slots__'",
        "Class docstring documents private attribute '_token'",
    )


def test_none_and_pep257_conventions_do_not_parse_class_attribute_entries() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    Attributes:\n        _token (str): Internal token.\n    """\n'

    for convention in (DocstringConvention.NONE, DocstringConvention.PEP257):
        assert_pdf514_lines(source, (), settings=CheckSettings(select=("PDF514",), docstring_convention=convention))


def test_broad_pdf5_selection_includes_class_private_owner_rule_under_parsed_conventions() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    Attributes:\n        _token (str): Internal token.\n    """\n\n    _token: str\n'

    active = format_source(source, settings=CheckSettings(select=("PDF5",), docstring_convention=DocstringConvention.GOOGLE))
    inert = format_source(source, settings=CheckSettings(select=("PDF5",), docstring_convention=DocstringConvention.PEP257))

    assert tuple(finding.rule for finding in active.unfixed_findings) == (PDF514PrivateClassAttributeOwnerDocstringForbidden.meta,)
    assert not inert.unfixed_findings


def test_module_and_function_attribute_entries_are_ignored() -> None:
    source = '"""Module.\n\nAttributes:\n    _token: Internal token.\n"""\n\ndef configure():\n    """Configure.\n\n    Attributes:\n        _token: Internal token.\n    """\n'

    assert_pdf514_lines(source, ())


def test_nested_class_private_attribute_owner_documentation_is_checked() -> None:
    source = 'class Outer:\n    """Outer.\n\n    Attributes:\n        _outer: Outer state.\n    """\n\n    class Inner:\n        """Inner.\n\n        Attributes:\n            _inner: Inner state.\n        """\n'

    assert_pdf514_lines(source, ((5,), (12,)))


def test_additional_class_string_literals_are_not_owner_docstrings() -> None:
    source = 'class Client:\n    """HTTP client."""\n\n    """Attributes:\n    _token: Internal token.\n    """\n'

    assert_pdf514_lines(source, ())


def test_suppresses_only_targeted_class_docstring() -> None:
    source = 'class Client:\n    # pydocfmt: ignore[PDF514]\n    """HTTP client.\n\n    Attributes:\n        _token: Internal token.\n    """\n\nclass Transport:\n    """HTTP transport.\n\n    Attributes:\n        _cache: Internal cache.\n    """\n'

    assert_pdf514_lines(source, ((13,),))
