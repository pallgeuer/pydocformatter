"""Source-preserving Python string literal helpers."""

# Future imports
from __future__ import annotations

# Standard library imports
import string
import dataclasses

# Third-party imports
import libcst as cst

# First-party imports
from pydocformatter.rules.definition_helpers import text_layout


@dataclasses.dataclass(frozen=True)
class StringValueFragment:
    """Source spelling for one evaluated string character.

    Attributes:
        value (str): Evaluated string fragment represented by the source spelling.
        source (str): Source characters that produce `value`.
    """

    value: str
    source: str


@dataclasses.dataclass(frozen=True)
class StringEscape:
    """One parsed escape sequence in a simple string body.

    Attributes:
        value (str): Evaluated value produced by the escape sequence.
        source (str): Source spelling that should be preserved or rewritten as a unit.
        end (int): Body offset immediately after the parsed escape sequence.
    """

    value: str
    source: str
    end: int


@dataclasses.dataclass(frozen=True)
class SourceWord:
    """One whitespace-delimited evaluated word with source spelling.

    Attributes:
        value (str): Evaluated word text used for wrapping decisions.
        source (str): Source spelling of the same word used for literal-preserving output.
    """

    value: str
    source: str


@dataclasses.dataclass(frozen=True)
class WrappedSourceLine:
    """One wrapped line in evaluated and source-literal forms.

    Attributes:
        value (str): Evaluated line text after wrapping.
        source (str): Source-literal line text that produces `value`.
    """

    value: str
    source: str


def _source_line(indent: str, words: tuple[SourceWord, ...]) -> WrappedSourceLine:
    """Render one source-aware wrapped line."""
    return WrappedSourceLine(value=f"{indent}{' '.join(word.value for word in words)}", source=f"{indent}{' '.join(word.source for word in words)}")


_SIMPLE_ESCAPES = {"\\": "\\", "'": "'", '"': '"', "a": "\a", "b": "\b", "f": "\f", "n": "\n", "r": "\r", "t": "\t", "v": "\v"}
_SIMPLE_ESCAPE_SOURCES = {value: f"\\{source}" for source, value in _SIMPLE_ESCAPES.items() if source not in {"'", '"', "n"}}


def value_fragments_for_simple_string(node: cst.SimpleString, *, line_ending: str) -> tuple[StringValueFragment, ...] | None:
    """Return source spellings for each evaluated character in a simple string.

    Args:
        node (cst.SimpleString): Simple string literal to decompose.
        line_ending (str): Canonical line ending to associate with physical newline fragments.

    Returns:
        tuple[StringValueFragment, ...] | None: Evaluated characters paired with original source spelling, or None for
            unsupported escapes.

    Raises:
        AssertionError: If an escape parser returns more than one evaluated character for a single fragment.
    """
    body = simple_string_body_source(node)
    if body is None:
        return None
    raw = "r" in node.prefix.lower()
    fragments: list[StringValueFragment] = []
    index = 0
    while index < len(body):
        char = body[index]
        if char == "\r":
            if index + 1 < len(body) and body[index + 1] == "\n":
                fragments.append(StringValueFragment(value="\n", source=line_ending))
                index += 2
            else:
                fragments.append(StringValueFragment(value="\n", source=line_ending))
                index += 1
        elif char == "\n":
            fragments.append(StringValueFragment(value="\n", source=line_ending))
            index += 1
        elif char != "\\" or raw:
            fragments.append(StringValueFragment(value=char, source=char))
            index += 1
        else:
            parsed = parse_simple_string_escape(body, index)
            if parsed is None:
                return None
            index = parsed.end
            if parsed.value:
                if len(parsed.value) != 1:
                    raise AssertionError(f"Expected a single-character escape value, got {parsed.value!r}")
                fragments.append(StringValueFragment(value=parsed.value, source=parsed.source))
    return tuple(fragments)


def simple_string_body_source(node: cst.SimpleString) -> str | None:
    """Return the exact source body between a simple string's delimiters.

    Args:
        node (cst.SimpleString): Simple string literal whose delimiter span should be stripped.

    Returns:
        str | None: Raw body source between the delimiters, or None when the literal spelling is inconsistent.
    """
    value = node.value
    prefix_length = len(node.prefix)
    quote = node.quote
    if not value[prefix_length:].startswith(quote) or not value.endswith(quote):
        return None
    return value[prefix_length + len(quote) : -len(quote)]


