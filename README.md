# pydocformatter

[![PyPI version](https://img.shields.io/pypi/v/pydocformatter.svg)](https://pypi.org/project/pydocformatter/)
[![Python versions](https://img.shields.io/pypi/pyversions/pydocformatter.svg)](https://pypi.org/project/pydocformatter/)
[![CI](https://github.com/pallgeuer/pydocformatter/actions/workflows/pre_commit_checks.yml/badge.svg)](https://github.com/pallgeuer/pydocformatter/actions/workflows/pre_commit_checks.yml)
[![Documentation](https://github.com/pallgeuer/pydocformatter/actions/workflows/build_deploy_docs.yml/badge.svg)](https://github.com/pallgeuer/pydocformatter/actions/workflows/build_deploy_docs.yml)
[![License: GPL-3.0-or-later](https://img.shields.io/badge/license-GPL--3.0--or--later-blue.svg)](https://www.gnu.org/licenses/gpl-3.0.html)

pydocformatter is a rule-based linter and source formatter for Python docstrings and comments. Its `pydocfmt` command reports precise rule findings, applies fixes when source changes are safe, and leaves ambiguous or content-creating decisions to the author.

pydocformatter handles documentation and comment source; it does not format ordinary Python expressions or statements. Use it alongside [Ruff](https://docs.astral.sh/ruff/) or another general Python formatter.

## What it does

- Reflows docstring and comment prose, normalizes source layout, and preserves supported structured regions such as doctests, code fences, directives, lists, tables, and block quotes.
- Understands PEP 257, Google, NumPy, and reStructuredText docstring conventions, including semantic sections and documented parameters, returns, yields, exceptions, and attributes.
- Formats standalone and trailing comments while protecting recognized type-checker, linter, formatter, security, and IDE directives.
- Selects independently documented PCF comment rules and PDF docstring rules, with per-rule diagnostics and explicit fix availability.
- Uses Ruff-style configuration, file discovery, selectors, per-file ignores, fixability controls, source suppressions, and inspection commands.
- Preserves evaluated docstring values for source-literal rewrites that require semantic equivalence, while content-formatting rules may intentionally change docstring whitespace, and avoids automatic changes when the intended source rewrite or missing documentation cannot be inferred safely.

## Documentation and help

The [documentation site](https://pallgeuer.github.io/pydocformatter/) is the complete user guide and reference. These links go directly to the relevant help:

| Need                                                           | Resource                                                                                                                                                                                                                                                                                                                         |
|----------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Install and complete a first run                               | [Tutorial](https://pallgeuer.github.io/pydocformatter/tutorial/) and [Installation](https://pallgeuer.github.io/pydocformatter/installation/)                                                                                                                                                                                    |
| Configure pydocfmt                                             | [Configuration](https://pallgeuer.github.io/pydocformatter/configuration/) and generated [Settings](https://pallgeuer.github.io/pydocformatter/settings/)                                                                                                                                                                        |
| Configure Ruff alongside pydocformatter                        | [Ruff rule links](https://pallgeuer.github.io/pydocformatter/rules/ruff-rule-links/)                                                                                                                                                                                                                                             |
| Understand a rule or browse available rules                    | [Rules](https://pallgeuer.github.io/pydocformatter/rules/) or `pydocfmt rule RULE`                                                                                                                                                                                                                                               |
| Choose or inspect active, ignored, per-file, and fixable rules | [Rule selection](https://pallgeuer.github.io/pydocformatter/reference/rule-selection/) and `pydocfmt check --show-rules`                                                                                                                                                                                                         |
| Understand checking, fixing, suppressions, and file discovery  | [Checking](https://pallgeuer.github.io/pydocformatter/checking/), [Formatting](https://pallgeuer.github.io/pydocformatter/formatting/), [Rule suppressions](https://pallgeuer.github.io/pydocformatter/reference/rule-suppressions/), and [File selection](https://pallgeuer.github.io/pydocformatter/reference/file-selection/) |
| Add pre-commit, CI, or editor workflows                        | [Integrations](https://pallgeuer.github.io/pydocformatter/integrations/)                                                                                                                                                                                                                                                         |
| Resolve common questions                                       | [FAQ](https://pallgeuer.github.io/pydocformatter/faq/), `pydocfmt --help`, `pydocfmt check --help`, and `pydocfmt config SETTING`                                                                                                                                                                                                |
| Report a bug or propose a change                               | [GitHub Issues](https://github.com/pallgeuer/pydocformatter/issues)                                                                                                                                                                                                                                                              |

## Installation

pydocformatter requires Python 3.11 or newer. Add it to a project as a development dependency with uv:

```bash
uv add --dev pydocformatter
uv run pydocfmt --version
```

To install the command independently of a project environment:

```bash
uv tool install pydocformatter
```

See [Installation](https://pallgeuer.github.io/pydocformatter/installation/) for pip, pipx, and Git pre-commit alternatives. If `pydocfmt` is already available on `PATH`, omit `uv run` from the commands below.

## Quick start

Run pydocformatter from a project root to check discovered Python files without changing them:

```bash
uv run pydocfmt check
```

Preview automatic fixes as a unified diff, or apply them in place:

```bash
uv run pydocfmt check --diff
uv run pydocfmt check --fix
```

Pass files or directories to limit the run, for example `uv run pydocfmt check src tests`. With no paths, pydocformatter checks the current directory. Check mode returns a nonzero exit status when it finds rule violations or operational errors, which makes the same command suitable for CI.

## Configuration

Place project settings in `pyproject.toml`. A small configuration might specify only the shared line length and the project's docstring convention:

```toml
[tool.pydocfmt]
line-length = 88

[tool.pydocfmt.docstring]
convention = "google"
```

Inspect the resolved configuration, discovered files, and active rules before changing source:

```bash
uv run pydocfmt check --show-settings
uv run pydocfmt check --show-files
uv run pydocfmt check --show-rules
uv run pydocfmt rule PDF101
```

Use `uv run pydocfmt config` to list every setting, or pass a setting name such as `uv run pydocfmt config line-length` for focused help. The documentation table above links the full configuration, settings, rule-selection, and Ruff-compatibility references.

## Examples

In each example, `[settings]` or `Settings` (when present) shows the relevant pydocformatter settings used, including pertinent defaults. `[input]` or `Before` shows the original source, `[output]` or `After` shows the source after automatic fixes, and `[findings]` or `Findings` shows the diagnostics that remain afterward (not auto-fixable).

### Reflow with human-authored documentation left to do

This function has ordinary long prose and a partially documented Google-style signature. pydocformatter can reflow the prose, but it cannot decide how the summary should be shortened or invent documentation for `default_role`.

```pydocfmt-example
[settings]
line-length = 88
docstring-convention = "google"

[input]
"""User configuration helpers."""


def load_user(path, default_role):
    """Loads a user record from disk and returns normalized settings for the application with predictable defaults.

    Args:
        path: Path to the user configuration file.
    """
    # Keep the fallback role in the returned record so callers can handle incomplete configuration files consistently across environments.
    return {"path": path, "role": default_role}

[output]
"""User configuration helpers."""


def load_user(path, default_role):
    """Loads a user record from disk and returns normalized settings for the application
    with predictable defaults.

    Args:
        path: Path to the user configuration file.
    """
    # Keep the fallback role in the returned record so callers can handle incomplete
    # configuration files consistently across environments.
    return {"path": path, "role": default_role}

[findings]
PDF203: Lines 5-6: Docstring summary spans 2 lines and does not fit on one line
PDF500: Line 4: Function parameter 'default_role' is missing docstring documentation
```

[`PDF101`](https://pallgeuer.github.io/pydocformatter/rules/docstring-reflow/) and [`PCF001`](https://pallgeuer.github.io/pydocformatter/rules/standalone-comment-formatting/) apply the safe wrapping changes. [`PDF203`](https://pallgeuer.github.io/pydocformatter/rules/summary-too-long/) and [`PDF500`](https://pallgeuer.github.io/pydocformatter/rules/missing-parameter-documentation/) remain as diagnostic-only findings for the author to resolve, including in particular that the docstring summary line now does not fit on one line, when in general it should.

### Trailing comments and stale suppressions

This retry helper contains an overlong trailing explanation and a suppression that no longer suppresses anything. Moving the explanation and removing the obsolete directive are separate policy decisions, so the relevant rules expose them separately.

```pydocfmt-example
[settings]
line-length = 72

[input]
"""Retry policy helpers."""


def _retry_delay(attempt):
    # pydocfmt: ignore[PCF001]
    # Keep retry delays bounded.
    delay = min(2**attempt, 60)#Cap exponential backoff so temporary failures do not stall a worker indefinitely.
    return delay

[output]
"""Retry policy helpers."""


def _retry_delay(attempt):
    # pydocfmt: ignore[PCF001]
    # Keep retry delays bounded.

    # Cap exponential backoff so temporary failures do not stall a
    # worker indefinitely.
    delay = min(2**attempt, 60)
    return delay

[findings]
PCF006: Line 5: Suppression selector 'PCF001' did not suppress any findings
```

[`PCF002`](https://pallgeuer.github.io/pydocformatter/rules/trailing-comment-spacing/) normalizes the trailing-comment delimiter before [`PCF004`](https://pallgeuer.github.io/pydocformatter/rules/trailing-comment-extraction/) moves and wraps the explanation. The blank line preserves separation from the independently authored comment above it. [`PCF006`](https://pallgeuer.github.io/pydocformatter/rules/unused-suppression/) reports the stale suppression but deliberately does not delete it.

## Using pydocformatter with Ruff

pydocformatter is intended to own docstring and comment formatting where its rules overlap with Ruff. Align shared settings such as indentation and line endings, and disable Ruff rules that would enforce the same docstring or comment policy. The [Ruff rule links](https://pallgeuer.github.io/pydocformatter/rules/ruff-rule-links/) page provides a paired configuration and rule-by-rule compatibility mapping.

## Contributing

See [Contributing](CONTRIBUTING.md) for the development environment, rule implementation workflow, documentation pipeline, and pull request checks. Project history and current unreleased changes are recorded in the [Changelog](CHANGELOG.md).

## License

pydocformatter is licensed under the [GNU General Public License v3.0 or later](LICENSE.md).

## Acknowledgments

pydocformatter draws inspiration from [pyformatter](https://github.com/RikGhosh487/pyformatter), [docformatter](https://github.com/PyCQA/docformatter), and established Python formatting tools such as [Ruff](https://docs.astral.sh/ruff).
