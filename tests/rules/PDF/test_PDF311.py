import pytest

import pydocformatter.formatter as formatter
import pydocformatter.rules_selection as rules_selection
import tests.rule_helpers as rule_helpers
import tests.rules.PDF.helpers as pdf_helpers
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definitions.PDF.PDF302_non_imperative_summary import PDF302NonImperativeSummary
from pydocformatter.rules.definitions.PDF.PDF311_property_docstring_starts_with_verb import PDF311PropertyDocstringStartsWithVerb

contexts = pdf_helpers.contexts_for("PDF311")
format_source = pdf_helpers.formatter_for("PDF311")


@pytest.mark.parametrize(
    "summary",
    (
        "Return the value.",
        "Returns the value.",
        "Get the value.",
        "Gets the value.",
        "Yield the value.",
        "Yields the value.",
        "Fetch the value.",
        "Fetches the value.",
        "Retrieve the value.",
        "Retrieves the value.",
    ),
)
def test_reports_property_docstrings_that_start_with_disallowed_verbs(summary: str) -> None:
    source = f'class Example:\n    @property\n    def value(self):\n        """{summary}"""\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((4,),)
    assert tuple(finding.message for finding in result.unfixed_findings) == (f'Property docstring should not start with a verb ("{summary.split()[0]}")',)
    assert not result.unfixed_findings[0].fixable
    assert PDF311PropertyDocstringStartsWithVerb.meta.name == "property-docstring-starts-with-verb"


@pytest.mark.parametrize("summary", ("return the value.", "RETURN the value.", '"Returns" the value.', "(returns) the value.", "Returns: the value."))
def test_verb_detection_is_case_insensitive_after_normalization(summary: str) -> None:
    source = f'class Example:\n    @property\n    def value(self):\n        """{summary}"""\n'
    result = format_source(source)

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((4,),)


@pytest.mark.parametrize("summary", ("The value.", "Computed value.", "Use the value.", "Getter value.", "ReturnValue object."))
def test_accepts_property_docstrings_with_other_first_words(summary: str) -> None:
    source = f'class Example:\n    @property\n    def value(self):\n        """{summary}"""\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.unfixed_findings


def test_applies_only_to_property_functions_and_skips_tests() -> None:
    source = '"""Returns module value."""\n\nclass Example:\n    """Returns class value."""\n\n    value = 1\n    """Returns attribute value."""\n\n    @property\n    def test_value(self):\n        """Returns test value."""\n\n    @property\n    def runTest(self):\n        """Returns unittest value."""\n\n    def value(self):\n        """Returns method value."""\n\n    @property\n    def current(self):\n        """Returns current value."""\n'
    result = format_source(source)

    assert result.new_source == source
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((22,),)


@pytest.mark.parametrize(
    "decorator",
    (
        "property",
        "builtins.property",
        "enum.property",
        "functools.cached_property",
        "functools.cached_property()",
        "abc.abstractproperty",
        "types.DynamicClassAttribute",
        "types.DynamicClassAttribute()",
    ),
)
def test_reports_default_property_decorators(decorator: str) -> None:
    source = f'class Example:\n    @{decorator}\n    def value(self):\n        """Returns property value."""\n'
    result = format_source(source)

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((4,),)


@pytest.mark.parametrize("decorator", ("value.getter", "value.setter", "value.deleter"))
def test_reports_property_accessor_decorators(decorator: str) -> None:
    source = f'class Example:\n    @{decorator}\n    def value(self):\n        """Returns property accessor value."""\n'
    result = format_source(source)

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((4,),)


def test_reports_import_alias_property_decorators() -> None:
    source = 'from functools import cached_property as cp\n\n\nclass Example:\n    @cp\n    def value(self):\n        """Returns cached value."""\n'
    result = format_source(source)

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((7,),)


def test_reports_called_import_alias_property_decorators() -> None:
    source = 'from functools import cached_property as cp\nfrom project import Property as P\n\n\nclass Example:\n    @cp()\n    def cached(self):\n        """Returns cached value."""\n\n    @P(read_only=True)\n    def custom(self):\n        """Returns custom value."""\n'
    result = format_source(source, settings=CheckSettings(select=("PDF311",), docstring_property_decorators=("builtins.property", "functools.cached_property", "project.Property")))

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((8,), (12,))


def test_shadowed_dotted_property_decorator_is_not_treated_as_configured_property() -> None:
    source = 'class Builtins:\n    property = object()\n\nbuiltins = Builtins()\n\n\nclass Example:\n    @builtins.property\n    def value(self):\n        """Returns property value."""\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.unfixed_findings


def test_property_decorator_setting_replaces_exact_property_decorator_names() -> None:
    source = (
        'class Example:\n    @property\n    def value(self):\n        """Returns property value."""\n\n    @project.Property\n    def custom(self):\n        """Returns custom property value."""\n'
    )
    result = format_source(source, settings=CheckSettings(select=("PDF311",), docstring_property_decorators=("project.Property",)))

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((8,),)


