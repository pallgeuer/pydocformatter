# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# Third-party imports
import pytest

# First-party imports
from pydocformatter import formatter, rules_selection
from pydocformatter.cli.settings_check import CheckSettings, LineEnding
from pydocformatter.rules.definitions.PDF.PDF import PDF, DocstringKind
from pydocformatter.rules.definitions.PDF.PDF000_docstring_literal_normalization import PDF000DocstringLiteralNormalization
from tests import rule_helpers


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.definition import RuleCategoryContext, RuleContext


def contexts(source: str) -> tuple[RuleCategoryContext, RuleContext]:
    """Return matching category and rule contexts for source."""
    resolved_settings = CheckSettings()
    return rule_helpers.prepared_direct_rule_contexts(PDF, source, settings=resolved_settings)


def format_pdf000(source: str, *, settings: CheckSettings | None = None, fix: bool = True) -> formatter.FormatterResult:
    """Format source with PDF000 selected."""
    resolved_settings = CheckSettings(select=("PDF000",)) if settings is None else settings
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=fix)


def test_check_and_fix_concatenated_docstring() -> None:
    _, context = contexts('def function():\n    ("first " "second")\n')
    findings = rule_helpers.rule_findings(PDF000DocstringLiteralNormalization, context)
    result = rule_helpers.rule_fix_result(PDF000DocstringLiteralNormalization, context)
    assert len(findings) == 1
    assert findings[0].line_numbers == (2,)
    assert result.module.code == 'def function():\n    ("""first second""")\n'
    fixed_category, _ = contexts(result.module.code)
    prepared = PDF.prepare(fixed_category)
    assert prepared.docstrings[0].kind == DocstringKind.SIMPLE
    assert prepared.docstrings[0].value == "first second"


def test_fix_literalizes_normal_whitespace_escapes_in_simple_docstring() -> None:
    _, context = contexts('def function():\n    """first\\n\\tsecond"""\n')

    findings = rule_helpers.rule_findings(PDF000DocstringLiteralNormalization, context)
    result = rule_helpers.rule_fix_result(PDF000DocstringLiteralNormalization, context)

    assert tuple(finding.line_numbers for finding in findings) == ((2,),)
    assert result.module.code == 'def function():\n    """first\n\tsecond"""\n'
    _, fixed_context = contexts(result.module.code)
    fixed = PDF.require_data(fixed_context).docstrings[0]
    assert fixed.kind == DocstringKind.SIMPLE
    assert fixed.value == "first\n\tsecond"
    assert rule_helpers.rule_findings(PDF000DocstringLiteralNormalization, fixed_context) == ()


@pytest.mark.parametrize("prefix", ["u", "U"])
def test_fix_removes_plain_unicode_prefix_from_simple_docstring(prefix: str) -> None:
    source = f'def function():\n    {prefix}"""simple doc"""\n'

    result = format_pdf000(source)

    assert result.fixed_findings[PDF000DocstringLiteralNormalization.meta] == 1
    assert result.new_source == 'def function():\n    """simple doc"""\n'
    assert not format_pdf000(result.new_source).modified
    _, fixed_context = contexts(result.new_source)
    assert PDF.require_data(fixed_context).docstrings[0].value == "simple doc"


def test_fix_removes_unicode_prefix_while_literalizing_whitespace_escapes() -> None:
    source = 'def function():\n    u"""first\\n\\tsecond"""\n'

    result = format_pdf000(source)

    assert result.fixed_findings[PDF000DocstringLiteralNormalization.meta] == 1
    assert result.new_source == 'def function():\n    """first\n\tsecond"""\n'
    _, fixed_context = contexts(result.new_source)
    assert PDF.require_data(fixed_context).docstrings[0].value == "first\n\tsecond"


def test_fix_requotes_simple_single_quoted_docstring_when_literalizing_newline() -> None:
    _, context = contexts('def function():\n    "first\\n\\tsecond"\n')

    result = rule_helpers.rule_fix_result(PDF000DocstringLiteralNormalization, context)

    assert result.module.code == 'def function():\n    """first\n\tsecond"""\n'
    _, fixed_context = contexts(result.module.code)
    assert PDF.require_data(fixed_context).docstrings[0].value == "first\n\tsecond"


