import unittest

import libcst as cst
import libcst.metadata as cst_metadata

import pydocformatter.rules.edits as rule_edits


class TestSourceEdits(unittest.TestCase):
    def test_empty_edits_return_original_module(self) -> None:
        module = cst.parse_module("x = 1\n")

        self.assertIs(rule_edits.apply_source_edits(module, ()), module)

    def test_multiple_unsorted_edits_support_unicode_and_adjacent_ranges(self) -> None:
        module = cst.parse_module("alpha = '\u03b1'\nbeta = 2\n")
        edits = (
            rule_edits.SourceEdit(cst_metadata.CodeRange(start=cst_metadata.CodePosition(2, 0), end=cst_metadata.CodePosition(2, 4)), "gamma"),
            rule_edits.SourceEdit(cst_metadata.CodeRange(start=cst_metadata.CodePosition(1, 9), end=cst_metadata.CodePosition(1, 10)), "\u03c9"),
            rule_edits.SourceEdit(cst_metadata.CodeRange(start=cst_metadata.CodePosition(1, 0), end=cst_metadata.CodePosition(1, 5)), "name"),
            rule_edits.SourceEdit(cst_metadata.CodeRange(start=cst_metadata.CodePosition(2, 4), end=cst_metadata.CodePosition(2, 5)), ""),
        )

        result = rule_edits.apply_source_edits(module, edits)

        self.assertEqual(result.code, "name = '\u03c9'\ngamma= 2\n")

    def test_overlapping_edits_are_rejected(self) -> None:
        module = cst.parse_module("value = 1\n")
        edits = (
            rule_edits.SourceEdit(cst_metadata.CodeRange(start=cst_metadata.CodePosition(1, 0), end=cst_metadata.CodePosition(1, 5)), "name"),
            rule_edits.SourceEdit(cst_metadata.CodeRange(start=cst_metadata.CodePosition(1, 4), end=cst_metadata.CodePosition(1, 7)), "x"),
        )

        with self.assertRaisesRegex(ValueError, "must not overlap"):
            rule_edits.apply_source_edits(module, edits)

    def test_invalid_range_positions_are_rejected(self) -> None:
        module = cst.parse_module("x = 1\n")

        with self.assertRaisesRegex(ValueError, "line is outside"):
            rule_edits.apply_source_edits(module, (rule_edits.SourceEdit(cst_metadata.CodeRange(start=cst_metadata.CodePosition(3, 0), end=cst_metadata.CodePosition(3, 0)), ""),))
        with self.assertRaisesRegex(ValueError, "column is outside"):
            rule_edits.apply_source_edits(module, (rule_edits.SourceEdit(cst_metadata.CodeRange(start=cst_metadata.CodePosition(1, 10), end=cst_metadata.CodePosition(1, 10)), ""),))

    def test_replacement_must_produce_valid_python(self) -> None:
        module = cst.parse_module("x = 1\n")
        edit = rule_edits.SourceEdit(cst_metadata.CodeRange(start=cst_metadata.CodePosition(1, 4), end=cst_metadata.CodePosition(1, 5)), "(")

        with self.assertRaises(cst.ParserSyntaxError):
            rule_edits.apply_source_edits(module, (edit,))

    def test_edits_preserve_crlf_parser_configuration(self) -> None:
        module = cst.parse_module("first = 1\r\nsecond = 2\r\n")
        edit = rule_edits.SourceEdit(cst_metadata.CodeRange(start=cst_metadata.CodePosition(2, 0), end=cst_metadata.CodePosition(2, 6)), "renamed")

        result = rule_edits.apply_source_edits(module, (edit,))

        self.assertEqual(result.code, "first = 1\r\nrenamed = 2\r\n")
