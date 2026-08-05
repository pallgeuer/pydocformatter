"""Whole-literal docstring output rendering."""

# Future imports
from __future__ import annotations

# Standard library imports
import enum
import typing
import dataclasses
from collections.abc import Iterator

# Third-party imports
import libcst as cst

# First-party imports
import pydocformatter.rules.edits as rule_edits
from pydocformatter.rules.definition_helpers import docstring_source, string_literals
from pydocformatter.rules.definitions.PDF.PDF import DocstringInfo, DocstringValueLine


if typing.TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.definition import RuleContext


@dataclasses.dataclass(frozen=True)
class DocstringOutputLine:
    """One output logical docstring line for whole-literal rendering.

    Attributes:
        original (DocstringValueLine | None): Existing value line to preserve when no replacement text is supplied.
        source (str | None): Replacement source text for this logical line, when it differs from evaluated text.
        value (str | None): Replacement evaluated value text for this logical line.
        strip_docstring_margin (bool): Whether to render `original` after removing the docstring margin.
    """

    original: DocstringValueLine | None = None
    source: str | None = dataclasses.field(kw_only=True)
    value: str | None = dataclasses.field(kw_only=True)
    strip_docstring_margin: bool = False


class DocstringOutputSeparatorFallback(enum.Enum):
    """Separator fallback direction for whole-literal rendering.

    Attributes:
        OPENING: Prefer inserting separator whitespace after the opening quotes.
        CLOSING: Prefer inserting separator whitespace before the closing quotes.
        BOTH: Allow fallback whitespace on both quote boundaries.
    """

    OPENING = "opening"
    CLOSING = "closing"
    BOTH = "both"


def planned_simple_docstring_output_change(
    docstring: DocstringInfo,
    *,
    context: RuleContext,
    output_lines: tuple[DocstringOutputLine, ...],
    line_numbers: tuple[int, ...],
    preserve_trailing_newline: bool | None = None,
    separator_fallback: DocstringOutputSeparatorFallback | None = None,
) -> rule_edits.PlannedSourceChange | None:
    """Return one whole-literal replacement from target output lines.

    Args:
        docstring (DocstringInfo): Simple docstring whose full literal source should be replaced.
        context (RuleContext): Rule context providing source line endings and string fragment mapping.
        output_lines (tuple[DocstringOutputLine, ...]): Render-ready line descriptors combining preserved source lines
            and synthesized text.
        line_numbers (tuple[int, ...]): Source lines that should be reported as affected by the resulting change.
        preserve_trailing_newline (bool | None): Optional override for whether the rendered docstring value keeps a
            final newline.
        separator_fallback (DocstringOutputSeparatorFallback | None): Optional strategy for adding boundary spaces when
            adjacent quote delimiters cannot be represented safely.

    Returns:
        Planned whole-literal source change, or None when the docstring is not safely renderable or the rendered source is unchanged.
    """
    if not isinstance(docstring.node, cst.SimpleString):
        return None
    source_map = docstring.source_map
    if source_map is None:
        return None
    keep_trailing_newline = docstring_source.docstring_value_ends_with_newline(docstring) if preserve_trailing_newline is None else preserve_trailing_newline
    body_source = _output_body_source(output_lines, source_map=source_map, line_ending=context.line_ending, preserve_trailing_newline=keep_trailing_newline)
    expected_value = _output_expected_value(output_lines, preserve_trailing_newline=keep_trailing_newline)
    rendered = _render_output_with_separator_fallback(docstring, body_source=body_source, expected_value=expected_value, separator_fallback=separator_fallback)
    if rendered is None or rendered == docstring.source:
        return None
    return rule_edits.PlannedSourceChange(edit=rule_edits.SourceEdit(range=docstring.range, replacement=rendered), line_numbers=line_numbers, suppression_line_numbers=())


