from dataclasses import dataclass
from fnmatch import fnmatchcase


class GlobPatternError(ValueError):
    """Raised when a file-selection glob pattern is invalid.

    This exception is used for validation failures in include or exclude glob lists
    before those patterns are compiled for file selection.
    """


@dataclass(frozen=True)
class CompiledGlobPattern:
    """A single compiled glob pattern.

    Attributes:
        pattern (str): Original glob pattern.
        segments (tuple[str, ...]): Non-empty slash-delimited pattern segments.
        has_slash (bool): Whether the original pattern contains a slash and should be
            matched against path segments instead of only a basename.
    """

    pattern: str
    segments: tuple[str, ...]
    has_slash: bool

    @classmethod
    def compile(cls, pattern: str) -> "CompiledGlobPattern":
        """Compile a raw glob pattern into normalized path segments.

        Args:
            pattern (str): Glob pattern using POSIX-style `/` path separators.

        Returns:
            CompiledGlobPattern: Compiled pattern with cached segment metadata.
        """
        return cls(
            pattern=pattern,
            segments=tuple(segment for segment in pattern.split("/") if segment),
            has_slash="/" in pattern,
        )

    def matches(
        self,
        normalized_path: str,
        *,
        match_parent_segments_for_bare: bool,
        match_descendants_for_slash: bool,
    ) -> bool:
        """Return whether this pattern matches a normalized POSIX-style path.

        Args:
            normalized_path (str): Path to match, already normalized to POSIX
                separators.
            match_parent_segments_for_bare (bool): Whether slashless patterns can match
                parent directory segments as well as the basename.
            match_descendants_for_slash (bool): Whether slash-containing patterns also
                match descendant paths after the pattern itself matches.

        Returns:
            bool: True if the normalized path matches this pattern.
        """
        path_segments = tuple(
            segment for segment in normalized_path.split("/") if segment
        )
        if not path_segments or not self.segments:
            return False

        if not self.has_slash:
            if fnmatchcase(path_segments[-1], self.pattern):
                return True
            if match_parent_segments_for_bare:
                return any(
                    fnmatchcase(segment, self.pattern) for segment in path_segments[:-1]
                )
            return False

        return _match_segment_glob(
            path_segments,
            self.segments,
            0,
            0,
            allow_descendants=match_descendants_for_slash,
        )


@dataclass(frozen=True)
class GlobPatternSet:
    """A compile-once set of glob patterns.

    Attributes:
        patterns (tuple[CompiledGlobPattern, ...]): Compiled glob patterns to evaluate.
        match_parent_segments_for_bare (bool): Whether slashless patterns can match
            parent directory segments.
        match_descendants_for_slash (bool): Whether slash-containing patterns match
            descendant paths.
    """

    patterns: tuple[CompiledGlobPattern, ...]
    match_parent_segments_for_bare: bool = False
    match_descendants_for_slash: bool = False

    @classmethod
    def compile(
        cls,
        patterns: tuple[str, ...],
        *,
        include_patterns: bool,
        match_parent_segments_for_bare: bool,
        match_descendants_for_slash: bool = False,
    ) -> "GlobPatternSet":
        """Validate and compile glob patterns with the requested match semantics.

        Args:
            patterns (tuple[str, ...]): Raw glob patterns to validate and compile.
            include_patterns (bool): Whether to validate patterns with include-pattern
                restrictions instead of exclude-pattern restrictions.
            match_parent_segments_for_bare (bool): Whether slashless patterns can match
                parent directory segments.
            match_descendants_for_slash (bool): Whether slash-containing patterns match
                descendant paths.

        Returns:
            GlobPatternSet: Compiled pattern set configured with the requested matching
                behavior.

        Raises:
            `GlobPatternError`: If any pattern is invalid for its include or exclude
                role.
        """
        if include_patterns:
            validate_include_patterns(patterns)
        else:
            validate_exclude_patterns(patterns)
        return cls(
            patterns=tuple(
                CompiledGlobPattern.compile(pattern) for pattern in patterns
            ),
            match_parent_segments_for_bare=match_parent_segments_for_bare,
            match_descendants_for_slash=match_descendants_for_slash,
        )

    def matches(self, normalized_path: str) -> bool:
        """Return whether any compiled pattern matches a normalized POSIX-style path.

        Args:
            normalized_path (str): Path to match, already normalized to POSIX
                separators.

        Returns:
            bool: True if at least one compiled pattern matches the path.
        """
        return any(
            pattern.matches(
                normalized_path,
                match_parent_segments_for_bare=self.match_parent_segments_for_bare,
                match_descendants_for_slash=self.match_descendants_for_slash,
            )
            for pattern in self.patterns
        )


def validate_include_patterns(patterns: tuple[str, ...]) -> None:
    """Validate glob patterns used for file inclusion.

    Include patterns must be non-empty and must target files rather than all descendants
    or directory-only paths.

    Args:
        patterns (tuple[str, ...]): Include glob patterns to validate.

    Returns:
        None: This function returns normally when all patterns are valid.

    Raises:
        `GlobPatternError`: If an include pattern is empty or does not target files.
    """
    for pattern in patterns:
        if not pattern:
            raise GlobPatternError("include patterns must not be empty")
        if pattern.endswith("/"):
            raise GlobPatternError(f"include pattern must target files: {pattern}")
        if pattern.rstrip("/") in {"**", "**/*"}:
            raise GlobPatternError(f"include pattern must target files: {pattern}")


def validate_exclude_patterns(patterns: tuple[str, ...]) -> None:
    """Validate glob patterns used for file exclusion.

    Args:
        patterns (tuple[str, ...]): Exclude glob patterns to validate.

    Returns:
        None: This function returns normally when all patterns are valid.

    Raises:
        `GlobPatternError`: If an exclude pattern is empty.
    """
    for pattern in patterns:
        if not pattern:
            raise GlobPatternError("exclude patterns must not be empty")


def _match_segment_glob(
    path_segments: tuple[str, ...],
    pattern_segments: tuple[str, ...],
    path_index: int,
    pattern_index: int,
    *,
    allow_descendants: bool = False,
) -> bool:
    """Recursively match path segments against glob segments with ** support."""
    if pattern_index == len(pattern_segments):
        return allow_descendants or path_index == len(path_segments)

    current_pattern = pattern_segments[pattern_index]
    if current_pattern == "**":
        if _match_segment_glob(
            path_segments,
            pattern_segments,
            path_index,
            pattern_index + 1,
            allow_descendants=allow_descendants,
        ):
            return True
        if path_index < len(path_segments):
            return _match_segment_glob(
                path_segments,
                pattern_segments,
                path_index + 1,
                pattern_index,
                allow_descendants=allow_descendants,
            )
        return False

    if path_index >= len(path_segments):
        return False
    if not fnmatchcase(path_segments[path_index], current_pattern):
        return False
    return _match_segment_glob(
        path_segments,
        pattern_segments,
        path_index + 1,
        pattern_index + 1,
        allow_descendants=allow_descendants,
    )
