import pydocformatter.formatter as formatter
import tests.rules.PDF.helpers as pdf_helpers
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definitions.PDF.PDF516_private_class_attribute_docstring import PDF516PrivateClassAttributeDocstring

format_source = pdf_helpers.formatter_for("PDF516")


def assert_pdf516_lines(source: str, expected: tuple[tuple[int, ...], ...], *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Assert PDF516 line findings for source."""
    return pdf_helpers.assert_unfixed_lines(format_source, source, expected, meta=PDF516PrivateClassAttributeDocstring.meta, settings=settings)


def test_reports_attached_private_class_attribute_docstring() -> None:
    source = 'class Client:\n    _token: str\n    """Internal token."""\n\n    timeout: float\n    """Request timeout in seconds."""\n'
    result = assert_pdf516_lines(source, ((3,),))

    assert tuple(finding.message for finding in result.unfixed_findings) == ("Private class attribute '_token' should not have an attached docstring",)


def test_reports_private_init_instance_attribute_docstring() -> None:
    source = 'class Client:\n    def __init__(self):\n        self._token = ""\n        """Internal token."""\n\n    def configure(self):\n        self._cache = {}\n        """Ignored non-init instance attribute docstring."""\n'

    assert_pdf516_lines(source, ((4,),))


def test_reports_same_line_private_class_and_init_attribute_docstrings() -> None:
    source = 'class Client:\n    _token = ""; """Class token."""\n\n    def __init__(self): self._cache = {}; """Instance cache."""\n'

    assert_pdf516_lines(source, ((2,), (4,)))


def test_reports_each_attached_docstring_for_repeated_private_class_attribute() -> None:
    source = 'class Client:\n    _token = ""\n    """Primary token."""\n\n    _token = "fallback"\n    """Fallback token."""\n'
    result = assert_pdf516_lines(source, ((3,), (6,)))

    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Private class attribute '_token' should not have an attached docstring",
        "Private class attribute '_token' should not have an attached docstring",
    )


def test_reports_attached_dunder_class_attribute_docstring_as_private() -> None:
    source = 'class Client:\n    __slots__ = ("_token",)\n    """Slot names."""\n'

    assert_pdf516_lines(source, ((3,),))


def test_reports_each_private_target_for_shared_class_attribute_docstring() -> None:
    source = 'class Client:\n    _primary, fallback, *_aliases = endpoints\n    """Endpoint internals."""\n'
    result = assert_pdf516_lines(source, ((3,), (3,)))

    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Private class attribute '_primary' should not have an attached docstring",
        "Private class attribute '_aliases' should not have an attached docstring",
    )


def test_repeated_assignment_target_class_attribute_docstring_reports_once() -> None:
    source = 'class Client:\n    _token, _token = values\n    """Internal token."""\n'

    assert_pdf516_lines(source, ((3,),))


def test_reports_private_class_attribute_docstrings_in_source_order() -> None:
    source = 'class Client:\n    _primary, fallback, *_aliases = endpoints\n    """Endpoint internals."""\n\n    _primary = fallback\n    """Fallback endpoint."""\n'
    result = assert_pdf516_lines(source, ((3,), (3,), (6,)))

    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Private class attribute '_primary' should not have an attached docstring",
        "Private class attribute '_aliases' should not have an attached docstring",
        "Private class attribute '_primary' should not have an attached docstring",
    )


def test_reports_multiline_private_class_attribute_docstring_lines() -> None:
    source = 'class Client:\n    _token: str\n    """Internal token.\n\n    Used for tests.\n    """\n'

    assert_pdf516_lines(source, ((3, 4, 5, 6),))


def test_reports_concatenated_private_class_attribute_docstring() -> None:
    source = 'class Client:\n    _token: str\n    """Internal """ "token."\n'

    assert_pdf516_lines(source, ((3,),))


def test_exact_selection_checks_attached_class_docstrings_under_none_convention() -> None:
    source = 'class Client:\n    _token: str\n    """Internal token."""\n'

    assert_pdf516_lines(source, ((3,),), settings=CheckSettings(select=("PDF516",), docstring_convention=DocstringConvention.NONE))


def test_default_broad_selection_does_not_enable_private_class_attribute_docstring_rule() -> None:
    source = 'class Client:\n    _token: str\n    """Internal token."""\n'

    broad = format_source(source, settings=CheckSettings(select=("PDF5",), docstring_convention=DocstringConvention.GOOGLE))
    exact = format_source(source, settings=CheckSettings(select=("PDF5", "PDF516"), docstring_convention=DocstringConvention.GOOGLE))
    disabled_requirement = format_source(source, settings=CheckSettings(select=("PDF5",), require_explicit=(), docstring_convention=DocstringConvention.GOOGLE))

    assert not broad.unfixed_findings
    assert tuple(finding.rule for finding in exact.unfixed_findings) == (PDF516PrivateClassAttributeDocstring.meta,)
    assert tuple(finding.rule for finding in disabled_requirement.unfixed_findings) == (PDF516PrivateClassAttributeDocstring.meta,)


def test_module_nested_class_and_function_local_docstrings_are_ignored() -> None:
    source = (
        '_module_token: str\n"""Module token."""\n\nclass Outer:\n    class Inner:\n        _token: str\n        """Inner token."""\n\ndef configure():\n    _token = ""\n    """Local string."""\n'
    )

    assert_pdf516_lines(source, ((7,),))


def test_unsupported_class_attribute_targets_are_ignored() -> None:
    source = 'class Client:\n    self._token = ""\n    """Arbitrary class-body object attribute."""\n\n    items[0] = ""\n    """Subscript target."""\n\n    [_name] = values\n    """List destructuring target."""\n'

    assert_pdf516_lines(source, ())


def test_non_docstring_literals_after_private_class_attributes_are_ignored() -> None:
    source = 'class Client:\n    _bytes = b""\n    b"Bytes are not docstrings."\n\n    _formatted = ""\n    f"Formatted {value}"\n'

    assert_pdf516_lines(source, ())


def test_suppresses_only_targeted_private_class_attribute_docstring() -> None:
    source = 'class Client:\n    _token: str\n    """Internal token."""  # pydocfmt: ignore[PDF516]\n\n    _cache: dict[str, object]\n    """Internal cache."""\n'

    assert_pdf516_lines(source, ((6,),))
