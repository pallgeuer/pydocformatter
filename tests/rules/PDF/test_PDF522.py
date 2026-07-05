import pydocformatter.formatter as formatter
import tests.rules.PDF.helpers as pdf_helpers
from pydocformatter.cli.settings_check import CheckSettings
from pydocformatter.rules.definitions.PDF.PDF522_private_class_attribute_docstring_must_be_owner import PDF522PrivateClassAttributeDocstringMustBeOwner

format_source = pdf_helpers.formatter_for("PDF522")


def assert_pdf522_lines(source: str, expected: tuple[tuple[int, ...], ...], *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Assert PDF522 line findings for source."""
    return pdf_helpers.assert_unfixed_lines(format_source, source, expected, meta=PDF522PrivateClassAttributeDocstringMustBeOwner.meta, settings=settings)


def test_reports_attached_private_class_attribute_docstrings() -> None:
    source = 'class Client:\n    _token: str\n    """Internal token."""\n\n    timeout: float\n    """Request timeout."""\n'
    result = assert_pdf522_lines(source, ((3,),))

    assert tuple(finding.message for finding in result.unfixed_findings) == ("Private class attribute '_token' must use class docstring documentation, not attached docstring",)


def test_reports_private_init_attribute_docstrings() -> None:
    source = 'class Client:\n    def __init__(self):\n        self._token = ""\n        """Internal token."""\n'

    assert_pdf522_lines(source, ((4,),))


def test_reports_each_private_tuple_unpacked_class_target() -> None:
    source = 'class Client:\n    _primary, fallback, *_aliases = endpoints\n    """Endpoint internals."""\n'

    assert_pdf522_lines(source, ((3,), (3,)))


def test_repeated_private_class_assignment_target_reports_once_for_shared_docstring() -> None:
    source = 'class Client:\n    _token, _token = values\n    """Internal token."""\n'

    assert_pdf522_lines(source, ((3,),))


def test_ignores_unsupported_private_class_attached_docstring_targets() -> None:
    source = 'class Client:\n    items[0] = ""\n    """Subscript target."""\n\n    [_name] = values\n    """List destructuring target."""\n'

    assert_pdf522_lines(source, ())
