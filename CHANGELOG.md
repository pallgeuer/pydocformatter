# Changelog

All notable changes to this project will be documented in this file.

The format is based on the ideas of [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) (e.g. Added, Changed, Removed, Fixed headings), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## Unreleased

### Added

- **CLI:**
  - Added `-v` / `--verbose` to `pydocfmt` and `pycommentfmt` to report all considered files during discovery, including included files and ignored files with include/exclude regex reasons.

### Changed

- **pydocfmt:**
  - `--check` output now includes docstring line locations, emitted once per file with compressed consecutive ranges.

- **pycommentfmt:**
  - `--check` output is now emitted once per file, with line numbers compressed into consecutive ranges (e.g. `223-224`) for lower-noise, more token-efficient diagnostics.

## v0.2.0 (2026-05-01)

### Changed

- **Fork:**
  - Moved from `pyformatter` and `python-doc-formatter` to `pydocformatter` in both cases
  - Many files and directories were renamed and subject to find-replace
  - Updated project architecture and bug fixes

## v0.1.1 (2025-07-31)

### Fixed

- **Formatting:**
  - Multi-line summaries are now properly treated as a single summary block instead of splitting into summary + description
  - Proper blank line spacing between summary and sections when no description is present
  - Improved formatting consistency for various docstring structures
  - Enhanced multi-line summary support in Google-style docstring formatting

## v0.1.0 (2025-07-31)

### Added

- **pydocfmt:** Command-line tool for formatting Python docstrings
  - Google-style docstring formatting support
  - Intelligent line wrapping for docstring sections (Args, Returns, Raises, Examples, etc.)
  - Preservation of code blocks in Examples sections with automatic fencing
  - Support for parameter descriptions with type annotations
  - Proper handling of multi-paragraph descriptions and lists
  - Configuration via `pyproject.toml` and command-line arguments

- **pycommentfmt:** Command-line tool for formatting Python comments
  - Automatic comment line wrapping based on configurable line length
  - Intelligent handling of inline comments vs. block comments
  - Preservation of special comments (noqa, type: ignore, pylint directives, etc.)
  - Smart spacing correction for inline comments
  - Preservation of code-style comment blocks
  - Long inline comment extraction to separate comment blocks

- **Core Infrastructure:**
  - Configurable line length (default: 88 characters)
  - Include/exclude file patterns with regex support
  - Check mode for CI/CD integration (non-destructive validation)
  - Recursive directory processing
  - TOML configuration support via `pyproject.tool.<formatter>`

- **CLI Features:**
  - `--check` flag for validation without modification
  - `--line-length` for custom line length configuration
  - `--include` and `--exclude` for file filtering
  - Exit code 1 when formatting issues are detected in check mode

- **Google-style Docstring Support:**
  - Args/Arguments section formatting with type annotations
  - Returns/Return section formatting
  - Raises/Raise section formatting with exception backticks
  - Yields/Yield section formatting
  - Examples section with automatic code block fencing
  - Attributes section formatting
  - Intelligent paragraph and list handling in descriptions

- **Comment Formatting Features:**
  - Block comment rewrapping with proper indentation preservation
  - Inline comment spacing standardization
  - Long inline comment extraction and placement above code
  - Special comment preservation (tool directives, pragmas, etc.)
  - Code comment block detection and preservation

- **Testing & Quality Assurance:**
  - Comprehensive test suite with 100% coverage for core functionality
  - Unit tests for both docstring and comment formatting
  - Edge case handling for malformed docstrings and comments
  - Test coverage for check mode and file modification detection

- **Developer Experience:**
  - Pre-commit hook configuration
  - Pre-commit hooks for external repositories (`.pre-commit-hooks.yaml`)
  - GitHub Actions CI/CD workflows
  - Black and isort integration
  - Development environment configuration

- **Documentation:**
  - Comprehensive README with usage examples
  - Configuration documentation
  - Before/after formatting examples
  - Integration guides for popular tools

---

- **Unreleased:** https://github.com/pallgeuer/pydocformatter/compare/v0.2.0...HEAD
- **v0.2.0:** Not directly comparable to v0.1.1 as forked to a new GitHub repository
- **v0.1.1:** https://github.com/RikGhosh487/pyformatter/compare/v0.1.0...v0.1.1
- **v0.1.0:** https://github.com/RikGhosh487/pyformatter/releases/tag/v0.1.0
