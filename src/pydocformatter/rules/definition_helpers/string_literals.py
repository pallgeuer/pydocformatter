"""Source-preserving Python string literal helpers."""

# Future imports
from __future__ import annotations

# Standard library imports
import enum
import bisect
import string
import warnings
import dataclasses
from collections.abc import Sequence

# Third-party imports
import libcst as cst

# First-party imports
from pydocformatter.rules.definition_helpers import inline_markup, text_layout


@dataclasses.dataclass(frozen=True)
class StringValueFragment:
    """Source spelling for one evaluated string character.

    Attributes:
        value (str): Evaluated string fragment represented by the source spelling.
        source (str): Source characters that produce `value`.
    """

    value: str
    source: str


class StringNewlineOrigin(enum.Enum):
    r"""Source origin of an evaluated newline character.

    Attributes:
        PHYSICAL: A physical LF, CR, or CRLF sequence in the literal body.
        ESCAPE: A value-producing Python escape such as ``\\n``.
    """

    PHYSICAL = "physical"
    ESCAPE = "escape"


@dataclasses.dataclass(frozen=True)
class SimpleStringSourceMap:
    """Lossless mapping between evaluated characters and literal body source.

    Attributes:
        body_source (str): Exact source between the literal delimiters.
        value (str): Evaluated string value represented by the map.
        fragments (tuple[StringValueFragment, ...]): One source-aware fragment per evaluated character.
        owned_source_starts (tuple[int, ...]): Body offsets where source owned by each evaluated offset begins.
        producing_source_starts (tuple[int, ...]): Body offsets where each character-producing source spelling begins.
        newline_origins (tuple[StringNewlineOrigin | None, ...]): Source origin for each evaluated newline character.
        physical_newline_ends (tuple[int, ...]): Exclusive body offsets of physical LF, CR, and CRLF sequences.
    """

    body_source: str
    value: str
    fragments: tuple[StringValueFragment, ...]
    owned_source_starts: tuple[int, ...]
    producing_source_starts: tuple[int, ...]
    newline_origins: tuple[StringNewlineOrigin | None, ...]
    physical_newline_ends: tuple[int, ...]

    def owned_source_for_value_slice(self, start_offset: int, end_offset: int) -> str:
        """Return exact source owned by an evaluated-value slice.

        Args:
            start_offset (int): Evaluated offset where the slice starts.
            end_offset (int): Evaluated offset immediately after the slice.

        Returns:
            str: Original source spelling owned by the slice.

        Raises:
            ValueError: If the slice is outside the evaluated value.
        """
        self._validate_value_slice(start_offset, end_offset)
        source_end = len(self.body_source) if end_offset == len(self.fragments) else self.owned_source_starts[end_offset]
        return self.body_source[self.owned_source_starts[start_offset] : source_end]

    def source_offset_for_value_offset(self, value_offset: int, *, include_leading_zero_value_source: bool = False) -> int:
        """Return the body-source offset matching an evaluated-value offset.

        Args:
            value_offset (int): Evaluated offset to map.
            include_leading_zero_value_source (bool): Whether preceding zero-value source belongs to the mapped offset.

        Returns:
            int: Corresponding offset in the literal body source.

        Raises:
            ValueError: If the offset is outside the evaluated value.
        """
        if not 0 <= value_offset <= len(self.fragments):
            raise ValueError("String source-map offset is outside the evaluated value")
        if value_offset == len(self.fragments):
            return self.owned_source_starts[value_offset] if include_leading_zero_value_source else len(self.body_source)
        return self.owned_source_starts[value_offset] if include_leading_zero_value_source else self.producing_source_starts[value_offset]

    def producing_source_for_value_slice(self, start_offset: int, end_offset: int) -> str:
        """Return character-producing source for an evaluated-value slice.

        Args:
            start_offset (int): Evaluated offset where the slice starts.
            end_offset (int): Evaluated offset immediately after the slice.

        Returns:
            str: Concatenated source spelling that produces the slice characters.

        Raises:
            ValueError: If the slice is outside the evaluated value.
        """
        self._validate_value_slice(start_offset, end_offset)
        return "".join(fragment.source for fragment in self.fragments[start_offset:end_offset])

    def preserved_source_for_value_deletion(self, start_offset: int, end_offset: int) -> str:
        """Return internal zero-value source that must survive a value deletion.

        Args:
            start_offset (int): Evaluated offset where the deletion starts.
            end_offset (int): Evaluated offset immediately after the deletion.

        Returns:
            str: Zero-value source occurring between deleted evaluated characters.

        Raises:
            ValueError: If the slice is outside the evaluated value.
        """
        self._validate_value_slice(start_offset, end_offset)
        return "".join(self.body_source[self.owned_source_starts[index] : self.producing_source_starts[index]] for index in range(start_offset + 1, end_offset))

    def body_source_with_replacements(self, replacements: Sequence[tuple[int, int, str]], *, preserve_zero_value_source: bool = True) -> str:
        """Return body source after sorted non-overlapping evaluated-value replacements.

        Args:
            replacements (Sequence[tuple[int, int, str]]): Evaluated start, end, and replacement-source triples.
            preserve_zero_value_source (bool): Whether source continuations adjacent to replacements remain unchanged.

        Returns:
            str: Literal body source with the replacements applied.

        Raises:
            ValueError: If a replacement is invalid, out of order, or overlapping.
        """
        chunks: list[str] = []
        cursor_offset = 0
        cursor_source = 0
        for start_offset, end_offset, text in replacements:
            self._validate_value_slice(start_offset, end_offset)
            if start_offset < cursor_offset:
                raise ValueError("String source-map replacements must be sorted and non-overlapping")
            replacement_source_start = self.source_offset_for_value_offset(start_offset, include_leading_zero_value_source=not preserve_zero_value_source)
            replacement_source_end = replacement_source_start if start_offset == end_offset else self.source_offset_for_value_offset(end_offset, include_leading_zero_value_source=True)
            chunks.extend((self.body_source[cursor_source:replacement_source_start], text))
            cursor_offset = end_offset
            cursor_source = replacement_source_end
        chunks.append(self.body_source[cursor_source:])
        return "".join(chunks)

    def body_source_for_fragments(self, fragments: Sequence[StringValueFragment]) -> str:
        """Return body source with transformed character fragments and preserved zero-value source.

        Args:
            fragments (Sequence[StringValueFragment]): Replacement fragment for every evaluated character.

        Returns:
            str: Literal body source containing the transformed fragments.

        Raises:
            ValueError: If the replacement fragment count differs from the mapped value length.
        """
        if len(fragments) != len(self.fragments):
            raise ValueError("Transformed fragments must match the source map's evaluated value length")
        chunks: list[str] = []
        for index, fragment in enumerate(fragments):
            chunks.extend((self.body_source[self.owned_source_starts[index] : self.producing_source_starts[index]], fragment.source))
        chunks.append(self.body_source[self.owned_source_starts[-1] :])
        return "".join(chunks)

    def physical_line_numbers(self, start_offset: int, end_offset: int, *, first_line_number: int) -> tuple[int, ...]:
        """Return physical source lines touched by an evaluated-value slice.

        Args:
            start_offset (int): Evaluated offset where the slice starts.
            end_offset (int): Evaluated offset immediately after the slice.
            first_line_number (int): Physical source line containing the literal body start.

        Returns:
            tuple[int, ...]: One-based physical source lines owned by the slice.

        Raises:
            ValueError: If the slice is outside the evaluated value.
        """
        self._validate_value_slice(start_offset, end_offset)
        source_start = self.owned_source_starts[start_offset]
        source_end = len(self.body_source) if end_offset == len(self.fragments) else self.owned_source_starts[end_offset]
        start_line = first_line_number + bisect.bisect_right(self.physical_newline_ends, source_start)
        end_line = first_line_number + bisect.bisect_right(self.physical_newline_ends, source_end)
        return tuple(range(start_line, end_line + 1))

    def has_escaped_newline(self, start_offset: int, end_offset: int) -> bool:
        """Return whether a value slice contains a value-producing newline escape.

        Args:
            start_offset (int): Evaluated offset where the slice starts.
            end_offset (int): Evaluated offset immediately after the slice.

        Returns:
            bool: Whether the slice contains an escaped logical newline.

        Raises:
            ValueError: If the slice is outside the evaluated value.
        """
        self._validate_value_slice(start_offset, end_offset)
        return any(origin is StringNewlineOrigin.ESCAPE for origin in self.newline_origins[start_offset:end_offset])

    def _validate_value_slice(self, start_offset: int, end_offset: int) -> None:
        """Validate one half-open evaluated-value slice.

        Args:
            start_offset (int): Evaluated offset where the slice starts.
            end_offset (int): Evaluated offset immediately after the slice.

        Raises:
            ValueError: If the slice is outside the evaluated value.
        """
        if not 0 <= start_offset <= end_offset <= len(self.fragments):
            raise ValueError("String source-map slice is outside the evaluated value")