def render_simple_string_from_fragments(node: cst.SimpleString, fragments: tuple[StringValueFragment, ...], *, expected_value: str, prefix: str | None = None) -> str | None:
    """Render a simple string from source fragments and validate its value.

    Args:
        node (cst.SimpleString): Original simple string supplying quote style and fallback prefix.
        fragments (tuple[StringValueFragment, ...]): Source fragments to concatenate into the rendered body.
        expected_value (str): Runtime string value that the rendered literal must evaluate to.
        prefix (str | None): Optional replacement prefix such as `r` or an empty prefix.

    Returns:
        str | None: Rendered literal source, or None when parsing or value validation fails.
    """
    body = "".join(fragment.source for fragment in fragments)
    effective_prefix = node.prefix if prefix is None else prefix
    return render_simple_string_from_body_source(effective_prefix, node.quote, body, expected_value=expected_value)


def literalized_whitespace_fragments(fragments: tuple[StringValueFragment, ...], *, line_ending: str) -> tuple[StringValueFragment, ...]:
    """Return fragments with safe normal whitespace escapes rendered literally.

    Args:
        fragments (tuple[StringValueFragment, ...]): Source-aware fragments from a simple string literal.
        line_ending (str): Canonical line ending to use when replacing escaped newline values.

    Returns:
        tuple[StringValueFragment, ...]: Fragments with safe whitespace escapes converted to literal whitespace source.
    """
    literalized: list[StringValueFragment] = []
    for index, fragment in enumerate(fragments):
        previous = fragments[index - 1] if index > 0 else None
        literalized.append(_literalized_whitespace_fragment(fragment, previous=previous, line_ending=line_ending))
    return tuple(literalized)


def retarget_fragments(fragments: tuple[StringValueFragment, ...], *, quote: str, line_ending: str) -> tuple[StringValueFragment, ...]:
    """Return fragments that can be reused in a literal with another quote style.

    Args:
        fragments (tuple[StringValueFragment, ...]): Source-aware fragments to adapt.
        quote (str): Target string delimiter whose embedded quote characters must be escaped.
        line_ending (str): Canonical line ending to use for newline fragments.

    Returns:
        tuple[StringValueFragment, ...]: Fragments safe to render inside the target delimiter.
    """
    return tuple(_retarget_fragment(fragment, quote=quote, line_ending=line_ending) for fragment in fragments)


def render_simple_string_from_body_source(prefix: str, quote: str, body_source: str, *, expected_value: str) -> str | None:
    """Render and validate a simple string from an already escaped body.

    Args:
        prefix (str): String literal prefix to write before the delimiter.
        quote (str): String delimiter to use on both sides of the body.
        body_source (str): Already escaped string body source.
        expected_value (str): Runtime string value that the rendered literal must evaluate to.

    Returns:
        str | None: Rendered literal source, or None when parsing or value validation fails.
    """
    rendered = f"{prefix}{quote}{body_source}{quote}"
    try:
        expression = cst.parse_expression(rendered)
    except Exception:
        return None
    if not isinstance(expression, cst.SimpleString) or expression.evaluated_value != expected_value:
        return None
    return rendered


def render_value_as_simple_string(value: str, *, prefix: str = "", quote: str = '"""', line_ending: str = "\n", escape_non_ascii: bool) -> str | None:
    """Render a value as one simple string literal with canonical escaping.

    Args:
        value (str): Runtime string value to serialize.
        prefix (str): String literal prefix to write before the delimiter.
        quote (str): String delimiter to use on both sides of the body.
        line_ending (str): Canonical line ending to use for newline characters.
        escape_non_ascii (bool): Whether non-ASCII characters should be rendered with escape sequences.

    Returns:
        str | None: Rendered literal source, or None when parsing or value validation fails.
    """
    body = serialize_string_body(value, quote=quote, line_ending=line_ending, escape_non_ascii=escape_non_ascii)
    return render_simple_string_from_body_source(prefix, quote, body, expected_value=value)


def serialize_string_body(value: str, *, quote: str, line_ending: str = "\n", escape_non_ascii: bool) -> str:
    """Serialize a simple string body with explicit non-ASCII escaping policy.

    Args:
        value (str): Runtime string value to serialize.
        quote (str): String delimiter whose embedded quote characters must be escaped.
        line_ending (str): Canonical line ending to use for newline characters.
        escape_non_ascii (bool): Whether non-ASCII characters should be rendered with escape sequences.

    Returns:
        str: Escaped source body without surrounding prefix or delimiters.
    """
    return "".join(_escape_char(char, quote=quote, line_ending=line_ending, escape_non_ascii=escape_non_ascii) for char in value)


