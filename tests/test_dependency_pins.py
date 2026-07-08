"""Tests for locked development dependency pins."""

# Standard library imports
import re
import pathlib
import tomllib
from typing import Any

# Third-party imports
import pytest


ROOT = pathlib.Path(__file__).resolve().parents[1]
PYPROJECT_PATH = ROOT / "pyproject.toml"
GROUPS_TO_CHECK = ("test", "dev")
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*(?:\[[A-Za-z0-9_,.-]+\])?$")
VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.!+_-]*$")


def normalize_name(name: str) -> str:
    """Return a canonical package name for dependency comparisons."""
    return re.sub(r"[-_.]+", "-", name).lower()


def parse_exact_pin(requirement: str) -> tuple[str, str] | None:
    """Parse a dependency requirement if it is pinned with an exact concrete version."""
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
    if not VERSION_RE.match(version_part):
        return None
    package_name = normalize_name(name_part.split("[", 1)[0])
    return package_name, version_part


def is_include_group(entry: dict[Any, Any]) -> bool:
    """Return whether a dependency-group entry includes another dependency group."""
    return set(entry) == {"include-group"} and isinstance(entry["include-group"], str)


def dependency_pin_errors(pyproject: dict[str, Any]) -> list[str]:
    """Return dependency-group pin validation errors."""
    errors: list[str] = []
    dependency_groups = pyproject.get("dependency-groups")
    if not isinstance(dependency_groups, dict):
        return ["Unable to find [dependency-groups] in pyproject.toml"]

    for group_name in GROUPS_TO_CHECK:
        group = dependency_groups.get(group_name)
        if not isinstance(group, list):
            errors.append(f"dependency-groups.{group_name} must be a list")
            continue

        for entry in group:
            if isinstance(entry, dict):
                if is_include_group(entry):
                    continue
                errors.append(f"dependency-groups.{group_name} contains unsupported table entry: {entry!r}")
                continue
            if not isinstance(entry, str):
                errors.append(f"dependency-groups.{group_name} contains unsupported entry type: {entry!r}")
                continue

            if parse_exact_pin(entry) is None:
                errors.append(f"dependency-groups.{group_name} must use exact pins (name==version): {entry!r}")

    return errors


@pytest.mark.parametrize(
    ("requirement", "expected"),
    [
        ("pytest==9.1.1", ("pytest", "9.1.1")),
        ("pytest_cov==7.1.0", ("pytest-cov", "7.1.0")),
        ("pkg[extra,other]==1.2.3", ("pkg", "1.2.3")),
        ('pkg==1.2.3; python_version >= "3.11"', ("pkg", "1.2.3")),
        ("pkg == 1.0.0rc1", ("pkg", "1.0.0rc1")),
    ],
)
def test_parse_exact_pin_accepts_concrete_exact_pins(requirement: str, expected: tuple[str, str]) -> None:
    """Check that concrete equality pins are parsed."""
    assert parse_exact_pin(requirement) == expected


@pytest.mark.parametrize("requirement", ["pkg>=1.2.3", "pkg<=1.2.3", "pkg~=1.2.3", "pkg!=1.2.3", "pkg===1.2.3", "pkg==1.2.*", "pkg==1.2.3,<=2", "pkg @ https://example.com/pkg.whl", "pkg", "pkg=="])
def test_parse_exact_pin_rejects_flexible_or_non_dependency_pins(requirement: str) -> None:
    """Check that flexible and non-standard dependency spellings are rejected."""
    assert parse_exact_pin(requirement) is None


def test_dependency_groups_use_exact_pins() -> None:
    """Check that test and dev dependency groups use exact concrete pins."""
    with PYPROJECT_PATH.open("rb") as f:
        pyproject = tomllib.load(f)

    assert dependency_pin_errors(pyproject) == []


def test_dependency_pin_errors_accepts_pinned_test_and_dev_groups() -> None:
    """Check that pinned test and dev dependencies pass."""
    pyproject: dict[str, Any] = {"dependency-groups": {"test": ["pytest==9.1.1"], "dev": [{"include-group": "test"}, "ruff==0.15.20"]}}

    assert dependency_pin_errors(pyproject) == []


def test_dependency_pin_errors_rejects_flexible_dependency_pins() -> None:
    """Check that flexible dependency specifiers fail."""
    pyproject: dict[str, Any] = {"dependency-groups": {"test": ["pytest>=9.1.1"], "dev": [{"include-group": "test"}, "ruff==0.15.20"]}}

    assert dependency_pin_errors(pyproject) == ["dependency-groups.test must use exact pins (name==version): 'pytest>=9.1.1'"]


def test_dependency_pin_errors_rejects_unsupported_table_entries() -> None:
    """Check that only include-group table entries are skipped."""
    pyproject: dict[str, Any] = {"dependency-groups": {"test": ["pytest==9.1.1"], "dev": [{"include-group": "test", "extra": "bad"}, "ruff==0.15.20"]}}

    assert dependency_pin_errors(pyproject) == ["dependency-groups.dev contains unsupported table entry: {'include-group': 'test', 'extra': 'bad'}"]
