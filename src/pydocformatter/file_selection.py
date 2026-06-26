"""File discovery and filtering for checkable Python sources."""

from __future__ import annotations

import dataclasses
import os
import subprocess
from collections import defaultdict
from collections.abc import Mapping
from enum import Enum

import pydocformatter.settings as settings_core
import pydocformatter.utils.misc as misc
from pydocformatter.cli.settings_check import CheckSettings
from pydocformatter.utils.globs import GlobPatternSet

STDIN_VIRTUAL_FILE = "-"


class FileSelectionError(ValueError):
    """Raised when file-selection settings cannot be applied."""


class DecisionReason(str, Enum):
    """Stable reason codes for file-selection decisions.

    Attributes:
        INCLUDED (DecisionReason): The path matched include rules and did not match exclude rules.
        EXPLICIT_INCLUDED (DecisionReason): The path was passed explicitly and accepted.
        NOT_INCLUDED (DecisionReason): The path did not match configured include patterns.
        EXCLUDED (DecisionReason): The path matched configured exclude patterns.
        GITIGNORED (DecisionReason): The path was rejected because git reported it as ignored.
        DUPLICATE (DecisionReason): The path resolves to the same file as another accepted path.
    """

    INCLUDED = "included"
    EXPLICIT_INCLUDED = "explicit-included"
    NOT_INCLUDED = "not-included"
    EXCLUDED = "excluded"
    GITIGNORED = "gitignored"
    DUPLICATE = "duplicate"


_REASON_MESSAGES = {
    DecisionReason.INCLUDED: "included",
    DecisionReason.EXPLICIT_INCLUDED: "included explicitly",
    DecisionReason.NOT_INCLUDED: "does not match include patterns",
    DecisionReason.EXCLUDED: "matches exclude patterns",
    DecisionReason.GITIGNORED: "matches .gitignore",
    DecisionReason.DUPLICATE: "duplicate path to already selected file",
}


@dataclasses.dataclass(frozen=True)
class SelectedFile:
    """An accepted path with the settings profile that applies to it.

    Attributes:
        path (str): Display path accepted for formatting.
        profile (settings_core.SettingsProfile[CheckSettings]): Resolved settings profile to use for this path.
    """

    path: str
    profile: settings_core.SettingsProfile[CheckSettings]

    @property
    def settings(self) -> CheckSettings:
        """Return the resolved settings for this selected file."""
        return self.profile.settings


@dataclasses.dataclass(frozen=True)
class FileDecision:
    """Result of evaluating whether one path should be formatted.

    Attributes:
        path (str): Display path that was evaluated.
        accepted (bool): Whether the path should be formatted.
        reason (DecisionReason): Stable machine-readable decision reason.
        explicit (bool): Whether the path came directly from a CLI argument rather than directory traversal.
        profile (settings_core.SettingsProfile[CheckSettings] | None): Settings profile used to make the decision.
    """

    path: str
    accepted: bool
    reason: DecisionReason
    explicit: bool
    profile: settings_core.SettingsProfile[CheckSettings] | None = dataclasses.field(compare=False, repr=False)
    respect_gitignore: bool = dataclasses.field(compare=False, repr=False)

    @property
    def message(self) -> str:
        """Return the human-readable reason message for file-selection output.

        Returns:
            str: Message corresponding to the decision reason.
        """
        return _REASON_MESSAGES[self.reason]


@dataclasses.dataclass(frozen=True)
class SelectionResult:
    """Accepted files and all file-selection decisions.

    Attributes:
        accepted_paths (tuple[str, ...]): Ordered, deduplicated display paths that should be formatted.
        decisions (tuple[FileDecision, ...]): Ordered decisions for every considered path or pruned directory.
        selected_files (tuple[SelectedFile, ...]): Accepted paths paired with their resolved settings profiles.
    """

    accepted_paths: tuple[str, ...]
    decisions: tuple[FileDecision, ...]
    selected_files: tuple[SelectedFile, ...]

    def profile_for_path(self, path: str) -> settings_core.SettingsProfile[CheckSettings]:
        """Return the selected settings profile for an accepted display path."""
        for selected_file in self.selected_files:
            if selected_file.path == path:
                return selected_file.profile
        raise KeyError(path)


@dataclasses.dataclass(frozen=True)
class _Candidate:
    """A discovered path that still needs include, exclude, and gitignore checks."""

    path: str
    explicit: bool
    profile: settings_core.SettingsProfile[CheckSettings]
    respect_gitignore: bool


