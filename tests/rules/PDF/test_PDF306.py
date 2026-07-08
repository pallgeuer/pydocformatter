# Third-party imports
import pytest

# First-party imports
import tests.rules.PDF.helpers as pdf_helpers
from pydocformatter import rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definitions.PDF.PDF306_parameter_documentation_too_generic import PDF306ParameterDocumentationTooGeneric
from tests import rule_helpers


contexts = pdf_helpers.contexts_for("PDF306")
format_source = pdf_helpers.formatter_for("PDF306")


@pytest.mark.parametrize(
    ("description", "parameter"),
    [
        ("timeout", "timeout"),
        ("The timeout.", "timeout"),
        ("The timeout value.", "timeout"),
        ("timeout parameter", "timeout"),
        ("timeout argument", "timeout"),
        ("value of timeout", "timeout"),
        ("The value of timeout.", "timeout"),
        ("The parameter timeout.", "timeout"),
        ("The argument timeout.", "timeout"),
        ("`timeout` parameter.", "timeout"),
        ('"timeout" argument.', "timeout"),
        ("max_retries value", "max_retries"),
        ("max retries value", "max_retries"),
        ("API2 token value", "api2_token"),
        ("args value", "*args"),
        ("kwargs parameter", "**kwargs"),
    ],
)
def test_reports_google_parameter_documentation_that_only_restates_parameter_name(description: str, parameter: str) -> None:
    source = f'def connect({parameter.lstrip("*")}):\n    """Connect.\n\n    Args:\n        {parameter}: {description}\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((5,),)
    assert tuple(finding.message for finding in result.unfixed_findings) == (f"Parameter '{parameter}' documentation is too generic",)
    assert not result.unfixed_findings[0].fixable


def test_reports_numpy_and_rest_parameter_entries() -> None:
    numpy_source = 'def connect(timeout):\n    """Connect.\n\n    Parameters\n    ----------\n    timeout : int\n        The timeout value.\n    """\n'
    rest_source = 'def connect(timeout):\n    """Connect.\n\n    :param timeout: The timeout value.\n    """\n'

    numpy = format_source(numpy_source, settings=CheckSettings(select=("PDF306",), docstring_convention=DocstringConvention.NUMPY))
    rest = format_source(rest_source, settings=CheckSettings(select=("PDF306",), docstring_convention=DocstringConvention.REST))

    assert tuple(finding.message for finding in numpy.unfixed_findings) == ("Parameter 'timeout' documentation is too generic",)
    assert tuple(finding.line_numbers for finding in numpy.unfixed_findings) == ((6,),)
    assert tuple(finding.message for finding in rest.unfixed_findings) == ("Parameter 'timeout' documentation is too generic",)
    assert tuple(finding.line_numbers for finding in rest.unfixed_findings) == ((4,),)


def test_reports_rest_parameter_field_aliases() -> None:
    source = 'def connect(timeout, token, retries):\n    """Connect.\n\n    :arg timeout: The timeout value.\n    :keyword token: The token value.\n    :kwarg retries: Maximum number of retry attempts.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF306",), docstring_convention=DocstringConvention.REST))

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((4,), (5,))
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Parameter 'timeout' documentation is too generic", "Parameter 'token' documentation is too generic")


def test_reports_google_variadic_argument_phrases_for_signature_backed_parameters() -> None:
    source = 'def collect(*values, **options):\n    """Collect.\n\n    Args:\n        values: The additional positional arguments.\n        **options: Extra keyword args.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((5,), (6,))
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Parameter 'values' documentation is too generic", "Parameter '**options' documentation is too generic")


def test_reports_numpy_variadic_argument_phrases() -> None:
    source = 'def collect(*args, **kwargs):\n    """Collect.\n\n    Parameters\n    ----------\n    args : tuple[object, ...]\n        Positional arguments.\n    kwargs : dict[str, object]\n        Additional keyword arguments.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF306",), docstring_convention=DocstringConvention.NUMPY))

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((6,), (8,))
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Parameter 'args' documentation is too generic", "Parameter 'kwargs' documentation is too generic")


def test_reports_rest_variadic_argument_phrases() -> None:
    source = 'def collect(*args, **kwargs):\n    """Collect.\n\n    :param *args: Extra positional args.\n    :kwarg **kwargs: The keyword arguments.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF306",), docstring_convention=DocstringConvention.REST))

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((4,), (5,))
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Parameter '*args' documentation is too generic", "Parameter '**kwargs' documentation is too generic")


def test_reports_bare_arguments_for_positional_and_keyword_variadic_parameters() -> None:
    source = 'def collect(*args, **kwargs):\n    """Collect.\n\n    Args:\n        args: Arguments.\n        kwargs: The additional arguments.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((5,), (6,))
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Parameter 'args' documentation is too generic", "Parameter 'kwargs' documentation is too generic")


def test_reports_variadic_argument_phrases_for_unpack_kwargs_entry() -> None:
    source = 'def collect(**kwargs: Unpack[Options]):\n    """Collect.\n\n    Args:\n        kwargs: Additional keyword arguments.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((5,),)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Parameter 'kwargs' documentation is too generic",)