def source_for_value_slice(fragments: tuple[StringValueFragment, ...], start_offset: int, end_offset: int) -> str:
    """Return source spelling for one evaluated-value slice.

    Args:
        fragments (tuple[StringValueFragment, ...]): Source-aware fragments indexed by evaluated-character offset.
        start_offset (int): Inclusive evaluated-character start offset.
        end_offset (int): Exclusive evaluated-character end offset.

    Returns:
        str: Concatenated original source spelling for the selected evaluated-value slice.
    """
    return "".join(fragment.source for fragment in fragments[start_offset:end_offset])


def source_words_for_value_slice(fragments: tuple[StringValueFragment, ...], start_offset: int, end_offset: int) -> tuple[SourceWord, ...]:
    """Return whitespace-delimited source-aware words from one evaluated-value slice.

    Args:
        fragments (tuple[StringValueFragment, ...]): Source-aware fragments indexed by evaluated-character offset.
        start_offset (int): Inclusive evaluated-character start offset.
        end_offset (int): Exclusive evaluated-character end offset.

    Returns:
        tuple[SourceWord, ...]: Non-whitespace words preserving both evaluated text and source spelling.
    """
    words: list[SourceWord] = []
    value_parts: list[str] = []
    source_parts: list[str] = []
    for fragment in fragments[start_offset:end_offset]:
        if fragment.value.isspace():
            if value_parts:
                words.append(SourceWord(value="".join(value_parts), source="".join(source_parts)))
                value_parts = []
                source_parts = []
        else:
            value_parts.append(fragment.value)
            source_parts.append(fragment.source)
    if value_parts:
        words.append(SourceWord(value="".join(value_parts), source="".join(source_parts)))
    return tuple(words)


def wrap_source_words(
    words: tuple[SourceWord, ...],
    *,
    width: int,
    initial_indent: str = "",
    subsequent_indent: str = "",
    tab_width: int,
    initial_width: int | None = None,
    subsequent_width: int | None = None,
    final_suffix_width: int = 0,
    url_aware: bool = False,
) -> tuple[WrappedSourceLine, ...]:
    """Wrap words using their final source spelling for width calculations.

    When variable budgets are supplied, `width` is only the fallback for unspecified initial or subsequent widths, and
    `final_suffix_width` is reserved on the final generated line.

    Args:
        words (tuple[SourceWord, ...]): Source-aware words to group into output lines.
        width (int): Fallback maximum line width in display columns.
        initial_indent (str): Prefix to add to the first output line.
        subsequent_indent (str): Prefix to add to continuation output lines.
        tab_width (int): Tab stop width used when measuring indentation and source words.
        initial_width (int | None): Optional content width for the first output line.
        subsequent_width (int | None): Optional content width for continuation lines.
        final_suffix_width (int): Display width reserved on the final output line.
        url_aware (bool): Whether URL tokens should remain intact and use balanced wrapping.

    Returns:
        tuple[WrappedSourceLine, ...]: Wrapped lines preserving source spelling for each word.
    """
    if url_aware and any(text_layout.is_url_token(word.value) for word in words):
        return _wrap_source_words_with_balanced_spans(
            words,
            width=width,
            initial_width=initial_width,
            subsequent_width=subsequent_width,
            final_suffix_width=final_suffix_width,
            initial_indent=initial_indent,
            subsequent_indent=subsequent_indent,
            tab_width=tab_width,
        )
    if initial_width is not None or subsequent_width is not None or final_suffix_width:
        return _wrap_source_words_with_variable_widths(
            words,
            initial_width=width if initial_width is None else initial_width,
            subsequent_width=width if subsequent_width is None else subsequent_width,
            final_suffix_width=final_suffix_width,
            initial_indent=initial_indent,
            subsequent_indent=subsequent_indent,
            tab_width=tab_width,
        )
    if not words:
        stripped = initial_indent.rstrip()
        return (WrappedSourceLine(value=stripped, source=stripped),)
    if width <= 0:
        return tuple(
            WrappedSourceLine(value=f"{initial_indent if index == 0 else subsequent_indent}{word.value}", source=f"{initial_indent if index == 0 else subsequent_indent}{word.source}")
            for index, word in enumerate(words)
        )

    lines: list[WrappedSourceLine] = []
    current_indent = initial_indent
    current_words: list[SourceWord] = []

    def current_source(candidate_words: list[SourceWord]) -> str:
        return f"{current_indent}{' '.join(word.source for word in candidate_words)}"

    for word in words:
        candidate = [*current_words, word]
        if current_words and text_layout.display_width(current_source(candidate), tab_width=tab_width) > width:
            lines.append(_source_line(current_indent, tuple(current_words)))
            current_indent = subsequent_indent
            current_words = [word]
        else:
            current_words = candidate
    if current_words:
        lines.append(_source_line(current_indent, tuple(current_words)))
    return tuple(lines)


