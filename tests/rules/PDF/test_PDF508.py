# First-party imports
from pydocformatter import formatter, rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention, DocstringMissingDocumentation
from pydocformatter.rules.definitions.PDF.PDF508_missing_public_class_attribute_documentation import PDF508MissingPublicClassAttributeDocumentation


def format_source(source: str, *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Format source with PDF508 selected."""
    resolved_settings = CheckSettings(select=("PDF508",), docstring_convention=DocstringConvention.GOOGLE) if settings is None else settings
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=True)


def assert_pdf508_lines(source: str, expected: tuple[tuple[int, ...], ...], *, settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Assert PDF508 line findings for source."""
    result = format_source(source, settings=settings)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.rule for finding in result.unfixed_findings) == (PDF508MissingPublicClassAttributeDocumentation.meta,) * len(expected)
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == expected
    return result


def test_reports_google_class_attribute_missing_from_attributes_section() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    Attributes:\n        timeout (float): Request timeout.\n    """\n\n    timeout: float\n    retries: int\n'

    result = assert_pdf508_lines(source, ((9,),))
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Public class attribute 'retries' is missing docstring documentation",)


def test_empty_attributes_section_still_triggers_class_missing_check() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    Attributes:\n    """\n\n    timeout: float\n'

    assert_pdf508_lines(source, ((7,),))


def test_attached_attribute_docstring_counts_as_documentation_and_triggers_missing_check() -> None:
    source = 'class Client:\n    timeout: float\n    """Request timeout."""\n\n    retries: int\n'

    assert_pdf508_lines(source, ((5,),))


def test_inert_conventions_do_not_report_attached_class_attribute_docstrings() -> None:
    source = 'class Client:\n    timeout: float\n    """Request timeout."""\n\n    retries: int\n'

    for convention in (DocstringConvention.NONE, DocstringConvention.PEP257):
        assert_pdf508_lines(source, (), settings=CheckSettings(select=("PDF508",), docstring_convention=convention))


def test_attached_attribute_docstring_directive_does_not_suppress_unrelated_missing_class_attribute() -> None:
    source = 'class Client:\n    timeout: float\n    """Request timeout."""  # pydocfmt: ignore[PDF508]\n\n    retries: int\n'

    assert_pdf508_lines(source.replace("  # pydocfmt: ignore[PDF508]", ""), ((5,),))
    assert_pdf508_lines(source, ((5,),))


def test_accepts_numpy_and_rest_attribute_documentation() -> None:
    numpy = 'class Client:\n    """HTTP client.\n\n    Attributes\n    ----------\n    timeout : float\n        Request timeout.\n    """\n\n    timeout: float\n    retries: int\n'
    rest = 'class Client:\n    """HTTP client.\n\n    :ivar timeout: Request timeout.\n    """\n\n    timeout: float\n    retries: int\n'

    assert_pdf508_lines(numpy, ((11,),), settings=CheckSettings(select=("PDF508",), docstring_convention=DocstringConvention.NUMPY))
    assert_pdf508_lines(rest, ((8,),), settings=CheckSettings(select=("PDF508",), docstring_convention=DocstringConvention.REST))


def test_rest_vartype_activates_check_without_documenting_class_attribute() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    :cvar timeout: Request timeout.\n    :vartype retries: int\n    """\n\n    timeout: float\n    retries: int\n    stale: str\n'

    assert_pdf508_lines(source, ((9,), (10,)), settings=CheckSettings(select=("PDF508",), docstring_convention=DocstringConvention.REST))


def test_unrelated_orphan_vartype_activates_class_attribute_check_without_documenting_inventory() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    :vartype removed: int\n    """\n\n    timeout: float\n    retries: int\n'

    assert_pdf508_lines(source, ((7,), (8,)), settings=CheckSettings(select=("PDF508",), docstring_convention=DocstringConvention.REST))


def test_empty_rest_attribute_value_field_documents_class_attribute_but_vartype_does_not() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    :vartype timeout: float\n    :var retries:\n    """\n\n    timeout: float\n    retries: int\n'

    assert_pdf508_lines(source, ((8,),), settings=CheckSettings(select=("PDF508",), docstring_convention=DocstringConvention.REST))


def test_attached_docstring_satisfies_class_attribute_even_when_owner_has_orphan_vartype() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    :vartype timeout: float\n    """\n\n    timeout: float\n    """Request timeout."""\n'

    assert_pdf508_lines(source, (), settings=CheckSettings(select=("PDF508",), docstring_convention=DocstringConvention.REST))


def test_orphan_vartype_does_not_document_init_attribute_when_requirement_is_enabled() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    :vartype retries: int\n    """\n\n    def __init__(self):\n        self.retries = 3\n'
    settings = CheckSettings(select=("PDF508",), docstring_convention=DocstringConvention.REST, docstring_require_init_attribute_documentation=True)

    assert_pdf508_lines(source, ((8,),), settings=settings)


def test_numpy_comma_separated_attribute_entry_documents_multiple_class_attributes() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    Attributes\n    ----------\n    primary, fallback : str\n        Request endpoints.\n    """\n\n    primary = fallback = "https://example.com"\n    retries: int\n'

    assert_pdf508_lines(source, ((11,),), settings=CheckSettings(select=("PDF508",), docstring_convention=DocstringConvention.NUMPY))


