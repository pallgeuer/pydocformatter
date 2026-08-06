"""Docstring source mapping and edit planning."""

# Future imports
from __future__ import annotations

# Standard library imports
import typing

# Third-party imports
import libcst as cst
import libcst.metadata as cst_metadata

# First-party imports
import pydocformatter.rules.edits as rule_edits
from pydocformatter.rules.definition_helpers import ascii_whitespace, source_text, string_literals, text_layout


if typing.TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.definition import RuleContext
    from pydocformatter.rules.definitions.PDF.PDF import DocstringInfo, DocstringValueLine


_INDENTATION_WHITESPACE = f"{ascii_whitespace.SPACE_AND_TAB}\f"


def is_same_line_closing_delimiter_prefix(docstring: DocstringInfo, line: DocstringValueLine) -> bool:
    """Return whether a value line prefixes same-line closing quotes.

    Args:
        docstring (DocstringInfo): Simple or suite docstring that owns the logical line.
        line (DocstringValueLine): Logical value line to compare against the docstring terminator position.

    Returns:
        True when the line is the final logical line of a non-empty docstring value without a trailing newline.
    """
    return line.index == len(docstring.structure.lines) - 1 and docstring.value != "" and not docstring_value_ends_with_newline(docstring)


def is_same_line_opening_delimiter_suffix(docstring: DocstringInfo, line: DocstringValueLine) -> bool:
    """Return whether a value line follows opening quotes before a physical line break.

    Args:
        docstring (DocstringInfo): Simple or suite docstring that owns the logical line.
        line (DocstringValueLine): Logical value line to compare against the docstring opener position.

    Returns:
        True when the first mapped logical line contains only ASCII spaces and tabs before a later physical line.
    """
    return line.index == 0 and line.source_line_number is not None and len(docstring.structure.lines) > 1 and not line.raw_text.strip(ascii_whitespace.SPACE_AND_TAB)


def is_safely_mapped_simple_docstring(docstring: DocstringInfo, *, require_multiline: bool = False) -> bool:
    """Return whether a simple docstring is safely mapped by evaluated line.

    Args:
        docstring (DocstringInfo): Docstring candidate whose source mapping must be a LibCST simple string with mapped
            logical lines.
        require_multiline (bool): Whether single-line simple strings should be rejected for callers that only operate on
            multiline layouts.

    Returns:
        bool: Whether every parsed value line maps to concrete source and source-preserving edits can retain spelling.
    """
    return (
        isinstance(docstring.node, cst.SimpleString) and (not require_multiline or len(docstring.physical_lines) > 1) and all(line.source_line_number is not None for line in docstring.structure.lines)
    )


def can_canonically_rewrite_simple_docstring(docstring: DocstringInfo, *, require_multiline: bool = False) -> bool:
    """Return whether a simple docstring permits canonical payload reconstruction.

    Args:
        docstring (DocstringInfo): Docstring candidate whose evaluated lines and Unicode policy must permit rewriting.
        require_multiline (bool): Whether single-line simple strings should be rejected.

    Returns:
        bool: Whether mapped source can be reconstructed without consuming suspicious Unicode.
    """
    return is_safely_mapped_simple_docstring(docstring, require_multiline=require_multiline) and not docstring.has_unicode_rewrite_barrier


def docstring_canonical_margin(docstring: DocstringInfo, *, context: RuleContext) -> str:
    """Return the raw indentation margin for continuation and aligned blank lines.

    Args:
        docstring (DocstringInfo): Docstring whose opening source column determines the reusable margin.
        context (RuleContext): Rule context providing file source and indentation settings.

    Returns:
        Raw whitespace prefix that should be used for generated continuation lines in the docstring body.
    """
    source_line = context.source_lines[docstring.range.start.line - 1]
    if isinstance(docstring.statement, cst.SimpleStatementSuite):
        return f"{_effective_indentation(source_line)}{text_layout.indent_unit(context.settings)}"
    source_prefix = source_line[: docstring.range.start.column]
    if _has_preceding_small_statement(docstring):
        return " " * len(source_prefix.rsplit("\f", maxsplit=1)[-1])
    if not source_prefix.strip(_INDENTATION_WHITESPACE):
        return source_prefix.rsplit("\f", maxsplit=1)[-1]
    return _effective_indentation(source_line)


def _effective_indentation(source_line: str) -> str:
    """Return leading spaces and tabs after the final indentation form feed."""
    physical_indent = source_line[: len(source_line) - len(source_line.lstrip(_INDENTATION_WHITESPACE))]
    return physical_indent.rsplit("\f", maxsplit=1)[-1]


