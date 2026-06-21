import libcst.metadata as cst_metadata

import pydocformatter.rules.definition_helpers.source_text as source_text


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
