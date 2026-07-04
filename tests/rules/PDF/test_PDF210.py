import tests.rules.PDF.statement_spacing_helpers as statement_spacing_helpers
from pydocformatter.rules.definitions.PDF.PDF210_no_blank_line_after_class_docstring import PDF210NoBlankLineAfterClassDocstring


def test_removes_blank_lines_after_class_docstring() -> None:
    source = 'class Client:\n    """Docstring."""\n\n\n    value = 1\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF210")

    assert result.new_source == 'class Client:\n    """Docstring."""\n    value = 1\n'
    assert result.fixed_findings[PDF210NoBlankLineAfterClassDocstring.meta] == 1
    assert not statement_spacing_helpers.format_source(result.new_source, rule_code="PDF210").modified


def test_removes_adjacent_blank_before_body_comment() -> None:
    source = 'class Client:\n    """Docstring."""\n\n    # Body comment.\n    value = 1\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF210")

    assert result.new_source == 'class Client:\n    """Docstring."""\n    # Body comment.\n    value = 1\n'


def test_ignores_class_with_only_docstring() -> None:
    source = 'class Client:\n    """Docstring."""\n\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF210")

    assert result.new_source == source
    assert not result.fixed_findings


def test_ignores_functions() -> None:
    source = 'def function():\n    """Docstring."""\n\n    return None\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF210")

    assert result.new_source == source
    assert not result.fixed_findings


def test_removes_blank_line_before_nested_class_body_statement_only() -> None:
    source = 'class Client:\n    """Docstring."""\n\n    class Nested:\n        """Nested docstring."""\n\n        value = 1\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF210")

    assert result.new_source == 'class Client:\n    """Docstring."""\n    class Nested:\n        """Nested docstring."""\n        value = 1\n'
    assert result.fixed_findings[PDF210NoBlankLineAfterClassDocstring.meta] == 2


def test_suppression_on_docstring_line_suppresses_after_finding() -> None:
    source = 'class Client:\n    """Docstring."""  # noqa: PDF210\n\n    value = 1\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF210")

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_ignores_trailing_body_comment_without_following_statement() -> None:
    source = 'class Client:\n    """Docstring."""\n\n    # Body comment.\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF210")

    assert result.new_source == source
    assert not result.fixed_findings


def test_removes_blank_lines_after_multiline_class_docstring() -> None:
    source = 'class Client:\n    """Summary.\n\n    Body.\n    """\n\n    value = 1\n'
    result = statement_spacing_helpers.format_source(source, rule_code="PDF210")

    assert result.new_source == 'class Client:\n    """Summary.\n\n    Body.\n    """\n    value = 1\n'
    assert result.fixed_findings[PDF210NoBlankLineAfterClassDocstring.meta] == 1
