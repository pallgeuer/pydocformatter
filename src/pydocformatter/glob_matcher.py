from dataclasses import dataclass
from fnmatch import fnmatchcase


class GlobPatternError(ValueError):
    """Raised when a file-selection glob pattern is invalid."""


@dataclass(frozen=True)
class CompiledGlobPattern:
    """A single compiled glob pattern."""

    pattern: str
    segments: tuple[str, ...]
    has_slash: bool

    @classmethod
    def compile(cls, pattern: str) -> "CompiledGlobPattern":
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
    """A compile-once set of glob patterns."""

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
        return any(
            pattern.matches(
                normalized_path,
                match_parent_segments_for_bare=self.match_parent_segments_for_bare,
                match_descendants_for_slash=self.match_descendants_for_slash,
            )
            for pattern in self.patterns
        )


def validate_include_patterns(patterns: tuple[str, ...]) -> None:
    """Validate glob patterns used for file inclusion."""
    for pattern in patterns:
        if not pattern:
            raise GlobPatternError("include patterns must not be empty")
        if pattern.endswith("/"):
            raise GlobPatternError(f"include pattern must target files: {pattern}")
        if pattern.rstrip("/") in {"**", "**/*"}:
            raise GlobPatternError(f"include pattern must target files: {pattern}")


def validate_exclude_patterns(patterns: tuple[str, ...]) -> None:
    """Validate glob patterns used for file exclusion."""
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
