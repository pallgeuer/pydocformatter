# AGENTS.md

## Code Style

- Do not manually wrap code/comments/docstrings; let formatters enforce line length.

## Commands

- Use uv for venv management and all Python execution.
- Never run uv with a custom/temporary cache dir (e.g. UV_CACHE_DIR or --cache-dir); if cache-related uv failures occur then abort and notify the user.
- The venv has no pip; use `uv pip`, `uv tree`, or similar.

## Workflows

- When changing function signatures or class attributes, update all affected docstrings in the same change.
- Concisely document significant completed work in CHANGELOG.md; use Added/Changed/Fixed/Removed subheadings of the Unreleased section, and use nested bullets for clear organization under bolded categories.
