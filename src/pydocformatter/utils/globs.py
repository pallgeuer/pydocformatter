"""Gitignore-style glob matching helpers."""

# Future imports
from __future__ import annotations

# Standard library imports
import os
import fnmatch
import dataclasses


@dataclasses.dataclass(frozen=True)
class CompiledGlobPattern:
    """A single compiled glob pattern.

    Attributes:
        pattern (str): Original glob pattern.
        segments (tuple[str, ...]): Non-empty slash-delimited pattern segments.
        has_slash (bool): Whether the original pattern contains a slash and should be matched against path segments
            instead of only a basename.
    """

    pattern: str
    segments: tuple[str, ...]
    has_slash: bool

    @classmethod
    def compile(cls, pattern: str) -> CompiledGlobPattern:
        """Compile a raw glob pattern into normalized path segments.

        Args:
            pattern (str): Glob pattern using POSIX-style `/` path separators.

        Returns:
            CompiledGlobPattern: Compiled pattern with cached segment metadata.
        """
        return cls(pattern=pattern, segments=tuple(segment for segment in pattern.split("/") if segment), has_slash="/" in pattern)

    def matches(self, normalized_path: str, *, match_parent_segments_for_bare: bool, match_descendants_for_slash: bool) -> bool:
        """Return whether this pattern matches a normalized POSIX-style path.

        Args:
            normalized_path (str): Path to match, already normalized to POSIX separators.
            match_parent_segments_for_bare (bool): Whether slashless patterns can match parent directory segments as
                well as the basename.
            match_descendants_for_slash (bool): Whether slash-containing patterns also match descendant paths after the
                pattern itself matches.

        Returns:
            bool: True if the normalized path matches this pattern.
        """
        path_segments = tuple(segment for segment in normalized_path.split("/") if segment)
        return self.matches_segments(path_segments, match_parent_segments_for_bare=match_parent_segments_for_bare, match_descendants_for_slash=match_descendants_for_slash)

    def matches_segments(self, path_segments: tuple[str, ...], *, match_parent_segments_for_bare: bool, match_descendants_for_slash: bool) -> bool:
        """Return whether this pattern matches already split non-empty path segments.

        Args:
            path_segments (tuple[str, ...]): Non-empty candidate segments shared across pattern evaluation.
            match_parent_segments_for_bare (bool): Whether a bare pattern can match candidate parent segments.
            match_descendants_for_slash (bool): Whether a complete slash pattern also accepts descendant segments.

        Returns:
            bool: Whether this compiled pattern matches the supplied segments.
        """
        if not path_segments or not self.segments:
            return False

        if not self.has_slash:
            if fnmatch.fnmatchcase(path_segments[-1], self.pattern):
                return True
            if match_parent_segments_for_bare:
                return any(fnmatch.fnmatchcase(segment, self.pattern) for segment in path_segments[:-1])
            return False

        return _match_segment_glob(path_segments, self.segments, 0, 0, allow_descendants=match_descendants_for_slash)


@dataclasses.dataclass(frozen=True)
class GlobPatternSet:
    """A compile-once set of glob patterns.

    Attributes:
        literal_bare_patterns (frozenset[str]): Non-empty slashless patterns with exact segment semantics.
        wildcard_bare_patterns (tuple[CompiledGlobPattern, ...]): Ordered non-empty slashless patterns requiring
            `fnmatchcase()`.
        slash_patterns (tuple[CompiledGlobPattern, ...]): Ordered non-empty patterns matched against anchored path
            segments.
        match_parent_segments_for_bare (bool): Whether slashless patterns can match parent directory segments.
        match_descendants_for_slash (bool): Whether slash-containing patterns match descendant paths.
    """

    literal_bare_patterns: frozenset[str]
    wildcard_bare_patterns: tuple[CompiledGlobPattern, ...]
    slash_patterns: tuple[CompiledGlobPattern, ...]
    match_parent_segments_for_bare: bool = False
    match_descendants_for_slash: bool = False

    @classmethod
    def compile(cls, patterns: tuple[str, ...], *, match_parent_segments_for_bare: bool, match_descendants_for_slash: bool = False) -> GlobPatternSet:
        """Compile glob patterns with the requested match semantics.

        Args:
            patterns (tuple[str, ...]): Raw glob patterns to compile.
            match_parent_segments_for_bare (bool): Whether slashless patterns can match parent directory segments.
            match_descendants_for_slash (bool): Whether slash-containing patterns match descendant paths.

        Returns:
            GlobPatternSet: Compiled pattern set configured with the requested matching behavior.
        """
        compiled_patterns = tuple(CompiledGlobPattern.compile(pattern) for pattern in patterns)
        return cls(
            literal_bare_patterns=frozenset(pattern.pattern for pattern in compiled_patterns if pattern.segments and not pattern.has_slash and not _has_fnmatch_magic(pattern.pattern)),
            wildcard_bare_patterns=tuple(pattern for pattern in compiled_patterns if pattern.segments and not pattern.has_slash and _has_fnmatch_magic(pattern.pattern)),
            slash_patterns=tuple(pattern for pattern in compiled_patterns if pattern.segments and pattern.has_slash),
            match_parent_segments_for_bare=match_parent_segments_for_bare,
            match_descendants_for_slash=match_descendants_for_slash,
        )

    def matches(self, normalized_path: str) -> bool:
        """Return whether any compiled pattern matches a normalized POSIX-style path.

        Args:
            normalized_path (str): Path to match, already normalized to POSIX separators.

        Returns:
            bool: True if at least one compiled pattern matches the path.
        """
        path_segments = tuple(segment for segment in normalized_path.split("/") if segment)
        if not path_segments:
            return False

        bare_segments = path_segments if self.match_parent_segments_for_bare else path_segments[-1:]
        if any(segment in self.literal_bare_patterns for segment in bare_segments):
            return True
        if any(fnmatch.fnmatchcase(segment, pattern.pattern) for pattern in self.wildcard_bare_patterns for segment in bare_segments):
            return True
        return any(
            pattern.matches_segments(path_segments, match_parent_segments_for_bare=self.match_parent_segments_for_bare, match_descendants_for_slash=self.match_descendants_for_slash)
            for pattern in self.slash_patterns
        )