def _render_output_body_source(docstring: DocstringInfo, *, body_source: str, expected_value: str) -> str | None:
    """Render output body source using the docstring's original literal spelling."""
    if not isinstance(docstring.node, cst.SimpleString):
        return None
    return string_literals.render_simple_string_from_body_source(docstring.node.prefix, docstring.node.quote, body_source, expected_value=expected_value)


def _render_output_with_separator_fallback(docstring: DocstringInfo, *, body_source: str, expected_value: str, separator_fallback: DocstringOutputSeparatorFallback | None) -> str | None:
    """Render output source, applying separator fallback strategy when configured."""
    if separator_fallback is DocstringOutputSeparatorFallback.OPENING:
        return _opening_separator_rendered_output(docstring, body_source=body_source, expected_value=expected_value)
    if separator_fallback is DocstringOutputSeparatorFallback.CLOSING:
        return _closing_separator_rendered_output(docstring, body_source=body_source, expected_value=expected_value)
    if separator_fallback is DocstringOutputSeparatorFallback.BOTH:
        rendered = _render_output_body_source(docstring, body_source=body_source, expected_value=expected_value)
        if rendered is not None:
            return rendered
        fallback_body_source, fallback_expected_value = _separator_fallback_output(body_source, expected_value, separator_fallback=separator_fallback)
        return _render_output_body_source(docstring, body_source=fallback_body_source, expected_value=fallback_expected_value)
    return _render_output_body_source(docstring, body_source=body_source, expected_value=expected_value)


def render_docstring_output_with_separator_fallback(docstring: DocstringInfo, *, body_source: str, expected_value: str, separator_fallback: DocstringOutputSeparatorFallback | None) -> str | None:
    """Render output source, applying a configured separator fallback strategy.

    Args:
        docstring (DocstringInfo): Simple-string docstring whose original literal spelling should be reused.
        body_source (str): Desired literal body source.
        expected_value (str): Evaluated value expected from the rendered output.
        separator_fallback (DocstringOutputSeparatorFallback | None): Optional boundary separator strategy.

    Returns:
        str | None: Full rendered literal source, or None when the output cannot be represented safely.
    """
    return _render_output_with_separator_fallback(docstring, body_source=body_source, expected_value=expected_value, separator_fallback=separator_fallback)


def render_simple_docstring_body_with_separator_fallbacks(docstring: DocstringInfo, *, body_source: str, expected_value: str) -> str | None:
    """Render output source after trying value-preserving quote escapes and separator fallbacks.

    Args:
        docstring (DocstringInfo): Simple-string docstring whose quote style should be kept if possible.
        body_source (str): Desired literal body before escape or separator adjustments.
        expected_value (str): Desired evaluated value before separator fallbacks potentially add boundary spaces.

    Returns:
        First renderable full literal source from the candidate sequence, or None when every candidate is unsafe.
    """
    if not isinstance(docstring.node, cst.SimpleString):
        return None
    for candidate_body, candidate_value in simple_docstring_body_source_candidates(docstring.node, body_source, expected_value=expected_value):
        rendered = _render_output_body_source(docstring, body_source=candidate_body, expected_value=candidate_value)
        if rendered is not None:
            return rendered
    return None


