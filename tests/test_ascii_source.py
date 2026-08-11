"""Repository ASCII source policy tests."""

# Standard library imports
import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
TEXT_DIRECTORIES = (ROOT / ".claude", ROOT / ".codex", ROOT / ".github", ROOT / "docs", ROOT / "docs_site", ROOT / "src", ROOT / "tests", ROOT / "tools")
TEXT_FILENAMES = {".gitignore", ".python-version", "CODEOWNERS"}
TEXT_SUFFIXES = {
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
    ".md",
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
INTENTIONAL_UNICODE_DOCUMENTATION = {
    ROOT / "src/pydocformatter/rules/definitions/PCF/PCF200_comment_ascii_only.md",
    ROOT / "src/pydocformatter/rules/definitions/PCF/PCF201_comment_suspicious_unicode.md",
    ROOT / "src/pydocformatter/rules/definitions/PDF/PDF003_docstring_ascii_only.md",
    ROOT / "src/pydocformatter/rules/definitions/PDF/PDF004_docstring_suspicious_unicode.md",
    ROOT / "src/pydocformatter/rules/definitions/PDF/PDF104_opening_quotes_whitespace.md",
}


def test_repository_text_files_are_ascii_only() -> None:
    """Require escapes for non-ASCII text outside intentional documentation examples."""
    candidates = (path for directory in TEXT_DIRECTORIES if directory.is_dir() for path in directory.rglob("*") if path.is_file() and (path.name in TEXT_FILENAMES or path.suffix in TEXT_SUFFIXES))
    candidates = (*candidates, *(path for path in ROOT.iterdir() if path.is_file() and (path.name in TEXT_FILENAMES or path.suffix in TEXT_SUFFIXES)))
    offenders = tuple(sorted(path.relative_to(ROOT).as_posix() for path in candidates if path not in INTENTIONAL_UNICODE_DOCUMENTATION and not path.read_bytes().isascii()))

    assert not offenders, "Non-ASCII repository text files:\n" + "\n".join(offenders)


def test_intentional_unicode_documentation_allowlist_is_required() -> None:
    """Keep documentation exceptions limited to files that require literal Unicode."""
    unnecessary = tuple(sorted(path.relative_to(ROOT).as_posix() for path in INTENTIONAL_UNICODE_DOCUMENTATION if not path.is_file() or path.read_bytes().isascii()))

    assert not unnecessary, "Missing or ASCII-only intentional Unicode documentation files:\n" + "\n".join(unnecessary)
