import pydocformatter.formatter as formatter
import tests.rules.PDF.helpers as pdf_helpers
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definitions.PDF.PDF517_private_module_attribute_attached_docstring_forbidden import PDF517PrivateModuleAttributeAttachedDocstringForbidden

format_source = pdf_helpers.formatter_for("PDF517")


def assert_pdf517_lines(source: str, expected: tuple[tuple[int, ...], ...], *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Assert PDF517 line findings for source."""
    return pdf_helpers.assert_unfixed_lines(format_source, source, expected, meta=PDF517PrivateModuleAttributeAttachedDocstringForbidden.meta, settings=settings)


def test_reports_attached_private_module_attribute_docstring() -> None:
    source = '_token: str\n"""Internal token."""\n\ntimeout: float\n"""Request timeout in seconds."""\n'
    result = assert_pdf517_lines(source, ((2,),))

    assert tuple(finding.message for finding in result.unfixed_findings) == ("Private module attribute '_token' should not have an attached docstring",)


def test_reports_same_line_private_module_attribute_docstring() -> None:
    source = '_token = ""; """Internal token."""\n'

    assert_pdf517_lines(source, ((1,),))


def test_reports_each_private_target_for_shared_module_attribute_docstring() -> None:
    source = '_primary, fallback, *_aliases = endpoints\n"""Endpoint internals."""\n'
    result = assert_pdf517_lines(source, ((2,), (2,)))

    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Private module attribute '_primary' should not have an attached docstring",
        "Private module attribute '_aliases' should not have an attached docstring",
    )


def test_repeated_assignment_target_module_attribute_docstring_reports_once() -> None:
    source = '_token, _token = values\n"""Internal token."""\n'

    assert_pdf517_lines(source, ((2,),))


def test_reports_private_module_attribute_docstrings_in_source_order() -> None:
    source = '_primary, fallback, *_aliases = endpoints\n"""Endpoint internals."""\n\n_primary = fallback\n"""Fallback endpoint."""\n'
    result = assert_pdf517_lines(source, ((2,), (2,), (5,)))

    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Private module attribute '_primary' should not have an attached docstring",
        "Private module attribute '_aliases' should not have an attached docstring",
        "Private module attribute '_primary' should not have an attached docstring",
    )


def test_reports_each_attached_docstring_for_repeated_private_module_attribute() -> None:
    source = '_token = ""\n"""Primary token."""\n\n_token = "fallback"\n"""Fallback token."""\n'
    result = assert_pdf517_lines(source, ((2,), (5,)))

    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Private module attribute '_token' should not have an attached docstring",
        "Private module attribute '_token' should not have an attached docstring",
    )


def test_reports_attached_dunder_module_attribute_docstring_as_private() -> None:
    source = '__all__ = ("Client",)\n"""Export names."""\n'

    assert_pdf517_lines(source, ((2,),))


def test_reports_multiline_private_module_attribute_docstring_lines() -> None:
    source = '_token: str\n"""Internal token.\n\nUsed for tests.\n"""\n'

    assert_pdf517_lines(source, ((2, 3, 4, 5),))


def test_reports_concatenated_private_module_attribute_docstring() -> None:
    source = '_token: str\n"""Internal """ "token."\n'

    assert_pdf517_lines(source, ((2,),))


def test_exact_selection_checks_attached_module_docstrings_under_none_convention() -> None:
    source = '_token: str\n"""Internal token."""\n'

    assert_pdf517_lines(source, ((2,),), settings=CheckSettings(select=("PDF517",), docstring_convention=DocstringConvention.NONE))


def test_default_broad_selection_does_not_enable_private_module_attribute_docstring_rule() -> None:
    source = '_token: str\n"""Internal token."""\n'

    broad = format_source(source, settings=CheckSettings(select=("PDF5",), docstring_convention=DocstringConvention.GOOGLE))
    exact = format_source(source, settings=CheckSettings(select=("PDF5", "PDF517"), docstring_convention=DocstringConvention.GOOGLE))
    disabled_requirement = format_source(source, settings=CheckSettings(select=("PDF5",), require_explicit=(), docstring_convention=DocstringConvention.GOOGLE))

    assert not broad.unfixed_findings
    assert tuple(finding.rule for finding in exact.unfixed_findings) == (PDF517PrivateModuleAttributeAttachedDocstringForbidden.meta,)
    assert tuple(finding.rule for finding in disabled_requirement.unfixed_findings) == (PDF517PrivateModuleAttributeAttachedDocstringForbidden.meta,)


def test_class_and_function_local_docstrings_are_ignored() -> None:
    source = 'class Client:\n    _token: str\n    """Class token."""\n\ndef configure():\n    _token = ""\n    """Local string."""\n'

    assert_pdf517_lines(source, ())


def test_unsupported_module_attribute_targets_are_ignored() -> None:
    source = 'client._token = ""\n"""Arbitrary object attribute."""\n\nitems[0] = ""\n"""Subscript target."""\n\n[_name] = values\n"""List destructuring target."""\n'

    assert_pdf517_lines(source, ())


def test_non_docstring_literals_after_private_module_attributes_are_ignored() -> None:
    source = '_bytes = b""\nb"Bytes are not docstrings."\n\n_formatted = ""\nf"Formatted {value}"\n'

    assert_pdf517_lines(source, ())


def test_suppresses_only_targeted_private_module_attribute_docstring() -> None:
    source = '_token: str\n"""Internal token."""  # pydocfmt: ignore[PDF517]\n\n_cache: dict[str, object]\n"""Internal cache."""\n'

    assert_pdf517_lines(source, ((5,),))
