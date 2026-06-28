import importlib.util
import json
import subprocess
from pathlib import Path
from types import ModuleType

import pytest

DIFF_HELPER_PATH = Path(__file__).resolve().parents[1] / ".agents" / "skills" / "loupe" / "scripts" / "collect_review_diff.py"


def load_loupe_diff_helper() -> ModuleType:
    """Load the Loupe diff helper script as an importable module."""
    spec = importlib.util.spec_from_file_location("loupe_collect_review_diff", DIFF_HELPER_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_git(cwd: Path, *args: str) -> None:
    """Run Git in a temporary repository."""
    subprocess.run(["git"] + list(args), cwd=str(cwd), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def initialize_repo(repo: Path) -> None:
    """Create a temporary Git repository with one committed file."""
    run_git(repo, "init", "-q")
    run_git(repo, "config", "user.email", "loupe@example.com")
    run_git(repo, "config", "user.name", "Loupe Test")
    (repo / "tracked.txt").write_text("base\n", encoding="utf-8")
    run_git(repo, "add", "tracked.txt")
    run_git(repo, "commit", "-q", "-m", "initial")


def test_collects_default_diff_artifact_for_staged_unstaged_and_untracked_text(capsys: pytest.CaptureFixture[str], isolated_cwd: Path) -> None:
    """Collect the default Loupe diff into an artifact with all uncommitted text changes."""
    helper = load_loupe_diff_helper()
    initialize_repo(isolated_cwd)
    (isolated_cwd / "tracked.txt").write_text("staged\n", encoding="utf-8")
    run_git(isolated_cwd, "add", "tracked.txt")
    (isolated_cwd / "tracked.txt").write_text("unstaged\n", encoding="utf-8")
    (isolated_cwd / "untracked.txt").write_text("untracked\n", encoding="utf-8")
    output_path = isolated_cwd / "review.diff"

    exit_code = helper.main([helper.DEFAULT_REVIEW_SCOPE, "--output", str(output_path)])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    diff_text = output_path.read_text(encoding="utf-8")
    assert list(payload) == ["review_scope", "git_root", "diff_path", "byte_count", "binary_payloads_included", "note"]
    assert payload["review_scope"] == helper.DEFAULT_REVIEW_SCOPE
    assert payload["git_root"] == str(isolated_cwd)
    assert payload["diff_path"] == str(output_path)
    assert payload["byte_count"] == len(output_path.read_bytes())
    assert payload["binary_payloads_included"] is False
    assert "-base" in diff_text
    assert "+staged" in diff_text
    assert "-staged" in diff_text
    assert "+unstaged" in diff_text
    assert "+untracked" in diff_text


def test_collects_binary_untracked_files_as_markers_without_payload(capsys: pytest.CaptureFixture[str], isolated_cwd: Path) -> None:
    """Represent untracked binary files without embedding binary payload bytes."""
    helper = load_loupe_diff_helper()
    initialize_repo(isolated_cwd)
    (isolated_cwd / "binary.dat").write_bytes(b"prefix\0suffix")
    output_path = isolated_cwd / "review.diff"

    exit_code = helper.main([helper.DEFAULT_REVIEW_SCOPE, "--output", str(output_path)])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    diff_bytes = output_path.read_bytes()
    diff_text = diff_bytes.decode("utf-8", errors="replace")
    assert payload["byte_count"] == len(diff_bytes)
    assert b"prefix\0suffix" not in diff_bytes
    assert "Binary files /dev/null and b/binary.dat differ" in diff_text


def test_diff_helper_rejects_custom_scopes(isolated_cwd: Path) -> None:
    """Reject custom scopes so agents must choose an explicit custom diff command."""
    helper = load_loupe_diff_helper()

    with pytest.raises(SystemExit) as exc_info:
        helper.parse_args(["only staged", "--output", str(isolated_cwd / "review.diff")])

    assert exc_info.value.code == 2
