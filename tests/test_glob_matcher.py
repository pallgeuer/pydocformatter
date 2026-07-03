import tempfile
import unittest

import pydocformatter.file_selection as file_selection
from pydocformatter.file_selection import FileSelectionError
from pydocformatter.utils.globs import BaseRelativeGlobMatcher, GlobPatternSet


class TestGlobMatcher(unittest.TestCase):
    def test_ruff_spec_basename_patterns(self) -> None:
        matcher = GlobPatternSet.compile(
            ("*.py", "module.p?", "file[0-9].py"),
            match_parent_segments_for_bare=False,
        )

        self.assertTrue(matcher.matches("pkg/module.py"))
        self.assertTrue(matcher.matches("pkg/module.px"))
        self.assertTrue(matcher.matches("pkg/file7.py"))
        self.assertFalse(matcher.matches("pkg/file7.txt"))
        self.assertFalse(matcher.matches("pkg/module.txt"))

    def test_ruff_spec_bare_exclude_matches_parent_segments(self) -> None:
        matcher = GlobPatternSet.compile(
            (".mypy_cache", "skip.py"),
            match_parent_segments_for_bare=True,
        )

        self.assertTrue(matcher.matches("pkg/.mypy_cache/cache.py"))
        self.assertTrue(matcher.matches("pkg/skip.py"))
        self.assertFalse(matcher.matches("pkg/keep.py"))

    def test_ruff_spec_slash_patterns_are_project_relative(self) -> None:
        matcher = GlobPatternSet.compile(
            ("src/*.py", "tests/**/test_*.py"),
            match_parent_segments_for_bare=True,
        )

        self.assertTrue(matcher.matches("src/a.py"))
        self.assertTrue(matcher.matches("tests/test_a.py"))
        self.assertTrue(matcher.matches("tests/unit/test_a.py"))
        self.assertFalse(matcher.matches("pkg/src/a.py"))
        self.assertFalse(matcher.matches("tests/unit/helper.py"))

    def test_ruff_spec_slash_excludes_match_descendants(self) -> None:
        matcher = GlobPatternSet.compile(
            ("src/generated",),
            match_parent_segments_for_bare=True,
            match_descendants_for_slash=True,
        )

        self.assertTrue(matcher.matches("src/generated"))
        self.assertTrue(matcher.matches("src/generated/a.py"))
        self.assertTrue(matcher.matches("src/generated/pkg/a.py"))
        self.assertFalse(matcher.matches("src/generated_extra/a.py"))

    def test_ruff_spec_double_star_matches_zero_or_more_segments(self) -> None:
        matcher = GlobPatternSet.compile(
            ("src/**/test*.py",),
            match_parent_segments_for_bare=False,
        )

        self.assertTrue(matcher.matches("src/test_a.py"))
        self.assertTrue(matcher.matches("src/pkg/test_a.py"))
        self.assertFalse(matcher.matches("pkg/test_a.py"))

    def test_base_relative_matcher_normalizes_filesystem_paths(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            matcher = BaseRelativeGlobMatcher.compile(("src/*.py",), base_path=td, match_parent_segments_for_bare=False)

            self.assertTrue(matcher.matches(f"{td}/src/module.py"))
            self.assertFalse(matcher.matches(f"{td}/pkg/module.py"))

    def test_empty_include_patterns_are_rejected(self) -> None:
        with self.assertRaises(FileSelectionError):
            file_selection.validate_include_patterns(
                ("",),
            )

    def test_directory_shaped_include_patterns_are_allowed(self) -> None:
        file_selection.validate_include_patterns(
            ("src/", "src/**", "**"),
        )

    def test_invalid_exclude_patterns_are_rejected(self) -> None:
        with self.assertRaises(FileSelectionError):
            file_selection.validate_exclude_patterns(
                ("",),
            )


if __name__ == "__main__":
    unittest.main()
