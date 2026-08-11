"""Repository ASCII source policy tests."""

# Standard library imports
import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE_AND_CONFIG_DIRECTORIES = (ROOT / ".claude", ROOT / ".codex", ROOT / ".github", ROOT / "docs_site", ROOT / "src", ROOT / "tests", ROOT / "tools")
SOURCE_AND_CONFIG_SUFFIXES = {
    ".cfg",
    ".css",
    ".fish",
    ".html",
    ".ini",
    ".j2",
    ".jinja",
    ".js",
    ".json",
    ".lock",
    ".mjs",
    ".py",
    ".pyi",
    ".pyx",
    ".pxd",
    ".sh",
    ".svg",
    ".toml",
    ".ts",
    ".tsx",
    ".yaml",
    ".yml",
    ".zsh",
}


def test_source_and_configuration_files_are_ascii_only() -> None:
    """Require escapes for non-ASCII source and configuration values."""
    candidates = (path for directory in SOURCE_AND_CONFIG_DIRECTORIES if directory.is_dir() for path in directory.rglob("*") if path.is_file() and path.suffix in SOURCE_AND_CONFIG_SUFFIXES)
    candidates = (*candidates, *(path for path in ROOT.iterdir() if path.is_file() and path.suffix in SOURCE_AND_CONFIG_SUFFIXES))
    offenders = tuple(sorted(path.relative_to(ROOT).as_posix() for path in candidates if not path.read_bytes().isascii()))

    assert not offenders, "Non-ASCII source or configuration files:\n" + "\n".join(offenders)
