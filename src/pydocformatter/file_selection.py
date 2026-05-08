import dataclasses
import os
import subprocess
from collections import defaultdict
from enum import Enum

from pydocformatter.config import FormatterSettings
from pydocformatter.glob_matcher import GlobPatternSet


class DecisionReason(str, Enum):
    """Stable reason codes for file-selection decisions.

    Attributes:
        INCLUDED (DecisionReason): The path matched include rules and did not match
            exclude rules.
        EXPLICIT_INCLUDED (DecisionReason): The path was passed explicitly while
            `force_exclude` was disabled.
        NOT_INCLUDED (DecisionReason): The path did not match configured include
            patterns.
        EXCLUDED (DecisionReason): The path matched configured exclude patterns.
        GITIGNORED (DecisionReason): The path was rejected because git reported it as
            ignored.
    """

    INCLUDED = "included"
    EXPLICIT_INCLUDED = "explicit-included"
    NOT_INCLUDED = "not-included"
    EXCLUDED = "excluded"
    GITIGNORED = "gitignored"


_REASON_MESSAGES = {
    DecisionReason.INCLUDED: "included",
    DecisionReason.EXPLICIT_INCLUDED: "included explicitly (force-exclude disabled)",
    DecisionReason.NOT_INCLUDED: "does not match include patterns",
    DecisionReason.EXCLUDED: "matches exclude patterns",
    DecisionReason.GITIGNORED: "matches .gitignore",
}


@dataclasses.dataclass(frozen=True)
class FileDecision:
    """Result of evaluating whether one path should be formatted.

    Attributes:
        path (str): Original path that was evaluated.
        accepted (bool): Whether the path should be formatted.
        reason (DecisionReason): Stable machine-readable decision reason.
        explicit (bool): Whether the path came directly from a CLI argument rather than
            directory traversal.
    """

    path: str
    accepted: bool
    reason: DecisionReason
    explicit: bool

    @property
    def message(self) -> str:
        """Return the human-readable reason message for verbose output.

        Returns:
            str: Message corresponding to the decision reason.
        """
        return _REASON_MESSAGES[self.reason]


@dataclasses.dataclass(frozen=True)
class SelectionResult:
    """Accepted files and all file-selection decisions.

    Attributes:
        accepted_files (tuple[str, ...]): Ordered paths that should be formatted.
        decisions (tuple[FileDecision, ...]): Ordered decisions for every considered
            path or pruned directory.
    """

    accepted_files: tuple[str, ...]
    decisions: tuple[FileDecision, ...]


@dataclasses.dataclass(frozen=True)
class _Candidate:
    """A discovered path that still needs include, exclude, and gitignore checks."""

    path: str
    explicit: bool


_CollectedPath = _Candidate | FileDecision


def select_files(paths: list[str], settings: FormatterSettings) -> SelectionResult:
    """Select files from CLI paths using resolved formatter settings.

    Direct file paths are accepted without include, exclude, or gitignore filtering
    unless `settings.force_exclude` is enabled. Directory paths are walked recursively
    with excluded directories pruned before file candidates are evaluated.

    Args:
        paths (list[str]): CLI path arguments naming files or directories to consider.
        settings (FormatterSettings): Resolved formatter settings controlling include,
            exclude, force-exclude, and gitignore behavior.

    Returns:
        SelectionResult: Accepted files plus verbose decisions for accepted and rejected
            paths.
    """
    include_matcher = GlobPatternSet.compile(
        settings.include_patterns,
        include_patterns=True,
        match_parent_segments_for_bare=False,
    )
    exclude_matcher = GlobPatternSet.compile(
        settings.exclude_patterns,
        include_patterns=False,
        match_parent_segments_for_bare=True,
        match_descendants_for_slash=True,
    )
    root_cache: dict[str, str | None] = {}

    evaluated = tuple(
        (
            collected
            if isinstance(collected, FileDecision)
            else _evaluate_candidate(
                collected,
                settings,
                include_matcher,
                exclude_matcher,
                root_cache,
            )
        )
        for collected in _collect_candidates(paths, exclude_matcher, root_cache)
    )

    if not settings.respect_gitignore:
        return _selection_result(evaluated)

    gitignored_paths = _collect_gitignored_absolute_paths(
        _accepted_paths_by_git_root(evaluated, settings.force_exclude, root_cache)
    )
    if not gitignored_paths:
        return _selection_result(evaluated)

    decisions = tuple(
        _apply_gitignore_decision(decision, settings.force_exclude, gitignored_paths)
        for decision in evaluated
    )
    return _selection_result(decisions)


def _collect_candidates(
    paths: list[str],
    exclude_matcher: GlobPatternSet,
    root_cache: dict[str, str | None],
) -> tuple[_CollectedPath, ...]:
    """Collect explicit files and recursively discovered files, pruning excluded
    directories.
    """
    candidates: list[_CollectedPath] = []
    for path in paths:
        if os.path.isdir(path):
            if exclude_matcher.matches(_normalized_posix_path(path, root_cache)):
                candidates.append(_excluded_directory_decision(path, explicit=True))
                continue
            for root, dirs, files in os.walk(path):
                kept_dirs = []
                for name in sorted(dirs):
                    directory = os.path.join(root, name)
                    if exclude_matcher.matches(
                        _normalized_posix_path(directory, root_cache)
                    ):
                        candidates.append(
                            _excluded_directory_decision(directory, explicit=False)
                        )
                    else:
                        kept_dirs.append(name)
                dirs[:] = kept_dirs
                files.sort()
                candidates.extend(
                    _Candidate(path=os.path.join(root, name), explicit=False)
                    for name in files
                    if name != ".git"
                )
        else:
            candidates.append(_Candidate(path=path, explicit=True))
    return tuple(candidates)