@dataclasses.dataclass(frozen=True)
class SimpleStringPart:
    """One evaluated simple-string leaf of a string expression.

    Attributes:
        node (cst.SimpleString): Simple-string syntax leaf.
        value_start (int): Inclusive offset of the leaf in the complete evaluated value.
        value_end (int): Exclusive offset of the leaf in the complete evaluated value.
        value (str): Evaluated value of the leaf.
        source_map (SimpleStringSourceMap | None): Lossless mapping for the leaf body, or None when its source spelling
            is unsupported.
    """

    node: cst.SimpleString
    value_start: int
    value_end: int
    value: str
    source_map: SimpleStringSourceMap | None


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
class WrappedSourceLine:
    """One wrapped line in evaluated and source-literal forms.

    Attributes:
        value (str): Evaluated line text after wrapping.
        source (str): Source-literal line text that produces `value`.
    """

    value: str
    source: str


def _source_line(indent: str, tokens: tuple[inline_markup.InlineToken, ...]) -> WrappedSourceLine:
    """Render one source-aware wrapped line."""
    return WrappedSourceLine(value=f"{indent}{' '.join(token.value for token in tokens)}", source=f"{indent}{' '.join(token.source for token in tokens)}")


_SIMPLE_ESCAPES = {"\\": "\\", "'": "'", '"': '"', "a": "\a", "b": "\b", "f": "\f", "n": "\n", "r": "\r", "t": "\t", "v": "\v"}
_SIMPLE_ESCAPE_SOURCES = {value: f"\\{source}" for source, value in _SIMPLE_ESCAPES.items() if source not in {"'", '"', "n"}}