def simple_docstring_body_source_candidates(node: cst.SimpleString, body_source: str, *, expected_value: str) -> Iterator[tuple[str, str]]:
    """Yield source-body candidates ordered by value preservation before separator fallback.

    Args:
        node (cst.SimpleString): Simple-string syntax node whose prefix and delimiter determine which escapes are legal.
        body_source (str): Desired literal body before trying quote escapes or separator spaces.
        expected_value (str): Evaluated value corresponding to the desired body source.

    Yields:
        Candidate body source and the evaluated value expected from rendering it.
    """
    seen: set[tuple[str, str]] = set()

    def candidate_once(candidate: tuple[str, str]) -> Iterator[tuple[str, str]]:
        """Yield a candidate pair only the first time it appears.

        Args:
            candidate (tuple[str, str]): Body-source and expected-value pair produced by an escape or separator
                strategy.

        Yields:
            The candidate pair when it has not already been emitted.
        """
        if candidate not in seen:
            seen.add(candidate)
            yield candidate

    escaped_opening = escaped_opening_quote_body_source(node, body_source)
    escaped_closing = escaped_closing_quote_body_source(node, body_source)
    if escaped_opening is not None:
        escaped_both = escaped_closing_quote_body_source(node, escaped_opening)
        if escaped_both is not None:
            yield from candidate_once((escaped_both, expected_value))
        yield from candidate_once((escaped_opening, expected_value))
    if escaped_closing is not None:
        escaped_closing_opening = escaped_opening_quote_body_source(node, escaped_closing)
        if escaped_closing_opening is not None:
            yield from candidate_once((escaped_closing_opening, expected_value))
        yield from candidate_once((escaped_closing, expected_value))
    yield from candidate_once((body_source, expected_value))
    yield from candidate_once(_separator_fallback_output(body_source, expected_value, separator_fallback=DocstringOutputSeparatorFallback.OPENING))
    yield from candidate_once(_separator_fallback_output(body_source, expected_value, separator_fallback=DocstringOutputSeparatorFallback.CLOSING))
    yield from candidate_once(_separator_fallback_output(body_source, expected_value, separator_fallback=DocstringOutputSeparatorFallback.BOTH))


def _opening_separator_rendered_output(docstring: DocstringInfo, *, body_source: str, expected_value: str) -> str | None:
    """Render output with opening quote separator precedence."""
    rendered = _render_output_body_source(docstring, body_source=body_source, expected_value=expected_value)
    if rendered is None:
        fallback_body_source, fallback_expected_value = _separator_fallback_output(body_source, expected_value, separator_fallback=DocstringOutputSeparatorFallback.OPENING)
        return _render_output_body_source(docstring, body_source=fallback_body_source, expected_value=fallback_expected_value)
    return _opening_quote_separator_output(docstring, body_source=body_source, expected_value=expected_value) or rendered


def _closing_separator_rendered_output(docstring: DocstringInfo, *, body_source: str, expected_value: str) -> str | None:
    """Render output with closing quote separator precedence."""
    rendered = _render_output_body_source(docstring, body_source=body_source, expected_value=expected_value)
    if rendered is not None:
        return rendered
    rendered = _closing_quote_separator_output(docstring, body_source=body_source, expected_value=expected_value)
    if rendered is not None:
        return rendered
    fallback_body_source, fallback_expected_value = _separator_fallback_output(body_source, expected_value, separator_fallback=DocstringOutputSeparatorFallback.CLOSING)
    return _render_output_body_source(docstring, body_source=fallback_body_source, expected_value=fallback_expected_value)


def _opening_quote_separator_output(docstring: DocstringInfo, *, body_source: str, expected_value: str) -> str | None:
    """Render an escaped leading quote to keep opening delimiter and content distinct."""
    if not isinstance(docstring.node, cst.SimpleString):
        return None
    escaped_body_source = escaped_opening_quote_body_source(docstring.node, body_source)
    if escaped_body_source is None:
        return None
    return _render_output_body_source(docstring, body_source=escaped_body_source, expected_value=expected_value)


def escaped_opening_quote_body_source(node: cst.SimpleString, body_source: str) -> str | None:
    """Return body source with a leading delimiter quote escaped where possible.

    Args:
        node (cst.SimpleString): Simple-string node whose raw prefix and delimiter control whether escaping is allowed.
        body_source (str): Literal body source that may start with the delimiter quote character.

    Returns:
        Body source with an inserted leading backslash escape, or None for raw strings and non-conflicting bodies.
    """
    if "r" in node.prefix.lower():
        return None
    quote_char = "'" if "'" in node.quote else '"'
    if not body_source.startswith(quote_char):
        return None
    return f"\\{body_source}"


