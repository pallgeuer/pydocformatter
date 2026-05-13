import unittest

import pydocformatter.utils.misc as misc


class TestUtils(unittest.TestCase):
    def test_format_line_ranges(self) -> None:
        self.assertEqual(misc.format_line_ranges([7]), "7")
        self.assertEqual(misc.format_line_ranges([3, 4, 5]), "3-5")
        self.assertEqual(misc.format_line_ranges([1, 2, 4, 6, 7, 8, 10]), "1-2, 4, 6-8, 10")

    def test_auto_plural(self) -> None:
        self.assertEqual(misc.auto_plural(1, "error"), "error")
        self.assertEqual(misc.auto_plural(0, "error"), "errors")
        self.assertEqual(misc.auto_plural(2, "error"), "errors")


if __name__ == "__main__":
    unittest.main()
