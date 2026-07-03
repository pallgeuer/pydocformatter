import pydocformatter.formatter as formatter
import pydocformatter.rules_selection as rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definitions.PDF.PDF512_duplicate_class_attribute_documentation import PDF512DuplicateClassAttributeDocumentation


def format_source(source: str, *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Format source with PDF512 selected."""
    resolved_settings = CheckSettings(select=("PDF512",), docstring_convention=DocstringConvention.GOOGLE) if settings is None else settings
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=True)


def assert_pdf512_lines(source: str, expected: tuple[tuple[int, ...], ...], *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Assert PDF512 line findings for source."""
    result = format_source(source, settings=settings)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.rule for finding in result.unfixed_findings) == (PDF512DuplicateClassAttributeDocumentation.meta,) * len(expected)
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == expected
    return result


def test_reports_google_duplicate_class_attribute_documentation_on_attached_docstring() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    Attributes:\n        timeout (float): Request timeout.\n    """\n\n    timeout: float\n    """Request timeout in seconds."""\n'
    result = assert_pdf512_lines(source, ((9,),))

    assert tuple(finding.message for finding in result.unfixed_findings) == ("Attached docstring for class attribute 'timeout' duplicates class docstring attribute documentation",)


def test_no_finding_when_only_one_class_attribute_documentation_style_is_present() -> None:
    attached_only = 'class Client:\n    timeout: float\n    """Request timeout in seconds."""\n'
    owner_only = 'class Client:\n    """HTTP client.\n\n    Attributes:\n        timeout (float): Request timeout.\n    """\n\n    timeout: float\n'

    assert_pdf512_lines(attached_only, ())
    assert_pdf512_lines(owner_only, ())


def test_none_and_pep257_conventions_do_not_parse_class_attribute_entries() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    Attributes:\n        timeout (float): Request timeout.\n    """\n\n    timeout: float\n    """Request timeout in seconds."""\n'

    for convention in (DocstringConvention.NONE, DocstringConvention.PEP257):
        assert_pdf512_lines(source, (), settings=CheckSettings(select=("PDF512",), docstring_convention=convention))


def test_broad_pdf5_selection_includes_class_duplicate_rule_under_parsed_conventions() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    Attributes:\n        timeout (float): Request timeout.\n    """\n\n    timeout: float\n    """Request timeout in seconds."""\n'

    active = format_source(source, settings=CheckSettings(select=("PDF5",), docstring_convention=DocstringConvention.GOOGLE))
    inert = format_source(source, settings=CheckSettings(select=("PDF5",), docstring_convention=DocstringConvention.PEP257))

    assert tuple(finding.rule for finding in active.unfixed_findings) == (PDF512DuplicateClassAttributeDocumentation.meta,)
    assert not inert.unfixed_findings


def test_reports_numpy_comma_separated_class_attribute_duplicates_by_name() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    Attributes\n    ----------\n    primary, fallback : str\n        Request endpoints.\n    """\n\n    primary = fallback = "https://example.com"\n    """Request endpoint values."""\n'

    result = assert_pdf512_lines(source, ((11,), (11,)), settings=CheckSettings(select=("PDF512",), docstring_convention=DocstringConvention.NUMPY))

    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Attached docstring for class attribute 'primary' duplicates class docstring attribute documentation",
        "Attached docstring for class attribute 'fallback' duplicates class docstring attribute documentation",
    )


def test_multi_target_class_docstring_reports_only_targets_also_documented_by_class_docstring() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    Attributes:\n        primary (str): Primary endpoint.\n    """\n\n    primary = fallback = "https://example.com"\n    """Request endpoint values."""\n'

    assert_pdf512_lines(source, ((9,),))


def test_tuple_unpacked_class_attribute_docstring_duplicates_each_documented_target() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    Attributes:\n        primary (str): Primary endpoint.\n        aliases (tuple[str, ...]): Endpoint aliases.\n    """\n\n    primary, (fallback, *aliases) = endpoints\n    """Request endpoints."""\n'

    assert_pdf512_lines(source, ((10,), (10,)))