def _excluded_directory_decision(path: str, explicit: bool) -> FileDecision:
    """Return a rejection decision for an excluded directory path."""
    return FileDecision(
        path=path,
        accepted=False,
        reason=DecisionReason.EXCLUDED,
        explicit=explicit,
    )


def _evaluate_candidate(
    candidate: _Candidate,
    settings: FormatterSettings,
    include_matcher: GlobPatternSet,
    exclude_matcher: GlobPatternSet,
    root_cache: dict[str, str | None],
) -> FileDecision:
    """Evaluate one candidate path against explicit-path, include, and exclude rules."""
    if candidate.explicit and not settings.force_exclude:
        return FileDecision(
            path=candidate.path,
            accepted=True,
            reason=DecisionReason.EXPLICIT_INCLUDED,
            explicit=True,
        )

    normalized_path = _normalized_posix_path(candidate.path, root_cache)
    if not include_matcher.matches(normalized_path):
        return FileDecision(
            path=candidate.path,
            accepted=False,
            reason=DecisionReason.NOT_INCLUDED,
            explicit=candidate.explicit,
        )
    if exclude_matcher.matches(normalized_path):
        return FileDecision(
            path=candidate.path,
            accepted=False,
            reason=DecisionReason.EXCLUDED,
            explicit=candidate.explicit,
        )
    return FileDecision(
        path=candidate.path,
        accepted=True,
        reason=DecisionReason.INCLUDED,
        explicit=candidate.explicit,
    )


def _apply_gitignore_decision(
    decision: FileDecision,
    force_exclude: bool,
    gitignored_paths: set[str],
) -> FileDecision:
    """Reject accepted paths that git reported as ignored, honoring explicit path rules."""
    if not decision.accepted:
        return decision
    if decision.explicit and not force_exclude:
        return decision
    if os.path.abspath(decision.path) not in gitignored_paths:
        return decision
    return FileDecision(
        path=decision.path,
        accepted=False,
        reason=DecisionReason.GITIGNORED,
        explicit=decision.explicit,
    )


def _selection_result(decisions: tuple[FileDecision, ...]) -> SelectionResult:
    """Build a selection result from the ordered file-decision stream."""
    return SelectionResult(
        accepted_files=tuple(
            decision.path for decision in decisions if decision.accepted
        ),
        decisions=decisions,
    )


def _normalized_posix_path(path: str, root_cache: dict[str, str | None]) -> str:
    """Return a git-root-relative or cwd-relative path using POSIX separators."""
    absolute_path = os.path.abspath(path)
    git_root = _find_git_root_for_path(absolute_path, root_cache)
    base_path = git_root if git_root is not None else os.getcwd()
    return os.path.relpath(absolute_path, base_path).replace(os.sep, "/")


def _accepted_paths_by_git_root(
    decisions: tuple[FileDecision, ...],
    force_exclude: bool,
    root_cache: dict[str, str | None],
) -> dict[str, list[str]]:
    """Group accepted, gitignore-checkable paths by containing git root."""
    grouped_paths: dict[str, list[str]] = defaultdict(list)

    for decision in decisions:
        if not decision.accepted:
            continue
        if decision.explicit and not force_exclude:
            continue

        absolute_path = os.path.abspath(decision.path)
        git_root = _find_git_root_for_path(absolute_path, root_cache)
        if git_root is None:
            continue

        relative_path = os.path.relpath(absolute_path, git_root).replace(os.sep, "/")
        grouped_paths[git_root].append(relative_path)

    return dict(grouped_paths)


def _find_git_root_for_path(
    absolute_path: str,
    root_cache: dict[str, str | None],
) -> str | None:
    """Find and cache the nearest containing git root for an absolute path."""
    start_dir = (
        absolute_path
        if os.path.isdir(absolute_path)
        else os.path.dirname(absolute_path)
    )
    if start_dir in root_cache:
        return root_cache[start_dir]

    current_dir = os.path.abspath(start_dir)
    while True:
        git_marker = os.path.join(current_dir, ".git")
        if _is_valid_git_marker(git_marker):
            root_cache[start_dir] = current_dir
            return current_dir

        parent_dir = os.path.dirname(current_dir)
        if parent_dir == current_dir:
            root_cache[start_dir] = None
            return None
        current_dir = parent_dir


def _is_valid_git_marker(path: str) -> bool:
    """Return whether a .git path looks like a worktree marker."""
    if os.path.isfile(path):
        return True
    if not os.path.isdir(path):
        return False
    return os.path.exists(os.path.join(path, "HEAD"))


def _collect_gitignored_absolute_paths(
    paths_by_git_root: dict[str, list[str]],
) -> set[str]:
    """Return absolute paths reported as ignored by git for each repository root."""
    gitignored_paths: set[str] = set()

    for git_root, relative_paths in paths_by_git_root.items():
        ignored_relative_paths, error = _query_git_ignored_paths(
            git_root, relative_paths
        )
        if error is not None:
            print(
                f"{git_root} WARNING: unable to apply gitignore filtering ({error}); "
                f"continuing without gitignore filtering for this repository root"
            )
            continue
        gitignored_paths.update(
            os.path.abspath(os.path.join(git_root, path))
            for path in ignored_relative_paths
        )

    return gitignored_paths


def _query_git_ignored_paths(
    git_root: str,
    relative_paths: list[str],
) -> tuple[set[str], str | None]:
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
        return (
            set(),
            error_message
            or f"git check-ignore exited with status {process.returncode}",
        )

    stdout = process.stdout.decode("utf-8", errors="surrogateescape")
    return {path for path in stdout.split("\0") if path}, None
