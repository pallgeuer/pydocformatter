# Standard library imports
import fnmatch
import tempfile

# Third-party imports
import pytest

# First-party imports
from pydocformatter import file_selection
from pydocformatter.file_selection import FileSelectionError
from pydocformatter.utils.globs import BaseRelativeGlobMatcher, CompiledGlobPattern, GlobPatternSet


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


def test_literal_bare_pattern_matches_only_basename_when_parent_matching_is_disabled() -> None:
    matcher = GlobPatternSet.compile(("target",), match_parent_segments_for_bare=False)

    assert matcher.matches("pkg/target")
    assert not matcher.matches("target/file.py")
    assert not matcher.matches("pkg/other")


def test_literal_bare_patterns_match_parent_segments_only_when_enabled() -> None:
    enabled = GlobPatternSet.compile(("build", "dist", "node_modules"), match_parent_segments_for_bare=True)
    disabled = GlobPatternSet.compile(("build", "dist", "node_modules"), match_parent_segments_for_bare=False)

    assert enabled.matches("pkg/node_modules/module.py")
    assert enabled.matches("build/module.py")
    assert not enabled.matches("pkg/source/module.py")
    assert not disabled.matches("pkg/node_modules/module.py")


@pytest.mark.parametrize(
    ("pattern", "matching", "missing"),
    [
        pytest.param("*.py", "module.py", "module.txt", id="star"),
        pytest.param("module.p?", "module.py", "module.pyw", id="question"),
        pytest.param("file[0-9].py", "file7.py", "filex.py", id="bracket"),
    ],
)
def test_wildcard_bare_patterns_use_fnmatchcase(pattern: str, matching: str, missing: str) -> None:
    matcher = GlobPatternSet.compile((pattern,), match_parent_segments_for_bare=False)

    assert matcher.matches(f"pkg/{matching}")
    assert not matcher.matches(f"pkg/{missing}")


@pytest.mark.parametrize("pattern", ["name[", "[abc", "module[.py"])
def test_unmatched_open_bracket_matches_exactly_like_fnmatchcase(pattern: str) -> None:
    matcher = GlobPatternSet.compile((pattern,), match_parent_segments_for_bare=False)

    for candidate in (pattern, f"{pattern}x", "other"):
        assert matcher.matches(candidate) is fnmatch.fnmatchcase(candidate, pattern)


@pytest.mark.parametrize("literal", ["name]", "file.name", "dash-name", "two words", ".", "-"])
def test_non_magic_literal_characters_use_exact_matching(literal: str) -> None:
    matcher = GlobPatternSet.compile((literal,), match_parent_segments_for_bare=False)

    assert matcher.matches(f"pkg/{literal}")
    assert not matcher.matches(f"pkg/{literal}x")


def test_ruff_spec_slash_patterns_are_project_relative() -> None:
    matcher = GlobPatternSet.compile(("src/*.py", "tests/**/test_*.py"), match_parent_segments_for_bare=True)

    assert matcher.matches("src/a.py")
    assert matcher.matches("tests/test_a.py")
    assert matcher.matches("tests/unit/test_a.py")
    assert not matcher.matches("pkg/src/a.py")
    assert not matcher.matches("tests/unit/helper.py")


@pytest.mark.parametrize(
    ("pattern", "path", "expected"),
    [
        pytest.param("/", "value", False, id="zero-segments"),
        pytest.param("/src/", "src", True, id="one-segment"),
        pytest.param("/src/", "pkg/src", False, id="one-segment-anchored"),
        pytest.param("src/pkg/*.py", "src/pkg/module.py", True, id="multiple-segments"),
        pytest.param("src/pkg/*.py", "pkg/src/pkg/module.py", False, id="multiple-segments-anchored"),
    ],
)
def test_slash_patterns_handle_zero_one_and_multiple_segments(pattern: str, path: str, expected: bool) -> None:
    matcher = GlobPatternSet.compile((pattern,), match_parent_segments_for_bare=False)

    assert matcher.matches(path) is expected


