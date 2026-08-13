"""Source text range and line-bound helpers.

Attributes:
    LineBounds (TypeAlias): Per-line absolute source offsets excluding line-ending bytes, used to map LibCST positions
        back to slices.
"""

# Future imports
from __future__ import annotations

# Standard library imports
import dataclasses
from collections.abc import Mapping, Sequence

# Third-party imports
import libcst as cst
import libcst.metadata as cst_metadata

# First-party imports
from pydocformatter.utils import text


LineBounds = tuple[tuple[int, int], ...]
_PHYSICAL_WHITESPACE = " \t\f\r\n"


@dataclasses.dataclass(frozen=True)
class SourceOffsetSegment:
    """Contiguous rendered-source offsets with one exact-source delta.

    Attributes:
        rendered_start (int): Inclusive rendered-source offset where the segment begins.
        rendered_end (int): Exclusive rendered-source offset where the segment ends.
        source_start (int): Exact-source offset corresponding to `rendered_start`.
    """

    rendered_start: int
    rendered_end: int
    source_start: int


@dataclasses.dataclass(frozen=True)
class SourceOffsetMap:
    """Map LibCST-rendered ranges onto exact source text.

    Attributes:
        rendered_line_bounds (LineBounds): Line offsets for the LibCST-rendered source.
        source_line_bounds (LineBounds): Line offsets for the exact source.
        rendered_length (int): LibCST-rendered source length used for end-of-file mappings.
        source_length (int): Exact source length used for end-of-file mappings.
        source_offset_segments (tuple[SourceOffsetSegment, ...] | None): Contiguous exact-source mapping segments, or
            None for an identity mapping.
    """

    rendered_line_bounds: LineBounds
    source_line_bounds: LineBounds
    rendered_length: int
    source_length: int
    source_offset_segments: tuple[SourceOffsetSegment, ...] | None

    def code_range(self, code_range: cst_metadata.CodeRange) -> cst_metadata.CodeRange:
        """Return an exact-source range for one rendered-source range.

        Args:
            code_range (cst_metadata.CodeRange): LibCST-rendered range to map.

        Returns:
            cst_metadata.CodeRange: Corresponding exact-source range.
        """
        rendered_start = self._rendered_offset(code_range.start)
        rendered_end = self._rendered_offset(code_range.end)
        if rendered_start == rendered_end:
            source_start = source_end = self._source_start_offset(rendered_start)
        else:
            source_start = self._source_start_offset(rendered_start)
            source_end = self._source_end_offset(rendered_end)
        return cst_metadata.CodeRange(start=position_for_offset(source_start, line_bounds=self.source_line_bounds), end=position_for_offset(source_end, line_bounds=self.source_line_bounds))

    def positions(self, positions: Mapping[cst.CSTNode, cst_metadata.CodeRange]) -> Mapping[cst.CSTNode, cst_metadata.CodeRange]:
        """Return all LibCST positions remapped onto exact source.

        Args:
            positions (Mapping[cst.CSTNode, cst_metadata.CodeRange]): Rendered-source positions keyed by node.

        Returns:
            Mapping[cst.CSTNode, cst_metadata.CodeRange]: Exact-source positions keyed by the same nodes.
        """
        if self.source_offset_segments is None:
            return positions
        return {node: self.code_range(code_range) for node, code_range in positions.items()}

    def _source_start_offset(self, rendered_offset: int) -> int:
        """Return the right-biased exact offset for a rendered boundary."""
        if self.source_offset_segments is None:
            return rendered_offset
        if rendered_offset == self.rendered_length:
            return self.source_length
        return self._mapped_source_offset(rendered_offset)

    def _rendered_offset(self, position: cst_metadata.CodePosition) -> int:
        """Return a rendered offset, including LibCST's virtual EOF line."""
        if position.line == len(self.rendered_line_bounds) + 1 and position.column == 0:
            return self.rendered_length
        return offset_for_position(position, line_bounds=self.rendered_line_bounds)

    def _source_end_offset(self, rendered_offset: int) -> int:
        """Return the left-biased exact offset for a rendered boundary."""
        if self.source_offset_segments is None:
            return rendered_offset
        if rendered_offset > 0:
            return self._mapped_source_offset(rendered_offset - 1) + 1
        return 0

    def _mapped_source_offset(self, rendered_offset: int) -> int:
        """Return the exact-source offset for one rendered character."""
        if self.source_offset_segments is None:
            return rendered_offset
        low = 0
        high = len(self.source_offset_segments)
        while low < high:
            middle = (low + high) // 2
            if self.source_offset_segments[middle].rendered_start <= rendered_offset:
                low = middle + 1
            else:
                high = middle
        if low == 0:
            raise ValueError(f"Rendered offset has no exact-source mapping: {rendered_offset}")
        segment = self.source_offset_segments[low - 1]
        if rendered_offset >= segment.rendered_end:
            raise ValueError(f"Rendered offset has no exact-source mapping: {rendered_offset}")
        return segment.source_start + rendered_offset - segment.rendered_start


