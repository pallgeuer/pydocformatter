"""Tests for policies that require a complete repository checkout."""

# Standard library imports
import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[2]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "pre_commit_checks.yml"


def test_ci_runs_the_test_suite_once_with_configured_coverage() -> None:
    """CI must skip the plain pytest hook and defer policy details to coverage configuration."""
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "SKIP: pytest" in workflow
    assert "run: uv run --no-sync pytest -q --cov" in workflow
    assert "--cov=pydocformatter" not in workflow
    assert "--cov-branch" not in workflow
    assert "--cov-report" not in workflow
    assert "--cov-fail-under" not in workflow


def test_release_runbook_reuses_changelog_notes_for_github() -> None:
    """Release publication must use and verify the prepared changelog notes."""
    release = (ROOT / "RELEASE.md").read_text(encoding="utf-8")

    assert '--notes-file "$RELEASE_NOTES"' in release
    assert 'test "$(gh release view "$TAG" --json body --jq .body)" = "$(cat "$RELEASE_NOTES")"' in release