def test_fix_requotes_simple_docstring_with_target_delimiter_in_one_pass() -> None:
    source = 'def function():\n    \'first\\n\\tcontains """ delimiter\'\n'

    result = format_pdf000(source)

    assert result.fixed_findings[PDF000DocstringLiteralNormalization.meta] == 1
    assert result.new_source == 'def function():\n    """first\n\tcontains \\"\\"\\" delimiter"""\n'
    assert not format_pdf000(result.new_source).modified
    _, fixed_context = contexts(result.new_source)
    assert PDF.require_data(fixed_context).docstrings[0].value == 'first\n\tcontains """ delimiter'


def test_fix_literalizes_simple_docstring_newline_in_single_line_suite() -> None:
    _, context = contexts('def function(): "first\\nsecond"; return 1\n')

    result = rule_helpers.rule_fix_result(PDF000DocstringLiteralNormalization, context)

    assert tuple(finding.line_numbers for finding in result.fixed_findings) == ((1,),)
    assert result.module.code == 'def function(): """first\nsecond"""; return 1\n'
    _, fixed_context = contexts(result.module.code)
    assert PDF.require_data(fixed_context).docstrings[0].value == "first\nsecond"


def test_fix_literalizes_normal_whitespace_escapes_in_concatenated_docstring() -> None:
    _, context = contexts('def function():\n    ("first\\n" "\\tsecond")\n')

    result = rule_helpers.rule_fix_result(PDF000DocstringLiteralNormalization, context)

    assert result.module.code == 'def function():\n    ("""first\n\tsecond""")\n'
    _, fixed_context = contexts(result.module.code)
    fixed = PDF.require_data(fixed_context).docstrings[0]
    assert fixed.kind == DocstringKind.SIMPLE
    assert fixed.value == "first\n\tsecond"


def test_fix_uses_configured_line_ending_for_literalized_newline() -> None:
    source = 'def function():\n    """first\\nsecond"""\n'
    settings = CheckSettings(select=("PDF000",), line_ending=LineEnding.CR_LF)

    result = format_pdf000(source, settings=settings)

    assert result.new_source == 'def function():\n    """first\r\nsecond"""\n'
    _, fixed_context = contexts(result.new_source)
    assert PDF.require_data(fixed_context).docstrings[0].value == "first\nsecond"


def test_fix_leaves_carriage_return_newline_escape_split_across_components_unchanged() -> None:
    _, context = contexts('def function():\n    ("first\\r" "\\nsecond")\n')

    result = rule_helpers.rule_fix_result(PDF000DocstringLiteralNormalization, context)

    assert result.module.code == 'def function():\n    ("""first\\r\\nsecond""")\n'
    _, fixed_context = contexts(result.module.code)
    assert PDF.require_data(fixed_context).docstrings[0].value == "first\r\nsecond"
    assert rule_helpers.rule_findings(PDF000DocstringLiteralNormalization, fixed_context) == ()


def test_fix_preserves_complex_evaluated_values() -> None:
    source = 'def function():\n    (r"backslash\\n" "\\nquotes: \\"\\"\\"" "\\x00")\n'
    _, context = contexts(source)
    original = PDF.require_data(context).docstrings[0].value
    result = rule_helpers.rule_fix_result(PDF000DocstringLiteralNormalization, context)
    _, fixed_context = contexts(result.module.code)
    fixed = PDF.require_data(fixed_context).docstrings[0]
    assert fixed.kind == DocstringKind.SIMPLE
    assert fixed.value == original
    assert rule_helpers.rule_findings(PDF000DocstringLiteralNormalization, fixed_context) == ()


def test_fix_keeps_non_ascii_code_points_escaped_for_ascii_source() -> None:
    source = '# -*- coding: ascii -*-\n"\\u00e9" "\\u20ac" "\\U0001f600"\n'
    _, context = contexts(source)
    result = rule_helpers.rule_fix_result(PDF000DocstringLiteralNormalization, context)
    assert result.module.code == '# -*- coding: ascii -*-\n"""\\u00e9\\u20ac\\U0001f600"""\n'
    compile(result.module.code.encode("ascii"), "example.py", "exec")
    _, fixed_context = contexts(result.module.code)
    assert PDF.require_data(fixed_context).docstrings[0].value == "\xe9\u20ac\U0001f600"