def _wrap_source_words_with_balanced_spans(
    words: tuple[SourceWord, ...], *, width: int, initial_width: int | None, subsequent_width: int | None, final_suffix_width: int, initial_indent: str, subsequent_indent: str, tab_width: int
) -> tuple[WrappedSourceLine, ...]:
    """Wrap source words with shared URL-aware balanced spans."""
    if not words:
        stripped = initial_indent.rstrip()
        return (WrappedSourceLine(value=stripped, source=stripped),)
    spans = text_layout.balanced_word_spans(
        tuple(word.value for word in words),
        width_words=tuple(word.source for word in words),
        width=width,
        initial_width=initial_width,
        subsequent_width=subsequent_width,
        final_suffix_width=final_suffix_width,
        initial_indent=initial_indent,
        subsequent_indent=subsequent_indent,
        tab_width=tab_width,
    )
    return tuple(_source_line(initial_indent if index == 0 else subsequent_indent, words[span.start : span.end]) for index, span in enumerate(spans))


def _wrap_source_words_with_variable_widths(
    words: tuple[SourceWord, ...], *, initial_width: int, subsequent_width: int, final_suffix_width: int, initial_indent: str, subsequent_indent: str, tab_width: int
) -> tuple[WrappedSourceLine, ...]:
    """Wrap words when first, continuation, or final physical lines have different budgets."""
    if not words:
        stripped = initial_indent.rstrip()
        return (WrappedSourceLine(value=stripped, source=stripped),)

    lines: list[WrappedSourceLine] = []
    start = 0
    first_line = True
    while start < len(words):
        indent = initial_indent if first_line else subsequent_indent
        column = text_layout.display_width(indent, tab_width=tab_width)
        chosen_end = start + 1
        for end in range(start + 1, len(words) + 1):
            if end > start + 1:
                column += 1
            column = text_layout.advance_display_column(column, words[end - 1].source, tab_width=tab_width)
            final_line = end == len(words)
            limit = initial_width if first_line else subsequent_width
            if final_line:
                limit -= final_suffix_width
            single_word = end == start + 1
            if single_word or (limit > 0 and column <= limit):
                chosen_end = end
            elif final_suffix_width >= 0:
                # Once a prefix overflows, longer prefixes cannot fit under nonnegative suffix reservation.
                break
        lines.append(_source_line(indent, words[start:chosen_end]))
        start = chosen_end
        first_line = False
    return tuple(lines)


def fragments_for_concatenated_string(node: cst.ConcatenatedString, *, target_quote: str, line_ending: str) -> tuple[StringValueFragment, ...] | None:
    """Return source-preserving fragments for a concatenated string in a target literal.

    Args:
        node (cst.ConcatenatedString): Concatenated string expression to flatten.
        target_quote (str): Target delimiter whose embedded quote characters must be escaped.
        line_ending (str): Canonical line ending to use for newline fragments.

    Returns:
        tuple[StringValueFragment, ...] | None: Flattened fragments safe for the target delimiter, or None for
            unsupported parts.
    """
    fragments: list[StringValueFragment] = []
    parts = _iter_simple_string_parts(node)
    if parts is None:
        return None
    for part in parts:
        part_fragments = value_fragments_for_simple_string(part, line_ending=line_ending)
        if part_fragments is None:
            return None
        fragments.extend(_retarget_fragment(fragment, quote=target_quote, line_ending=line_ending) for fragment in part_fragments)
    return tuple(fragments)


def _iter_simple_string_parts(node: cst.ConcatenatedString) -> tuple[cst.SimpleString, ...] | None:
    """Return all simple-string leaves in a concatenation tree."""
    parts: list[cst.SimpleString] = []

    def visit(part: cst.BaseExpression) -> bool:
        if isinstance(part, cst.SimpleString):
            parts.append(part)
            return True
        if isinstance(part, cst.ConcatenatedString):
            return visit(part.left) and visit(part.right)
        return False

    if not visit(node):
        return None
    return tuple(parts)


