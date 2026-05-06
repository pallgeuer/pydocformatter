import unittest

from pydocformatter.utils import format_line_ranges


class TestUtils(unittest.TestCase):
    def test_format_line_ranges(self) -> None:
        self.assertEqual(format_line_ranges([7]), "7")
        self.assertEqual(format_line_ranges([3, 4, 5]), "3-5")
        self.assertEqual(format_line_ranges([1, 2, 4, 6, 7, 8, 10]), "1-2, 4, 6-8, 10")


if __name__ == "__main__":
    unittest.main()
