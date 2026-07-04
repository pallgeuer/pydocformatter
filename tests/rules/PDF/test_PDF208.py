import tests.rules.PDF.statement_spacing_helpers as statement_spacing_helpers
from pydocformatter.rules.definitions.PDF.PDF208_no_blank_line_before_class_docstring import PDF208NoBlankLineBeforeClassDocstring


def test_removes_blank_lines_before_class_docstring() -> None:
    source = 'class Client:\n\n\n    """Docstring."""\n    value = 1\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF208")

    assert result.new_source == 'class Client:\n    """Docstring."""\n    value = 1\n'
    assert result.fixed_findings[PDF208NoBlankLineBeforeClassDocstring.meta] == 1
    assert not statement_spacing_helpers.format_source(result.new_source, rule_code="PDF208").modified


def test_removes_adjacent_blank_after_leading_comment() -> None:
    source = 'class Client:\n    # Leading comment.\n\n    """Docstring."""\n    value = 1\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF208")

    assert result.new_source == 'class Client:\n    # Leading comment.\n    """Docstring."""\n    value = 1\n'


def test_ignores_functions() -> None:
    source = 'def function():\n\n    """Docstring."""\n    return None\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF208")

    assert result.new_source == source
    assert not result.fixed_findings


def test_preserves_crlf_line_endings() -> None:
    source = 'class Client:\r\n\r\n    """Docstring."""\r\n    value = 1\r\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF208")

    assert result.new_source == 'class Client:\r\n    """Docstring."""\r\n    value = 1\r\n'


def test_removes_whitespace_only_blank_lines_before_class_docstring() -> None:
    source = 'class Client:\n    \t  \n    """Docstring."""\n    value = 1\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF208")

    assert result.new_source == 'class Client:\n    """Docstring."""\n    value = 1\n'
    assert result.fixed_findings[PDF208NoBlankLineBeforeClassDocstring.meta] == 1


def test_ignores_attribute_docstrings() -> None:
    source = 'class Client:\n    value = 1\n    """Attribute docstring."""\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF208")

    assert result.new_source == source
    assert not result.fixed_findings
