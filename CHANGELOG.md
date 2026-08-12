# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and pydocformatter follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## Release diffs

- **Unreleased:** <https://github.com/pallgeuer/pydocformatter/compare/v1.1.0...HEAD>
- **v1.1.0:** <https://github.com/pallgeuer/pydocformatter/compare/v1.0.0...v1.1.0>
- **v1.0.0:** <https://github.com/pallgeuer/pydocformatter/compare/v0.2.0...v1.0.0>
- **v0.2.0:** <https://github.com/pallgeuer/pydocformatter/releases/tag/v0.2.0>

---

## Unreleased

### Changed

#### Developer documentation

- Standardized changelog categories as non-bulleted level-four headings, condensed the historical v1.1.0 notes into external release outcomes, and added an explicit editorial checkpoint to the release runbook.

---

## v1.1.0

Released 2026-08-13

**Compatibility warning:** This minor release intentionally includes a breaking reassignment of all PCF rule codes. Existing code-based selectors and suppressions must migrate using the table below because the previous codes are not retained as aliases; canonical rule-name selectors remain unchanged.

### Added

#### Persistent caching

- Added strict persistent clean-proof caching for disk-backed checks and fixes. Cache reuse verifies complete source contents, effective settings, selected rules, implementation identity, and package-path semantics before skipping analysis.
- Added the `cache` and `cache-dir` settings, `--cache`/`--no-cache`, `--cache-dir`, opt-in `--cache-stats`, safe project-cache pruning, and the ownership-checked `pydocfmt clean` command.

#### Rule selection and suppressions

- Added exact canonical rule-name selectors across configuration, CLI options, per-file ignores, fixability controls, explicit-selection policies, and source suppressions.
- Added opt-in PCF102 and PCF103 policies for requiring code-based or name-based selectors in pydocfmt and Ruff suppression comments, with safe conversions where possible.

#### Docstring and comment diagnostics

- Added PDF004 and PCF201 for suspicious bidirectional, invisible-format, control, and separator characters, including exact fixes for nonbreaking indentation spaces.
- Added PDF212 and PDF213 for missing summaries and configurable placeholder docstrings.
- Added PDF312, PDF720, PDF721, and PDF723 for content-free entry descriptions and missing exception, warning, or method descriptions.
- Added PDF414, PDF415, and PDF418 for malformed convention entries, convention indentation, and malformed reStructuredText directive introducers.
- Added PDF416 and PDF417 for convention type spelling and NumPy return-entry structure.
- Added PDF526, PDF527, and PDF528 for parameter order, variadic-marker style, and attribute documentation order.
- Added PDF722 for reStructuredText type fields without corresponding value fields.

#### Configuration

- Added `docstring-placeholder-markers` to configure PDF213, including an empty-list opt-out.
- Added `docstring-include-assertion-errors` so PDF506 and PDF507 can optionally account for syntactic `assert` statements.

### Changed

#### Breaking PCF rule-code reassignment

- Reorganized PCF codes into general comment formatting (`PCF0xx`), directives and suppressions (`PCF1xx`), and ASCII/Unicode character policies (`PCF2xx`). Canonical rule-name selectors remain unchanged, while old code selectors are not retained as aliases.

| Previous code | New code | Rule name                            |
|---------------|----------|--------------------------------------|
| `PCF001`      | `PCF000` | `standalone-comment-formatting`      |
| `PCF002`      | `PCF001` | `trailing-comment-spacing`           |
| `PCF004`      | `PCF002` | `trailing-comment-extraction`        |
| `PCF003`      | `PCF100` | `comment-directive-normalization`    |
| `PCF006`      | `PCF101` | `unused-suppression`                 |
| `PCF008`      | `PCF102` | `rule-codes-in-suppression-comments` |
| `PCF009`      | `PCF103` | `rule-names-in-suppression-comments` |
| `PCF005`      | `PCF200` | `comment-ascii-only`                 |
| `PCF007`      | `PCF201` | `comment-suspicious-unicode`         |

#### Platform compatibility