def value_fragments_for_simple_string(node: cst.SimpleString) -> tuple[StringValueFragment, ...] | None:
    """Return source spellings for each evaluated character in a simple string.

    Args:
        node (cst.SimpleString): Simple string literal to decompose.

    Returns:
        tuple[StringValueFragment, ...] | None: Evaluated characters paired with original source spelling, or None for
            unsupported escapes.

    Raises:
        AssertionError: If an escape parser returns more than one evaluated character for a single fragment.
    """
    source_map = source_map_for_simple_string(node)
    return None if source_map is None else source_map.fragments


def source_map_for_simple_string(node: cst.SimpleString, *, value: str | None = None) -> SimpleStringSourceMap | None:
    """Return a lossless evaluated-value/source map for a simple string.

    Unsupported escape spellings deliberately return ``None`` even when the running Python version still evaluates them,
    keeping rewrite behavior conservative.

    Args:
        node (cst.SimpleString): Simple string literal to map.
        value (str | None): Optional previously evaluated string value.

    Returns:
        SimpleStringSourceMap | None: Lossless map, or None when the literal cannot be mapped conservatively.

    Raises:
        AssertionError: If a supported escape produces more than one evaluated character.
    """
    body = simple_string_body_source(node)
    if value is None:
        try:
            evaluated_value = node.evaluated_value
        except (SyntaxError, ValueError):
            return None
        value = evaluated_value if isinstance(evaluated_value, str) else None
    if body is None or not isinstance(value, str):
        return None
    raw = "r" in node.prefix.lower()
    fragments: list[StringValueFragment] = []
    owned_source_starts: list[int] = []
    producing_source_starts: list[int] = []
    newline_origins: list[StringNewlineOrigin | None] = []
    pending_source_start = 0
    index = 0
    while index < len(body):
        fragment_source_start = index
        char = body[index]
        origin: StringNewlineOrigin | None = None
        if char == "\r":
            source = "\r\n" if index + 1 < len(body) and body[index + 1] == "\n" else "\r"
            fragment_value = "\n"
            index += len(source)
            origin = StringNewlineOrigin.PHYSICAL
        elif char == "\n":
            source = "\n"
            fragment_value = "\n"
            index += 1
            origin = StringNewlineOrigin.PHYSICAL
        elif char != "\\" or raw:
            source = char
            fragment_value = char
            index += 1
        else:
            parsed = parse_simple_string_escape(body, index)
            if parsed is None:
                return None
            source = parsed.source
            fragment_value = parsed.value
            index = parsed.end
            if not fragment_value:
                continue
            if fragment_value in {"\r", "\n"}:
                origin = StringNewlineOrigin.ESCAPE
        if len(fragment_value) != 1:
            raise AssertionError(f"Expected a single-character escape value, got {fragment_value!r}")
        owned_source_starts.append(pending_source_start)
        producing_source_starts.append(fragment_source_start)
        fragments.append(StringValueFragment(value=fragment_value, source=source))
        newline_origins.append(origin)
        pending_source_start = index
    owned_source_starts.append(pending_source_start)
    mapped_value = "".join(fragment.value for fragment in fragments)
    if mapped_value != value:
        return None
    return SimpleStringSourceMap(
        body_source=body,
        value=value,
        fragments=tuple(fragments),
        owned_source_starts=tuple(owned_source_starts),
        producing_source_starts=tuple(producing_source_starts),
        newline_origins=tuple(newline_origins),
        physical_newline_ends=_physical_newline_ends(body),
    )