def test_skips_variadic_argument_phrases_for_regular_parameters_and_wrong_variadic_kind() -> None:
    source = 'def collect(args, kwargs, *values, **options):\n    """Collect.\n\n    Args:\n        args: Arguments.\n        kwargs: Keyword arguments.\n        values: Keyword arguments.\n        options: Positional arguments.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_reports_generic_parameter_documentation_split_across_continuation_lines() -> None:
    source = 'def connect(timeout):\n    """Connect.\n\n    Args:\n        timeout:\n            The timeout\n            value.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((5,),)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Parameter 'timeout' documentation is too generic",)


def test_reports_only_generic_parameters_in_mixed_google_docstring() -> None:
    source = 'def connect(timeout, retries, base_url):\n    """Connect.\n\n    Args:\n        timeout: The timeout value.\n        retries: Maximum number of retry attempts.\n        base_url:\n            The base url\n            value.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((5,), (7,))
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Parameter 'timeout' documentation is too generic", "Parameter 'base_url' documentation is too generic")


def test_suppresses_only_the_targeted_parameter_entry() -> None:
    source = 'def connect(timeout, retries):\n    """Connect.\n\n    Args:\n        timeout: The timeout value.  # pydocfmt: ignore[PDF306]\n        retries: The retries value.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((6,),)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Parameter 'retries' documentation is too generic",)


def test_preserves_crlf_source_when_reporting_generic_parameter_documentation() -> None:
    source = 'def connect(timeout):\r\n    """Connect.\r\n\r\n    Args:\r\n        timeout: The timeout value.\r\n    """\r\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((5,),)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Parameter 'timeout' documentation is too generic",)


@pytest.mark.parametrize(
    "description",
    ["Request timeout in seconds.", "Maximum number of retry attempts.", "URL used for outgoing API requests.", "Whether retries are enabled.", "Value read from the client configuration."],
)
def test_skips_parameter_documentation_with_extra_meaning(description: str) -> None:
    source = f'def connect(timeout):\n    """Connect.\n\n    Args:\n        timeout: {description}\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_skips_parameter_documentation_without_word_tokens() -> None:
    source = 'def connect(timeout):\n    """Connect.\n\n    Args:\n        timeout: !!!\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_skips_parameter_entries_outside_function_docstrings() -> None:
    source = 'class Client:\n    """Client.\n\n    Args:\n        timeout: The timeout value.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_skips_multi_name_entries_and_type_only_rest_fields() -> None:
    source = 'def connect(first, second, timeout):\n    """Connect.\n\n    Parameters\n    ----------\n    first, second : int\n        Value.\n\n    :type timeout: Timeout\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF306",), docstring_convention=DocstringConvention.NUMPY))
    rest = format_source(source, settings=CheckSettings(select=("PDF306",), docstring_convention=DocstringConvention.REST))

    assert not result.unfixed_findings
    assert not rest.unfixed_findings


def test_skips_multi_name_numpy_entries_without_skipping_single_name_entries() -> None:
    source = (
        'def connect(first, second, timeout):\n    """Connect.\n\n    Parameters\n    ----------\n    first, second : int\n        Value.\n    timeout : float\n        The timeout value.\n    """\n'
    )
    result = format_source(source, settings=CheckSettings(select=("PDF306",), docstring_convention=DocstringConvention.NUMPY))

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((8,),)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Parameter 'timeout' documentation is too generic",)


def test_broad_selection_enables_google_numpy_and_rest_conventions() -> None:
    for convention in (DocstringConvention.GOOGLE, DocstringConvention.NUMPY, DocstringConvention.REST):
        selection = rules_selection.select_rules(CheckSettings(select=("PDF3",), docstring_convention=convention))

        assert "PDF306" in {rule.rule.code.tag for rule in selection.rules}


def test_broad_selection_ignores_none_and_pep257_conventions() -> None:
    source = 'def connect(timeout):\n    """Connect.\n\n    Args:\n        timeout: The timeout value.\n    """\n'
    none_selection = rules_selection.select_rules(CheckSettings(select=("PDF3",), docstring_convention=DocstringConvention.NONE))
    pep257_selection = rules_selection.select_rules(CheckSettings(select=("PDF3",), docstring_convention=DocstringConvention.PEP257))

    assert "PDF306" not in {rule.rule.code.tag for rule in none_selection.rules}
    assert "PDF306" not in {rule.rule.code.tag for rule in pep257_selection.rules}
    assert not format_source(source, settings=CheckSettings(select=("PDF306",), docstring_convention=DocstringConvention.NONE)).unfixed_findings


def test_check_and_fix_false_findings_agree() -> None:
    source = 'def connect(timeout):\n    """Connect.\n\n    Args:\n        timeout: The timeout value.\n    """\n'
    _, context = contexts(source)
    findings = rule_helpers.rule_findings(PDF306ParameterDocumentationTooGeneric, context)
    fixed = rule_helpers.rule_fix_result(PDF306ParameterDocumentationTooGeneric, context)
    check_only = format_source(source, fix=False)

    assert tuple(finding.line_numbers for finding in findings) == ((5,),)
    assert tuple(finding.message for finding in findings) == ("Parameter 'timeout' documentation is too generic",)
    assert fixed.module.code == source
    assert not fixed.fixed_findings
    assert tuple(finding.line_numbers for finding in check_only.unfixed_findings) == ((5,),)