def test_ruff_spec_slash_excludes_match_descendants() -> None:
    matcher = GlobPatternSet.compile(("src/generated",), match_parent_segments_for_bare=True, match_descendants_for_slash=True)

    assert matcher.matches("src/generated")
    assert matcher.matches("src/generated/a.py")
    assert matcher.matches("src/generated/pkg/a.py")
    assert not matcher.matches("src/generated_extra/a.py")


def test_slash_descendant_matching_can_be_disabled() -> None:
    enabled = GlobPatternSet.compile(("src/generated",), match_parent_segments_for_bare=False, match_descendants_for_slash=True)
    disabled = GlobPatternSet.compile(("src/generated",), match_parent_segments_for_bare=False, match_descendants_for_slash=False)

    assert enabled.matches("src/generated/a.py")
    assert not disabled.matches("src/generated/a.py")
    assert enabled.matches("src/generated")
    assert disabled.matches("src/generated")


def test_ruff_spec_double_star_matches_zero_or_more_segments() -> None:
    matcher = GlobPatternSet.compile(("src/**/test*.py",), match_parent_segments_for_bare=False)

    assert matcher.matches("src/test_a.py")
    assert matcher.matches("src/pkg/test_a.py")
    assert not matcher.matches("pkg/test_a.py")


@pytest.mark.parametrize("pattern", ["/src//*.py/", "src///*.py", "//src/*.py//"])
def test_slash_pattern_normalization_ignores_leading_repeated_and_trailing_separators(pattern: str) -> None:
    matcher = GlobPatternSet.compile((pattern,), match_parent_segments_for_bare=False)

    assert matcher.matches("/src//module.py/")
    assert not matcher.matches("pkg/src/module.py")


@pytest.mark.parametrize("pattern", ["", "/", "///"])
def test_patterns_without_non_empty_segments_do_not_match(pattern: str) -> None:
    matcher = GlobPatternSet.compile((pattern,), match_parent_segments_for_bare=True, match_descendants_for_slash=True)

    assert not matcher.matches("")
    assert not matcher.matches("/")
    assert not matcher.matches("value")


def test_glob_pattern_set_compile_builds_expected_partitions() -> None:
    matcher = GlobPatternSet.compile(("build", "two words", "*.py", "name[", "src/*.py", "", "///"), match_parent_segments_for_bare=True)

    assert matcher.literal_bare_patterns == frozenset(("build", "two words"))
    assert tuple(pattern.pattern for pattern in matcher.wildcard_bare_patterns) == ("*.py", "name[")
    assert tuple(pattern.pattern for pattern in matcher.slash_patterns) == ("src/*.py",)


@pytest.mark.parametrize(
    ("pattern", "path", "parent_segments", "descendants"),
    [
        pytest.param("literal", "pkg/literal", False, False, id="literal"),
        pytest.param("parent", "parent/module.py", True, False, id="parent-literal"),
        pytest.param("*.py", "pkg/module.py", False, False, id="wildcard"),
        pytest.param("name[", "pkg/name[", False, False, id="unmatched-bracket"),
        pytest.param("src/**/test*.py", "src/pkg/test_a.py", False, False, id="double-star"),
        pytest.param("src/generated", "src/generated/pkg/a.py", False, True, id="descendants"),
        pytest.param("///", "src/module.py", True, True, id="empty-segments"),
    ],
)
def test_direct_compiled_pattern_and_one_pattern_set_agree(pattern: str, path: str, parent_segments: bool, descendants: bool) -> None:
    compiled = CompiledGlobPattern.compile(pattern)
    pattern_set = GlobPatternSet.compile((pattern,), match_parent_segments_for_bare=parent_segments, match_descendants_for_slash=descendants)

    assert compiled.matches(path, match_parent_segments_for_bare=parent_segments, match_descendants_for_slash=descendants) is pattern_set.matches(path)


def test_compiled_pattern_matches_presegmented_paths_through_public_method() -> None:
    compiled = CompiledGlobPattern.compile("src/**/test*.py")

    assert compiled.matches_segments(("src", "pkg", "test_module.py"), match_parent_segments_for_bare=False, match_descendants_for_slash=False)
    assert not compiled.matches_segments(("src", "pkg", "module.py"), match_parent_segments_for_bare=False, match_descendants_for_slash=False)


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
