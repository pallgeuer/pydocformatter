import pydocformatter.formatter as formatter
import pydocformatter.rules_selection as rules_selection
import tests.rules.PDF.helpers as pdf_helpers
from pydocformatter.cli.settings_check import CheckSettings
from pydocformatter.rules.definitions.PDF.PDF520_public_module_attribute_docstring_must_be_owner import PDF520PublicModuleAttributeDocstringMustBeOwner

format_source = pdf_helpers.formatter_for("PDF520")


def assert_pdf520_lines(source: str, expected: tuple[tuple[int, ...], ...], *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Assert PDF520 line findings for source."""
    return pdf_helpers.assert_unfixed_lines(format_source, source, expected, meta=PDF520PublicModuleAttributeDocstringMustBeOwner.meta, settings=settings)


def test_reports_attached_public_module_attribute_docstrings() -> None:
    source = 'timeout: float\n"""Request timeout."""\n\n_token: str\n"""Internal token."""\n'
    result = assert_pdf520_lines(source, ((2,),))

    assert tuple(finding.message for finding in result.unfixed_findings) == ("Public module attribute 'timeout' must use module docstring documentation, not attached docstring",)


def test_reports_each_public_tuple_unpacked_module_target() -> None:
    source = 'primary, (_fallback, *aliases) = endpoints\n"""Endpoint values."""\n'

    assert_pdf520_lines(source, ((2,), (2,)))


def test_repeated_public_module_assignment_target_reports_once_for_shared_docstring() -> None:
    source = 'timeout, timeout = values\n"""Request timeout."""\n'

    assert_pdf520_lines(source, ((2,),))


def test_public_attribute_in_private_module_path_still_uses_public_module_policy() -> None:
    source = 'timeout: float\n"""Request timeout."""\n'
    settings = CheckSettings(select=("PDF520",))
    result = formatter.format_source(source, "package/_private.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)

    assert tuple(finding.rule for finding in result.unfixed_findings) == (PDF520PublicModuleAttributeDocstringMustBeOwner.meta,)
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2,),)


def test_reports_same_line_and_concatenated_public_module_attribute_docstrings() -> None:
    source = 'timeout = 30.0; """Request timeout."""\nretries: int\n"""Retry """ "count."\n\nitems[0] = 1\n"""Ignored subscript target."""\n'

    assert_pdf520_lines(source, ((1,), (3,)))


def test_ignores_class_and_function_local_attached_docstrings() -> None:
    source = 'class Client:\n    timeout: float\n    """Class timeout."""\n\ndef configure():\n    timeout = 1\n    """Local timeout."""\n'

    assert_pdf520_lines(source, ())
