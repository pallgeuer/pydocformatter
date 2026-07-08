# AGENTS.md

## Code Style

- NEVER manually wrap code/comments/docstrings during code writing and edits; allow the formatters to later enforce line length.
- Use ASCII-only project source; represent required non-ASCII values with escapes. Markdown files may use literal non-ASCII when required.
- Avoid unqualified function imports like `from X.Y import func`; use `import X.Y` or `import X.Y as Y` and call via the module. Classes, exceptions, types, and constants may be imported directly.
- Write concise, meaningful docstrings. Module docstrings should identify what the file/package is, not say that it "provides support" or "implements" something. Attribute documentation must explain the role, semantics, units, source, or downstream use of the attribute; never restate the identifier with filler like "The foo value" or "The FOO enum member."

## Commands

- Use uv for venv management and ALL Python execution.
- Never run uv with a custom/temporary cache dir (e.g. UV_CACHE_DIR or --cache-dir); if cache-related uv failures occur then abort and notify the user.
- The venv has no pip; use `uv pip`, `uv tree`, or similar.
- Use pytest for running tests. Pytest uses pytest-xdist multiprocessing by default; pass `-n 0` for serial debugging or focused runs where worker startup is slower.
- Use ty for type checking, Ruff for code formatting/linting, and `pydocfmt check --fix` to format docstrings/comments.
- Do not run pydocfmt on Markdown files; it only parses Python source and will fail on Markdown.

## Tests

- Write tests as module-level pytest functions. Use plain `assert`, `pytest.raises`, fixtures, `@pytest.mark.parametrize`, and `pytest-mock`; do not add `unittest.TestCase` test classes.

## Workflows

- Interview me for relevant details when making plans, unless the details are quite clear already from the provided information.
- When editing a rule implementation, refer to `docs/rule_implementation_spec.md`.
- Rule documentation Markdown files follow the templates `rule_template.md` and `rule_category_template.md` in `src/pydocformatter/rules/`.
- When changing function signatures or class attributes, update all affected docstrings in the same change.
- If some tests fail only because the exact wording of a string has changed, then ask what to do instead of just blindly reverting the wording of the string.
- Concisely document significant completed work in CHANGELOG.md; use Added/Changed/Fixed/Removed subheadings of the Unreleased section, and use nested bullets for clear organization under short and very general bolded categories.
