import contextlib
import os
import tempfile
import unittest
from io import StringIO

import pydocformatter.formatters.pydocfmt as pydocfmt
from pydocformatter.cli.settings_check import CheckSettings, LineEnding


class TestCommentFormatting(unittest.TestCase):
    @staticmethod
    def _write_and_readback(content: str, *, line_length: int, check: bool = False) -> tuple[bool, str, str]:
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".py", encoding="utf-8") as tf:
            tf.write(content)
            filename = tf.name

        try:
            output = StringIO()
            with contextlib.redirect_stdout(output):
                result = pydocfmt.format_file(filename, CheckSettings(line_length=line_length), fix=not check, output=None)
            with open(filename, encoding="utf-8") as file:
                final = file.read()
        finally:
            os.unlink(filename)

        return result, final, output.getvalue()

    def test_basic_rewrap(self) -> None:
        source = "# This is a really long comment that should be wrapped properly by the formatter tool to multiple lines.\n"
        result, final, _ = self._write_and_readback(source, line_length=60)
        self.assertTrue(result)
        self.assertIn("# This is a really long comment that should be", final)
        self.assertIn("# properly by the formatter tool to multiple lines.\n", final)

    def test_noop_if_already_formatted(self) -> None:
        source = "# A short comment.\n"
        result, final, _ = self._write_and_readback(source, line_length=88)
        self.assertFalse(result)
        self.assertEqual(final, source)

    def test_line_ending_only_difference_does_not_rewrite_formatted_comment(self) -> None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".py") as tf:
            filename = tf.name
        source = b"# A short comment.\r\n"
        with open(filename, "wb") as file:
            file.write(source)

        try:
            result = pydocfmt.format_file(filename, CheckSettings(line_length=88, line_ending=LineEnding.LF), fix=True, output=None)
            with open(filename, "rb") as file:
                final = file.read()
        finally:
            os.unlink(filename)

        self.assertFalse(result)
        self.assertEqual(source, final)

    def test_check_mode_ignores_line_ending_only_difference_for_formatted_comment(self) -> None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".py") as tf:
            filename = tf.name
        source = b"# A short comment.\r\n"
        with open(filename, "wb") as file:
            file.write(source)

        try:
            output = StringIO()
            with contextlib.redirect_stdout(output):
                result = pydocfmt.format_file(filename, CheckSettings(line_length=88, line_ending=LineEnding.LF), fix=False, output=None)
            with open(filename, "rb") as file:
                final = file.read()
        finally:
            os.unlink(filename)

        self.assertFalse(result)
        self.assertEqual("", output.getvalue())
        self.assertEqual(source, final)

    def test_auto_line_ending_preserves_first_detected_crlf_when_rewriting(self) -> None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".py") as tf:
            filename = tf.name
        with open(filename, "wb") as file:
            file.write(b"x = 1\r\n# This is a really long comment that should be wrapped properly by the formatter tool to multiple lines.\n")

        try:
            result = pydocfmt.format_file(filename, CheckSettings(line_length=60), fix=True, output=None)
            with open(filename, "rb") as file:
                final = file.read()
        finally:
            os.unlink(filename)

        self.assertTrue(result)
        self.assertIn(b"\r\n", final)
        self.assertNotIn(b"\n", final.replace(b"\r\n", b""))

    def test_partial_comment_rewrite_preserves_untouched_mixed_line_endings(self) -> None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".py") as tf:
            filename = tf.name
        source = b"first = 1\r\nsecond = 2\n# This is a really long comment that should be wrapped properly by the formatter tool to multiple lines.\nthird = 3\r\n"
        expected = b"first = 1\r\nsecond = 2\n# This is a really long comment that should be wrapped\r\n# properly by the formatter tool to multiple lines.\r\nthird = 3\r\n"
        with open(filename, "wb") as file:
            file.write(source)

        try:
            result = pydocfmt.format_file(filename, CheckSettings(line_length=60), fix=True, output=None)
            with open(filename, "rb") as file:
                final = file.read()
        finally:
            os.unlink(filename)

        self.assertTrue(result)
        self.assertEqual(expected, final)

    def test_crlf_line_ending_converts_rewritten_comment_file(self) -> None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".py") as tf:
            filename = tf.name
        with open(filename, "wb") as file:
            file.write(b"# This is a really long comment that should be wrapped properly by the formatter tool to multiple lines.\n")

        try:
            result = pydocfmt.format_file(filename, CheckSettings(line_length=60, line_ending=LineEnding.CR_LF), fix=True, output=None)
            with open(filename, "rb") as file:
                final = file.read()
        finally:
            os.unlink(filename)

        self.assertTrue(result)
        self.assertIn(b"\r\n", final)
        self.assertNotIn(b"\n", final.replace(b"\r\n", b""))

    def test_inline_comment_spacing(self) -> None:
        source = "x = 1  #bad spacing\n"
        expected = "x = 1  # bad spacing\n"
        result, final, _ = self._write_and_readback(source, line_length=88)
        self.assertTrue(result)
        self.assertEqual(expected, final)

    def test_inline_comment_wrapping(self) -> None:
        source = "x = 1  # This is an inline comment that is way too long and must be wrapped above the code.\n"
        result, final, _ = self._write_and_readback(source, line_length=60)
        self.assertTrue(result)
        self.assertTrue("# This is an inline comment" in final)
        self.assertTrue("x = 1" in final.splitlines()[-1])

    def test_check_mode_outputs_lines(self) -> None:
        source = "# This is a long comment that should be wrapped because it exceeds the given line length.\n"
        result, _, stdout = self._write_and_readback(source, line_length=60, check=True)
        self.assertTrue(result)
        self.assertRegex(
            stdout.strip(),
            r"^.+: Needs comment formatting on line 1$",
        )

    def test_check_mode_no_changes(self) -> None:
        source = "# All good.\n"
        result, _, stdout = self._write_and_readback(source, line_length=88, check=True)
        self.assertFalse(result)
        self.assertEqual(stdout, "")

    def test_shebang_and_encoding_ignored(self) -> None:
        source = "#!/usr/bin/env python\n# -*- coding: utf-8 -*-\n#Comment that needs wrapping because it is long.\n"
        result, final, _ = self._write_and_readback(source, line_length=60)
        self.assertTrue(result)
        self.assertTrue(final.startswith("#!/usr/bin/env python\n# -*- coding: utf-8 -*-\n"))

    def test_special_comments_skipped(self) -> None:
        for comment in [
            "# noqa",
            "# type: ignore",
            "# pylint: disable=E1101",
            "# fmt: off",
            "# pragma: no cover",
        ]:
            result, final, _ = self._write_and_readback(comment + "\n", line_length=88)
            self.assertFalse(result)
            self.assertEqual(comment + "\n", final)

    def test_code_comment_block_preserved(self) -> None:
        source = "#     if x == y:\n#         print('match')\n"
        result, final, _ = self._write_and_readback(source, line_length=40)
        self.assertFalse(result)
        self.assertEqual(final, source)

    def test_mixed_comments(self) -> None:
        source = (
            "# This is fine.\n"
            "x = 42  #bad spacing\n"
            "# This comment is very very long and needs to be wrapped across multiple lines based on the line length.\n"
            "#     for x in range(5):\n"
            "#         print(x)\n"
        )
        result, _, stdout = self._write_and_readback(source, line_length=60, check=True)
        self.assertTrue(result)
        self.assertRegex(
            stdout.strip(),
            r"^.+: Needs comment formatting on lines 2-3$",
        )

    def test_check_mode_compresses_non_consecutive_line_ranges(self) -> None:
        source = "# This first comment line is very long and should be wrapped by formatting.\nx = 1\nx = 2\n# This second comment line is also very long and should be wrapped by formatting.\n"
        result, _, stdout = self._write_and_readback(source, line_length=60, check=True)
        self.assertTrue(result)
        self.assertRegex(
            stdout.strip(),
            r"^.+: Needs comment formatting on lines 1, 4$",
        )

    def test_single_run_formats_docstrings_and_comments(self) -> None:
        source = 'def foo():\n    """Does something.\n\nArgs:\n    x (int): some parameter.\n    """\n    # This comment is very very long and needs to be wrapped across multiple lines based on the line length.\n    pass\n'
        result, final, _ = self._write_and_readback(source, line_length=72)
        self.assertTrue(result)
        self.assertIn("    Args:\n        x (int): some parameter.", final)
        self.assertIn("    # This comment is very very long and needs to be wrapped across\n", final)

    def test_check_mode_reports_docstrings_and_comments(self) -> None:
        source = 'def foo():\n    """Does something.\n\nArgs:\n    x (int): some parameter.\n    """\n    # This comment is very very long and needs to be wrapped across multiple lines based on the line length.\n    pass\n'
        result, _, stdout = self._write_and_readback(source, line_length=72, check=True)
        self.assertTrue(result)
        self.assertIn("Needs docstring formatting on lines 2-6", stdout)
        self.assertIn("Needs comment formatting on line 7", stdout)

    def test_check_mode_reports_comment_locations_from_original_source(self) -> None:
        source = 'def foo():\n    """This summary is long enough that formatting expands it across multiple docstring lines before the comment below."""\n    # This comment is very very long and needs to be wrapped across multiple lines based on the line length.\n    pass\n'
        result, _, stdout = self._write_and_readback(source, line_length=72, check=True)
        self.assertTrue(result)
        self.assertIn("Needs docstring formatting on line 2", stdout)
        self.assertIn("Needs comment formatting on line 3", stdout)

    def test_empty_comment_separator_lines_are_preserved(self) -> None:
        source = "#\n#   \n"
        result, final, _ = self._write_and_readback(source, line_length=88)
        self.assertFalse(result)
        self.assertEqual(source, final)

    def test_empty_comment_separator_splits_comment_blocks(self) -> None:
        source = "# First comment that already fits.\n#\n# Second comment that already fits.\n"
        result, final, _ = self._write_and_readback(source, line_length=88)
        self.assertFalse(result)
        self.assertEqual(source, final)


if __name__ == "__main__":
    unittest.main()
