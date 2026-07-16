"""Release artifact checksum manifest generator.

Attributes:
    READ_SIZE (int): Bytes read per artifact chunk while calculating SHA-256 digests.
"""

# Future imports
from __future__ import annotations

# Standard library imports
import os
import sys
import hashlib
import pathlib
import argparse
import tempfile


READ_SIZE = 1024 * 1024


def main(argv: list[str] | None = None) -> int:
    """Generate a checksum manifest for two release artifacts.

    Args:
        argv (list[str] | None): Command-line arguments, excluding the executable name.

    Returns:
        Zero after writing and printing the manifest, otherwise one.
    """
    parser = argparse.ArgumentParser(description="Generate a failure-safe SHA-256 manifest for two release artifacts.")
    parser.add_argument("--output", required=True, type=pathlib.Path, help="Manifest path to replace after both artifacts are hashed successfully.")
    parser.add_argument("artifacts", nargs=2, type=pathlib.Path, metavar="ARTIFACT", help="Release artifacts to hash in manifest order.")
    args = parser.parse_args(argv)

    try:
        manifest = write_checksum_manifest(tuple(args.artifacts), output=args.output)
    except (OSError, ValueError) as error:
        print(f"Unable to generate release checksums: {error}", file=sys.stderr)
        return 1

    print(manifest, end="")
    return 0


def write_checksum_manifest(artifacts: tuple[pathlib.Path, ...], *, output: pathlib.Path) -> str:
    """Replace an output manifest after hashing both release artifacts.

    Args:
        artifacts (tuple[pathlib.Path, ...]): Two distinct release artifacts in manifest order.
        output (pathlib.Path): Manifest path to invalidate before hashing and replace atomically after success.

    Returns:
        Written basename-only SHA-256 manifest text.

    Raises:
        OSError: If an artifact cannot be read or the manifest cannot be replaced.
        ValueError: If artifact or output path validation fails.
    """
    artifact_paths = tuple(artifacts)
    absolute_output = pathlib.Path(os.path.abspath(output))
    if any(pathlib.Path(os.path.abspath(path)) == absolute_output for path in artifact_paths):
        raise ValueError("Output manifest must not refer to an input artifact")
    try:
        resolved_output = _resolved_path(output)
        resolved_artifacts = tuple(_resolved_path(path) for path in artifact_paths)
    except (OSError, ValueError):
        output.unlink(missing_ok=True)
        raise
    if resolved_output in resolved_artifacts:
        raise ValueError("Output manifest must not refer to an input artifact")

    output.unlink(missing_ok=True)
    try:
        manifest = generate_checksum_manifest(artifact_paths)
        _replace_text(output, manifest)
    except (OSError, ValueError):
        output.unlink(missing_ok=True)
        raise
    return manifest


def generate_checksum_manifest(artifacts: tuple[pathlib.Path, ...]) -> str:
    """Return basename-only SHA-256 entries for two release artifacts.

    Args:
        artifacts (tuple[pathlib.Path, ...]): Two distinct release artifacts in manifest order.

    Returns:
        Manifest text with one checksum entry per artifact.

    Raises:
        OSError: If an artifact cannot be read.
        ValueError: If artifact path, name, count, or file-type validation fails.
    """
    artifact_paths = _validate_artifact_paths(artifacts)
    return "".join(f"{_sha256_digest(path)}  {path.name}\n" for path in artifact_paths)


def _validate_artifact_paths(artifacts: tuple[pathlib.Path, ...]) -> tuple[pathlib.Path, pathlib.Path]:
    """Return two release artifact paths after validating their identities and names."""
    if len(artifacts) != 2:
        raise ValueError(f"Expected exactly two release artifacts, received {len(artifacts)}")
    first, second = artifacts
    if _resolved_path(first) == _resolved_path(second):
        raise ValueError("Release artifact paths must be distinct")
    if first.name == second.name:
        raise ValueError("Release artifact basenames must be distinct")
    return first, second


def _resolved_path(path: pathlib.Path) -> pathlib.Path:
    """Return a resolved path while reporting symlink loops as validation errors."""
    try:
        return path.resolve(strict=False)
    except RuntimeError as error:
        raise ValueError(f"Unable to resolve path because of a symlink loop: {path}") from error


def _sha256_digest(path: pathlib.Path) -> str:
    """Return the streaming SHA-256 digest for one regular file."""
    if not path.is_file():
        raise ValueError(f"Release artifact is not a regular file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as file:
        while chunk := file.read(READ_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def _replace_text(output: pathlib.Path, text: str) -> None:
    """Atomically replace an output path with ASCII text."""
    temporary_path: pathlib.Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="ascii", newline="\n", dir=output.parent, prefix=f".{output.name}.", delete=False) as temporary_file:
            temporary_path = pathlib.Path(temporary_file.name)
            temporary_file.write(text)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        temporary_path.replace(output)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
