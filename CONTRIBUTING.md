# Contributing to pydocformatter

pydocformatter is a rule-based linter and formatter. Contributions should preserve predictable diagnostics, safe source edits, idempotent formatting, and stable rule-selection behavior.

Small bug fixes, tests, and documentation corrections can go directly to a pull request. Open an issue before starting a new rule, a substantial feature, or a breaking behavior change so that its scope and compatibility can be agreed first.

## Reporting bugs and proposing changes

Search the [existing issues](https://github.com/pallgeuer/pydocformatter/issues) before opening a new one. A useful bug report includes:

- A minimal Python input that reproduces the problem.
- The exact `pydocfmt` command and relevant configuration.
- The observed diagnostics or formatted output and the expected result.
- The pydocformatter version, Python version, operating system, and installation method.
- Whether `--fix` changes code incorrectly, is not idempotent, or loses source details such as comments or line endings.

Feature proposals should describe the use case, intended behavior, configuration or CLI impact, and compatibility with existing rules. For a new rule, also identify its likely category, fix safety, and interaction with related pydocformatter or Ruff rules.

## Development setup

Development requires Git, [uv](https://docs.astral.sh/uv/), and Python 3.11 or newer. The supported compatibility targets are Ubuntu 20.04 and newer and macOS 14 and newer, with best-effort support for other POSIX Linux systems. Native Windows and WSL are unsupported. CI exercises Python 3.11 through 3.14 across glibc and musl Linux, x64 and ARM64, and Intel and ARM64 macOS environments.

Fork the repository if needed to `YOUR-USERNAME/pydocformatter`, then create the locked development environment from the repository root:

```bash
git clone https://github.com/YOUR-USERNAME/pydocformatter.git
cd pydocformatter
uv sync --locked --no-default-groups --group dev
uv run pre-commit install
```

Verify the checkout with:

```bash
uv run pydocfmt --version
uv run pytest -q
```

Use `uv run` for all Python commands. The project environment intentionally has no `pip`; use commands such as `uv sync`, `uv lock`, and `uv tree` for dependency work. The local `pydocfmt` command runs the checked-out source, including from pre-commit hooks.

## Repository layout

- `src/pydocformatter/cli/` contains the command-line interface and diagnostic rendering.
- `src/pydocformatter/settings.py`, `file_selection.py`, and `rules_selection.py` contain configuration, path selection, and rule-selection behavior.
- `src/pydocformatter/formatter.py` and `src/pydocformatter/rules/` contain formatting orchestration, the rule framework, source edits, suppression handling, and rule execution.
- `src/pydocformatter/rules/definitions/` contains built-in rule categories and rules, with adjacent rule documentation.
- `tests/` contains the pytest suite; `tests/rules/` mirrors the built-in rule categories.
- `docs_site/` contains hand-authored website pages, `docs/public/` contains published specifications, and `docs/devel/` contains implementation specifications and audits.
- `tools/docs/generate_zensical.py` builds the generated documentation input from project, public, and rule documentation.

The `pydocfmt` CLI is the primary supported public interface. Treat its options, exit behavior, diagnostics, configuration schema, rule metadata, and formatted output as compatibility-sensitive.

## Making changes

Keep each change focused and include tests at the level where behavior is defined. A typical contribution should:

1. Add or adjust a focused test that demonstrates the intended behavior.
2. Implement the smallest coherent change.
3. Update affected user documentation, specifications, rule documentation, and docstrings.
4. Add a concise entry to `CHANGELOG.md` when the result is significant to users or developers.
5. Run focused checks while iterating and the full relevant checks before submitting.

Do not combine unrelated cleanup or generated artifacts with a functional change. Preserve compatibility unless the change has been discussed as breaking, and document any required migration.

### Python and Markdown conventions

Repository configuration and automated tools are the source of truth for formatting and linting. In addition:

- Do not manually wrap Python code, comments, or docstrings; let Ruff and pydocfmt enforce their configured layouts.
- Keep project source ASCII-only. Use escapes when source code must represent non-ASCII values; Markdown may use literal non-ASCII text where needed.
- Use qualified module imports for functions rather than `from package.module import function`. Direct imports are acceptable for classes, exceptions, types, and constants.
- Keep type annotations and affected docstrings current when changing function signatures, dataclass fields, enum values, or class attributes.
- Write concise docstrings that explain semantics rather than restating identifiers. Project docstrings use the configured Google convention.
- Use sentence case for Markdown headings and table headers.
- Do not run pydocfmt on Markdown files; it parses Python source only.

Tests are module-level pytest functions. Use plain `assert`, fixtures, `pytest.raises`, `@pytest.mark.parametrize`, and `pytest-mock`; do not introduce `unittest.TestCase` classes.

## Working on rules

Read the [rule implementation specification](https://github.com/pallgeuer/pydocformatter/blob/main/docs/devel/rule_implementation_spec.md) before adding or changing a rule. It is the normative contract for rule identity, metadata, registration, execution, violations, source fixes, documentation, and tests.

A built-in rule normally has these matching files:

```text
src/pydocformatter/rules/definitions/<PREFIX>/<CODE>_<rule_name>.py
src/pydocformatter/rules/definitions/<PREFIX>/<CODE>_<rule_name>.md
tests/rules/<PREFIX>/test_<CODE>.py
```

Category modules and documentation use the category prefix as their stem. Rule modules define one registered `RuleBase` subclass; category modules define one registered `RuleCategoryBase` subclass. File stems, class names, metadata names, codes, category ranges, and documentation headings must agree.

Rule implementations report violations and planned source changes. They do not mutate the context, apply edits, or process suppressions themselves; the runner owns suppression filtering, effective fixability, edit validation, application, and post-fix accounting. Put behavior shared by multiple rules in the existing definition helpers or edit helpers instead of duplicating it.

Every new or changed rule must also address the following:

- Update `docs/devel/rule_settings_audit.md` for settings read directly, through category data, or through called helpers.
- Follow `src/pydocformatter/rules/templates/rule_template.md` and the category template when applicable.
- Keep structured `pydocfmt-example` blocks executable and their findings exact.
- Cover diagnostics, fixes and non-fixable cases, no-op and edge cases, settings interactions, idempotence, unsafe-fix behavior, suppressions, and line endings where relevant.
- Add category, selection, settings, or CLI coverage when metadata or externally visible behavior changes.
- Update public rule-selection, settings, suppression, or Ruff-compatibility documentation when the corresponding contract changes.

Useful focused verification for a rule change is:

```bash
uv run pytest -n 0 tests/rules/<PREFIX>/test_<CODE>.py
uv run pytest -n 0 tests/test_rules.py tests/test_formatting_rules_doc.py tests/test_rule_markdown_examples.py tests/test_rule_settings_audit.py
```

Add the relevant category, settings, formatter, and CLI tests for changes that cross those boundaries.

## Testing and quality checks

Pytest uses pytest-xdist multiprocessing by default. Run a focused test serially when worker startup would dominate or when debugging shared state:

```bash
uv run pytest -n 0 tests/path/to/test_module.py -q
uv run pytest -n 0 tests/path/to/test_module.py::test_name -q
```

Run the full suite with the configured parallelism:

```bash
uv run pytest -q
```

Apply and inspect the automated fixes before final verification:

```bash
uv run ruff check --fix
uv run pydocfmt check --fix
uv run ruff format
uv run ty check
```

The complete local CI-equivalent hook suite runs formatting, linting, type checking, and pytest. It may modify files, so review the diff and rerun it until clean:

```bash
uv run pre-commit run --all-files
```

For check-only runs, omit `--fix` and use `uv run ruff format --check`. Select checks in proportion to the change, but run the full hook suite before submitting code or rule changes.

## Documentation site

Edit authored sources, not ignored outputs under `.generated/`, `site/`, or `zensical.generated.toml`. The documentation generator publishes `docs_site/`, `docs/public/`, built-in rule documentation, and selected top-level project files, including this guide.

For documentation-site changes, first run the focused generation tests:

```bash
uv run pytest -n 0 tests/test_docs_generation.py tests/test_formatting_rules_doc.py tests/test_rule_markdown_examples.py tests/test_markdown_tables.py
```

Then generate and build the site in sequence. Do not run these commands in parallel because the build consumes the tree refreshed by the generator:

```bash
uv run python tools/docs/generate_zensical.py
uv run zensical build --strict -f zensical.generated.toml
```

To preview the generated site, run `uv run zensical serve -f zensical.generated.toml` after generation. The site intentionally uses Zensical without MkDocs or MkDocs plugin dependencies.

Repository Markdown tables have a tested alignment style. If its test fails, normalize tracked Markdown tables with:

```bash
uv run la-dev-markdown-tables
```

## Dependencies

Declare dependencies in `pyproject.toml` and commit the corresponding `uv.lock` update. Direct entries in the `docs`, `test`, and `dev` dependency groups must use exact `name==version` pins; included groups are allowed. After a dependency change, run:

```bash
uv lock
uv sync --locked --no-default-groups --group dev
uv run pytest -n 0 tests/test_dependency_pins.py
```

Keep runtime dependencies minimal and compatible with every supported Python version. Explain new runtime or documentation dependencies in the pull request.

## Submitting a pull request

Before requesting review:

- Review the complete diff for unrelated edits and generated files.
- Rebase or merge the current `main` branch as appropriate and resolve conflicts deliberately.
- Run the relevant focused tests and the full pre-commit suite.
- Complete the pull request template, explaining the problem, behavior change, compatibility implications, and commands used for verification.
- Link related issues and include concise before-and-after examples for formatter, diagnostic, or CLI output changes.
- Confirm that both the pre-commit and strict documentation GitHub Actions checks pass.

Keep review follow-ups in the same scope. If feedback reveals a separate problem, prefer a new issue or pull request rather than expanding the original change without discussion.