@dataclasses.dataclass(frozen=True)
class BaseRelativeGlobMatcher:
    """A glob matcher evaluated against paths relative to one base directory.

    Attributes:
        base_path (str): Directory relative to which filesystem paths are normalized before matching.
        matcher (GlobPatternSet): Compiled POSIX-style glob matcher used for normalized relative paths.
    """

    base_path: str
    matcher: GlobPatternSet

    @classmethod
    def compile(cls, patterns: tuple[str, ...], *, base_path: str, match_parent_segments_for_bare: bool, match_descendants_for_slash: bool = False) -> BaseRelativeGlobMatcher:
        """Compile a base-relative glob matcher.

        Args:
            patterns (tuple[str, ...]): Raw POSIX-style glob patterns to compile.
            base_path (str): Directory relative to which matched filesystem paths are normalized.
            match_parent_segments_for_bare (bool): Whether slashless patterns can match parent directory segments.
            match_descendants_for_slash (bool): Whether slash-containing patterns also match descendant paths.

        Returns:
            BaseRelativeGlobMatcher: Compiled matcher that normalizes filesystem paths against `base_path`.
        """
        return cls(
            base_path=base_path, matcher=GlobPatternSet.compile(patterns, match_parent_segments_for_bare=match_parent_segments_for_bare, match_descendants_for_slash=match_descendants_for_slash)
        )

    def matches(self, path: str) -> bool:
        """Return whether `path` matches after base-relative POSIX normalization.

        Args:
            path (str): Filesystem path to normalize relative to this matcher's base path.

        Returns:
            bool: Whether the normalized relative path matches this matcher's glob patterns.
        """
        return self.matcher.matches(base_relative_posix_path(path, self.base_path))


def base_relative_posix_path(path: str, base_path: str) -> str:
    """Return a base-relative path using POSIX separators.

    Args:
        path (str): Filesystem path to normalize.
        base_path (str): Directory used as the relative path base.

    Returns:
        str: Relative path from `base_path` to `path` using `/` separators.
    """
    return os.path.relpath(os.path.abspath(path), os.path.abspath(base_path)).replace(os.sep, "/")


def _has_fnmatch_magic(pattern: str) -> bool:
    """Return whether a pattern conservatively contains `fnmatch` wildcard syntax.

    Args:
        pattern (str): Slashless raw pattern to classify.

    Returns:
        bool: Whether `*`, `?`, or `[` keeps the pattern on the wildcard path.
    """
    return any(character in pattern for character in "*?[")


def _match_segment_glob(path_segments: tuple[str, ...], pattern_segments: tuple[str, ...], path_index: int, pattern_index: int, *, allow_descendants: bool = False) -> bool:
    """Recursively match path segments against glob segments with ** support."""
    if pattern_index == len(pattern_segments):
        return allow_descendants or path_index == len(path_segments)

    current_pattern = pattern_segments[pattern_index]
    if current_pattern == "**":
        if _match_segment_glob(path_segments, pattern_segments, path_index, pattern_index + 1, allow_descendants=allow_descendants):
            return True
        if path_index < len(path_segments):
            return _match_segment_glob(path_segments, pattern_segments, path_index + 1, pattern_index, allow_descendants=allow_descendants)
        return False

    if path_index >= len(path_segments):
        return False
    if not fnmatch.fnmatchcase(path_segments[path_index], current_pattern):
        return False
    return _match_segment_glob(path_segments, pattern_segments, path_index + 1, pattern_index + 1, allow_descendants=allow_descendants)
