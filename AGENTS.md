# AGENTS.md

## Code Style

- NEVER manually wrap code/comments/docstrings during code writing and edits; allow the formatters to later enforce line length.
- Avoid unqualified function imports like `from X.Y import func`; use `import X.Y` or `import X.Y as Y` and call via the module. Classes, exceptions, types, and constants may be imported directly.

## Commands

- Use uv for venv management and ALL Python execution.
- Never run uv with a custom/temporary cache dir (e.g. UV_CACHE_DIR or --cache-dir); if cache-related uv failures occur then abort and notify the user.
- The venv has no pip; use `uv pip`, `uv tree`, or similar.
- Use pytest for running tests, mypy for type checking, black/isort (NOT ruff) to format code, and `pydocfmt check` to format docstrings/comments.

## Workflows

- Rule documentation Markdown files follow the templates `rule_template.md` and `rule_category_template.md` in `src/pydocformatter/rules/`.
- When changing function signatures or class attributes, update all affected docstrings in the same change.
- If some tests fail only because the exact wording of a string has changed, then ask what to do instead of just blindly reverting the wording of the string.
- Concisely document significant completed work in CHANGELOG.md; use Added/Changed/Fixed/Removed subheadings of the Unreleased section, and use nested bullets for clear organization under short and very general bolded categories.
