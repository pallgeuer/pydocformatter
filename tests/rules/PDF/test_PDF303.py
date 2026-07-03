import libcst as cst
import libcst.metadata as cst_metadata
import pytest

import pydocformatter.formatter as formatter
import pydocformatter.rules.definition_helpers.source_text as source_text
import pydocformatter.rules_selection as rules_selection
import tests.rule_helpers as rule_helpers
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definition import RuleCategoryContext, RuleContext
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.definitions.PDF.PDF303_signature_like_summary import PDF303SignatureLikeSummary


def contexts(source: str, *, settings: CheckSettings | None = None) -> tuple[RuleCategoryContext, RuleContext]:
    """Return matching category and rule contexts for source."""
    module = cst.parse_module(source)
    wrapper = cst_metadata.MetadataWrapper(module, unsafe_skip_copy=True)
    category = RuleCategoryContext(
        path="example.py",
        settings=CheckSettings(select=("PDF303",)) if settings is None else settings,
        module=module,
        metadata_wrapper=wrapper,
        positions=wrapper.resolve(cst_metadata.PositionProvider),
        line_ending="\r\n" if "\r\n" in source else "\n",
        source=source,
        source_lines=tuple(source_text.source_lines(source)),
        line_bounds=None,
    )
    return category, RuleContext(
        path=category.path,
        settings=category.settings,
        module=category.module,
        metadata_wrapper=category.metadata_wrapper,
        positions=category.positions,
        line_ending=category.line_ending,
        source=category.source,
        source_lines=category.source_lines,
        line_bounds=category.line_bounds,
        category_data=PDF.prepare(category),
    )


def format_source(source: str, *, settings: CheckSettings | None = None, fix: bool = True) -> formatter.FormatterResult:
    """Format source with supplied settings."""
    resolved_settings = CheckSettings(select=("PDF303",)) if settings is None else settings
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=fix)


@pytest.mark.parametrize("summary", ("function(value) -> str", "Return; function(value)", "Return, function(value)", "Return\tfunction(value)"))
def test_reports_function_signature_summaries(summary: str) -> None:
    source = f'def function(value):\n    """{summary}"""\n'
    result = format_source(source)

    assert result.new_source == source
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2,),)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring summary should not include a function signature",)
    assert not result.unfixed_findings[0].fixable


@pytest.mark.parametrize("summary", ("__call__(value)", "Return function()", "Return function(value, *, option=True)"))
def test_reports_dunder_empty_and_keyword_signature_shapes(summary: str) -> None:
    source = f'def __call__(value):\n    """{summary}"""\n' if summary.startswith("__call__") else f'def function(value, *, option=True):\n    """{summary}"""\n'
    result = format_source(source)

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2,),)


@pytest.mark.parametrize("summary", ("myfunction(value)", "module.function(value)", "function (value)", "Return value."))
def test_does_not_report_non_signature_summaries(summary: str) -> None:
    source = f'def function(value):\n    """{summary}"""\n'
    result = format_source(source)

    assert not result.unfixed_findings


@pytest.mark.parametrize("summary", ("FUNCTION(value)", "Return:function(value)", "Return=function(value)"))
def test_does_not_report_case_mismatches_or_unsupported_signature_boundaries(summary: str) -> None:
    source = f'def function(value):\n    """{summary}"""\n'
    result = format_source(source)

    assert not result.unfixed_findings


def test_checks_only_first_summary_line() -> None:
    source = 'def function(value):\n    """Return value.\n    function(value)\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.unfixed_findings


def test_applies_only_to_functions_and_respects_summary_parsing() -> None:
    source = '"""module(value)"""\n\nclass module:\n    """module(value)"""\n\n\ndef field():\n    """:return: field(value)"""\n\n\ndef function(value):\n    """function(value)"""\n'
    result = format_source(source, settings=CheckSettings(select=("PDF303",), docstring_convention=DocstringConvention.REST))

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((12,),)


def test_ignores_attribute_docstrings() -> None:
    source = 'module_value = 1\n"""module_value(value)"""\n\nclass Example:\n    class_value = 1\n    """class_value(value)"""\n\n    def __init__(self):\n        self.instance_value = 1\n        """instance_value(value)"""\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.unfixed_findings


def test_leading_blank_lines_do_not_hide_signature_like_summary() -> None:
    source = 'def function(value):\n    """\n    function(value)\n    """\n'
    result = format_source(source)

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((3,),)


def test_numpy_convention_ignores_broad_selection_but_exact_selection_still_applies() -> None:
    broad = rules_selection.select_rules(CheckSettings(select=("PDF3",), docstring_convention=DocstringConvention.NUMPY))
    active_codes = tuple(rule.rule.code.tag for rule in broad.rules)

    assert "PDF303" not in active_codes

    exact = format_source('def function(value):\n    """function(value)"""\n', settings=CheckSettings(select=("PDF303",), docstring_convention=DocstringConvention.NUMPY))

    assert tuple(finding.line_numbers for finding in exact.unfixed_findings) == ((2,),)


def test_check_and_fix_false_findings_agree() -> None:
    source = 'def function(value):\n    """function(value)"""\n'
    _, context = contexts(source)
    findings = rule_helpers.rule_findings(PDF303SignatureLikeSummary, context)
    fixed = rule_helpers.rule_fix_result(PDF303SignatureLikeSummary, context)
    check_only = format_source(source, fix=False)

    assert tuple(finding.line_numbers for finding in findings) == ((2,),)
    assert fixed.module.code == source
    assert not fixed.fixed_findings
    assert tuple(finding.line_numbers for finding in check_only.unfixed_findings) == ((2,),)
