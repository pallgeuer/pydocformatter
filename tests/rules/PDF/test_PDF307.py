# Third-party imports
import pytest

# First-party imports
import tests.rules.PDF.helpers as pdf_helpers
from pydocformatter import rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definitions.PDF.PDF307_attribute_documentation_too_generic import PDF307AttributeDocumentationTooGeneric
from tests import rule_helpers


contexts = pdf_helpers.contexts_for("PDF307")
format_source = pdf_helpers.formatter_for("PDF307")


@pytest.mark.parametrize(
    ("description", "attribute"),
    [
        ("timeout", "timeout"),
        ("The timeout.", "timeout"),
        ("The timeout value.", "timeout"),
        ("timeout attribute", "timeout"),
        ("timeout field", "timeout"),
        ("value of timeout", "timeout"),
        ("The value of timeout.", "timeout"),
        ("The attribute timeout.", "timeout"),
        ("The field timeout.", "timeout"),
        ("`timeout` attribute.", "timeout"),
        ('"timeout" field.', "timeout"),
        ("max_retries value", "max_retries"),
        ("max retries value", "max_retries"),
        ("API2 token value", "api2_token"),
    ],
)
def test_reports_attached_attribute_docstrings_that_only_restate_attribute_name(description: str, attribute: str) -> None:
    source = f'{attribute} = 1\n"""{description}"""\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2,),)
    assert tuple(finding.message for finding in result.unfixed_findings) == (f"Attribute '{attribute}' documentation is too generic",)
    assert not result.unfixed_findings[0].fixable


def test_reports_class_instance_and_owner_docstring_attribute_entries() -> None:
    source = 'class Client:\n    """Client.\n\n    Attributes:\n        class_timeout: class timeout value.\n        instance_timeout: The instance timeout value.\n    """\n\n    class_timeout = 30\n\n    def __init__(self):\n        self.instance_timeout = 30\n        """The instance timeout value."""\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((5,), (6,), (13,))
    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Attribute 'class_timeout' documentation is too generic",
        "Attribute 'instance_timeout' documentation is too generic",
        "Attribute 'instance_timeout' documentation is too generic",
    )


def test_reports_numpy_and_rest_attribute_entries() -> None:
    numpy_source = 'class Client:\n    """Client.\n\n    Attributes\n    ----------\n    timeout : int\n        The timeout value.\n    """\n'
    rest_source = '"""Module.\n\n:ivar timeout: The timeout value.\n"""\n'

    numpy = format_source(numpy_source, settings=CheckSettings(select=("PDF307",), docstring_convention=DocstringConvention.NUMPY))
    rest = format_source(rest_source, settings=CheckSettings(select=("PDF307",), docstring_convention=DocstringConvention.REST))

    assert tuple(finding.message for finding in numpy.unfixed_findings) == ("Attribute 'timeout' documentation is too generic",)
    assert tuple(finding.line_numbers for finding in numpy.unfixed_findings) == ((6,),)
    assert tuple(finding.message for finding in rest.unfixed_findings) == ("Attribute 'timeout' documentation is too generic",)
    assert tuple(finding.line_numbers for finding in rest.unfixed_findings) == ((3,),)


def test_reports_rest_attribute_field_aliases() -> None:
    source = '"""Module.\n\n:ivar timeout: The timeout value.\n:cvar token: The token value.\n:var retries: Maximum number of retry attempts.\n:vartype timeout: Timeout\n"""\n'
    result = format_source(source, settings=CheckSettings(select=("PDF307",), docstring_convention=DocstringConvention.REST))

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((3,), (4,))
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Attribute 'timeout' documentation is too generic", "Attribute 'token' documentation is too generic")


def test_reports_module_owner_docstring_attribute_entries() -> None:
    source = '"""Module.\n\nAttributes:\n    timeout: The timeout value.\n"""\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((4,),)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Attribute 'timeout' documentation is too generic",)


def test_reports_generic_attribute_documentation_split_across_continuation_lines() -> None:
    source = 'class Client:\n    """Client.\n\n    Attributes:\n        timeout:\n            The timeout\n            value.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((5,),)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Attribute 'timeout' documentation is too generic",)


def test_reports_only_generic_attributes_in_mixed_owner_docstring() -> None:
    source = 'class Client:\n    """Client.\n\n    Attributes:\n        timeout: The timeout value.\n        retries: Maximum number of retry attempts.\n        base_url:\n            The base url\n            value.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((5,), (7,))
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Attribute 'timeout' documentation is too generic", "Attribute 'base_url' documentation is too generic")


def test_reports_same_line_and_annotated_attached_attribute_docstrings() -> None:
    source = 'class Client:\n    timeout: int\n    """The timeout value."""\n\n    def __init__(self):\n        self.retries = 3; """The retries value."""\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((3,), (6,))
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Attribute 'timeout' documentation is too generic", "Attribute 'retries' documentation is too generic")


def test_reports_mixed_tuple_assignments_with_one_supported_attached_attribute_target() -> None:
    source = 'module_supported, helper.value = endpoints\n"""The module supported value."""\n\nclass Client:\n    class_supported, helper.value = endpoints\n    """The class supported value."""\n\n    def __init__(self):\n        self.instance_supported, helper.value = endpoints\n        """The instance supported value."""\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2,), (6,), (10,))
    assert tuple(finding.message for finding in result.unfixed_findings) == (
        "Attribute 'module_supported' documentation is too generic",
        "Attribute 'class_supported' documentation is too generic",
        "Attribute 'instance_supported' documentation is too generic",
    )


