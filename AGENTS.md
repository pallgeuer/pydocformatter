# AGENTS.md

## Project layout

- `src/pydocformatter/` contains the installed package and `pydocfmt` CLI; its command behavior, diagnostics, configuration schema, rule metadata, and formatted output are compatibility-sensitive public interfaces.
- `tests/` contains the pytest suite, including rule tests that mirror `src/pydocformatter/rules/definitions/`.
- `docs_site/` contains authored site pages, `docs/public/` contains published specifications, and `docs/devel/` contains internal specifications, audits, and temporary plans.
- `tools/docs/generate_zensical.py` produces the ignored `.generated/`, `zensical.generated.toml`, and `site/` documentation outputs.

## Code style

- NEVER manually wrap code/comments/in-code documentation during code writing and edits; allow the formatters to later enforce line length.
- Use ASCII-only project source; represent required non-ASCII values with escapes. Markdown files may use literal non-ASCII when required, but should still make obvious near-equivalent ASCII replacements where suitable.
- Use sentence case for Markdown headings and table headers; capitalize only the first word, the first word after a colon, and proper nouns.
- Do not import functions directly into the local namespace; import the containing module and call functions through it (for example, `from X import Y` followed by `Y.func()`, or `import X.Y` followed by `X.Y.func()`, or `import X.Y as Z` followed by `Z.func()`). Classes, exceptions, types, and constants may be imported directly. Direct function imports are allowed in `__init__.py` files (or other clearly sole-purpose public API files) solely to re-export functions as part of the package's public API.
- Write concise, meaningful docstrings. Module docstrings should identify what the file/package is, not say that it "provides support" or "implements" something. Attribute documentation must explain the role, semantics, units, source, or downstream use of the attribute; never restate the identifier with filler like "The foo value" or "The FOO enum member."

## Commands

- Use uv for venv management and ALL Python execution.
- Never run uv with a custom/temporary cache dir (e.g. UV_CACHE_DIR or --cache-dir); if cache-related uv failures occur then abort and notify the user.
- The venv has no pip; use `uv pip`, `uv tree`, or similar.
- Use `uv sync --locked --no-default-groups --group dev` to create the complete locked development environment.
- Use pytest for running tests. Pytest uses pytest-xdist multiprocessing by default; pass `-n 0` for serial debugging or focused runs where worker startup is slower.
- Use `uv run ty check` for type checking, `uv run ruff ...` for code formatting/linting, and `uv run pydocfmt check --fix` to format docstrings/comments.
- Do not run pydocfmt on Markdown files; it only parses Python source and will fail on Markdown.
- Use `uv run la-dev-markdown-tables` to format Markdown tables and `uv run la-dev-markdown-tables --check` to verify them.
- Use `uv run pre-commit run --all-files` for the potentially mutating complete fix stage and `uv run pre-commit run --all-files --hook-stage manual` for the non-mutating complete check used by CI.
- For documentation changes, run `uv run python tools/docs/generate_zensical.py` followed by `uv run zensical build --strict -f zensical.generated.toml`.
- Do not run `tools/docs/generate_zensical.py` and `zensical build` in parallel; the build reads the generated tree that the generator refreshes.

## Tests

- Write tests as module-level pytest functions. Use plain `assert`, `pytest.raises`, fixtures, `@pytest.mark.parametrize`, and `pytest-mock`; do not add `unittest.TestCase` test classes.
- After changing behavior, run applicable functional tests in addition to formatting, linting, type checking, and compatibility checks.

## Packaging

- Keep wheel contents limited to installed runtime code, runtime data, licenses, and required metadata. Include in the source distribution the source, build metadata, license and user-documentation files, and tests and configuration needed to build, document, and validate the unpacked archive. Exclude CI and agent configuration, repository-only helpers, and local state unless a non-sensitive file is required by those checks; never package credentials or secrets.

## Workflows

- Do not change project versions during ordinary development; update them only when the user explicitly requests a version bump or release.
- Interview me for relevant details when making plans, unless the details are quite clear already from the provided information.
- When editing a rule implementation, refer to `docs/devel/rule_implementation_spec.md`.
- Rule documentation Markdown files follow `src/pydocformatter/rules/templates/rule_template.md` and `src/pydocformatter/rules/templates/rule_category_template.md`.
- When changing function signatures or class attributes, update all affected docstrings in the same change.
- Do not lock incidental text into test assertions. If tests fail only because wording changed, determine whether the wording is a public contract and ask when unclear; do not blindly revert the wording.
- Concisely document significant completed work in CHANGELOG.md under the Unreleased section, using Added/Changed/Fixed/Removed headings, short general level-four category headings, and outcome bullets beneath those category headings.
