import unittest

import pydocformatter.utils as utils


class TestUtils(unittest.TestCase):
    def test_format_line_ranges(self) -> None:
        self.assertEqual(utils.format_line_ranges([7]), "7")
        self.assertEqual(utils.format_line_ranges([3, 4, 5]), "3-5")
        self.assertEqual(utils.format_line_ranges([1, 2, 4, 6, 7, 8, 10]), "1-2, 4, 6-8, 10")


if __name__ == "__main__":
    unittest.main()