def test_reports_rest_class_attribute_duplicates() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    :ivar timeout: Request timeout.\n    """\n\n    timeout: float\n    """Request timeout in seconds."""\n'

    assert_pdf512_lines(source, ((8,),), settings=CheckSettings(select=("PDF512",), docstring_convention=DocstringConvention.REST))


def test_rest_cvar_and_vartype_class_attribute_duplicates() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    :cvar timeout: Request timeout.\n    :vartype retries: int\n    """\n\n    timeout: float\n    """Request timeout in seconds."""\n    retries: int\n    """Retry attempts."""\n'

    assert_pdf512_lines(source, ((9,), (11,)), settings=CheckSettings(select=("PDF512",), docstring_convention=DocstringConvention.REST))


def test_reports_each_attached_class_docstring_duplicate_for_same_owner_entry() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    Attributes:\n        timeout (float): Request timeout.\n    """\n\n    timeout: float\n    """Request timeout in seconds."""\n\n    timeout = 30.0\n    """Default timeout in seconds."""\n'

    assert_pdf512_lines(source, ((9,), (12,)))


def test_repeated_class_attribute_entries_each_duplicate_attached_docstring() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    Attributes:\n        timeout (float): Request timeout.\n        timeout (float): Timeout in seconds.\n    """\n\n    timeout: float\n    """Request timeout in seconds."""\n'

    assert_pdf512_lines(source, ((10,), (10,)))


def test_multiline_attached_class_docstring_targets_all_docstring_lines() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    Attributes:\n        timeout (float): Request timeout.\n    """\n\n    timeout: float\n    """Request timeout.\n\n    Measured in seconds.\n    """\n'

    assert_pdf512_lines(source, ((9, 10, 11, 12),))


def test_attached_class_docstring_suppression_only_suppresses_that_duplicate() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    Attributes:\n        timeout (float): Request timeout.\n        retries (int): Retry count.\n    """\n\n    timeout: float\n    """Request timeout in seconds."""  # pydocfmt: ignore[PDF512]\n\n    retries: int\n    """Retry attempts."""\n'

    assert_pdf512_lines(source, ((13,),))


def test_class_docstring_suppression_does_not_suppress_attached_docstring_duplicate() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    Attributes:\n        timeout (float): Request timeout.  # pydocfmt: ignore[PDF512]\n    """\n\n    timeout: float\n    """Request timeout in seconds."""\n'

    assert_pdf512_lines(source, ((9,),))


def test_private_class_and_private_attribute_duplicates_are_reported() -> None:
    source = 'class _Client:\n    """HTTP client.\n\n    Attributes:\n        _token (str): Internal token.\n    """\n\n    _token: str\n    """Internal token."""\n'

    assert_pdf512_lines(source, ((9,),))


def test_init_attribute_docstring_duplicate_is_checked_without_require_init_setting() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    Attributes:\n        timeout (float): Request timeout.\n    """\n\n    def __init__(self):\n        self.timeout = 30.0\n        """Request timeout in seconds."""\n'

    assert_pdf512_lines(source, ((10,),), settings=CheckSettings(select=("PDF512",), docstring_convention=DocstringConvention.GOOGLE, docstring_require_init_attribute_documentation=False))


def test_non_init_attribute_docstring_does_not_duplicate_class_docstring() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    Attributes:\n        timeout (float): Request timeout.\n    """\n\n    def configure(self):\n        self.timeout = 30.0\n        """Request timeout in seconds."""\n'

    assert_pdf512_lines(source, ())


def test_nested_class_attached_docstring_does_not_duplicate_outer_class_docstring() -> None:
    source = 'class Outer:\n    """Outer client.\n\n    Attributes:\n        timeout: Outer timeout.\n    """\n\n    class Inner:\n        timeout: float\n        """Inner timeout."""\n'

    assert_pdf512_lines(source, ())
