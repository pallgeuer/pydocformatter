"""Tests for whole-literal docstring rendering."""

# Third-party imports
import libcst as cst

# First-party imports
from pydocformatter.rules.definition_helpers import docstring_rendering


def test_escaped_closing_quote_body_source_skips_single_character_delimiter() -> None:
    node = cst.ensure_type(cst.parse_expression("'Summary'"), cst.SimpleString)

    assert docstring_rendering.escaped_closing_quote_body_source(node, "Say '") is None


def test_simple_docstring_body_source_candidates_try_value_preserving_both_end_quote_escape_first() -> None:
    node = cst.ensure_type(cst.parse_expression('"""Summary"""'), cst.SimpleString)

    assert next(docstring_rendering.simple_docstring_body_source_candidates(node, '"quoted"', expected_value='"quoted"')) == ('\\"quoted\\"', '"quoted"')


def test_simple_docstring_body_source_candidates_include_separator_fallback_value_changes() -> None:
    node = cst.ensure_type(cst.parse_expression('r"""Summary"""'), cst.SimpleString)

    candidates = tuple(docstring_rendering.simple_docstring_body_source_candidates(node, "Path \\", expected_value="Path \\"))

    assert (" Path \\", " Path \\") in candidates
    assert ("Path \\ ", "Path \\ ") in candidates
    assert (" Path \\ ", " Path \\ ") in candidates
