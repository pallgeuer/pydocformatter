import contextlib
import os
import tempfile
import unittest
from io import StringIO

import pydocformatter.formatters.pycommentfmt as pycommentfmt
from pydocformatter.config import FormatterSettings


class TestPyCommentFmt(unittest.TestCase):

    @staticmethod
    def _write_and_readback(
        content: str, line_length: int = 88, check: bool = False
    ) -> tuple[bool, str, str]:
        with tempfile.NamedTemporaryFile(
            mode="w+", delete=False, suffix=".py", encoding="utf-8"
        ) as tf:
            tf.write(content)
            filename = tf.name

        try:
            output = StringIO()
            with contextlib.redirect_stdout(output):
                result = pycommentfmt.format_comments(
                    filename, FormatterSettings(line_length=line_length), check=check
                )
            with open(filename, encoding="utf-8") as f:
                final = f.read()
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
        result, final, _ = self._write_and_readback(source)
        self.assertFalse(result)
        self.assertEqual(final, source)

    def test_inline_comment_spacing(self) -> None:
        source = "x = 1  #bad spacing\n"
        expected = "x = 1  # bad spacing\n"
        result, final, _ = self._write_and_readback(source)
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
        result, _, stdout = self._write_and_readback(source, check=True)
        self.assertFalse(result)
        self.assertEqual(stdout, "")

    def test_shebang_and_encoding_ignored(self) -> None:
        source = "#!/usr/bin/env python\n# -*- coding: utf-8 -*-\n#Comment that needs wrapping because it is long.\n"
        result, final, _ = self._write_and_readback(source, line_length=60)
        self.assertTrue(result)
        self.assertTrue(
            final.startswith("#!/usr/bin/env python\n# -*- coding: utf-8 -*-\n")
        )

    def test_special_comments_skipped(self) -> None:
        for comment in [
            "# noqa",
            "# type: ignore",
            "# pylint: disable=E1101",
            "# fmt: off",
            "# pragma: no cover",
        ]:
            result, final, _ = self._write_and_readback(comment + "\n")
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
        source = (
            "# This first comment line is very long and should be wrapped by formatting.\n"
            "x = 1\n"
            "x = 2\n"
            "# This second comment line is also very long and should be wrapped by formatting.\n"
        )
        result, _, stdout = self._write_and_readback(source, line_length=60, check=True)
        self.assertTrue(result)
        self.assertRegex(
            stdout.strip(),
            r"^.+: Needs comment formatting on lines 1, 4$",
        )


if __name__ == "__main__":
    unittest.main()