def test_private_attributes_are_not_required() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    Attributes:\n        timeout (float): Request timeout.\n    """\n\n    timeout: float\n    _token: str\n'

    assert_pdf508_lines(source, ())


def test_private_class_is_skipped_by_public_only_but_checked_when_disabled() -> None:
    source = 'class _Client:\n    """HTTP client.\n\n    Attributes:\n        timeout (float): Request timeout.\n    """\n\n    timeout: float\n    retries: int\n'

    assert_pdf508_lines(source, ())
    assert_pdf508_lines(source, ((9,),), settings=CheckSettings(select=("PDF508",), docstring_convention=DocstringConvention.GOOGLE, docstring_missing_documentation_public_only=False))


def test_init_instance_attributes_are_required_only_when_setting_enabled() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    Attributes:\n        timeout (float): Request timeout.\n    """\n\n    timeout: float\n\n    def __init__(self):\n        self.retries = 3\n'

    assert_pdf508_lines(source, ())
    assert_pdf508_lines(source, ((11,),), settings=CheckSettings(select=("PDF508",), docstring_convention=DocstringConvention.GOOGLE, docstring_require_init_attribute_documentation=True))


def test_all_docstrings_policy_reports_summary_only_public_class_docstring() -> None:
    source = 'class Client:\n    """HTTP client."""\n\n    timeout: float\n'

    assert_pdf508_lines(source, (), settings=CheckSettings(select=("PDF508",), docstring_convention=DocstringConvention.GOOGLE))
    assert_pdf508_lines(
        source, ((4,),), settings=CheckSettings(select=("PDF508",), docstring_convention=DocstringConvention.GOOGLE, docstring_missing_documentation=DocstringMissingDocumentation.ALL_DOCSTRINGS)
    )


def test_inert_conventions_do_not_report_broad_class_missing_policies() -> None:
    summary = 'class Client:\n    """HTTP client."""\n\n    timeout: float\n'
    body = 'class Client:\n    """HTTP client.\n\n    Used by the transport layer.\n    """\n\n    timeout: float\n'

    for convention in (DocstringConvention.NONE, DocstringConvention.PEP257):
        assert_pdf508_lines(summary, (), settings=CheckSettings(select=("PDF508",), docstring_convention=convention, docstring_missing_documentation=DocstringMissingDocumentation.ALL_DOCSTRINGS))
        assert_pdf508_lines(body, (), settings=CheckSettings(select=("PDF508",), docstring_convention=convention, docstring_missing_documentation=DocstringMissingDocumentation.NON_SUMMARY_DOCSTRINGS))


def test_repeated_assignment_reports_first_missing_attribute_line_once() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    Attributes:\n        timeout (float): Request timeout.\n    """\n\n    timeout: float\n    retries: int\n    retries = 3\n'

    assert_pdf508_lines(source, ((9,),))


def test_multi_target_assignment_reports_only_undocumented_targets_on_shared_line() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    Attributes:\n        timeout (float): Request timeout.\n        primary (str): Primary endpoint.\n    """\n\n    primary = fallback = "https://example.com"\n'

    assert_pdf508_lines(source, ((9,),))


def test_tuple_unpacked_assignment_reports_only_undocumented_class_targets() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    Attributes:\n        timeout (float): Request timeout.\n        primary (str): Primary endpoint.\n    """\n\n    primary, (fallback, *aliases) = endpoints\n'

    assert_pdf508_lines(source, ((9,), (9,)))


def test_multiline_tuple_unpacked_assignment_reports_target_lines() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    Attributes:\n        primary (str): Primary endpoint.\n    """\n\n    (\n        primary,\n        (\n            fallback,\n            *aliases,\n        ),\n    ) = endpoints\n'

    assert_pdf508_lines(source, ((11,), (12,)))


def test_tuple_unpacked_attribute_docstring_documents_supported_class_targets() -> None:
    source = 'class Client:\n    primary, fallback = endpoints\n    """Request endpoints."""\n\n    retries: int\n'

    assert_pdf508_lines(source, ((5,),))


def test_tuple_unpacked_init_attribute_mixed_with_discard_is_required_when_enabled() -> None:
    source = (
        'class Client:\n    """HTTP client.\n\n    Attributes:\n        timeout (float): Request timeout.\n    """\n\n    timeout: float\n\n    def __init__(self):\n        self.retries, _ = values\n'
    )

    assert_pdf508_lines(source, ((11,),), settings=CheckSettings(select=("PDF508",), docstring_convention=DocstringConvention.GOOGLE, docstring_require_init_attribute_documentation=True))


def test_non_summary_policy_reports_body_only_class_docstring() -> None:
    source = 'class Client:\n    """HTTP client.\n\n    Used by the transport layer.\n    """\n\n    timeout: float\n'

    assert_pdf508_lines(
        source,
        ((7,),),
        settings=CheckSettings(select=("PDF508",), docstring_convention=DocstringConvention.GOOGLE, docstring_missing_documentation=DocstringMissingDocumentation.NON_SUMMARY_DOCSTRINGS),
    )


def test_nested_class_attributes_are_checked_against_their_own_class_docstring() -> None:
    source = 'class Outer:\n    """Outer client.\n\n    Attributes:\n        outer_timeout (float): Outer timeout.\n    """\n\n    outer_timeout: float\n\n    class Inner:\n        """Inner client.\n\n        Attributes:\n            inner_timeout (float): Inner timeout.\n        """\n\n        inner_timeout: float\n        retries: int\n'

    assert_pdf508_lines(source, ((18,),))