def _has_preceding_small_statement(docstring: DocstringInfo) -> bool:
    """Return whether an attached docstring follows another statement on its source line."""
    if not isinstance(docstring.statement, cst.SimpleStatementLine):
        return False
    for index, statement in enumerate(docstring.statement.body):
        if statement is docstring.expression:
            return index > 0
    return False


def planned_simple_docstring_line_change(docstring: DocstringInfo, *, raw_line_targets: tuple[str | None, ...]) -> rule_edits.PlannedSourceChange | None:
    """Return one whole-literal replacement for changed raw evaluated lines.

    Args:
        docstring (DocstringInfo): Simple docstring whose logical line bodies may be replaced.
        raw_line_targets (tuple[str | None, ...]): Target raw value text for each logical line, with None preserving the
            existing line.

    Returns:
        Planned replacement for the whole string literal, or None when no line changes or no safe source rendering is available.

    Raises:
        ValueError: Raised when the caller provides a target tuple that does not match the parsed logical line count.
    """
    if len(raw_line_targets) != len(docstring.structure.lines):
        raise ValueError("Raw line targets must match the docstring line count")
    replacements: list[rule_edits.PlannedTextReplacement] = []
    for line, target in zip(docstring.structure.lines, raw_line_targets, strict=True):
        line_number = line.source_line_number
        if target is not None and line_number is not None and line.raw_text != target:
            replacements.append(rule_edits.PlannedTextReplacement(start_offset=line.start_offset, end_offset=line.end_offset, text=target, line_numbers=(line_number,)))
    if not replacements:
        return None
    value_lines = [target if target is not None else line.raw_text for line, target in zip(docstring.structure.lines, raw_line_targets, strict=True)]
    return planned_simple_docstring_source_change(docstring, replacements=tuple(replacements), value_lines=value_lines)


def planned_simple_docstring_source_change(
    docstring: DocstringInfo, *, replacements: tuple[rule_edits.PlannedTextReplacement, ...], value_lines: list[str], source_map: string_literals.SimpleStringSourceMap | None = None
) -> rule_edits.PlannedSourceChange | None:
    """Return one whole-literal replacement from evaluated-value replacements.

    Args:
        docstring (DocstringInfo): Simple docstring whose body source should be rebuilt from evaluated-value edits.
        replacements (tuple[rule_edits.PlannedTextReplacement, ...]): Evaluated-offset replacements that identify
            changed slices and affected source lines.
        value_lines (list[str]): Complete logical value lines after all replacements, used to verify that the rendered
            literal still evaluates correctly.
        source_map (string_literals.SimpleStringSourceMap | None): Optional precomputed lossless source map.

    Returns:
        Planned replacement for the whole string literal, or None when rendering would be unsafe or unchanged.
    """
    if not replacements:
        return None
    source_map = docstring.source_map if source_map is None else source_map
    if source_map is None or not isinstance(docstring.node, cst.SimpleString):
        return None
    value = join_docstring_value_lines(docstring, value_lines)
    body_source = source_map.body_source_with_replacements(tuple((replacement.start_offset, replacement.end_offset, replacement.text) for replacement in replacements))
    rendered = string_literals.render_simple_string_from_body_source(docstring.node.prefix, docstring.node.quote, body_source, expected_value=value)
    if rendered is None or rendered == docstring.source:
        return None
    return rule_edits.PlannedSourceChange(
        edit=rule_edits.SourceEdit(range=docstring.range, replacement=rendered),
        line_numbers=tuple(line_number for replacement in replacements for line_number in replacement.line_numbers),
        suppression_line_numbers=(),
    )


