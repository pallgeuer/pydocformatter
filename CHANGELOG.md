# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and pydocformatter follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## Release diffs

- **Unreleased:** <https://github.com/pallgeuer/pydocformatter/compare/v1.0.0...HEAD>
- **v1.0.0:** <https://github.com/pallgeuer/pydocformatter/compare/v0.2.0...v1.0.0>
- **v0.2.0:** <https://github.com/pallgeuer/pydocformatter/releases/tag/v0.2.0>

---

## Unreleased

None.

---

## v1.0.0

Released 2026-07-16

### Added

#### Rule-based formatting

- Rebuilt pydocformatter as a rule-based linter and formatter with 122 stable, independently selectable rules: `PCF001` through `PCF006` for comments and 116 `PDF` rules for docstrings.
- Added conservative automatic fixes with repeated passes, convergence checks, source suppressions, per-finding fixability, exact source locations, and read-only diagnostics when a safe change cannot be inferred.
- Added convention-aware docstring parsing for PEP 257, Google, NumPy, and reStructuredText, including semantic sections and entries plus protected lists, headings, doctests, code fences, block quotes, tables, directives, literal blocks, and reST fields.
- Added docstring rules for literal and quote normalization, indentation, reflow, whitespace, blank lines, summary style, section structure, entry formatting, signature and documented-value consistency, attribute documentation placement, missing documentation, description quality, and conservative annotation/type agreement.
- Added comment rules for standalone prose reflow, trailing-comment spacing and extraction, recognized tool-directive normalization, non-ASCII reporting, and unused pydocfmt suppression reporting. Formatting preserves supported type-checker, linter, formatter, security, IDE, doctest, code, table, directive, and task-marker structures.

#### CLI and configuration

- Added the Ruff-style `pydocfmt check` workflow, with `--fix`, `--diff`, stdin, output redirection, exit-status controls, explicit and inline configuration, isolated mode, deterministic file-level parallelism, line-ending control, and grouped diagnostics.
- Added `pydocfmt config`, `pydocfmt rule`, `pydocfmt linter`, `pydocfmt help`, `pydocfmt version`, and inspection output for settings, rules, and discovered files.
- Added Ruff-style rule selection and fixability controls, per-file ignores and settings, path-aware configuration discovery, glob-based file selection, gitignore support, explicit-file force exclusion, URL-aware wrapping, and detailed docstring and comment behavior settings.
- Added published `pydocfmt-check` and `pydocfmt-fix` pre-commit hooks.

#### Documentation and packaging

- Added a documentation site with tutorials, workflows, settings and rule references, Ruff compatibility guidance, executable examples, public behavior specifications, and adjacent documentation for every built-in rule.
- Added reproducible Hatchling builds, tested wheel and source-distribution contents, and portable release checksum generation.

### Changed

#### Breaking migration from v0.2.0

- Replaced the old top-level `pydocfmt` and `pydocfmt --check` forms with `pydocfmt check --fix` and `pydocfmt check`, respectively.
- Merged comment formatting into `pydocfmt` and removed the separate comment-formatting command.
- Renamed the configuration table from `[tool.pydocformatter]` to `[tool.pydocfmt]`. Only hyphenated setting keys are accepted, and nested `[tool.pydocfmt.docstring]` and `[tool.pydocfmt.comment]` tables are the preferred forms for formatter-specific settings.
- Replaced regex include and exclude settings with Ruff-style glob lists. Configuration now follows explicit source precedence, closest-file discovery, config-relative pattern bases, per-file overrides, and gitignore-aware file selection.
- Replaced `docstring-parse-sphinx-fields` with `docstring-convention = "rest"` for semantic reStructuredText and Sphinx field parsing.
- Changed the default docstring convention to `pep257`; convention-dependent rules are enabled, ignored, or disabled according to whether the selected convention supplies their semantic targets.

#### Project and behavior

- Established pydocformatter as a standalone Ruff-style formatter, with the package version sourced from `src/pydocformatter/_version.py` and the project licensed under `GPL-3.0-or-later`.
- Moved builds from setuptools to Hatchling, added Python 3.14 support metadata, and replaced Black, isort, and mypy with Ruff and ty in the development workflow.
- Made automatic edits preserve untouched mixed line endings, UTF-8 byte order marks, final-newline state, source encodings, escaped non-ASCII spellings, and evaluated docstring values whenever a rule promises semantic equivalence.
- Changed rule and fixability selector resolution to Ruff-style source priority and specificity, with deterministic conflict handling and exact-rule restoration where supported.

### Fixed

- Corrected docstring parsing, source mapping, indentation, wrapping, delimiter placement, line-ending handling, and protected-structure behavior across tab-indented, simple-suite, escaped, concatenated, mixed-ending, and convention-specific docstrings.
- Corrected comment locations, empty separators, directive handling, syntax-sensitive trailing comments, line endings, and interactions between extracted trailing comments and surrounding standalone prose.
- Corrected parameter, return, yield, exception, class-attribute, and module-attribute documentation checks for aliases, shadowing, rebindings, variadic parameters, tuple unpacking, private packages, repeated entries, and suppressions.
- Corrected configuration validation, rule-selection precedence, per-file ignores, explicit configuration, glob bases, gitignore filtering, symlink traversal, duplicate physical files, and surrogate-escaped paths.
- Prevented quadratic or recursive wrapping behavior for long paragraphs and URLs, reduced repeated syntax and metadata work, and fixed final-iteration convergence handling.

### Removed

- Removed the v0.2.0 direct-formatter configuration and command surfaces superseded by the rule-based CLI and settings model.
- Removed the old `[tool.pydocformatter]` table, underscore setting aliases, regex file-selection semantics, and `docstring-parse-sphinx-fields` setting.
- Removed source-only internal compatibility wrappers and obsolete formatter, command, selector, and configuration helpers that were not part of the new stable interface.

---

## v0.2.0

Released 2026-05-01

### Added

- Initial preliminary release of `pydocformatter` as a simple direct formatter of comments and docstrings (no linting, no concept of rules, no complete CLI interface, and no complete/correct coverage of formatting fixes yet).
