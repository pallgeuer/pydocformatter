# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and pydocformatter follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## Release diffs

- **Unreleased:** <https://github.com/pallgeuer/pydocformatter/compare/v1.0.0...HEAD>
- **v1.0.0:** <https://github.com/pallgeuer/pydocformatter/compare/v0.2.0...v1.0.0>
- **v0.2.0:** <https://github.com/pallgeuer/pydocformatter/releases/tag/v0.2.0>

---

## Unreleased

### Added

- **Persistent caching:**
  - Added strict persistent clean-proof caching for disk-backed checks and fixes, with complete source hashing, semantic analysis-setting and final-rule-code invalidation, shared invocation-local analysis fingerprints, engine/path invalidation, miss-only process execution, bounded parent-side probes, and source-free warm results.
  - Added `cache` and `cache-dir` settings, `--cache`/`--no-cache`, `--cache-dir`, opt-in `--cache-stats`, safe project cache self-pruning, and the ownership-checked `pydocfmt clean` command with its own `--cache-dir` override.
  - Added a dedicated public cache reference covering validation, population, mode reuse, storage, cleanup, failures, trust, statistics, and performance expectations.

### Changed

- **Command performance:**
  - Reused successfully parsed configuration documents, closest-config discovery results, and resolved source profiles within each invocation.
  - Reduced directory-walk resolver calls and repeated cache-root, glob-segment, and literal-pattern preparation without changing file-selection semantics.
- **Caching performance:**
  - Reused resolved package ancestry and canonical sibling path encodings within each invocation while preserving exact cache identities and rule-facing path semantics.
  - Batched complete-source proof validation with worker-proportional task submission and pending futures while preserving full-content hashing, ordered results, and the all-hit no-analysis-pool path.
  - Released raw input bytes before parsing and rule execution, and skipped metadata collection when clean source snapshots are not requested.
  - Derived normal-wheel implementation identities from complete trusted distribution-manifest metadata only when it identifies the imported package root, with complete source-tree hashing retained for editable installs, source runs, mismatched installations, and unusable manifests.
  - Reduced worker requests to immutable path-specific rule execution plans, returned frozen batch results, made probe and persistence outcomes explicit, aggregated cache statistics once per phase, and touched each engine retention row once with its maximum observed day.
  - Deferred engine, path-builder, and store construction until at least one selected file is cacheable, so disabled and wholly uncacheable runs avoid cache-only fingerprint work.
- **Rule and path contracts:**
  - Centralized package, module, symlink-target, and public/private path semantics in a precomputed rule context shared with cache invalidation.
  - Made rule cache dependencies explicit and fail closed, with every built-in rule audited as file-local and new external dependency kinds requiring canonical invalidation before cache use.
- **Configuration:**
  - Extended settings profiles with the auto-discovered project root so default cache locations are stable across nested paths and relocated workspaces.

### Fixed

- **Persistent caching:**
  - Prevented a configured cache directory equal to the traversal root from suppressing all input files; an unusable shared or project-root cache now degrades without changing file selection.
  - Fingerprinted symlinked implementation sources and targets without disabling caching for valid symlinked package trees, while rejecting incomplete or cyclic identities.
  - Reused the frozen source-path context during rule execution so concurrent package-marker changes cannot misalign analysis and proof identities.
  - Limited internal-cache pruning to the safe current-working-directory run root so nested or non-empty unowned cache settings cannot hide source files.
  - Reported cache cleanup filesystem failures as contextual status-2 errors without leaking tracebacks, including safe retry guidance after partial cleanup.
  - Required exact ownership before corrupt or incompatible databases can be quarantined or replaced, preserved unowned databases and sidecars, and limited cleanup to numeric version directories and their quarantine files.
  - Required the ownership tag to be a non-symlinked regular file for lookup and every mutation, while retaining the intentional ability to claim an empty untagged directory only during cache creation.
  - Serialized cache writes, recovery, quarantine, pruning, and cleanup with a retained native file lock; writers now revalidate the current database after locking so stale lookup state cannot replace newer proofs.
  - Kept transaction rollback and connection closure inside the mutation-lock lifetime, and sampled each quarantine candidate through one non-following metadata read before retention decisions.
  - Preserved committed WAL data by checkpointing readable incompatible databases and quarantining main, WAL, and shared-memory files as recoverable groups with group-aware retention and partial-move rollback.
  - Counted engine-identity, shared-analysis, path-fingerprint, malformed-row, lookup, lock, recovery, and commit failures through explicit typed outcomes while keeping valid path-context mismatches as ordinary misses.
  - Prevented filesystem roots from contributing an empty package component to rule and cache path semantics.
  - Separated list identities from tuples and other canonical values, rejected non-finite floats, and made normal-wheel manifest identities complete and unambiguous.
  - Reported a missing or non-directory immediate cache parent exactly once while preserving uncached findings, fixes, and status.
  - Pruned the configured owned cache directory when traversal reaches it through a physical parent alias, while continuing to reject a symlinked final cache component.
  - Made retention days follow backward wall-clock changes so disposable cache entries are reanalyzed earlier instead of being pinned by future timestamps.
- **Configuration:**
  - Rejected NUL characters in `cache-dir` values from programmatic, inline, TOML, and command-line settings with contextual status-2 errors.
- **Documentation:**
  - Changed the README links for Contributing, Changelog, and License to absolute documentation-site targets so they resolve correctly in package descriptions rendered by PyPI.

### Removed

- **Internal cleanup:**
  - Removed the full selector and per-file matcher payload from workers, duplicate path-fingerprint helper APIs, contradictory optional cache-evidence states, the parallel cache-role map, duplicate store-side clean-proof validators, the unused source-context display field, the test-only settings-discovery wrapper, cached glob-pattern tuples, optional rule-context path fallbacks, duplicate formatter and rule-runner compatibility entry points, and pass-through CLI worker wrappers.

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