def source_offset_map(module: cst.Module, source: str, *, rendered_source: str | None = None) -> SourceOffsetMap:
    """Return a proven mapping from rendered source to exact source.

    Args:
        module (cst.Module): Parsed LibCST module whose rendered positions need mapping.
        source (str): Exact source spelling supplied to the rule runner.
        rendered_source (str | None): Cached rendering of `module`, or None to render it on demand.

    Returns:
        SourceOffsetMap: Character and line mapping for converting LibCST ranges.

    Raises:
        ValueError: If exact source is structurally different or differs by more than omitted physical whitespace or
            comment lines.
    """
    rendered_source = module.code if rendered_source is None else rendered_source
    if rendered_source == source:
        return source_offset_map_for_parsed_source(module, source, rendered_source=rendered_source)
    try:
        exact_module = cst.parse_module(source, config=module.config_for_parsing)
    except Exception as error:
        raise ValueError(f"Exact source could not be reparsed with the LibCST module configuration: {error}") from None
    if not module.deep_equals(exact_module):
        raise ValueError("Exact source is structurally different from the supplied LibCST module")
    return source_offset_map_for_parsed_source(module, source, rendered_source=rendered_source)


def source_offset_map_for_parsed_source(module: cst.Module, source: str, *, rendered_source: str | None = None) -> SourceOffsetMap:
    """Return an exact-source mapping for a module parsed from that source.

    Args:
        module (cst.Module): Module parsed directly from `source`.
        source (str): Exact source spelling used to parse `module`.
        rendered_source (str | None): Cached rendering of `module`, or None to render it on demand.

    Returns:
        SourceOffsetMap: Character and line mapping for converting LibCST ranges.

    Raises:
        ValueError: If rendered source differs by more than omitted physical whitespace or comment lines.
    """
    rendered_source = module.code if rendered_source is None else rendered_source
    rendered_lines = source_lines(rendered_source)
    rendered_line_bounds = line_bounds_from_lines(rendered_lines)
    if rendered_source == source:
        return SourceOffsetMap(
            rendered_line_bounds=rendered_line_bounds, source_line_bounds=rendered_line_bounds, rendered_length=len(rendered_source), source_length=len(source), source_offset_segments=None
        )
    exact_lines = source_lines(source)
    rendered_line_starts = _line_starts(rendered_lines)
    source_line_starts = _line_starts(exact_lines)
    source_offset_segments = _right_biased_source_offset_segments(rendered_lines, exact_lines, rendered_line_starts=rendered_line_starts, source_line_starts=source_line_starts)
    return SourceOffsetMap(
        rendered_line_bounds=rendered_line_bounds,
        source_line_bounds=line_bounds_from_lines(exact_lines),
        rendered_length=len(rendered_source),
        source_length=len(source),
        source_offset_segments=source_offset_segments,
    )