def test_empty_property_decorator_setting_keeps_accessors_but_disables_exact_decorators() -> None:
    source = 'class Example:\n    @property\n    def value(self):\n        """Returns property value."""\n\n    @functools.cached_property()\n    def cached(self):\n        """Returns cached value."""\n\n    @value.getter\n    def value(self):\n        """Returns accessor value."""\n'
    result = format_source(source, settings=CheckSettings(select=("PDF311",), docstring_property_decorators=()))

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((12,),)


def test_configured_property_decorator_calls_with_arguments_and_mixed_decorators_report() -> None:
    source = 'class Example:\n    @decorators.trace\n    @project.Property(read_only=True)\n    def first(self):\n        """Returns first value."""\n\n    @project.Wrapper\n    @decorators[0]\n    def second(self):\n        """Returns second value."""\n'
    result = format_source(source, settings=CheckSettings(select=("PDF311",), docstring_property_decorators=("project.Property",)))

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((5,),)


def test_static_but_non_exact_property_decorator_names_do_not_report() -> None:
    source = 'class Example:\n    @project.property\n    def first(self):\n        """Returns first value."""\n\n    @project.property()\n    def second(self):\n        """Returns second value."""\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.unfixed_findings


def test_complex_non_property_decorators_do_not_report() -> None:
    source = 'class Example:\n    @decorators[0]\n    def first(self):\n        """Returns first value."""\n\n    @decorators[0].property\n    def second(self):\n        """Returns second value."""\n\n    @setter\n    def third(self):\n        """Returns third value."""\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.unfixed_findings


def test_reports_async_and_nested_property_summaries() -> None:
    source = 'class Example:\n    @property\n    async def async_value(self):\n        """Returns async value."""\n\n    def outer(self):\n        @property\n        def nested():\n            """Returns nested value."""\n'
    result = format_source(source)

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((4,), (9,))


def test_protected_structures_and_heading_setting_control_summary_status() -> None:
    source = 'class Example:\n    @property\n    def heading(self):\n        """Returns\n        =======\n        """\n'
    protected = format_source(source)
    disabled = format_source(source, settings=CheckSettings(select=("PDF311",), docstring_parse_headings=False))

    assert not protected.unfixed_findings
    assert tuple(finding.line_numbers for finding in disabled.unfixed_findings) == ((4,),)


def test_rest_field_syntax_is_protected_only_under_rest_convention() -> None:
    source = 'class Example:\n    @property\n    def value(self):\n        """:returns: value"""\n'
    rest = format_source(source, settings=CheckSettings(select=("PDF311",), docstring_convention=DocstringConvention.REST))
    none = format_source(source, settings=CheckSettings(select=("PDF311",), docstring_convention=DocstringConvention.NONE))

    assert not rest.unfixed_findings
    assert tuple(finding.line_numbers for finding in none.unfixed_findings) == ((4,),)


def test_leading_blank_and_adornment_lines_are_not_summary_word_targets() -> None:
    source = 'class Example:\n    @property\n    def value(self):\n        """\n        ====\n        Returns value.\n        """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF311",), docstring_parse_headings=False))

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((6,),)


def test_reports_concatenated_and_escaped_newline_physical_lines() -> None:
    source = 'class Example:\n    @property\n    def concatenated(self):\n        ("Returns "\n         "value.")\n\n    @property\n    def escaped(self):\n        """Returns value\\ncontinued."""\n'
    result = format_source(source)

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((4, 5), (9,))


def test_combined_pdf302_and_pdf311_selection_keeps_property_and_method_findings_separate() -> None:
    source = 'class Example:\n    @property\n    def value(self):\n        """Returns property value."""\n\n    def calculate(self):\n        """Returns method value."""\n'
    settings = CheckSettings(select=("PDF302", "PDF311"))
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)

    assert {(finding.rule, finding.line_numbers) for finding in result.unfixed_findings} == {
        (PDF302NonImperativeSummary.meta, (7,)),
        (PDF311PropertyDocstringStartsWithVerb.meta, (4,)),
    }


def test_check_and_fix_false_findings_agree() -> None:
    source = 'class Example:\n    @property\n    def value(self):\n        """Returns value."""\n'
    _, context = contexts(source)
    findings = rule_helpers.rule_findings(PDF311PropertyDocstringStartsWithVerb, context)
    fixed = rule_helpers.rule_fix_result(PDF311PropertyDocstringStartsWithVerb, context)
    check_only = format_source(source, fix=False)

    assert tuple(finding.line_numbers for finding in findings) == ((4,),)
    assert fixed.module.code == source
    assert not fixed.fixed_findings
    assert tuple(finding.line_numbers for finding in check_only.unfixed_findings) == ((4,),)