- Documented official CPython 3.11-3.14 support on Ubuntu 20.04 and newer and macOS 14 and newer, best-effort support for other POSIX Linux systems, and no native Windows or WSL support.
- Clarified that PyPy and GraalPy are intended but unverified because of LibCST native-parser packaging, while Jython and IronPython are unsupported.

#### Rule behavior and selection

- Marked every current built-in rule as stable since 1.1.0.
- Made exact code and canonical-name selectors resolve to one rule identity, allowed stronger selectors to override incompatible weaker selections, and made equal-strength conflicts deterministic.
- Accepted mixed-case canonical names in pydocfmt suppressions, deduplicated equivalent code/name selectors without changing coverage, and extended PDF suppression over complete implicitly concatenated docstrings.
- Made strict trailing-period rules mutually exclusive with their terminal-punctuation alternatives and made overlapping attribute-documentation placement policies conflict-free under broad convention profiles.

#### Formatting and diagnostics

- Made docstring and comment reflow preserve recognized Markdown and reStructuredText inline markup, hard breaks, source continuations, fenced structures, and ambiguous constructs that cannot be rewritten safely.
- Added safe fixes for deterministic convention separators and indentation, convention type spelling, punctuation, variadic markers, and missing convention types recoverable from code annotations.
- Included proven immutable literal `__slots__` members in attribute documentation rules and kept raised exceptions and emitted warnings as distinct entry families.
- Required reStructuredText value fields for documentation coverage while retaining orphan type fields for type, duplicate, empty, extraneous, and PDF722 diagnostics.
- Increased the automatic-fix iteration limit from 20 to 30 and stopped earlier when an exact source state repeats, with cycle details in the diagnostic.

#### Performance

- Improved warm-cache, file-discovery, configuration-resolution, convention-parsing, suppression, and large-inventory rule performance without changing results.

### Fixed

#### Source preservation and fix convergence

- Corrected source-position remapping after edits so comments, blank lines, form feeds, escapes, mixed line endings, string prefixes, and untouched source spelling remain stable.
- Eliminated fix cycles and overlapping edits across docstring layout, reflow, entry spacing, convention indentation, punctuation, and closing-delimiter rules.
- Rolled back partial fixes when exact source alignment cannot be proven and report only fixes that survive convergence.

#### Convention parsing and diagnostics

- Corrected malformed Google, NumPy, and reStructuredText entry detection, including nested types and signatures, field arity, indentation, escaped logical lines, warning sections, and ambiguous prose-like candidates.
- Corrected convention type normalization, parameter and attribute ordering, entry descriptions, exception and warning normalization, literal `__slots__` handling, and structured-content punctuation boundaries.
- Corrected docstring reflow and whitespace behavior around lists, links, images, directives, literal blocks, tables, headings, block quotes, doctests, code fences, and Markdown hard breaks.
- Corrected suspicious-Unicode handling so formatting preserves reportable hazards and avoids unsafe reconstruction.

#### Suppressions and configuration

- Corrected directive parsing, duplicate selectors, invalid selector preservation, concatenated-string suppression coverage, and unused-suppression reporting.
- Corrected placeholder-marker validation, project-root handling for default caches, and contextual rejection of NUL characters in `cache-dir`.

#### Persistent caching

- Hardened cache ownership, concurrent access, recovery, retention, symlink handling, and cleanup so failures degrade to uncached analysis without hiding files or replacing unowned data.
- Corrected cache behavior for project-root cache directories, aliased paths, symlinked installations, filesystem roots, clock changes, missing parents, and concurrent writers.

#### Cross-platform behavior and packaging

- Corrected file identity and path handling for case-insensitive paths, hard links, symlinks, surrogate-escaped names, and missing Git executables.
- Corrected parsing, source fixes, cache cleanup, and parallel execution across supported Python, glibc, musl, x64, ARM64, Intel macOS, and Apple silicon environments.
- Excluded maintainer-only release and temporary-plan files from source distributions and corrected README links rendered on PyPI.

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