def simple_string_parts(node: cst.SimpleString | cst.ConcatenatedString, *, value: str | None = None) -> tuple[SimpleStringPart, ...] | None:
    """Return evaluated simple-string leaves and complete-value offsets.

    Args:
        node (cst.SimpleString | cst.ConcatenatedString): String expression to flatten.
        value (str | None): Optional expected value of the complete expression.

    Returns:
        tuple[SimpleStringPart, ...] | None: Ordered evaluated leaves with optional source maps, or None for unsupported
            syntax, evaluation, or a mismatched complete value.
    """
    leaves = simple_string_leaves(node)
    if leaves is None:
        return None
    parts: list[SimpleStringPart] = []
    value_start = 0
    for leaf in leaves:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                leaf_value = leaf.evaluated_value
        except (SyntaxError, ValueError):
            return None
        if not isinstance(leaf_value, str):
            return None
        source_map = source_map_for_simple_string(leaf, value=leaf_value)
        value_end = value_start + len(leaf_value)
        parts.append(SimpleStringPart(node=leaf, value_start=value_start, value_end=value_end, value=leaf_value, source_map=source_map))
        value_start = value_end
    if value is not None and "".join(part.value for part in parts) != value:
        return None
    return tuple(parts)


def simple_string_has_direct_line_mapping(node: cst.SimpleString, *, value: str) -> bool:
    """Return whether a simple string maps logical lines directly to physical lines.

    Args:
        node (cst.SimpleString): Simple string literal to inspect.
        value (str): Previously evaluated string value.

    Returns:
        bool: Whether supported source spellings produce `value` without value-producing newline escapes.

    Raises:
        AssertionError: If a supported escape produces more than one evaluated character.
    """
    body = simple_string_body_source(node)
    if body is None:
        return False
    raw = "r" in node.prefix.lower()
    source_index = 0
    value_index = 0
    while source_index < len(body):
        char = body[source_index]
        if char == "\r":
            fragment_value = "\n"
            source_index += 2 if source_index + 1 < len(body) and body[source_index + 1] == "\n" else 1
        elif char == "\n":
            fragment_value = "\n"
            source_index += 1
        elif char != "\\" or raw:
            fragment_value = char
            source_index += 1
        else:
            parsed = parse_simple_string_escape(body, source_index)
            if parsed is None:
                return False
            fragment_value = parsed.value
            source_index = parsed.end
            if not fragment_value:
                continue
            if fragment_value in {"\r", "\n"}:
                return False
        if len(fragment_value) != 1:
            raise AssertionError(f"Expected a single-character escape value, got {fragment_value!r}")
        if value_index >= len(value) or value[value_index] != fragment_value:
            return False
        value_index += 1
    return value_index == len(value)


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