def parse_simple_string_escape(body: str, start: int) -> StringEscape | None:
    """Return the parsed escape at start in a simple string body.

    Args:
        body (str): Raw simple-string body source without delimiters.
        start (int): Offset of the backslash that begins the escape.

    Returns:
        StringEscape | None: Parsed escape value, source, and end offset, or None for unsupported escape syntax.
    """
    if start + 1 >= len(body):
        return None
    escaped = body[start + 1]
    if escaped == "\r":
        if start + 2 < len(body) and body[start + 2] == "\n":
            return StringEscape(value="", source="", end=start + 3)
        return StringEscape(value="", source="", end=start + 2)
    if escaped == "\n":
        return StringEscape(value="", source="", end=start + 2)
    if escaped in _SIMPLE_ESCAPES:
        return StringEscape(value=_SIMPLE_ESCAPES[escaped], source=body[start : start + 2], end=start + 2)
    if escaped == "x" and _has_hex_digits(body, start + 2, 2):
        source = body[start : start + 4]
        return StringEscape(value=chr(int(body[start + 2 : start + 4], 16)), source=source, end=start + 4)
    if escaped == "u" and _has_hex_digits(body, start + 2, 4):
        source = body[start : start + 6]
        return StringEscape(value=chr(int(body[start + 2 : start + 6], 16)), source=source, end=start + 6)
    if escaped == "U" and _has_hex_digits(body, start + 2, 8):
        source = body[start : start + 10]
        return StringEscape(value=chr(int(body[start + 2 : start + 10], 16)), source=source, end=start + 10)
    if escaped in string.octdigits:
        end = start + 2
        while end < min(start + 4, len(body)) and body[end] in string.octdigits:
            end += 1
        source = body[start:end]
        return StringEscape(value=chr(int(body[start + 1 : end], 8)), source=source, end=end)
    if escaped == "N":
        end = body.find("}", start + 2)
        if end == -1 or start + 2 >= len(body) or body[start + 2] != "{":
            return None
        source = body[start : end + 1]
        try:
            expression = cst.parse_expression(f'"{source}"')
            evaluated_value = expression.evaluated_value if isinstance(expression, cst.SimpleString) else None
        except Exception:
            return None
        if not isinstance(evaluated_value, str) or len(evaluated_value) != 1:
            return None
        return StringEscape(value=evaluated_value, source=source, end=end + 1)
    return None


def _has_hex_digits(text: str, start: int, length: int) -> bool:
    """Return whether a text span contains exactly the requested number of hex digits."""
    return start + length <= len(text) and all(char in string.hexdigits for char in text[start : start + length])


def _retarget_fragment(fragment: StringValueFragment, *, quote: str, line_ending: str) -> StringValueFragment:
    """Return a value fragment whose source is safe for a target quote delimiter."""
    quote_char = "'" if "'" in quote else '"'
    if fragment.source == fragment.value and len(fragment.value) == 1 and fragment.value not in {"\\", "\r", "\n", quote_char}:
        return fragment
    rendered = render_simple_string_from_body_source("", quote, fragment.source, expected_value=fragment.value)
    if rendered is not None:
        return fragment
    return StringValueFragment(value=fragment.value, source=_escape_char(fragment.value, quote=quote, line_ending=line_ending, escape_non_ascii=False))


def _literalized_whitespace_fragment(fragment: StringValueFragment, *, previous: StringValueFragment | None, line_ending: str) -> StringValueFragment:
    """Return literal newline and tab fragments when escape spellings can be preserved as whitespace."""
    if fragment.value == "\n" and fragment.source == r"\n" and (previous is None or previous.value != "\r"):
        return StringValueFragment(value=fragment.value, source=line_ending)
    if fragment.value == "\t" and fragment.source == r"\t":
        return StringValueFragment(value=fragment.value, source="\t")
    return fragment


def _escape_char(char: str, *, quote: str, line_ending: str = "\n", escape_non_ascii: bool) -> str:
    """Return source text for one character inside a simple string body."""
    quote_char = "'" if "'" in quote else '"'
    codepoint = ord(char)
    if char == quote_char:
        return f"\\{char}"
    if char == "\n":
        return line_ending
    if char in _SIMPLE_ESCAPE_SOURCES:
        return _SIMPLE_ESCAPE_SOURCES[char]
    if codepoint < 0x80 and char.isprintable():
        return char
    if not escape_non_ascii and char.isprintable():
        return char
    if codepoint <= 0xFF:
        return f"\\x{codepoint:02x}"
    if codepoint <= 0xFFFF:
        return f"\\u{codepoint:04x}"
    return f"\\U{codepoint:08x}"