def test_fix_preserves_mixed_literal_and_escaped_non_ascii_spellings() -> None:
    source = '"café " "\\xe9" "\\u00e9"\n'
    _, context = contexts(source)
    result = rule_helpers.rule_fix_result(PDF000DocstringLiteralNormalization, context)

    assert result.module.code == '"""café \\xe9\\u00e9"""\n'
    _, fixed_context = contexts(result.module.code)
    assert PDF.require_data(fixed_context).docstrings[0].value == "café \xe9\xe9"


@pytest.mark.filterwarnings("ignore:invalid escape sequence.*:DeprecationWarning")
def test_unsupported_escape_reports_non_fixable_finding_without_crashing() -> None:
    source = r'"bad \z" " words"' + "\n"
    _, context = contexts(source)

    findings = rule_helpers.rule_findings(PDF000DocstringLiteralNormalization, context)
    result = rule_helpers.rule_fix_result(PDF000DocstringLiteralNormalization, context)

    assert tuple(finding.line_numbers for finding in findings) == ((1,),)
    assert [finding.fixable for finding in findings] == [False]
    assert result.module is context.module
    assert result.fixed_findings == ()


@pytest.mark.filterwarnings("ignore:invalid escape sequence.*:DeprecationWarning")
def test_fixable_simple_docstring_and_nonfixable_concatenation_are_reported_independently() -> None:
    source = '"""first\\nsecond"""\n\n\ndef unsupported():\n    "bad \\z" " words"\n'
    _, context = contexts(source)

    findings = rule_helpers.rule_findings(PDF000DocstringLiteralNormalization, context)
    result = rule_helpers.rule_fix_result(PDF000DocstringLiteralNormalization, context)

    assert tuple(finding.line_numbers for finding in findings) == ((1,), (5,))
    assert [finding.fixable for finding in findings] == [True, False]
    assert tuple(finding.line_numbers for finding in result.fixed_findings) == ((1,),)
    assert result.module.code == '"""first\nsecond"""\n\n\ndef unsupported():\n    "bad \\z" " words"\n'


def test_fix_handles_multiple_docstring_owners_in_one_pass() -> None:
    source = '"module " "doc"\n\nclass Outer:\n    "class " "doc"\n\n    def method(self):\n        "method " "doc"\n\n    def unchanged(self):\n        """simple doc"""\n'
    _, context = contexts(source)
    findings = rule_helpers.rule_findings(PDF000DocstringLiteralNormalization, context)
    result = rule_helpers.rule_fix_result(PDF000DocstringLiteralNormalization, context)
    assert tuple(finding.line_numbers for finding in findings) == ((1,), (4,), (7,))
    assert tuple(finding.line_numbers for finding in result.fixed_findings) == ((1,), (4,), (7,))
    assert result.module.code == '"""module doc"""\n\nclass Outer:\n    """class doc"""\n\n    def method(self):\n        """method doc"""\n\n    def unchanged(self):\n        """simple doc"""\n'


def test_fix_replaces_complete_multiline_expression_and_reports_its_source_span() -> None:
    source = 'def function():\n    (\n        r"first\\n"  # Preserve the raw backslash.\n        " second" \\\n        "\\tthird"\n    )\n    return None\n'
    _, context = contexts(source)
    findings = rule_helpers.rule_findings(PDF000DocstringLiteralNormalization, context)
    result = rule_helpers.rule_fix_result(PDF000DocstringLiteralNormalization, context)
    assert findings[0].line_numbers == (3, 4, 5)
    assert result.module.code == 'def function():\n    (\n        """first\\\\n second\tthird"""\n    )\n    return None\n'
    _, fixed_context = contexts(result.module.code)
    assert PDF.require_data(fixed_context).docstrings[0].value == "first\\n second\tthird"