@dataclasses.dataclass(frozen=True)
class _PatternGroup:
    """Compiled patterns that share one base directory."""

    base_path: str
    matcher: GlobPatternSet

    def matches(self, path: str) -> bool:
        """Return whether this group matches a filesystem path."""
        return self.matcher.matches(_base_relative_posix_path(path, self.base_path))


@dataclasses.dataclass(frozen=True)
class _PatternMatcher:
    """A matcher made from one or more source-base-specific pattern groups."""

    groups: tuple[_PatternGroup, ...]

    @classmethod
    def compile(
        cls,
        profile: settings_core.SettingsProfile[CheckSettings],
        fields: tuple[str, ...],
        *,
        match_parent_segments_for_bare: bool,
        match_descendants_for_slash: bool = False,
    ) -> "_PatternMatcher":
        """Compile path-pattern fields from a settings profile."""
        groups: list[_PatternGroup] = []
        for field in fields:
            patterns = getattr(profile.settings, field)
            if not patterns:
                continue
            groups.append(
                _PatternGroup(
                    base_path=profile.base_for_field(field),
                    matcher=GlobPatternSet.compile(
                        patterns,
                        match_parent_segments_for_bare=match_parent_segments_for_bare,
                        match_descendants_for_slash=match_descendants_for_slash,
                    ),
                )
            )
        return cls(tuple(groups))

    def matches(self, path: str) -> bool:
        """Return whether any source-base-specific group matches the path."""
        return any(group.matches(path) for group in self.groups)


@dataclasses.dataclass
class _SelectionContext:
    """Shared state for one file-selection run."""

    resolver: settings_core.SettingsResolver[CheckSettings]
    respect_gitignore: bool
    matcher_cache: dict[int, tuple[_PatternMatcher, _PatternMatcher]] = dataclasses.field(default_factory=dict)

    def profile_for_path(self, path: str | None = None) -> settings_core.SettingsProfile[CheckSettings]:
        """Return the settings profile for a path."""
        return self.resolver.profile_for_path(path)

    def matchers_for_profile(self, profile: settings_core.SettingsProfile[CheckSettings]) -> tuple[_PatternMatcher, _PatternMatcher]:
        """Return include and exclude matchers for a settings profile."""
        profile_id = id(profile)
        cached_matchers = self.matcher_cache.get(profile_id)
        if cached_matchers is not None:
            return cached_matchers

        validate_include_patterns(profile.settings.include_patterns)
        validate_exclude_patterns(profile.settings.exclude_patterns)
        matchers = (
            _PatternMatcher.compile(
                profile,
                ("include", "extend_include"),
                match_parent_segments_for_bare=False,
            ),
            _PatternMatcher.compile(
                profile,
                ("exclude", "extend_exclude"),
                match_parent_segments_for_bare=True,
                match_descendants_for_slash=True,
            ),
        )
        self.matcher_cache[profile_id] = matchers
        return matchers


_CollectedPath = _Candidate | FileDecision


def select_files(paths: list[str], resolver: settings_core.SettingsResolver[CheckSettings]) -> SelectionResult:
    """Select files from CLI paths using resolved formatter settings.

    Direct file paths are accepted without include or gitignore filtering. When `force_exclude` is enabled, direct file
    paths are rejected by matching exclude patterns. Directory paths are walked recursively with excluded directories
    pruned before file candidates are evaluated.

    Args:
        paths (list[str]): CLI path arguments naming files or directories to consider.
        resolver (settings_core.SettingsResolver[CheckSettings]): Path-aware settings resolver controlling include,
            exclude, force-exclude, and gitignore behavior.

    Returns:
        SelectionResult: Accepted paths plus file-selection decisions for accepted and rejected paths.
    """
    context = _selection_context(resolver)
    evaluated = tuple(
        (
            collected
            if isinstance(collected, FileDecision)
            else _evaluate_candidate(
                collected,
                context,
            )
        )
        for collected in _collect_candidates(paths, context)
    )

    return _selection_result_with_gitignore(evaluated)


