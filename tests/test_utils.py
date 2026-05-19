import tempfile
import unittest
from pathlib import Path

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

    def test_find_git_root_for_path_finds_nearest_containing_root(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            nested = root / "src" / "pkg"
            nested.mkdir(parents=True)
            (root / ".git").write_text("gitdir: .git-test\n", encoding="utf-8")

            self.assertEqual(misc.find_git_root_for_path(str(nested)), str(root))

    def test_find_git_root_for_path_returns_none_outside_git_root(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            self.assertIsNone(misc.find_git_root_for_path(td))

    def test_find_git_root_for_path_uses_cached_intermediate_directory(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            intermediate = root / "src"
            nested = intermediate / "pkg"
            nested.mkdir(parents=True)
            root_cache: dict[str, str | None] = {str(intermediate): str(root)}

            self.assertEqual(misc.find_git_root_for_path(str(nested), root_cache), str(root))
            self.assertEqual(root_cache[str(nested)], str(root))

    def test_find_git_root_for_path_backfills_visited_directories(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            nested = root / "src" / "pkg"
            nested.mkdir(parents=True)
            (root / ".git").write_text("gitdir: .git-test\n", encoding="utf-8")
            root_cache: dict[str, str | None] = {}

            self.assertEqual(misc.find_git_root_for_path(str(nested), root_cache), str(root))
            self.assertEqual(root_cache[str(nested)], str(root))
            self.assertEqual(root_cache[str(nested.parent)], str(root))
            self.assertEqual(root_cache[str(root)], str(root))


if __name__ == "__main__":
    unittest.main()