def _line_starts(lines: Sequence[str]) -> tuple[int, ...]:
    """Return absolute start offsets for physical source lines."""
    starts: list[int] = []
    offset = 0
    for line in lines:
        starts.append(offset)
        offset += len(line)
    return tuple(starts)


def _right_biased_source_offset_segments(
    rendered_lines: Sequence[str], exact_lines: Sequence[str], *, rendered_line_starts: Sequence[int], source_line_starts: Sequence[int]
) -> tuple[SourceOffsetSegment, ...]:
    """Return the latest monotonic rendered-to-exact alignment."""
    rendered_indexes = range(len(rendered_lines) - 1, -1, -1)
    source_index = len(exact_lines) - 1
    line_segment_groups: list[tuple[SourceOffsetSegment, ...]] = []
    for rendered_index in rendered_indexes:
        while 0 <= source_index < len(exact_lines):
            line_segments = _right_biased_line_source_offset_segments(rendered_lines[rendered_index], exact_lines[source_index])
            if line_segments is not None:
                line_segment_groups.append(
                    tuple(
                        SourceOffsetSegment(
                            rendered_start=rendered_line_starts[rendered_index] + segment.rendered_start,
                            rendered_end=rendered_line_starts[rendered_index] + segment.rendered_end,
                            source_start=source_line_starts[source_index] + segment.source_start,
                        )
                        for segment in line_segments
                    )
                )
                source_index -= 1
                break
            if not _is_omittable_source_line(exact_lines[source_index]):
                raise ValueError(f"LibCST-rendered line {rendered_index} cannot be aligned with exact line {source_index}")
            source_index -= 1
        else:
            raise ValueError(f"LibCST-rendered line {rendered_index} has no exact-source match")
    remaining_source_indexes = range(source_index, -1, -1)
    if any(not _is_omittable_source_line(exact_lines[index]) for index in remaining_source_indexes):
        raise ValueError("Exact source contains unmatched non-trivia lines")
    segments: list[SourceOffsetSegment] = []
    for line_segments in reversed(line_segment_groups):
        for segment in line_segments:
            _append_source_offset_segment(segments, segment)
    return tuple(segments)


def _right_biased_line_source_offset_segments(rendered_line: str, source_line: str) -> tuple[SourceOffsetSegment, ...] | None:
    """Return the latest line mapping that permits exact-only physical whitespace."""
    if rendered_line == source_line:
        return () if not rendered_line else (SourceOffsetSegment(rendered_start=0, rendered_end=len(rendered_line), source_start=0),)
    rendered_offset = len(rendered_line) - 1
    source_offset = len(source_line) - 1
    reversed_segments: list[SourceOffsetSegment] = []
    while rendered_offset >= 0:
        if source_offset < 0:
            return None
        if rendered_line[rendered_offset] != source_line[source_offset]:
            if source_line[source_offset] not in _PHYSICAL_WHITESPACE:
                return None
            source_offset -= 1
            continue
        rendered_end = rendered_offset + 1
        while rendered_offset >= 0 and source_offset >= 0 and rendered_line[rendered_offset] == source_line[source_offset]:
            rendered_offset -= 1
            source_offset -= 1
        reversed_segments.append(SourceOffsetSegment(rendered_start=rendered_offset + 1, rendered_end=rendered_end, source_start=source_offset + 1))
    if any(character not in _PHYSICAL_WHITESPACE for character in source_line[: source_offset + 1]):
        return None
    segments: list[SourceOffsetSegment] = []
    for segment in reversed(reversed_segments):
        _append_source_offset_segment(segments, segment)
    return tuple(segments)


def _append_source_offset_segment(segments: list[SourceOffsetSegment], segment: SourceOffsetSegment) -> None:
    """Append and coalesce one contiguous source-offset segment."""
    if segment.rendered_start == segment.rendered_end:
        return
    if segments:
        previous = segments[-1]
        previous_source_end = previous.source_start + previous.rendered_end - previous.rendered_start
        if previous.rendered_end == segment.rendered_start and previous_source_end == segment.source_start:
            segments[-1] = SourceOffsetSegment(rendered_start=previous.rendered_start, rendered_end=segment.rendered_end, source_start=previous.source_start)
            return
    segments.append(segment)


