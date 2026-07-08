# Third-party imports
import pytest

# First-party imports
from pydocformatter.rules.definitions.PDF.PDF211_blank_line_after_class_docstring import PDF211BlankLineAfterClassDocstring
from tests import rule_helpers
from tests.rules.PDF import statement_spacing_helpers


@pytest.mark.parametrize(
    ("body", "expected_body"),
    [
        ("    value = 1\n", "\n    value = 1\n"),
        ("    def close(self):\n        pass\n", "\n    def close(self):\n        pass\n"),
        ("    class Nested:\n        pass\n", "\n    class Nested:\n        pass\n"),
    ],
)
def test_inserts_blank_line_after_class_docstring_before_following_statement(body: str, expected_body: str) -> None:
    source = f'class Client:\n    """Docstring."""\n{body}'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF211")

    assert result.new_source == f'class Client:\n    """Docstring."""\n{expected_body}'
    assert result.fixed_findings[PDF211BlankLineAfterClassDocstring.meta] == 1
    assert result.new_source is not None
    assert not statement_spacing_helpers.format_source(result.new_source, rule_code="PDF211").modified


def test_collapses_excess_blank_lines_after_class_docstring() -> None:
    source = 'class Client:\n    """Docstring."""\n\n\n    value = 1\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF211")

    assert result.new_source == 'class Client:\n    """Docstring."""\n\n    value = 1\n'
    assert result.fixed_findings[PDF211BlankLineAfterClassDocstring.meta] == 1


def test_inserts_blank_before_body_comment_after_class_docstring() -> None:
    source = 'class Client:\n    """Docstring."""\n    # Body comment.\n    value = 1\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF211")

    assert result.new_source == 'class Client:\n    """Docstring."""\n\n    # Body comment.\n    value = 1\n'


def test_ignores_class_with_only_docstring() -> None:
    source = 'class Client:\n    """Docstring."""\n\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF211")

    assert result.new_source == source
    assert not result.fixed_findings


def test_inserts_blank_line_after_class_docstring_with_crlf_line_ending() -> None:
    source = 'class Client:\r\n    """Docstring."""\r\n    value = 1\r\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF211")

    assert result.new_source == 'class Client:\r\n    """Docstring."""\r\n\r\n    value = 1\r\n'


def test_ignores_simple_suite_class_docstring() -> None:
    source = 'class Client: """Docstring."""; value = 1\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF211")

    assert result.new_source == source
    assert not result.fixed_findings


def test_ignores_trailing_body_comment_without_following_statement() -> None:
    source = 'class Client:\n    """Docstring."""\n    # Body comment.\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF211")

    assert result.new_source == source
    assert not result.fixed_findings


def test_inserts_blank_line_after_multiline_class_docstring_and_targets_opening_line() -> None:
    source = 'class Client:\n    """Summary.\n\n    Body.\n    """\n    value = 1\n'
    _, context = statement_spacing_helpers.contexts(source, rule_code="PDF211")
    findings = rule_helpers.rule_findings(PDF211BlankLineAfterClassDocstring, context)
    result = statement_spacing_helpers.format_source(source, rule_code="PDF211")

    assert result.new_source == 'class Client:\n    """Summary.\n\n    Body.\n    """\n\n    value = 1\n'
    assert tuple(finding.line_numbers for finding in findings) == ((2,),)
    assert result.fixed_findings[PDF211BlankLineAfterClassDocstring.meta] == 1