def select_virtual_file(path: str, resolver: settings_core.SettingsResolver[CheckSettings]) -> SelectionResult:
    """Select one explicit file path without checking whether it exists on disk.

    Args:
        path (str): Virtual or display path to evaluate as an explicit input file.
        resolver (settings_core.SettingsResolver[CheckSettings]): Path-aware settings resolver controlling include,
            exclude, force-exclude, and gitignore behavior.

    Returns:
        SelectionResult: Selection result containing the accepted virtual path or the rejection decision.
    """
    context = _selection_context(resolver)
    profile = context.profile_for_path(None if path == STDIN_VIRTUAL_FILE else path)
    if path == STDIN_VIRTUAL_FILE:
        return _selection_result(
            (
                FileDecision(
                    path=STDIN_VIRTUAL_FILE,
                    accepted=True,
                    reason=DecisionReason.INCLUDED,
                    explicit=True,
                    profile=profile,
                    respect_gitignore=False,
                ),
            )
        )

    evaluated = (
        _evaluate_candidate(
            _Candidate(path=path, explicit=True, profile=profile, respect_gitignore=False),
            context,
        ),
    )

    return _selection_result_with_gitignore(evaluated)


def _selection_context(resolver: settings_core.SettingsResolver[CheckSettings]) -> _SelectionContext:
    """Return a selection context from a path-aware settings resolver."""
    return _SelectionContext(resolver, respect_gitignore=resolver.profile_for_path(os.getcwd()).settings.respect_gitignore)


def _selection_result_with_gitignore(evaluated: tuple[FileDecision, ...]) -> SelectionResult:
    """Build the final selection result, applying gitignore filtering when enabled."""
    gitignored_paths = _collect_gitignored_absolute_paths(_accepted_paths_by_git_root(evaluated))
    if not gitignored_paths:
        return _selection_result(evaluated)

    decisions = tuple(_apply_gitignore_decision(decision, gitignored_paths) for decision in evaluated)
    return _selection_result(decisions)


def _collect_candidates(paths: list[str], context: _SelectionContext) -> tuple[_CollectedPath, ...]:
    """Collect explicit files and recursively discovered files, pruning excluded directories."""
    candidates: list[_CollectedPath] = []
    for path in paths:
        if os.path.isdir(path):
            profile = context.profile_for_path(path)
            _, exclude_matcher = context.matchers_for_profile(profile)
            if exclude_matcher.matches(path) or _force_excluded_explicit_directory(path, profile):
                candidates.append(_excluded_directory_decision(path, explicit=True, profile=profile))
                continue
            candidates.extend(_walk_directory(path, context, respect_gitignore=context.respect_gitignore))
        else:
            candidates.append(_Candidate(path=path, explicit=True, profile=context.profile_for_path(path), respect_gitignore=False))
    return tuple(candidates)


def _walk_directory(path: str, context: _SelectionContext, *, respect_gitignore: bool) -> tuple[_CollectedPath, ...]:
    """Recursively collect candidates below one accepted directory."""
    candidates: list[_CollectedPath] = []
    for root, dirs, files in os.walk(path):
        profile = context.profile_for_path(root)
        _, exclude_matcher = context.matchers_for_profile(profile)

        kept_dirs = []
        for name in sorted(dirs):
            directory = os.path.join(root, name)
            if exclude_matcher.matches(directory):
                candidates.append(_excluded_directory_decision(directory, explicit=False, profile=profile))
            else:
                kept_dirs.append(name)
        dirs[:] = kept_dirs

        files.sort()
        for name in files:
            if name == ".git":
                continue
            file_path = os.path.join(root, name)
            candidates.append(_Candidate(path=file_path, explicit=False, profile=context.profile_for_path(file_path), respect_gitignore=respect_gitignore))
    return tuple(candidates)


def validate_include_patterns(patterns: tuple[str, ...]) -> None:
    """Validate glob patterns used for file inclusion.

    Args:
        patterns (tuple[str, ...]): Include glob patterns to validate.

    Raises:
        FileSelectionError: If any include pattern is empty.
    """
    for pattern in patterns:
        if not pattern:
            raise FileSelectionError("Include patterns must not be empty")


def validate_exclude_patterns(patterns: tuple[str, ...]) -> None:
    """Validate glob patterns used for file exclusion.

    Args:
        patterns (tuple[str, ...]): Exclude glob patterns to validate.

    Raises:
        FileSelectionError: If any exclude pattern is empty.
    """
    for pattern in patterns:
        if not pattern:
            raise FileSelectionError("Exclude patterns must not be empty")


