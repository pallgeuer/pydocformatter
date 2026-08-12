"""Package artifact content tests."""

# Standard library imports
import pathlib
import tarfile
import subprocess


ROOT = pathlib.Path(__file__).resolve().parents[1]
REPOSITORY_ONLY_SDIST_PATHS = frozenset({"RELEASE.md", "docs/devel/plans/.gitkeep"})


def test_sdist_excludes_repository_only_files(tmp_path: pathlib.Path) -> None:
    """Keep maintainer procedures and directory placeholders out of source distributions."""
    result = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        ["uv", "build", "--sdist", "--no-create-gitignore", "--out-dir", str(tmp_path), str(ROOT)], check=False, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr

    archives = tuple(tmp_path.glob("*.tar.gz"))
    assert len(archives) == 1
    with tarfile.open(archives[0], mode="r:gz") as archive:
        packaged_paths = frozenset(member.name.partition("/")[2] for member in archive.getmembers())

    assert packaged_paths.isdisjoint(REPOSITORY_ONLY_SDIST_PATHS)
