"""Tests for published project compatibility and contribution policies."""

# Standard library imports
import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_versioning_policy_exposes_stable_public_sections() -> None:
    """The policy must retain its linked public sections and references."""
    policy = (ROOT / "docs_site" / "versioning.md").read_text(encoding="utf-8")

    headings = {line.removeprefix("## ") for line in policy.splitlines() if line.startswith("## ")}
    assert headings == {"Public compatibility surface", "Release compatibility", "Runtime support", "Rule lifecycle", "Fix guarantees"}
    assert "[Installation](installation.md)" in policy
    assert "[Changelog](project/changelog.md)" in policy


def test_rule_contribution_policy_links_its_normative_references() -> None:
    """Rule guidance must link its normative implementation and compatibility references."""
    guidance = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")

    assert "### Proposing rules and fixes" in guidance
    assert "docs/devel/rule_implementation_spec.md" in guidance
    assert "https://pallgeuer.github.io/pydocformatter/versioning/" in guidance