def planned_simple_docstring_text_change(
    docstring: DocstringInfo, *, context: RuleContext, replacement: rule_edits.PlannedTextReplacement, expected_value: str, expected_source: str | None = None, replacement_source: str | None = None
) -> rule_edits.PlannedSourceChange | None:
    """Return one source-slice replacement from an evaluated-value replacement.

    Args:
        docstring (DocstringInfo): Simple docstring whose source body should receive the replacement.
        context (RuleContext): Rule context providing source lines and cached offset bounds.
        replacement (rule_edits.PlannedTextReplacement): Evaluated-offset replacement to map into current source text.
        expected_value (str): Complete evaluated docstring value expected after applying the replacement.
        expected_source (str | None): Optional exact source spelling required for the replaced value slice.
        replacement_source (str | None): Optional source spelling that differs from the evaluated replacement text.

    Returns:
        Planned replacement for the mapped source slice, or None when the source mapping is unsafe.
    """
    line_bounds = line_bounds_for_context(context)
    source_map = docstring.source_map
    if source_map is None or replacement.start_offset < 0 or replacement.end_offset < replacement.start_offset or replacement.end_offset > len(source_map.value):
        return None
    if expected_source is not None and source_map.producing_source_for_value_slice(replacement.start_offset, replacement.end_offset) != expected_source:
        return None
    source_text_value = replacement.text if replacement_source is None else replacement_source
    replacement_body = source_map.body_source_with_replacements(((replacement.start_offset, replacement.end_offset, source_text_value),))
    if (
        not isinstance(docstring.node, cst.SimpleString)
        or string_literals.render_simple_string_from_body_source(docstring.node.prefix, docstring.node.quote, replacement_body, expected_value=expected_value) is None
    ):
        return None
    return rule_edits.PlannedSourceChange(
        edit=rule_edits.SourceEdit(
            range=simple_docstring_source_range(docstring, source_map=source_map, start_offset=replacement.start_offset, end_offset=replacement.end_offset, line_bounds=line_bounds),
            replacement=source_text_value,
        ),
        line_numbers=replacement.line_numbers,
        suppression_line_numbers=(),
    )


def line_bounds_for_context(context: RuleContext) -> source_text.LineBounds:
    """Return cached or derived source line bounds for a rule context.

    Args:
        context (RuleContext): Current source context whose lines should be mapped to absolute offsets.

    Returns:
        source_text.LineBounds: Absolute source offset bounds for each physical source line.
    """
    return context.line_bounds if context.line_bounds is not None else source_text.line_bounds_from_lines(context.source_lines)


def simple_docstring_source_range(
    docstring: DocstringInfo, *, source_map: string_literals.SimpleStringSourceMap, start_offset: int, end_offset: int, line_bounds: source_text.LineBounds
) -> cst_metadata.CodeRange:
    """Return the concrete source range for one evaluated-value slice.

    Args:
        docstring (DocstringInfo): Simple docstring that owns the mapped literal body.
        source_map (string_literals.SimpleStringSourceMap): Lossless map for the docstring body.
        start_offset (int): Evaluated offset where the slice starts.
        end_offset (int): Evaluated offset immediately after the slice.
        line_bounds (source_text.LineBounds): Absolute source bounds for each physical line.

    Returns:
        cst_metadata.CodeRange: Concrete source range matching the evaluated slice.

    Raises:
        TypeError: If the docstring is not a simple string.
    """
    if not isinstance(docstring.node, cst.SimpleString):
        raise TypeError("A simple docstring source range requires a simple string node")
    body_start = source_text.offset_for_position(docstring.range.start, line_bounds=line_bounds) + len(docstring.node.prefix) + len(docstring.node.quote)
    source_start = body_start + source_map.source_offset_for_value_offset(start_offset)
    source_end = source_start if start_offset == end_offset else body_start + source_map.source_offset_for_value_offset(end_offset, include_leading_zero_value_source=True)
    return cst_metadata.CodeRange(start=source_text.position_for_offset(source_start, line_bounds=line_bounds), end=source_text.position_for_offset(source_end, line_bounds=line_bounds))


def simple_docstring_replacement_is_source_safe(docstring: DocstringInfo, replacement: str) -> bool:
    """Return whether replacement source spelling is identical to its evaluated value.

    Args:
        docstring (DocstringInfo): Simple docstring whose quote delimiter constrains replacement spelling.
        replacement (str): Replacement text to insert into the literal source body.

    Returns:
        bool: Whether the replacement can be inserted as source text without changing its evaluated value.
    """
    if not isinstance(docstring.node, cst.SimpleString) or not replacement.isascii() or "\\" in replacement or "\r" in replacement or "\n" in replacement:
        return False
    return docstring.node.quote not in replacement


def docstring_content_indexes(docstring: DocstringInfo) -> tuple[int, ...]:
    """Return logical line indexes containing non-space-tab text.

    Args:
        docstring (DocstringInfo): Parsed docstring whose logical value lines should be scanned.

    Returns:
        Zero-based logical line indexes that contain content other than spaces or tabs.
    """
    return tuple(line.index for line in docstring.structure.lines if line.text.strip(ascii_whitespace.SPACE_AND_TAB))