def escaped_closing_quote_body_source(node: cst.SimpleString, body_source: str) -> str | None:
    """Return body source with trailing delimiter quotes escaped where possible.

    Args:
        node (cst.SimpleString): Simple-string node whose delimiter length limits how many trailing quotes may be
            escaped.
        body_source (str): Literal body source that may end with delimiter quote characters.

    Returns:
        Body source with safe trailing quote escapes, or None when raw-string semantics or the body shape prevent escaping.
    """
    if "r" in node.prefix.lower():
        return None
    quote_char = "'" if "'" in node.quote else '"'
    trailing_quotes = len(body_source) - len(body_source.rstrip(quote_char))
    if trailing_quotes <= 0:
        return None
    escape_count = min(trailing_quotes, len(node.quote) - 1)
    if escape_count <= 0:
        return None
    escaped_quotes = ("\\" + quote_char) * escape_count
    return f"{body_source[:-escape_count]}{escaped_quotes}"


def _closing_quote_separator_output(docstring: DocstringInfo, *, body_source: str, expected_value: str) -> str | None:
    """Render escaped trailing quotes to keep closing delimiter and content distinct."""
    if not isinstance(docstring.node, cst.SimpleString):
        return None
    escaped_body_source = escaped_closing_quote_body_source(docstring.node, body_source)
    if escaped_body_source is None:
        return None
    return _render_output_body_source(docstring, body_source=escaped_body_source, expected_value=expected_value)


def _separator_fallback_output(body_source: str, expected_value: str, *, separator_fallback: DocstringOutputSeparatorFallback) -> tuple[str, str]:
    """Return a one-space separator fallback body and value."""
    if separator_fallback is DocstringOutputSeparatorFallback.OPENING:
        return f" {body_source}", f" {expected_value}"
    if separator_fallback is DocstringOutputSeparatorFallback.CLOSING:
        return f"{body_source} ", f"{expected_value} "
    if separator_fallback is DocstringOutputSeparatorFallback.BOTH:
        return f" {body_source} ", f" {expected_value} "
    raise ValueError(f"Unsupported separator fallback: {separator_fallback!r}")


def _output_body_source(output_lines: tuple[DocstringOutputLine, ...], *, source_map: string_literals.SimpleStringSourceMap, line_ending: str, preserve_trailing_newline: bool) -> str:
    """Return replacement literal body source from output lines."""
    chunks: list[str] = []
    for index, output_line in enumerate(output_lines):
        if index:
            chunks.append(line_ending)
        if output_line.original is None:
            if output_line.source is None:
                raise ValueError("Synthesized output lines require source text")
            chunks.append(output_line.source)
        else:
            chunks.append(docstring_source.docstring_line_source(output_line.original, source_map=source_map, strip_docstring_margin=output_line.strip_docstring_margin))
    if preserve_trailing_newline:
        chunks.append(line_ending)
    return "".join(chunks)


def _output_expected_value(output_lines: tuple[DocstringOutputLine, ...], *, preserve_trailing_newline: bool) -> str:
    """Return replacement evaluated value from output lines."""
    chunks: list[str] = []
    for index, output_line in enumerate(output_lines):
        if index:
            chunks.append("\n")
        if output_line.original is None:
            if output_line.value is None:
                raise ValueError("Synthesized output lines require evaluated text")
            chunks.append(output_line.value)
        elif output_line.strip_docstring_margin:
            chunks.append(output_line.original.text)
        else:
            chunks.append(output_line.original.raw_text)
    if preserve_trailing_newline:
        chunks.append("\n")
    return "".join(chunks)


def docstring_output_expected_value(output_lines: tuple[DocstringOutputLine, ...], *, preserve_trailing_newline: bool) -> str:
    """Return replacement evaluated value from output lines.

    Args:
        output_lines (tuple[DocstringOutputLine, ...]): Render-ready line descriptors for the replacement body.
        preserve_trailing_newline (bool): Whether the output value should end with a final newline.

    Returns:
        str: Evaluated docstring value expected after rendering the output lines.
    """
    return _output_expected_value(output_lines, preserve_trailing_newline=preserve_trailing_newline)