def _is_omittable_source_line(line: str) -> bool:
    """Return whether an exact-only physical line is blank or a standalone comment."""
    return all(character in _PHYSICAL_WHITESPACE for character in line) or line.rstrip("\r\n").lstrip(" \t\f").startswith("#")


def source_lines(source: str) -> list[str]:
    """Split source into lines retaining only Python physical line endings.

    Args:
        source (str): Full Python source text.

    Returns:
        list[str]: Physical source lines, preserving line endings and returning one empty line for empty source.
    """
    if not source:
        return [""]

    lines = text.split_physical_lines(source, keepends=True)
    if source.endswith(("\r", "\n")):
        lines.append("")
    return lines


def line_bounds_from_lines(source_lines: Sequence[str]) -> LineBounds:
    """Return source offsets bounding each line without its line ending.

    Args:
        source_lines (Sequence[str]): Physical source lines with their original line endings.

    Returns:
        LineBounds: Absolute start and content-end offsets for each physical line.
    """
    bounds: list[tuple[int, int]] = []
    line_start = 0
    for line in source_lines:
        line_ending_length = _python_line_ending_length(line)
        line_end = line_start + len(line) - line_ending_length
        bounds.append((line_start, line_end))
        line_start += len(line)
    return tuple(bounds)


def source_for_range(code_range: cst_metadata.CodeRange, *, source_lines: Sequence[str]) -> str:
    """Return the exact source inside a LibCST code range.

    Args:
        code_range (cst_metadata.CodeRange): One-based LibCST source range to slice.
        source_lines (Sequence[str]): Physical source lines indexed by the range line numbers.

    Returns:
        str: Exact source text covered by the range.
    """
    first_index = code_range.start.line - 1
    last_index = code_range.end.line - 1
    if first_index == last_index:
        return source_lines[first_index][code_range.start.column : code_range.end.column]
    lines = [source_lines[first_index][code_range.start.column :]]
    lines.extend(source_lines[first_index + 1 : last_index])
    lines.append(source_lines[last_index][: code_range.end.column])
    return "".join(lines)


def offset_for_position(position: cst_metadata.CodePosition, *, line_bounds: LineBounds) -> int:
    """Return the absolute source offset for a LibCST position.

    Args:
        position (cst_metadata.CodePosition): One-based line and zero-based column to convert.
        line_bounds (LineBounds): Absolute source offsets for physical lines.

    Returns:
        int: Absolute source offset matching the position.
    """
    line_start, _ = line_bounds[position.line - 1]
    return line_start + position.column


def position_for_offset(offset: int, *, line_bounds: LineBounds) -> cst_metadata.CodePosition:
    """Return the LibCST position for an absolute source offset.

    Args:
        offset (int): Absolute source offset to convert.
        line_bounds (LineBounds): Absolute source offsets for physical lines.

    Returns:
        cst_metadata.CodePosition: One-based line and zero-based column matching the offset.
    """
    low = 0
    high = len(line_bounds)
    while low < high:
        middle = (low + high) // 2
        if line_bounds[middle][0] <= offset:
            low = middle + 1
        else:
            high = middle
    line_index = max(0, low - 1)
    return cst_metadata.CodePosition(line=line_index + 1, column=offset - line_bounds[line_index][0])


def first_non_ascii_code_point(text: str) -> str:
    """Return the code point label for the first non-ASCII character in text.

    Args:
        text (str): Text known to contain at least one non-ASCII character.

    Returns:
        str: Uppercase `U+...` code point label for the first non-ASCII character.
    """
    return next(f"U+{ord(char):04X}" for char in text if not char.isascii())


def _python_line_ending_length(line: str) -> int:
    """Return the length of a trailing Python physical line ending."""
    if line.endswith("\r\n"):
        return 2
    if line.endswith(("\r", "\n")):
        return 1
    return 0
