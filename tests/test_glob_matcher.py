# Standard library imports
import tempfile

# Third-party imports
import pytest

# First-party imports
from pydocformatter import file_selection
from pydocformatter.file_selection import FileSelectionError
from pydocformatter.utils.globs import BaseRelativeGlobMatcher, GlobPatternSet


def test_ruff_spec_basename_patterns() -> None:
    matcher = GlobPatternSet.compile(("*.py", "module.p?", "file[0-9].py"), match_parent_segments_for_bare=False)

    assert matcher.matches("pkg/module.py")
    assert matcher.matches("pkg/module.px")
    assert matcher.matches("pkg/file7.py")
    assert not matcher.matches("pkg/file7.txt")
    assert not matcher.matches("pkg/module.txt")


def test_ruff_spec_bare_exclude_matches_parent_segments() -> None:
    matcher = GlobPatternSet.compile((".mypy_cache", "skip.py"), match_parent_segments_for_bare=True)

    assert matcher.matches("pkg/.mypy_cache/cache.py")
    assert matcher.matches("pkg/skip.py")
    assert not matcher.matches("pkg/keep.py")


def test_ruff_spec_slash_patterns_are_project_relative() -> None:
    matcher = GlobPatternSet.compile(("src/*.py", "tests/**/test_*.py"), match_parent_segments_for_bare=True)

    assert matcher.matches("src/a.py")
    assert matcher.matches("tests/test_a.py")
    assert matcher.matches("tests/unit/test_a.py")
    assert not matcher.matches("pkg/src/a.py")
    assert not matcher.matches("tests/unit/helper.py")


def test_ruff_spec_slash_excludes_match_descendants() -> None:
    matcher = GlobPatternSet.compile(("src/generated",), match_parent_segments_for_bare=True, match_descendants_for_slash=True)

    assert matcher.matches("src/generated")
    assert matcher.matches("src/generated/a.py")
    assert matcher.matches("src/generated/pkg/a.py")
    assert not matcher.matches("src/generated_extra/a.py")


def test_ruff_spec_double_star_matches_zero_or_more_segments() -> None:
    matcher = GlobPatternSet.compile(("src/**/test*.py",), match_parent_segments_for_bare=False)

    assert matcher.matches("src/test_a.py")
    assert matcher.matches("src/pkg/test_a.py")
    assert not matcher.matches("pkg/test_a.py")


def test_base_relative_matcher_normalizes_filesystem_paths() -> None:
    with tempfile.TemporaryDirectory() as td:
        matcher = BaseRelativeGlobMatcher.compile(("src/*.py",), base_path=td, match_parent_segments_for_bare=False)

        assert matcher.matches(f"{td}/src/module.py")
        assert not matcher.matches(f"{td}/pkg/module.py")


def test_empty_include_patterns_are_rejected() -> None:
    with pytest.raises(FileSelectionError):
        file_selection.validate_include_patterns(("",))


def test_directory_shaped_include_patterns_are_allowed() -> None:
    file_selection.validate_include_patterns(("src/", "src/**", "**"))


def test_invalid_exclude_patterns_are_rejected() -> None:
    with pytest.raises(FileSelectionError):
        file_selection.validate_exclude_patterns(("",))
