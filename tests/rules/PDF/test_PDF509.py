import pydocformatter.formatter as formatter
import pydocformatter.rules_selection as rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definitions.PDF.PDF509_extraneous_class_attribute_documentation import PDF509ExtraneousClassAttributeDocumentation


def format_source(source: str, *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Format source with PDF509 selected."""
    resolved_settings = CheckSettings(select=("PDF509",), docstring_convention=DocstringConvention.GOOGLE) if settings is None else settings
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=True)


def assert_pdf509_lines(source: str, expected: tuple[tuple[int, ...], ...], *, settings: CheckSettings | None = None) -> None:
    """Assert PDF509 line findings for source."""
    result = format_source(source, settings=settings)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.rule for finding in result.unfixed_findings) == (PDF509ExtraneousClassAttributeDocumentation.meta,) * len(expected)
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == expected


def test_reports_google_class_attribute_documentation_absent_from_class() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    Attributes:\n        timeout: Request timeout.\n        stale: Removed attribute.\n    """\n\n    timeout: float\n'
    result = format_source(source)

    assert_pdf509_lines(source, ((6,),))
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Class docstring documents attribute 'stale' that is not present",)


def test_init_instance_attributes_count_as_present_for_extraneous_checks() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    Attributes:\n        timeout: Request timeout.\n    """\n\n    def __init__(self):\n        self.timeout = 30.0\n'

    assert_pdf509_lines(source, ())


def test_private_attributes_may_be_voluntarily_documented_when_present() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    Attributes:\n        _token: Internal token.\n    """\n\n    _token: str\n'

    assert_pdf509_lines(source, ())


def test_reports_numpy_and_rest_stale_class_attributes() -> None:
    numpy = 'class Client:\n    """HTTP client.\n\n    Attributes\n    ----------\n    stale : str\n        Removed attribute.\n    """\n'
    rest = 'class Client:\n    """HTTP client.\n\n    :cvar stale: Removed attribute.\n    :vartype other: str\n    """\n'

    assert_pdf509_lines(numpy, ((6,),), settings=CheckSettings(select=("PDF509",), docstring_convention=DocstringConvention.NUMPY))
    assert_pdf509_lines(rest, ((4,), (5,)), settings=CheckSettings(select=("PDF509",), docstring_convention=DocstringConvention.REST))


def test_numpy_comma_separated_attribute_entry_reports_only_stale_class_names() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    Attributes\n    ----------\n    primary, stale : str\n        Request endpoints.\n    """\n\n    primary: str\n'

    assert_pdf509_lines(source, ((6,),), settings=CheckSettings(select=("PDF509",), docstring_convention=DocstringConvention.NUMPY))


def test_repeated_stale_documentation_reports_each_entry() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    Attributes:\n        stale: Removed attribute.\n        stale: Still removed.\n    """\n'

    assert_pdf509_lines(source, ((5,), (6,)))


def test_none_and_pep257_conventions_do_not_parse_attribute_sections() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    Attributes:\n        stale: Removed attribute.\n    """\n'

    for convention in (DocstringConvention.NONE, DocstringConvention.PEP257):
        assert_pdf509_lines(source, (), settings=CheckSettings(select=("PDF509",), docstring_convention=convention))


def test_multi_target_assignment_makes_each_target_present() -> None:
    source = (
        'class Client:\n    """HTTP client.\n\n    Attributes:\n        primary: Primary endpoint.\n        fallback: Fallback endpoint.\n    """\n\n    primary = fallback = "https://example.com"\n'
    )

    assert_pdf509_lines(source, ())


def test_tuple_unpacked_assignment_makes_each_target_present() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    Attributes:\n        primary: Primary endpoint.\n        fallback: Fallback endpoint.\n        aliases: Endpoint aliases.\n    """\n\n    primary, (fallback, *aliases) = endpoints\n'

    assert_pdf509_lines(source, ())


def test_tuple_unpacked_init_attribute_mixed_with_discard_counts_as_present() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    Attributes:\n        timeout: Request timeout.\n    """\n\n    def __init__(self):\n        self.timeout, _ = values\n'

    assert_pdf509_lines(source, ())


def test_unsupported_list_destructuring_assignment_does_not_make_attribute_present() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    Attributes:\n        primary: Primary endpoint.\n    """\n\n    [primary, fallback] = endpoints\n'

    assert_pdf509_lines(source, ((5,),))


def test_nested_class_attributes_do_not_satisfy_outer_class_documentation() -> None:
    source = 'class Outer:\n    """Outer client.\n\n    Attributes:\n        inner_timeout: Inner timeout.\n    """\n\n    class Inner:\n        inner_timeout: float\n'

    assert_pdf509_lines(source, ((5,),))
