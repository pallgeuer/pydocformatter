# Third-party imports
import libcst.metadata as cst_metadata

# First-party imports
from pydocformatter.rules.definition_helpers import source_text


def test_source_lines_preserve_python_line_endings() -> None:
    assert source_text.source_lines("a\r\nb\nc\rd") == ["a\r\n", "b\n", "c\r", "d"]


def test_source_lines_preserve_final_empty_or_partial_line() -> None:
    assert source_text.source_lines("") == [""]
    assert source_text.source_lines("a") == ["a"]
    assert source_text.source_lines("a\n") == ["a\n", ""]
    assert source_text.source_lines("a\r\n") == ["a\r\n", ""]


def test_source_lines_do_not_split_non_python_line_boundaries() -> None:
    assert source_text.source_lines("a\fb\u2028c\n") == ["a\fb\u2028c\n", ""]


def test_line_bounds_from_lines_return_content_offsets() -> None:
    lines = source_text.source_lines("alpha\r\nbeta\ngamma\rd")

    assert source_text.line_bounds_from_lines(lines) == ((0, 5), (7, 11), (12, 17), (18, 19))


def test_source_for_range_returns_exact_single_and_multiline_source() -> None:
    lines = source_text.source_lines("first\nsecond\nthird\n")

    assert source_text.source_for_range(cst_metadata.CodeRange(start=cst_metadata.CodePosition(1, 1), end=cst_metadata.CodePosition(1, 4)), source_lines=lines) == "irs"
    assert source_text.source_for_range(cst_metadata.CodeRange(start=cst_metadata.CodePosition(1, 2), end=cst_metadata.CodePosition(3, 2)), source_lines=lines) == "rst\nsecond\nth"


def test_position_and_offset_mapping_round_trips_unicode_across_mixed_line_endings() -> None:
    source = "a\xe9\r\nbeta\ngamma\r\u202e"
    line_bounds = source_text.line_bounds_from_lines(source_text.source_lines(source))
    positions = (cst_metadata.CodePosition(1, 0), cst_metadata.CodePosition(1, 2), cst_metadata.CodePosition(2, 3), cst_metadata.CodePosition(3, 5), cst_metadata.CodePosition(4, 1))

    offsets = tuple(source_text.offset_for_position(position, line_bounds=line_bounds) for position in positions)

    assert offsets == (0, 2, 7, 14, 16)
    assert tuple(source_text.position_for_offset(offset, line_bounds=line_bounds) for offset in offsets) == positions


def test_position_for_offset_maps_line_endings_and_eof_by_preceding_line_start() -> None:
    line_bounds = source_text.line_bounds_from_lines(source_text.source_lines("a\r\nb\n"))

    assert tuple(source_text.position_for_offset(offset, line_bounds=line_bounds) for offset in range(6)) == (
        cst_metadata.CodePosition(1, 0),
        cst_metadata.CodePosition(1, 1),
        cst_metadata.CodePosition(1, 2),
        cst_metadata.CodePosition(2, 0),
        cst_metadata.CodePosition(2, 1),
        cst_metadata.CodePosition(3, 0),
    )
