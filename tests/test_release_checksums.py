"""Release checksum command integration tests."""

# Standard library imports
import shutil
import hashlib
import pathlib
import subprocess


def test_release_checksum_command_writes_and_prints_ordered_manifest(tmp_path: pathlib.Path) -> None:
    """Protect the release guide's installed command and argument contract."""
    command = shutil.which("la-dev-release-checksums")
    assert command is not None
    sdist = tmp_path / "package.tar.gz"
    wheel = tmp_path / "package.whl"
    output = tmp_path / "SHA256SUMS"
    sdist.write_bytes(b"source distribution")
    wheel.write_bytes(b"wheel")
    expected = f"{hashlib.sha256(b'source distribution').hexdigest()}  package.tar.gz\n{hashlib.sha256(b'wheel').hexdigest()}  package.whl\n"

    result = subprocess.run([command, "--output", str(output), str(sdist), str(wheel)], check=False, capture_output=True, text=True)  # ruff: ignore[subprocess-without-shell-equals-true]

    assert result.returncode == 0
    assert result.stderr == ""
    assert result.stdout == expected
    assert output.read_text(encoding="utf-8") == expected
