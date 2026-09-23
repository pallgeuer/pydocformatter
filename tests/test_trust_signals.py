"""Project release and coverage trust-signal tests."""

# Future imports
from __future__ import annotations

# Standard library imports
import re
import pathlib
import tomllib


ROOT = pathlib.Path(__file__).resolve().parents[1]
CHANGELOG_PATH = ROOT / "CHANGELOG.md"


def test_coverage_configuration_is_branch_aware_and_enforces_the_advertised_floor() -> None:
    """Coverage configuration and the README badge must describe one policy."""
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    coverage = pyproject["tool"]["coverage"]

    assert coverage["run"] == {"branch": True, "source": ["pydocformatter"]}
    assert coverage["report"] == {"fail_under": 95, "precision": 2, "show_missing": True, "skip_covered": True}
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "actions/workflows/pre_commit_checks.yml/badge.svg" in readme
    assert "[![Coverage gate: >=95%](https://img.shields.io/badge/coverage%20gate-%3E%3D95%25-brightgreen.svg)]" in readme


def test_every_released_changelog_section_leads_with_one_highlight() -> None:
    """Released versions must summarize their user-facing outcome before categories."""
    changelog = CHANGELOG_PATH.read_text(encoding="utf-8")
    sections = re.findall(r"^## v(?P<version>[^\n]+)\n(?P<body>.*?)(?=^---$|\Z)", changelog, flags=re.DOTALL | re.MULTILINE)

    assert sections
    for version, body in sections:
        highlights = re.findall(r"^\*\*Highlights:\*\* .+$", body, flags=re.MULTILINE)
        assert len(highlights) == 1, version
        released_position = body.index("Released ")
        highlights_position = body.index("**Highlights:**")
        category_position = body.index("### ")
        assert released_position < highlights_position < category_position, version
        if "**Compatibility warning:**" in body:
            assert released_position < body.index("**Compatibility warning:**") < highlights_position, version
