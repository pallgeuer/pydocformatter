"""Release checksum manifest generator tests."""

# Future imports
from __future__ import annotations

# Standard library imports
import hashlib
import pathlib
from typing import TYPE_CHECKING

# Third-party imports
import pytest
import tools.generate_release_checksums as release_checksums


if TYPE_CHECKING:
    # Third-party imports
    from pytest_mock import MockerFixture


def test_write_checksum_manifest_hashes_both_artifacts_in_order(tmp_path: pathlib.Path) -> None:
    """The manifest must contain ordered basename-only SHA-256 entries."""
    sdist = tmp_path / "package.tar.gz"
    wheel = tmp_path / "package.whl"
    output = tmp_path / "SHA256SUMS"
    sdist.write_bytes(b"source distribution")
    wheel.write_bytes(b"wheel")
    expected = f"{hashlib.sha256(b'source distribution').hexdigest()}  package.tar.gz\n{hashlib.sha256(b'wheel').hexdigest()}  package.whl\n"

    manifest = release_checksums.write_checksum_manifest((sdist, wheel), output=output)

    assert manifest == expected
    assert output.read_text(encoding="ascii") == expected


def test_main_prints_the_written_manifest(tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A successful command must print exactly the persisted manifest."""
    first = tmp_path / "first.tar.gz"
    second = tmp_path / "second.whl"
    output = tmp_path / "SHA256SUMS"
    first.write_bytes(b"first")
    second.write_bytes(b"second")

    assert release_checksums.main(["--output", str(output), str(first), str(second)]) == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out == output.read_text(encoding="ascii")


def test_missing_artifact_removes_stale_manifest(tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Hashing failure must not leave a stale manifest available for publication."""
    present = tmp_path / "present.tar.gz"
    missing = tmp_path / "missing.whl"
    output = tmp_path / "SHA256SUMS"
    present.write_bytes(b"present")
    output.write_text("stale\n", encoding="ascii")

    assert release_checksums.main(["--output", str(output), str(present), str(missing)]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Release artifact is not a regular file" in captured.err
    assert not output.exists()


def test_cyclic_artifact_symlink_removes_stale_manifest(tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A symlink loop must fail cleanly without retaining an old manifest."""
    first = tmp_path / "first.tar.gz"
    second = tmp_path / "second.whl"
    output = tmp_path / "SHA256SUMS"
    try:
        first.symlink_to("first.tar.gz")
    except (NotImplementedError, OSError) as error:
        pytest.skip(f"Symbolic links are unavailable: {error}")
    second.write_bytes(b"second")
    output.write_text("stale\n", encoding="ascii")

    assert release_checksums.main(["--output", str(output), str(first), str(second)]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "symlink loop" in captured.err
    assert not output.exists()


def test_duplicate_artifact_basenames_remove_stale_manifest(tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Ambiguous basename entries must fail without retaining an old manifest."""
    first = tmp_path / "first" / "package.whl"
    second = tmp_path / "second" / "package.whl"
    output = tmp_path / "SHA256SUMS"
    first.parent.mkdir()
    second.parent.mkdir()
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    output.write_text("stale\n", encoding="ascii")

    assert release_checksums.main(["--output", str(output), str(first), str(second)]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "basenames must be distinct" in captured.err
    assert not output.exists()


def test_duplicate_artifact_paths_remove_stale_manifest(tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Repeated artifact paths must fail without retaining an old manifest."""
    artifact = tmp_path / "package.whl"
    output = tmp_path / "SHA256SUMS"
    artifact.write_bytes(b"artifact")
    output.write_text("stale\n", encoding="ascii")

    assert release_checksums.main(["--output", str(output), str(artifact), str(artifact)]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "paths must be distinct" in captured.err
    assert not output.exists()


def test_hashing_failure_removes_stale_manifest(tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str], mocker: MockerFixture) -> None:
    """A failure after hashing starts must leave no partial or stale manifest."""
    first = tmp_path / "package.tar.gz"
    second = tmp_path / "package.whl"
    output = tmp_path / "SHA256SUMS"
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    output.write_text("stale\n", encoding="ascii")
    mocker.patch.object(release_checksums, "_sha256_digest", side_effect=("0" * 64, PermissionError("unreadable artifact")))

    assert release_checksums.main(["--output", str(output), str(first), str(second)]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "unreadable artifact" in captured.err
    assert not output.exists()


def test_output_manifest_cannot_replace_an_artifact(tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Output validation must protect artifacts before stale-output invalidation."""
    first = tmp_path / "package.tar.gz"
    second = tmp_path / "package.whl"
    first.write_bytes(b"first")
    second.write_bytes(b"second")

    assert release_checksums.main(["--output", str(first), str(first), str(second)]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "must not refer to an input artifact" in captured.err
    assert first.read_bytes() == b"first"


def test_output_manifest_symlink_cannot_replace_an_artifact(tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Resolved output aliases must protect artifacts before stale-output invalidation."""
    first = tmp_path / "package.tar.gz"
    second = tmp_path / "package.whl"
    output = tmp_path / "SHA256SUMS"
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    try:
        output.symlink_to(first.name)
    except (NotImplementedError, OSError) as error:
        pytest.skip(f"Symbolic links are unavailable: {error}")

    assert release_checksums.main(["--output", str(output), str(first), str(second)]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "must not refer to an input artifact" in captured.err
    assert output.is_symlink()
    assert first.read_bytes() == b"first"
