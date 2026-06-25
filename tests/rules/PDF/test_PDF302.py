import libcst as cst
import libcst.metadata as cst_metadata
import pytest

import pydocformatter.formatter as formatter
import pydocformatter.rules.definition_helpers.source_text as source_text
import pydocformatter.rules_selection as rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definition import RuleCategoryContext, RuleContext
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.definitions.PDF.PDF302_non_imperative_summary import PDF302NonImperativeSummary


def contexts(source: str, *, settings: CheckSettings | None = None) -> tuple[RuleCategoryContext, RuleContext]:
    """Return matching category and rule contexts for source."""
    module = cst.parse_module(source)
    wrapper = cst_metadata.MetadataWrapper(module, unsafe_skip_copy=True)
    category = RuleCategoryContext(
        path="example.py",
        settings=CheckSettings(select=("PDF302",)) if settings is None else settings,
        module=module,
        metadata_wrapper=wrapper,
        positions=wrapper.resolve(cst_metadata.PositionProvider),
        line_ending="\r\n" if "\r\n" in source else "\n",
        source=source,
        source_lines=tuple(source_text.source_lines(source)),
    )
    return category, RuleContext(**category.__dict__, category_data=PDF.prepare(category), effectively_fixable=False)


def format_source(source: str, *, settings: CheckSettings | None = None, fix: bool = True) -> formatter.FormatterResult:
    """Format source with supplied settings."""
    resolved_settings = CheckSettings(select=("PDF302",)) if settings is None else settings
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=fix)


@pytest.mark.parametrize("summary", ("Returns the value.", "Calculates the value.", "Does the work.", "Has the value.", "This returns the value."))
def test_reports_non_imperative_function_summaries(summary: str) -> None:
    source = f'def function():\n    """{summary}"""\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2,),)
    assert tuple(finding.message for finding in result.unfixed_findings) == (f"Docstring summary first word '{summary.split()[0]}' is not imperative",)
    assert not result.unfixed_findings[0].fixable


@pytest.mark.parametrize("summary", ("returns the value.", "RETURNS the value.", "'returns' the value."))
def test_non_imperative_detection_is_case_insensitive_after_normalization(summary: str) -> None:
    source = f'def function():\n    """{summary}"""\n'
    result = format_source(source)

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2,),)


@pytest.mark.parametrize("summary", ("Return the value.", "Compute the value.", "Widget object."))
def test_accepts_imperative_or_unknown_function_summaries(summary: str) -> None:
    source = f'def function():\n    """{summary}"""\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.unfixed_findings


@pytest.mark.parametrize("summary", ("Trys invalid form.", "Processs invalid form."))
def test_accepts_invalid_synthetic_third_person_forms(summary: str) -> None:
    source = f'def function():\n    """{summary}"""\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.unfixed_findings


def test_applies_only_to_functions_and_skips_tests_and_properties() -> None:
    source = '"""Returns module value."""\n\nclass Example:\n    """Returns class value."""\n\n    @property\n    def value(self):\n        """Returns property value."""\n\n    @functools.cached_property()\n    def cached(self):\n        """Returns cached value."""\n\n    def test_value(self):\n        """Returns test value."""\n\n    def runTest(self):\n        """Returns test value."""\n\n    def value(self):\n        """Returns value."""\n'
    result = format_source(source)

    assert result.new_source == source
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((21,),)


def test_ignores_attribute_docstrings() -> None:
    source = 'module_value = 1\n"""Returns module value."""\n\nclass Example:\n    class_value = 1\n    """Returns class value."""\n\n    def __init__(self):\n        self.instance_value = 1\n        """Returns instance value."""\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.unfixed_findings


@pytest.mark.parametrize(
    "decorator",
    (
        "builtins.property",
        "enum.property",
        "abc.abstractproperty",
        "types.DynamicClassAttribute",
        "types.DynamicClassAttribute()",
    ),
)
def test_skips_qualified_property_like_decorators(decorator: str) -> None:
    source = f'class Example:\n    @{decorator}\n    def value(self):\n        """Returns property value."""\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.unfixed_findings


@pytest.mark.parametrize("decorator", ("value.getter", "value.setter", "value.deleter"))
def test_skips_property_accessor_decorators(decorator: str) -> None:
    source = f'class Example:\n    @{decorator}\n    def value(self):\n        """Returns property accessor value."""\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.unfixed_findings


def test_complex_non_property_decorators_do_not_suppress_findings() -> None:
    source = 'class Example:\n    @decorators[0]\n    def first(self):\n        """Returns first value."""\n\n    @decorators[0].property\n    def second(self):\n        """Returns second value."""\n\n    @setter\n    def third(self):\n        """Returns third value."""\n'
    result = format_source(source)

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((4,), (8,), (12,))


def test_protected_structures_and_heading_setting_control_summary_status() -> None:
    source = 'def heading():\n    """Returns\n    =======\n    """\n\n\ndef field():\n    """:return: value"""\n'
    protected = format_source(source)
    disabled = format_source(source, settings=CheckSettings(select=("PDF302",), docstring_parse_headings=False))

    assert not protected.unfixed_findings
    assert tuple(finding.line_numbers for finding in disabled.unfixed_findings) == ((2,),)


def test_leading_blank_and_adornment_lines_are_not_summary_word_targets() -> None:
    source = 'def function():\n    """\n    ====\n    Returns value.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF302",), docstring_parse_headings=False))

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((4,),)


def test_skips_summary_without_a_whitespace_delimited_first_word() -> None:
    source = 'def function():\n    """\\u00a0"""\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.unfixed_findings


@pytest.mark.parametrize("summary", ('"Returns" the value.', "(Returns) the value.", "Returns: the value."))
def test_normalizes_first_word_punctuation_before_mood_check(summary: str) -> None:
    source = f'def function():\n    """{summary}"""\n'
    result = format_source(source)

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2,),)


def test_reports_concatenated_and_escaped_newline_physical_lines() -> None:
    source = 'def concatenated():\n    ("Returns "\n     "value.")\n\n\ndef escaped():\n    """Returns value\\ncontinued."""\n'
    result = format_source(source)

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2, 3), (7,))


def test_reports_async_and_nested_function_summaries() -> None:
    source = 'async def outer():\n    """Returns outer value."""\n\n    def inner():\n        """Returns inner value."""\n'
    result = format_source(source)

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2,), (5,))


def test_google_convention_ignores_broad_selection_but_exact_selection_still_applies() -> None:
    broad = rules_selection.select_rules(CheckSettings(select=("PDF3",), docstring_convention=DocstringConvention.GOOGLE))
    active_codes = tuple(rule.rule.code.tag for rule in broad.rules)

    assert "PDF302" not in active_codes

    exact = format_source('def function():\n    """Returns value."""\n', settings=CheckSettings(select=("PDF302",), docstring_convention=DocstringConvention.GOOGLE))

    assert tuple(finding.line_numbers for finding in exact.unfixed_findings) == ((2,),)


def test_check_and_fix_false_findings_agree() -> None:
    source = 'def function():\n    """Returns value."""\n'
    _, context = contexts(source)
    findings = PDF302NonImperativeSummary.check(context)
    fixed = PDF302NonImperativeSummary.fix(context)
    check_only = format_source(source, fix=False)

    assert tuple(finding.line_numbers for finding in findings) == ((2,),)
    assert fixed.module.code == source
    assert not fixed.fixed_findings
    assert tuple(finding.line_numbers for finding in check_only.unfixed_findings) == ((2,),)
