"""Tests for published pydocformatter pre-commit hook metadata."""

# Standard library imports
import re
import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / ".pre-commit-hooks.yaml"
INTEGRATIONS = ROOT / "docs_site" / "integrations.md"
SUPPORTED_FILENAMES = ("guide.md", "GUIDE.MD", "module.py", "MODULE.PY", "module.pyi", "MODULE.PYI", "module.pyw", "MODULE.PYW")
UNSUPPORTED_FILENAMES = ("script", "build.gyp", "config.gypi", "module.pyt", "service.tac", "app.wsgi")


def _hook_fields() -> tuple[dict[str, str], ...]:
    """Return the simple scalar fields for each published hook."""
    hooks: list[dict[str, str]] = []
    for section in f"\n{MANIFEST.read_text(encoding='utf-8')}".split("\n- id: ")[1:]:
        hook_id, _, body = section.partition("\n")
        fields = {"id": hook_id}
        for line in body.splitlines():
            if ": " in line:
                key, value = line.strip().split(": ", maxsplit=1)
                fields[key] = value.strip("'")
        hooks.append(fields)
    return tuple(hooks)


def test_published_hooks_use_types_or_with_default_python_and_markdown_filenames() -> None:
    hooks = _hook_fields()

    assert tuple(hook["id"] for hook in hooks) == ("pydocfmt-check", "pydocfmt-fix")
    assert all(hook["types_or"] == "[python, pyi, markdown]" for hook in hooks)
    for hook in hooks:
        filename_pattern = re.compile(hook["files"])
        assert all(filename_pattern.search(filename) is not None for filename in SUPPORTED_FILENAMES)
        assert all(filename_pattern.search(filename) is None for filename in UNSUPPORTED_FILENAMES)
        assert hook["files"] == r"(?i)\.(?:py|pyi|pyw|md)$"


def test_published_hooks_require_types_or_capable_pre_commit() -> None:
    assert all(hook["minimum_pre_commit_version"] == "2.9.0" for hook in _hook_fields())


def test_custom_extension_guidance_covers_pre_commit_and_direct_discovery() -> None:
    guidance = INTEGRATIONS.read_text(encoding="utf-8")

    assert "types_or: [file]" in guidance
    assert "files: (?i)\\.(?:py|pyi|pyw|md|rpy|mdx)$" in guidance
    assert "extend-include" in guidance
    assert "[tool.pydocfmt.extension]" in guidance
