import os
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum

from pydocformatter.config import FormatterSettings
from pydocformatter.glob_matcher import GlobPatternSet


class DecisionReason(str, Enum):
    """Stable reason codes for file-selection decisions."""

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


@dataclass(frozen=True)
class FileDecision:
    """Result of evaluating whether one file path should be formatted."""

    path: str
    accepted: bool
    reason: DecisionReason
    explicit: bool

    @property
    def message(self) -> str:
        """Return a human-readable reason message for verbose output."""
        return _REASON_MESSAGES[self.reason]


@dataclass(frozen=True)
class SelectionResult:
    """Accepted files and all file-selection decisions."""

    accepted_files: tuple[str, ...]
    decisions: tuple[FileDecision, ...]


@dataclass(frozen=True)
class _Candidate:
    path: str
    explicit: bool


def select_files(paths: list[str], settings: FormatterSettings) -> SelectionResult:
    """Select files from CLI paths using resolved formatter settings."""
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
        _evaluate_candidate(
            candidate,
            settings,
            include_matcher,
            exclude_matcher,
            root_cache,
        )
        for candidate in _collect_candidates(paths, exclude_matcher, root_cache)
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
) -> tuple[_Candidate, ...]:
    candidates: list[_Candidate] = []
    for path in paths:
        if os.path.isdir(path):
            if exclude_matcher.matches(_normalized_posix_path(path, root_cache)):
                continue
            for root, dirs, files in os.walk(path):
                dirs[:] = [
                    name
                    for name in sorted(dirs)
                    if not exclude_matcher.matches(
                        _normalized_posix_path(os.path.join(root, name), root_cache)
                    )
                ]
                files.sort()
                candidates.extend(
                    _Candidate(path=os.path.join(root, name), explicit=False)
                    for name in files
                    if name != ".git"
                )
        else:
            candidates.append(_Candidate(path=path, explicit=True))
    return tuple(candidates)


def _evaluate_candidate(
    candidate: _Candidate,
    settings: FormatterSettings,
    include_matcher: GlobPatternSet,
    exclude_matcher: GlobPatternSet,
    root_cache: dict[str, str | None],
) -> FileDecision:
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
    return SelectionResult(
        accepted_files=tuple(
            decision.path for decision in decisions if decision.accepted
        ),
        decisions=decisions,
    )


def _normalized_posix_path(path: str, root_cache: dict[str, str | None]) -> str:
    absolute_path = os.path.abspath(path)
    git_root = _find_git_root_for_path(absolute_path, root_cache)
    base_path = git_root if git_root is not None else os.getcwd()
    return os.path.relpath(absolute_path, base_path).replace(os.sep, "/")


def _accepted_paths_by_git_root(
    decisions: tuple[FileDecision, ...],
    force_exclude: bool,
    root_cache: dict[str, str | None],
) -> dict[str, list[str]]:
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
    if os.path.isfile(path):
        return True
    if not os.path.isdir(path):
        return False
    return os.path.exists(os.path.join(path, "HEAD"))


def _collect_gitignored_absolute_paths(
    paths_by_git_root: dict[str, list[str]],
) -> set[str]:
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
