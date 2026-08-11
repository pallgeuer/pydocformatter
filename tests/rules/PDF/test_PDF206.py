# Third-party imports
import pytest

# First-party imports
from pydocformatter.rules.definitions.PDF.PDF206_no_blank_line_after_function_docstring import PDF206NoBlankLineAfterFunctionDocstring
from tests import rule_helpers
from tests.rules.PDF import statement_spacing_helpers


def test_removes_blank_lines_after_function_docstring() -> None:
    source = 'def function():\n    """Docstring."""\n\n\n    return None\n'
    _, context = statement_spacing_helpers.contexts(source, rule_code="PDF206")
    findings = rule_helpers.rule_findings(PDF206NoBlankLineAfterFunctionDocstring, context)
    result = statement_spacing_helpers.format_source(source, rule_code="PDF206")

    assert result.new_source == 'def function():\n    """Docstring."""\n    return None\n'
    assert tuple(finding.line_numbers for finding in findings) == ((2,),)
    assert tuple(finding.message for finding in findings) == ("Function docstring should have no blank lines after it",)
    assert result.fixed_findings[PDF206NoBlankLineAfterFunctionDocstring.meta] == 1
    assert not statement_spacing_helpers.format_source(result.new_source, rule_code="PDF206").modified


def test_removes_adjacent_blank_before_body_comment() -> None:
    source = 'def function():\n    """Docstring."""\n\n    # Body comment.\n    return None\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF206")

    assert result.new_source == 'def function():\n    """Docstring."""\n    # Body comment.\n    return None\n'


def test_ignores_function_with_only_docstring() -> None:
    source = 'def function():\n    """Docstring."""\n\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF206")

    assert result.new_source == source
    assert not result.fixed_findings


def test_ignores_classes() -> None:
    source = 'class Client:\n    """Docstring."""\n\n    value = 1\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF206")

    assert result.new_source == source
    assert not result.fixed_findings


def test_collapses_whitespace_only_blank_lines_after_function_docstring() -> None:
    source = 'def function():\n    """Docstring."""\n    \t  \n    return None\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF206")

    assert result.new_source == 'def function():\n    """Docstring."""\n    return None\n'
    assert result.fixed_findings[PDF206NoBlankLineAfterFunctionDocstring.meta] == 1


def test_suppression_on_docstring_line_suppresses_after_finding() -> None:
    source = 'def function():\n    """Docstring."""  # noqa: PDF206\n\n    return None\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF206")

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_ignores_trailing_body_comment_without_following_statement() -> None:
    source = 'def function():\n    """Docstring."""\n\n    # Body comment.\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF206")

    assert result.new_source == source
    assert not result.fixed_findings


def test_removes_blank_lines_after_multiline_function_docstring() -> None:
    source = 'def function():\n    """Summary.\n\n    Body.\n    """\n\n    return None\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF206")

    assert result.new_source == 'def function():\n    """Summary.\n\n    Body.\n    """\n    return None\n'
    assert result.fixed_findings[PDF206NoBlankLineAfterFunctionDocstring.meta] == 1


@pytest.mark.parametrize(
    "nested_definition",
    [
        "    def inner():\n        pass",
        "    async def inner():\n        pass",
        "    class Inner:\n        pass",
        "    @decorator\n    def inner():\n        pass",
        "    @decorator\n    class Inner:\n        pass",
    ],
)
def test_inserts_blank_line_before_nested_definition(nested_definition: str) -> None:
    source = f'def outer():\n    """Docstring."""\n{nested_definition}\n'
    _, context = statement_spacing_helpers.contexts(source, rule_code="PDF206")
    findings = rule_helpers.rule_findings(PDF206NoBlankLineAfterFunctionDocstring, context)
    result = statement_spacing_helpers.format_source(source, rule_code="PDF206")

    assert result.new_source == f'def outer():\n    """Docstring."""\n\n{nested_definition}\n'
    assert tuple(finding.message for finding in findings) == ("Function docstring should have one blank line after it before a nested definition",)
    assert result.fixed_findings[PDF206NoBlankLineAfterFunctionDocstring.meta] == 1
    assert not statement_spacing_helpers.format_source(result.new_source, rule_code="PDF206").modified


def test_collapses_excess_blank_lines_before_nested_definition() -> None:
    source = 'def outer():\n    """Docstring."""\n\n\n    def inner():\n        pass\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF206")

    assert result.new_source == 'def outer():\n    """Docstring."""\n\n    def inner():\n        pass\n'


def test_inserts_blank_line_before_comments_leading_nested_definition() -> None:
    source = 'def outer():\n    """Docstring."""\n    # Explain the helper.\n    def inner():\n        pass\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF206")

    assert result.new_source == 'def outer():\n    """Docstring."""\n\n    # Explain the helper.\n    def inner():\n        pass\n'


def test_only_classifies_first_statement_after_docstring() -> None:
    source = 'def outer():\n    """Docstring."""\n\n    value = 1\n\n    def inner():\n        return value\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF206")

    assert result.new_source == 'def outer():\n    """Docstring."""\n    value = 1\n\n    def inner():\n        return value\n'


def test_preserves_crlf_when_inserting_blank_line_before_nested_definition() -> None:
    source = 'def outer():\r\n    """Docstring."""\r\n    def inner():\r\n        pass\r\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF206")

    assert result.new_source == 'def outer():\r\n    """Docstring."""\r\n\r\n    def inner():\r\n        pass\r\n'


@pytest.mark.parametrize("terminal", ["", "\r"])
def test_preserves_cr_only_final_newline_state_when_inserting_blank_line_before_nested_definition(terminal: str) -> None:
    source = f'def outer():\r    """Docstring."""\r    def inner():\r        pass{terminal}'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF206")

    assert result.new_source == f'def outer():\r    """Docstring."""\r\r    def inner():\r        pass{terminal}'
    assert not statement_spacing_helpers.format_source(result.new_source, rule_code="PDF206").modified


def test_suppression_on_docstring_line_suppresses_nested_definition_finding() -> None:
    source = 'def outer():\n    """Docstring."""  # noqa: PDF206\n    def inner():\n        pass\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF206")

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings
