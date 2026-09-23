"""Tests for whole-literal docstring rendering."""

# Future imports
from __future__ import annotations

# Standard library imports
import types
import typing

# Third-party imports
import libcst as cst
import pytest

# First-party imports
from pydocformatter.rules.definition_helpers import docstring_rendering


if typing.TYPE_CHECKING:
    # First-party imports
    import pydocformatter.rules.definitions.PDF.PDF as PDF_definition


def _docstring_stub(source: str, *, source_map: object = None) -> PDF_definition.DocstringInfo:
    """Return the rendering-relevant portion of one docstring record."""
    return typing.cast("PDF_definition.DocstringInfo", types.SimpleNamespace(node=cst.parse_expression(source), source=source, source_map=source_map))


def test_escaped_closing_quote_body_source_skips_single_character_delimiter() -> None:
    node = cst.ensure_type(cst.parse_expression("'Summary'"), cst.SimpleString)

    assert docstring_rendering.escaped_closing_quote_body_source(node, "Say '") is None


def test_simple_docstring_body_source_candidates_try_value_preserving_both_end_quote_escape_first() -> None:
    node = cst.ensure_type(cst.parse_expression('"""Summary"""'), cst.SimpleString)

    assert next(docstring_rendering.simple_docstring_body_source_candidates(node, '"quoted"', expected_value='"quoted"')) == ('\\"quoted\\"', '"quoted"')


def test_quote_escape_helpers_refuse_raw_strings() -> None:
    """Raw docstrings cannot gain value-preserving delimiter escapes."""
    node = cst.ensure_type(cst.parse_expression('r"""Summary"""'), cst.SimpleString)

    assert docstring_rendering.escaped_opening_quote_body_source(node, '"Summary') is None
    assert docstring_rendering.escaped_closing_quote_body_source(node, 'Summary"') is None


def test_quote_escape_helpers_ignore_nonconflicting_boundaries() -> None:
    """Bodies away from the selected delimiters require no quote escapes."""
    node = cst.ensure_type(cst.parse_expression('"""Summary"""'), cst.SimpleString)

    assert docstring_rendering.escaped_opening_quote_body_source(node, "Summary") is None
    assert docstring_rendering.escaped_closing_quote_body_source(node, "Summary") is None


def test_quote_escape_helpers_protect_both_triple_quote_boundaries() -> None:
    """Escape the leading quote and every dangerous trailing quote."""
    node = cst.ensure_type(cst.parse_expression('"""Summary"""'), cst.SimpleString)

    assert docstring_rendering.escaped_opening_quote_body_source(node, '"Summary') == '\\"Summary'
    assert docstring_rendering.escaped_closing_quote_body_source(node, 'Summary""') == 'Summary\\"\\"'


def test_simple_docstring_body_source_candidates_are_unique() -> None:
    """Candidate fallback ordering must not retry identical renderings."""
    node = cst.ensure_type(cst.parse_expression('"""Summary"""'), cst.SimpleString)
    candidates = tuple(docstring_rendering.simple_docstring_body_source_candidates(node, "Summary", expected_value="Summary"))

    assert candidates == (("Summary", "Summary"), (" Summary", " Summary"), ("Summary ", "Summary "), (" Summary ", " Summary "))


def test_simple_docstring_body_source_candidates_include_separator_fallback_value_changes() -> None:
    node = cst.ensure_type(cst.parse_expression('r"""Summary"""'), cst.SimpleString)

    candidates = tuple(docstring_rendering.simple_docstring_body_source_candidates(node, "Path \\", expected_value="Path \\"))

    assert (" Path \\", " Path \\") in candidates
    assert ("Path \\ ", "Path \\ ") in candidates
    assert (" Path \\ ", " Path \\ ") in candidates


def test_whole_literal_rendering_refuses_concatenated_docstrings() -> None:
    """Whole-literal helpers must not collapse concatenated source spelling."""
    docstring = _docstring_stub('"first" "second"')

    assert docstring_rendering.render_docstring_output_with_separator_fallback(docstring, body_source="replacement", expected_value="replacement", separator_fallback=None) is None
    assert docstring_rendering.render_simple_docstring_body_with_separator_fallbacks(docstring, body_source="replacement", expected_value="replacement") is None
    assert docstring_rendering.planned_simple_docstring_output_change(docstring, context=typing.cast("typing.Any", object()), output_lines=(), line_numbers=()) is None


def test_planned_whole_literal_change_requires_a_lossless_source_map() -> None:
    """Unsupported string spellings must not be reconstructed speculatively."""
    docstring = _docstring_stub('"""Summary"""')

    assert docstring_rendering.planned_simple_docstring_output_change(docstring, context=typing.cast("typing.Any", object()), output_lines=(), line_numbers=()) is None


def test_both_boundary_fallback_preserves_renderable_raw_output() -> None:
    """The broad fallback must leave already safe raw-string output unchanged."""
    docstring = _docstring_stub('r"""Summary"""')

    assert (
        docstring_rendering.render_docstring_output_with_separator_fallback(
            docstring, body_source="Summary", expected_value="Summary", separator_fallback=docstring_rendering.DocstringOutputSeparatorFallback.BOTH
        )
        == 'r"""Summary"""'
    )


def test_both_boundary_fallback_makes_unsafe_raw_output_renderable() -> None:
    """Boundary spaces may safely represent a raw value ending in a backslash."""
    docstring = _docstring_stub('r"""Summary"""')

    assert (
        docstring_rendering.render_docstring_output_with_separator_fallback(
            docstring, body_source="Path \\", expected_value="Path \\", separator_fallback=docstring_rendering.DocstringOutputSeparatorFallback.BOTH
        )
        == 'r""" Path \\ """'
    )


def test_opening_only_fallback_refuses_an_unsafe_raw_closing_boundary() -> None:
    """An opening separator alone cannot repair a dangerous closing backslash."""
    docstring = _docstring_stub('r"""Summary"""')

    assert (
        docstring_rendering.render_docstring_output_with_separator_fallback(
            docstring, body_source="Path \\", expected_value="Path \\", separator_fallback=docstring_rendering.DocstringOutputSeparatorFallback.OPENING
        )
        is None
    )


def test_synthesized_output_lines_require_source_and_value_text() -> None:
    """Incomplete render descriptors must fail instead of silently dropping text."""
    missing_source = docstring_rendering.DocstringOutputLine(source=None, value="value")
    missing_value = docstring_rendering.DocstringOutputLine(source="source", value=None)

    with pytest.raises(ValueError, match="require source text"):
        docstring_rendering._output_body_source((missing_source,), source_map=typing.cast("typing.Any", object()), line_ending="\n", preserve_trailing_newline=False)
    with pytest.raises(ValueError, match="require evaluated text"):
        docstring_rendering.docstring_output_expected_value((missing_value,), preserve_trailing_newline=False)


def test_separator_fallback_rejects_unknown_strategies() -> None:
    """Invalid internal fallback values must not produce an arbitrary rewrite."""
    invalid = typing.cast("docstring_rendering.DocstringOutputSeparatorFallback", object())

    with pytest.raises(ValueError, match="Unsupported separator fallback"):
        docstring_rendering._separator_fallback_output("source", "value", separator_fallback=invalid)