def _force_excluded_explicit_directory(path: str, profile: settings_core.SettingsProfile[CheckSettings]) -> bool:
    """Return whether force-exclude rejects an explicit directory path."""
    if not profile.settings.force_exclude:
        return False
    matcher = GlobPatternSet.compile(
        profile.settings.exclude_patterns,
        match_parent_segments_for_bare=True,
        match_descendants_for_slash=True,
    )
    return matcher.matches(_base_relative_posix_path(path, os.getcwd()))


def _excluded_directory_decision(path: str, *, explicit: bool, profile: settings_core.SettingsProfile[CheckSettings]) -> FileDecision:
    """Return a rejection decision for an excluded directory path."""
    return FileDecision(
        path=path,
        accepted=False,
        reason=DecisionReason.EXCLUDED,
        explicit=explicit,
        profile=profile,
        respect_gitignore=True,
    )


def _evaluate_candidate(candidate: _Candidate, context: _SelectionContext) -> FileDecision:
    """Evaluate one candidate path against explicit-path, include, and exclude rules."""
    include_matcher, exclude_matcher = context.matchers_for_profile(candidate.profile)

    if candidate.explicit:
        if candidate.profile.settings.force_exclude and exclude_matcher.matches(candidate.path):
            return FileDecision(
                path=candidate.path,
                accepted=False,
                reason=DecisionReason.EXCLUDED,
                explicit=True,
                profile=candidate.profile,
                respect_gitignore=candidate.respect_gitignore,
            )
        return FileDecision(
            path=candidate.path,
            accepted=True,
            reason=DecisionReason.EXPLICIT_INCLUDED,
            explicit=True,
            profile=candidate.profile,
            respect_gitignore=candidate.respect_gitignore,
        )

    if not include_matcher.matches(candidate.path):
        return FileDecision(
            path=candidate.path,
            accepted=False,
            reason=DecisionReason.NOT_INCLUDED,
            explicit=False,
            profile=candidate.profile,
            respect_gitignore=candidate.respect_gitignore,
        )
    if exclude_matcher.matches(candidate.path):
        return FileDecision(
            path=candidate.path,
            accepted=False,
            reason=DecisionReason.EXCLUDED,
            explicit=False,
            profile=candidate.profile,
            respect_gitignore=candidate.respect_gitignore,
        )
    return FileDecision(
        path=candidate.path,
        accepted=True,
        reason=DecisionReason.INCLUDED,
        explicit=False,
        profile=candidate.profile,
        respect_gitignore=candidate.respect_gitignore,
    )


def _apply_gitignore_decision(decision: FileDecision, gitignored_paths: set[str]) -> FileDecision:
    """Reject accepted discovered paths that git reported as ignored."""
    if not decision.accepted:
        return decision
    if decision.explicit:
        return decision
    if os.path.realpath(decision.path) not in gitignored_paths:
        return decision
    return FileDecision(
        path=decision.path,
        accepted=False,
        reason=DecisionReason.GITIGNORED,
        explicit=decision.explicit,
        profile=decision.profile,
        respect_gitignore=decision.respect_gitignore,
    )


def _selection_result(decisions: tuple[FileDecision, ...]) -> SelectionResult:
    """Build a selection result from the ordered file-decision stream."""
    decisions = _deduplicated_decisions(decisions)
    selected_files = tuple(SelectedFile(path=decision.path, profile=decision.profile) for decision in decisions if decision.accepted and decision.profile is not None)
    return SelectionResult(
        accepted_paths=tuple(selected_file.path for selected_file in selected_files),
        decisions=decisions,
        selected_files=selected_files,
    )


def _deduplicated_decisions(decisions: tuple[FileDecision, ...]) -> tuple[FileDecision, ...]:
    """Return decisions with accepted file duplicates marked as rejected."""
    result: list[FileDecision] = []
    accepted_by_identity: dict[str, int] = {}

    for decision in decisions:
        display_decision = _with_display_path(decision)
        if not display_decision.accepted:
            result.append(display_decision)
            continue

        identity_key = path_identity_key(decision.path)
        if identity_key is None:
            result.append(display_decision)
            continue

        accepted_index = accepted_by_identity.get(identity_key)
        if accepted_index is None:
            accepted_by_identity[identity_key] = len(result)
            result.append(display_decision)
            continue

        accepted_decision = result[accepted_index]
        if _display_path_score(display_decision.path) < _display_path_score(accepted_decision.path):
            result[accepted_index] = _duplicate_decision(accepted_decision)
            accepted_by_identity[identity_key] = len(result)
            result.append(display_decision)
        else:
            result.append(_duplicate_decision(display_decision))

    return tuple(result)