def render_simple_string_from_source_map(
    node: cst.SimpleString, source_map: SimpleStringSourceMap, fragments: tuple[StringValueFragment, ...], *, expected_value: str, prefix: str | None = None
) -> str | None:
    """Render transformed fragments while preserving zero-value source spans.

    Args:
        node (cst.SimpleString): Original simple string supplying its delimiter.
        source_map (SimpleStringSourceMap): Lossless map supplying zero-value source spans.
        fragments (tuple[StringValueFragment, ...]): Replacement fragment for every evaluated character.
        expected_value (str): Evaluated value required from the rendered literal.
        prefix (str | None): Optional replacement literal prefix.

    Returns:
        str | None: Rendered literal source, or None when validation fails.
    """
    body = source_map.body_source_for_fragments(fragments)
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


def wrap_source_tokens(
    tokens: tuple[inline_markup.InlineToken, ...],
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
    """Wrap inline tokens using their source spelling for width calculations.

    When variable budgets are supplied, `width` is only the fallback for unspecified initial or subsequent widths, and
    `final_suffix_width` is reserved on the final generated line.

    Args:
        tokens (tuple[inline_markup.InlineToken, ...]): Source-aware tokens to group into output lines.
        width (int): Fallback maximum line width in display columns.
        initial_indent (str): Prefix to add to the first output line.
        subsequent_indent (str): Prefix to add to continuation output lines.
        tab_width (int): Tab stop width used when measuring indentation and source words.
        initial_width (int | None): Optional content width for the first output line.
        subsequent_width (int | None): Optional content width for continuation lines.
        final_suffix_width (int): Display width reserved on the final output line.
        url_aware (bool): Whether destination-bearing tokens should use balanced wrapping.

    Returns:
        tuple[WrappedSourceLine, ...]: Wrapped lines preserving source spelling for each word.
    """
    if not tokens:
        stripped = initial_indent.rstrip()
        return (WrappedSourceLine(value=stripped, source=stripped),)
    spans = text_layout.token_spans(
        tokens,
        width_words=tuple(token.source for token in tokens),
        width=width,
        initial_indent=initial_indent,
        subsequent_indent=subsequent_indent,
        tab_width=tab_width,
        initial_width=initial_width,
        subsequent_width=subsequent_width,
        final_suffix_width=final_suffix_width,
        url_aware=url_aware,
    )
    return tuple(_source_line(initial_indent if index == 0 else subsequent_indent, tokens[span.start : span.end]) for index, span in enumerate(spans))


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
    parts = simple_string_parts(node)
    if parts is None:
        return None
    for part in parts:
        if part.source_map is None:
            return None
        fragments.extend(_retarget_fragment(fragment, quote=target_quote, line_ending=line_ending) for fragment in part.source_map.fragments)
    return tuple(fragments)


def simple_string_leaves(node: cst.SimpleString | cst.ConcatenatedString) -> tuple[cst.SimpleString, ...] | None:
    """Return all simple-string leaves in a string expression.

    Args:
        node (cst.SimpleString | cst.ConcatenatedString): String expression to traverse.

    Returns:
        tuple[cst.SimpleString, ...] | None: Ordered leaves, or None when a non-simple expression is encountered.
    """
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
            return StringEscape(value="", source=body[start : start + 3], end=start + 3)
        return StringEscape(value="", source=body[start : start + 2], end=start + 2)
    if escaped == "\n":
        return StringEscape(value="", source=body[start : start + 2], end=start + 2)
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


def _physical_newline_ends(text: str) -> tuple[int, ...]:
    """Return exclusive offsets of physical LF, CR, and CRLF sequences."""
    ends: list[int] = []
    index = 0
    while index < len(text):
        if text[index] == "\r":
            index += 2 if index + 1 < len(text) and text[index + 1] == "\n" else 1
            ends.append(index)
        elif text[index] == "\n":
            index += 1
            ends.append(index)
        else:
            index += 1
    return tuple(ends)


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