def test_suppresses_only_the_targeted_attribute_entry_or_attached_docstring() -> None:
    source = 'class Client:\n    """Client.\n\n    Attributes:\n        timeout: The timeout value.  # pydocfmt: ignore[PDF307]\n        retries: The retries value.\n    """\n\n    class_timeout = 30\n    """The class timeout value."""  # pydocfmt: ignore[PDF307]\n\n    class_retries = 3\n    """The class retries value."""\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((6,), (13,))
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Attribute 'retries' documentation is too generic", "Attribute 'class_retries' documentation is too generic")


def test_preserves_crlf_source_when_reporting_generic_attribute_documentation() -> None:
    source = 'timeout = 30\r\n"""The timeout value."""\r\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2,),)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Attribute 'timeout' documentation is too generic",)


@pytest.mark.parametrize(
    "description",
    ["Request timeout in seconds.", "Maximum number of retry attempts.", "URL used for outgoing API requests.", "Whether retries are enabled.", "Value read from the client configuration."],
)
def test_skips_attribute_documentation_with_extra_meaning(description: str) -> None:
    source = f'timeout = 30\n"""{description}"""\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_skips_attribute_documentation_without_word_tokens() -> None:
    source = 'timeout = 30\n"""!!!"""\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_skips_attribute_entries_inside_function_docstrings() -> None:
    source = 'def configure():\n    """Configure.\n\n    Attributes:\n        timeout: The timeout value.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_skips_non_attribute_entries_inside_owner_docstrings() -> None:
    source = 'class Client:\n    """Client.\n\n    Args:\n        timeout: The timeout value.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_skips_multi_target_assignments_multi_name_entries_and_multiline_attached_docstrings() -> None:
    source = 'first = second = 1\n"""Value."""\n\nclass Client:\n    """Client.\n\n    Attributes:\n        first, second: Value.\n    """\n\n    timeout = 30\n    """The timeout value.\n    Additional details.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_skips_adornment_only_attached_attribute_docstrings() -> None:
    source = 'timeout = 30\n"""===="""\n'
    result = format_source(source, settings=CheckSettings(select=("PDF307",), docstring_convention=DocstringConvention.GOOGLE, docstring_parse_headings=False))

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_attached_docstring_structure_parsing_controls_summary_targets() -> None:
    source = 'timeout = 30\n"""- timeout value"""\n'
    protected = format_source(source)
    unprotected = format_source(source, settings=CheckSettings(select=("PDF307",), docstring_convention=DocstringConvention.GOOGLE, docstring_parse_list_items=False))

    assert protected.new_source == source
    assert not protected.fixed_findings
    assert not protected.unfixed_findings
    assert tuple(finding.line_numbers for finding in unprotected.unfixed_findings) == ((2,),)
    assert tuple(finding.message for finding in unprotected.unfixed_findings) == ("Attribute 'timeout' documentation is too generic",)


def test_broad_selection_enables_google_numpy_and_rest_conventions() -> None:
    for convention in (DocstringConvention.GOOGLE, DocstringConvention.NUMPY, DocstringConvention.REST):
        selection = rules_selection.select_rules(CheckSettings(select=("PDF3",), docstring_convention=convention))

        assert "PDF307" in {rule.rule.code.tag for rule in selection.rules}


def test_exact_selection_checks_attached_attribute_docstrings_under_none_convention() -> None:
    source = 'timeout = 30\n"""The timeout value."""\n'
    broad_selection = rules_selection.select_rules(CheckSettings(select=("PDF3",), docstring_convention=DocstringConvention.NONE))
    exact = format_source(source, settings=CheckSettings(select=("PDF307",), docstring_convention=DocstringConvention.NONE))

    assert "PDF307" not in {rule.rule.code.tag for rule in broad_selection.rules}
    assert tuple(finding.message for finding in exact.unfixed_findings) == ("Attribute 'timeout' documentation is too generic",)


def test_exact_selection_under_none_convention_does_not_parse_owner_attribute_entries() -> None:
    source = '"""Module.\n\nAttributes:\n    timeout: The timeout value.\n"""\n\ntimeout = 30\n"""The timeout value."""\n'
    result = format_source(source, settings=CheckSettings(select=("PDF307",), docstring_convention=DocstringConvention.NONE))

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((8,),)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Attribute 'timeout' documentation is too generic",)


def test_check_and_fix_false_findings_agree() -> None:
    source = 'timeout = 30\n"""The timeout value."""\n'
    _, context = contexts(source)
    findings = rule_helpers.rule_findings(PDF307AttributeDocumentationTooGeneric, context)
    fixed = rule_helpers.rule_fix_result(PDF307AttributeDocumentationTooGeneric, context)
    check_only = format_source(source, fix=False)

    assert tuple(finding.line_numbers for finding in findings) == ((2,),)
    assert tuple(finding.message for finding in findings) == ("Attribute 'timeout' documentation is too generic",)
    assert fixed.module.code == source
    assert not fixed.fixed_findings
    assert tuple(finding.line_numbers for finding in check_only.unfixed_findings) == ((2,),)
