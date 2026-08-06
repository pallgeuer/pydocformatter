# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# Third-party imports
import libcst as cst
import pytest
import libcst.metadata as cst_metadata


if TYPE_CHECKING:
    # Third-party imports
    from pytest_mock import MockerFixture

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


def test_source_offset_map_maps_form_feed_and_blank_line_normalization() -> None:
    source = '\f"""summary"""\ndef f():\n    """D."""\n\n \t# C.\n'
    module = cst.parse_module(source)
    offset_map = source_text.source_offset_map(module, source)

    assert module.code == '"""summary"""\ndef f():\n    """D."""\n \t# C.\n'

    assert offset_map.code_range(cst_metadata.CodeRange(start=cst_metadata.CodePosition(1, 0), end=cst_metadata.CodePosition(1, 13))) == cst_metadata.CodeRange(
        start=cst_metadata.CodePosition(1, 1), end=cst_metadata.CodePosition(1, 14)
    )
    assert offset_map.code_range(cst_metadata.CodeRange(start=cst_metadata.CodePosition(4, 2), end=cst_metadata.CodePosition(4, 6))) == cst_metadata.CodeRange(
        start=cst_metadata.CodePosition(5, 2), end=cst_metadata.CodePosition(5, 6)
    )


def test_source_offset_map_right_biases_zero_width_ranges_after_omitted_text() -> None:
    source = "first\n\n #last\n"
    module = cst.parse_module(source)
    offset_map = source_text.source_offset_map(module, source)

    mapped = offset_map.code_range(cst_metadata.CodeRange(start=cst_metadata.CodePosition(2, 0), end=cst_metadata.CodePosition(2, 0)))

    assert mapped == cst_metadata.CodeRange(start=cst_metadata.CodePosition(3, 0), end=cst_metadata.CodePosition(3, 0))


def test_source_offset_map_maps_comment_lines_omitted_by_libcst() -> None:
    source = "first\n #omitted\n #last\n"
    module = cst.parse_module(source)
    offset_map = source_text.source_offset_map(module, source)

    mapped = offset_map.code_range(cst_metadata.CodeRange(start=cst_metadata.CodePosition(2, 1), end=cst_metadata.CodePosition(2, 6)))

    assert mapped == cst_metadata.CodeRange(start=cst_metadata.CodePosition(3, 1), end=cst_metadata.CodePosition(3, 6))


def test_source_offset_map_maps_adjacent_form_feed_and_blank_line_normalization() -> None:
    source = "\fx = 1\n\n  # c\n"
    module = cst.parse_module(source)
    offset_map = source_text.source_offset_map(module, source)

    assert module.code == "x = 1\n  # c\n"
    assert offset_map.code_range(cst_metadata.CodeRange(start=cst_metadata.CodePosition(1, 0), end=cst_metadata.CodePosition(1, 5))) == cst_metadata.CodeRange(
        start=cst_metadata.CodePosition(1, 1), end=cst_metadata.CodePosition(1, 6)
    )
    assert offset_map.code_range(cst_metadata.CodeRange(start=cst_metadata.CodePosition(2, 2), end=cst_metadata.CodePosition(2, 5))) == cst_metadata.CodeRange(
        start=cst_metadata.CodePosition(3, 2), end=cst_metadata.CodePosition(3, 5)
    )


def test_source_offset_map_maps_virtual_eof_after_normalized_source() -> None:
    source = "\ffirst\nsecond"
    module = cst.parse_module(source)
    offset_map = source_text.source_offset_map(module, source)

    mapped = offset_map.code_range(cst_metadata.CodeRange(start=cst_metadata.CodePosition(2, 0), end=cst_metadata.CodePosition(3, 0)))

    assert mapped == cst_metadata.CodeRange(start=cst_metadata.CodePosition(2, 0), end=cst_metadata.CodePosition(2, 6))


@pytest.mark.parametrize(
    ("rendered", "source"),
    [
        ("value = 1\n", "other = 1\n"),
        ("value = 1\n", "value = 2\n"),
        ('value = "a"\n', 'value = " a"\n'),
        ('value = f"{name}"\n', 'value = f" {name}"\n'),
        ('value = """a\n"""\n', 'value = """a\n# inside\n"""\n'),
    ],
)
def test_source_offset_map_rejects_structural_divergence(rendered: str, source: str) -> None:
    with pytest.raises(ValueError, match="structurally different"):
        source_text.source_offset_map(cst.parse_module(rendered), source)


def test_source_offset_map_right_biases_duplicate_comment_alignment() -> None:
    source = "first\n #same\n #same\n"

    offset_map = source_text.source_offset_map(cst.parse_module(source), source)
    mapped = offset_map.code_range(cst_metadata.CodeRange(start=cst_metadata.CodePosition(2, 1), end=cst_metadata.CodePosition(2, 6)))

    assert mapped == cst_metadata.CodeRange(start=cst_metadata.CodePosition(3, 1), end=cst_metadata.CodePosition(3, 6))


def test_source_offset_map_right_biases_duplicate_form_feed_alignment() -> None:
    source = '"""D."""\ndef f():\n    """f"""\n\f\n\f\n'

    offset_map = source_text.source_offset_map(cst.parse_module(source), source)
    mapped = offset_map.code_range(cst_metadata.CodeRange(start=cst_metadata.CodePosition(4, 0), end=cst_metadata.CodePosition(4, 1)))

    assert mapped == cst_metadata.CodeRange(start=cst_metadata.CodePosition(5, 0), end=cst_metadata.CodePosition(5, 1))


def test_parsed_source_offset_map_does_not_reparse_exact_source(mocker: MockerFixture) -> None:
    source = "first\n #omitted\n #last\n"
    module = cst.parse_module(source)
    mocker.patch.object(cst, "parse_module", side_effect=AssertionError("Exact source should not be reparsed"))

    offset_map = source_text.source_offset_map_for_parsed_source(module, source)

    assert offset_map.code_range(cst_metadata.CodeRange(start=cst_metadata.CodePosition(2, 1), end=cst_metadata.CodePosition(2, 6))) == cst_metadata.CodeRange(
        start=cst_metadata.CodePosition(3, 1), end=cst_metadata.CodePosition(3, 6)
    )


def test_source_offset_map_uses_sparse_segments_for_large_repetitive_sources() -> None:
    sources = ("\f" + "x = 0\n" * 10_000, '\fvalue = "' + "a" * 8_000 + '"\n', "first\n" + "".join(f" # omitted {index}\n" for index in range(2_000)))

    offset_maps = tuple(source_text.source_offset_map(cst.parse_module(source), source) for source in sources)

    assert tuple(len(offset_map.source_offset_segments or ()) for offset_map in offset_maps) == (1, 1, 2)