def _with_display_path(decision: FileDecision) -> FileDecision:
    """Return a decision with its path normalized for display."""
    return dataclasses.replace(decision, path=_display_path(decision.path))


def _duplicate_decision(decision: FileDecision) -> FileDecision:
    """Return a duplicate-path rejection decision."""
    return FileDecision(
        path=decision.path,
        accepted=False,
        reason=DecisionReason.DUPLICATE,
        explicit=decision.explicit,
        profile=decision.profile,
        respect_gitignore=decision.respect_gitignore,
    )


def path_identity_key(path: str) -> str | None:
    """Return a physical-path key for deduplicating existing files.

    Args:
        path (str): File path to resolve.

    Returns:
        str | None: Normalized real path key, or None when the path does not exist.
    """
    if not os.path.exists(path):
        return None
    return os.path.normcase(os.path.realpath(path))


def _display_path(path: str) -> str:
    """Return the preferred path spelling for user-facing output."""
    if path == STDIN_VIRTUAL_FILE:
        return path

    normalized_path = os.path.normpath(path)
    if os.path.exists(normalized_path):
        return os.path.abspath(normalized_path)
    return normalized_path


def _display_path_score(path: str) -> tuple[int, int, int, str]:
    """Return a sortable score where lower means a clearer display path."""
    normalized_path = os.path.normpath(path)
    segments = tuple(segment for segment in normalized_path.split(os.sep) if segment)
    return (
        segments.count(".."),
        len(segments),
        len(normalized_path),
        normalized_path,
    )


def _base_relative_posix_path(path: str, base_path: str) -> str:
    """Return a base-relative path using POSIX separators."""
    return os.path.relpath(os.path.abspath(path), os.path.abspath(base_path)).replace(os.sep, "/")


def _accepted_paths_by_git_root(decisions: tuple[FileDecision, ...]) -> dict[str, list[str]]:
    """Group accepted, gitignore-checkable paths by containing git root."""
    grouped_paths: dict[str, list[str]] = defaultdict(list)
    root_cache: dict[str, str | None] = {}

    for decision in decisions:
        if not decision.accepted:
            continue
        if decision.explicit:
            continue
        if not decision.respect_gitignore:
            continue

        absolute_path = os.path.realpath(decision.path)
        git_root = misc.find_git_root_for_path(absolute_path, root_cache)
        if git_root is None:
            continue

        relative_path = os.path.relpath(absolute_path, git_root).replace(os.sep, "/")
        grouped_paths[git_root].append(relative_path)

    return dict(grouped_paths)


def _collect_gitignored_absolute_paths(paths_by_git_root: Mapping[str, list[str]]) -> set[str]:
    """Return absolute paths reported as ignored by git for each repository root."""
    gitignored_paths: set[str] = set()

    for git_root, relative_paths in paths_by_git_root.items():
        ignored_relative_paths, error = _query_git_ignored_paths(git_root, relative_paths)
        if error is not None:
            raise FileSelectionError(f"{git_root}: Unable to apply gitignore filtering: {error}")
        gitignored_paths.update(os.path.realpath(os.path.join(git_root, path)) for path in ignored_relative_paths)

    return gitignored_paths


def _query_git_ignored_paths(git_root: str, relative_paths: list[str]) -> tuple[set[str], str | None]:
    """Ask git which repository-relative paths are ignored."""
    unique_relative_paths = list(dict.fromkeys(relative_paths))
    if not unique_relative_paths:
        return set(), None

    stdin_bytes = ("\0".join(unique_relative_paths) + "\0").encode(
        "utf-8",
        errors="surrogateescape",
    )
    try:
        process = subprocess.run(
            ["git", "-C", git_root, "check-ignore", "--stdin", "--no-index", "-z"],
            input=stdin_bytes,
            capture_output=True,
            check=False,
        )
    except OSError as error:
        return set(), str(error)

    if process.returncode not in {0, 1}:
        error_message = process.stderr.decode("utf-8", errors="replace").strip()
        return set(), error_message or f"git check-ignore exited with status {process.returncode}"

    stdout = process.stdout.decode("utf-8", errors="surrogateescape")
    return {path for path in stdout.split("\0") if path}, None