def docstring_line_source(line: DocstringValueLine, *, source_map: string_literals.SimpleStringSourceMap, strip_docstring_margin: bool) -> str:
    """Return source spelling for a logical docstring line.

    Args:
        line (DocstringValueLine): Evaluated-value line whose source body slice should be reconstructed.
        source_map (string_literals.SimpleStringSourceMap): Lossless simple-string source mapping.
        strip_docstring_margin (bool): Whether to discard the literal indentation margin and keep only text content with
            virtual indentation.

    Returns:
        Source text for the line body, preserving escapes unless margin stripping is requested.
    """
    if not strip_docstring_margin:
        return source_map.owned_source_for_value_slice(line.start_offset, line.end_offset)
    start_offset = line.start_offset + line.text_raw_start_column
    return f"{' ' * line.text_virtual_prefix_length}{source_map.owned_source_for_value_slice(start_offset, line.end_offset)}"


def docstring_value_line_numbers(lines: tuple[DocstringValueLine, ...]) -> tuple[int, ...]:
    """Return deduplicated source line numbers for changed logical lines.

    Args:
        lines (tuple[DocstringValueLine, ...]): Logical docstring lines that may map to physical source lines.

    Returns:
        Source line numbers for mapped logical lines, preserving first occurrence order and omitting unmapped lines.
    """
    return tuple(dict.fromkeys(line.source_line_number for line in lines if line.source_line_number is not None))


def docstring_physical_line_numbers(docstring: DocstringInfo) -> tuple[int, ...]:
    """Return physical source lines occupied by a docstring expression.

    Args:
        docstring (DocstringInfo): Docstring expression whose LibCST source range has already been collected.

    Returns:
        Physical source line numbers covered by the complete docstring literal expression.
    """
    return tuple(source_line.line_number for source_line in docstring.physical_lines)


def docstring_line_numbers(docstring: DocstringInfo, line: DocstringValueLine) -> tuple[int, ...]:
    """Return concrete source lines for a docstring value line.

    Args:
        docstring (DocstringInfo): Docstring whose physical range is used when the logical line lacks a direct source
            mapping.
        line (DocstringValueLine): Logical docstring line being reported by a rule.

    Returns:
        Direct logical line source numbers when available, otherwise the complete physical docstring range.
    """
    if line.source_line_number is not None:
        return docstring_value_line_numbers((line,))
    return docstring_physical_line_numbers(docstring)


def docstring_value_ends_with_newline(docstring: DocstringInfo) -> bool:
    """Return whether an evaluated docstring value ends with a newline.

    Args:
        docstring (DocstringInfo): Docstring whose evaluated Python string value should be checked.

    Returns:
        True when the value ends with any supported newline spelling.
    """
    return docstring.value.endswith(("\r\n", "\r", "\n"))


def join_docstring_value_lines(docstring: DocstringInfo, lines: list[str]) -> str:
    """Join replacement logical lines with the original evaluated newline spellings.

    Args:
        docstring (DocstringInfo): Docstring whose evaluated value contains the separators between logical lines.
        lines (list[str]): Replacement logical line text in parsed line order.

    Returns:
        Full evaluated docstring value with caller-provided line text and original inter-line separators.
    """
    chunks: list[str] = []
    for index, (line_info, line) in enumerate(zip(docstring.structure.lines, lines, strict=True)):
        chunks.append(line)
        if index + 1 < len(lines):
            chunks.append(docstring.value[line_info.end_offset : docstring.structure.lines[index + 1].start_offset])
        else:
            chunks.append(docstring.value[line_info.end_offset :])
    return "".join(chunks)


@typing.overload
def value_offset_for_text_column(line: DocstringValueLine, column: int, *, require_source_text: typing.Literal[False] = False) -> int: ...


@typing.overload
def value_offset_for_text_column(line: DocstringValueLine, column: int, *, require_source_text: typing.Literal[True]) -> int | None: ...


def value_offset_for_text_column(line: DocstringValueLine, column: int, *, require_source_text: bool = False) -> int | None:
    """Return the evaluated-value offset for a line.text column.

    Args:
        line (DocstringValueLine): Logical docstring line whose visible text column should be translated.
        column (int): Zero-based column within the virtualized text field of the line.
        require_source_text (bool): Whether columns that exist only in virtual indentation should return None instead of
            clamping to the first source-backed character.

    Returns:
        Evaluated-value offset corresponding to the text column, or None when source-backed text is required but the column is outside the raw text span.
    """
    unclamped_raw_column = line.text_raw_start_column + column - line.text_virtual_prefix_length
    if require_source_text and (unclamped_raw_column < line.text_raw_start_column or unclamped_raw_column > len(line.raw_text)):
        return None
    raw_column = line.text_raw_start_column + max(column - line.text_virtual_prefix_length, 0)
    return line.start_offset + raw_column
