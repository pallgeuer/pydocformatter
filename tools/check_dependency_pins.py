#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT_PATH = ROOT / "pyproject.toml"
PRECOMMIT_PATH = ROOT / ".pre-commit-config.yaml"

GROUPS_TO_CHECK = ("test", "dev")
TOOL_PACKAGES = ("black", "isort", "mypy")
REPO_TO_PACKAGE = {
    "https://github.com/psf/black": "black",
    "https://github.com/PyCQA/isort": "isort",
    "https://github.com/pre-commit/mirrors-mypy": "mypy",
}

NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*(?:\[[A-Za-z0-9_,.-]+\])?$")
REPO_RE = re.compile(r"^\s*-\s*repo:\s*(\S+)\s*$")
REV_RE = re.compile(r"^\s*rev:\s*(\S+)\s*$")


def normalize_name(name: str) -> str:
    """Return a canonical package name for dependency comparisons.

    Args:
        name (str): Raw dependency package name.

    Returns:
        str: Lowercase package name with runs of `.`, `_`, and `-` collapsed to `-`.
    """
    return re.sub(r"[-_.]+", "-", name).lower()


def normalize_version(version: str) -> str:
    """Return a normalized version string for cross-file comparisons.

    Args:
        version (str): Raw version or pre-commit revision string.

    Returns:
        str: Version with surrounding quotes stripped and a leading `v` removed when followed by a digit.
    """
    version = version.strip().strip("'\"")
    if len(version) > 1 and version.startswith("v") and version[1].isdigit():
        return version[1:]
    return version


def parse_exact_pin(requirement: str) -> tuple[str, str] | None:
    """Parse a dependency requirement if it is pinned with an exact == version.

    Args:
        requirement (str): Dependency requirement string from `pyproject.toml`.

    Returns:
        tuple[str, str] | None: Normalized package name and pinned version, or `None` when the requirement is not an
            exact, concrete pin.
    """
    req = requirement.split(";", 1)[0].strip()
    if "===" in req or req.count("==") != 1:
        return None
    name_part, version_part = (part.strip() for part in req.split("==", 1))
    if not name_part or not version_part:
        return None
    if version_part.endswith(".*"):
        return None
    if not NAME_RE.match(name_part):
        return None
    package_name = normalize_name(name_part.split("[", 1)[0])
    return package_name, version_part


def load_pyproject() -> dict[str, Any]:
    """Load the repository pyproject.toml file.

    Returns:
        dict[str, Any]: Parsed TOML data from `pyproject.toml`.

    Raises:
        `OSError`: If `pyproject.toml` cannot be read.
        `tomllib.TOMLDecodeError`: If `pyproject.toml` contains invalid TOML.
    """
    with PYPROJECT_PATH.open("rb") as f:
        return tomllib.load(f)


def load_precommit_repo_revs() -> dict[str, str]:
    """Return first configured revision for each pre-commit repository.

    Returns:
        dict[str, str]: Mapping of pre-commit repository URLs to their configured `rev` values.

    Raises:
        `OSError`: If `.pre-commit-config.yaml` cannot be read.
    """
    revs: dict[str, str] = {}
    current_repo: str | None = None

    with PRECOMMIT_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            repo_match = REPO_RE.match(line)
            if repo_match:
                current_repo = repo_match.group(1).strip("'\"")
                continue
            if current_repo is None:
                continue
            rev_match = REV_RE.match(line)
            if rev_match and current_repo not in revs:
                revs[current_repo] = rev_match.group(1).strip("'\"")

    return revs


def main() -> int:
    """Check pinned dev dependency versions against pre-commit hook revisions.

    Returns:
        int: Zero when dependency pins match, otherwise one after printing validation errors.
    """
    errors: list[str] = []
    pyproject = load_pyproject()
    dependency_groups = pyproject.get("dependency-groups")
    if not isinstance(dependency_groups, dict):
        print("Unable to find [dependency-groups] in pyproject.toml", file=sys.stderr)
        return 1

    dev_versions: dict[str, str] = {}

    for group_name in GROUPS_TO_CHECK:
        group = dependency_groups.get(group_name)
        if not isinstance(group, list):
            errors.append(f"dependency-groups.{group_name} must be a list")
            continue

        for entry in group:
            if isinstance(entry, dict):
                # Allow include-group entries such as {include-group = "test"}.
                continue
            if not isinstance(entry, str):
                errors.append(f"dependency-groups.{group_name} contains unsupported entry type: {entry!r}")
                continue

            parsed = parse_exact_pin(entry)
            if parsed is None:
                errors.append(f"dependency-groups.{group_name} must use exact pins (name==version): {entry!r}")
                continue

            package_name, package_version = parsed
            if group_name == "dev" and package_name in TOOL_PACKAGES:
                dev_versions[package_name] = package_version

    repo_revs = load_precommit_repo_revs()
    for repo, package_name in REPO_TO_PACKAGE.items():
        rev = repo_revs.get(repo)
        if rev is None:
            errors.append(f".pre-commit-config.yaml is missing repo entry: {repo}")
            continue

        dev_version = dev_versions.get(package_name)
        if dev_version is None:
            errors.append(f"dependency-groups.dev is missing required pinned dependency for {package_name}")
            continue

        if normalize_version(rev) != normalize_version(dev_version):
            errors.append(f"Version mismatch for {package_name}: pyproject dev has {dev_version!r}, pre-commit rev is {rev!r}")

    if errors:
        print("Dependency pin/version consistency check failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("Dependency pin/version consistency check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