def test_fix_preserves_single_line_suite_statements() -> None:
    _, context = contexts('def function(): "first " "second"; return 1\n')
    result = rule_helpers.rule_fix_result(PDF000DocstringLiteralNormalization, context)
    assert result.module.code == 'def function(): """first second"""; return 1\n'


def test_fix_preserves_crlf_and_escaped_newline_spelling() -> None:
    source = 'def function():\r\n    ("first\\n"\r\n     "second")\r\n'
    category, context = contexts(source)
    result = rule_helpers.rule_fix_result(PDF000DocstringLiteralNormalization, context)
    assert result.fixed_findings[0].line_numbers == (2, 3)
    assert result.module.code == 'def function():\r\n    ("""first\r\nsecond""")\r\n'
    fixed_category, _ = contexts(result.module.code)
    assert PDF.prepare(fixed_category).docstrings[0].value == "first\nsecond"
    assert category.module.config_for_parsing.default_newline == "\r\n"


def test_fix_preserves_source_continuation_while_literalizing_escape() -> None:
    source = 'def function():\n    """first\\\nsecond\\nthird"""\n'
    _, context = contexts(source)

    result = rule_helpers.rule_fix_result(PDF000DocstringLiteralNormalization, context)

    assert result.module.code == 'def function():\n    """first\\\nsecond\nthird"""\n'


def test_fix_leaves_raw_string_and_carriage_return_escape_values_unchanged() -> None:
    _, raw_context = contexts('def raw():\n    r"first\\nsecond"\n')
    _, carriage_return_context = contexts('def carriage_return():\n    """first\\r\\nsecond"""\n')

    assert rule_helpers.rule_findings(PDF000DocstringLiteralNormalization, raw_context) == ()
    assert rule_helpers.rule_fix_result(PDF000DocstringLiteralNormalization, raw_context).module is raw_context.module
    assert rule_helpers.rule_findings(PDF000DocstringLiteralNormalization, carriage_return_context) == ()
    assert rule_helpers.rule_fix_result(PDF000DocstringLiteralNormalization, carriage_return_context).module is carriage_return_context.module


@pytest.mark.filterwarnings("ignore:invalid escape sequence.*:DeprecationWarning")
def test_unsupported_escape_in_simple_docstring_is_ignored() -> None:
    _, context = contexts('def function():\n    """bad \\z words"""\n')

    assert rule_helpers.rule_findings(PDF000DocstringLiteralNormalization, context) == ()
    assert rule_helpers.rule_fix_result(PDF000DocstringLiteralNormalization, context).module is context.module


def test_ignores_concatenations_that_are_not_string_valued_first_expressions() -> None:
    source = 'def formatted():\n    f"first" "second"\n\ndef assigned():\n    value = "first" "second"\n\ndef later():\n    pass\n    "first" "second"\n'
    _, context = contexts(source)
    assert rule_helpers.rule_findings(PDF000DocstringLiteralNormalization, context) == ()
    assert rule_helpers.rule_fix_result(PDF000DocstringLiteralNormalization, context).module is context.module


def test_ignores_simple_string_escapes_that_are_not_docstrings() -> None:
    source = 'def assigned():\n    value = "first\\nsecond"\n\ndef later():\n    pass\n    "first\\nsecond"\n'
    _, context = contexts(source)

    assert rule_helpers.rule_findings(PDF000DocstringLiteralNormalization, context) == ()
    assert rule_helpers.rule_fix_result(PDF000DocstringLiteralNormalization, context).module is context.module


def test_ignores_unicode_prefix_on_non_docstring_simple_string() -> None:
    source = 'def function():\n    value = u"simple"\n'

    result = format_pdf000(source)

    assert not result.modified


def test_simple_docstrings_are_unchanged() -> None:
    _, context = contexts('"""simple"""\n')
    assert rule_helpers.rule_findings(PDF000DocstringLiteralNormalization, context) == ()
    assert rule_helpers.rule_fix_result(PDF000DocstringLiteralNormalization, context).module is context.module


def test_normalization_rule_runs_before_other_pdf_rules() -> None:
    assert PDF.ordered_rules()[0] is PDF000DocstringLiteralNormalization
