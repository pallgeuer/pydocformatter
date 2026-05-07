# pydocformatter

[![CI](https://github.com/pallgeuer/pydocformatter/actions/workflows/unit-tests.yml/badge.svg)](https://github.com/pallgeuer/pydocformatter/actions)
[![CI](https://github.com/pallgeuer/pydocformatter/actions/workflows/pre-commit-checks.yml/badge.svg)](https://github.com/pallgeuer/pydocformatter/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**pydocformatter** is a fork of [pyformatter](https://github.com/RikGhosh487/pyformatter), and provides Python formatting tools that automatically format your docstrings and comments according to configurable style guidelines. It consists of two formatters:

- **pydocfmt:** Formats Python docstrings with support for Google-style docstrings
- **pycommentfmt:** Formats Python comments to ensure proper line length and readability

---

## Key Features

### pydocfmt
- **Google-style docstring formatting:** Complete support for Google docstring conventions
- **Multi-line summary handling:** Intelligently formats long summaries that span multiple lines
- **Smart section parsing:** Properly handles Args, Returns, Raises, Examples, and other sections
- **Code block preservation:** Maintains formatting within Examples sections with automatic fencing
- **Type annotation support:** Handles parameter type annotations gracefully
- **Blank line management:** Ensures proper spacing between summary, description, and sections

### pycommentfmt
- **Intelligent comment wrapping:** Respects line length while preserving meaning
- **Inline vs block comment handling:** Different formatting strategies for different comment types
- **Special comment preservation:** Maintains pylint, mypy, and other tool directives
- **Smart spacing:** Ensures consistent spacing between code and comments

### File Selection and Configuration
- **Ruff-style file selection:** Supports glob-based include/exclude rules, default excludes, `force-exclude`, and `.gitignore`-aware discovery
- **Shared and tool-specific config:** Reads `[tool.pydocformatter]` plus per-tool overrides from `pyproject.toml`
- **Verbose discovery output:** Reports included and ignored files, including excluded directories and gitignored paths
- **Line-aware check diagnostics:** Reports affected files with line numbers and compressed line ranges in check mode

## Key Improvements over pyformatter

- Project architecture updates and bug fixes

---

## Table of Contents

- [Key Features](#key-features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Command Line Usage](#command-line-usage)
  - [pydocfmt](#pydocfmt)
  - [pycommentfmt](#pycommentfmt)
- [Configuration](#configuration)
- [Examples](#examples)
- [Integration](#integration)
  - [Pre-commit](#pre-commit)
- [Security](#security)
- [Contributing](#contributing)
- [License](#license)

---

## Installation

Install pydocformatter via pip:

```bash
pip install pydocformatter
```

---

## Quick Start

Format all Python files in your project:

```bash
# Format docstrings
pydocfmt

# Format comments
pycommentfmt

# Check formatting without making changes
pydocfmt --check
pycommentfmt --check
```

---

## Command Line Usage

### pydocfmt

Format Python docstrings with intelligent Google-style docstring support.

```bash
pydocfmt [OPTIONS] [FILES/DIRECTORIES]
```

If no files or directories are specified, `pydocfmt` formats the current directory.

**Options:**
- `--line-length INTEGER`: Maximum line length for docstrings (default: 88)
- `--indent-style {space,tab}`: Indentation style for generated docstring sections (default: space)
- `--indent-width INTEGER`: Indentation width for generated docstring sections (default: 4)
- `--check`: Check if files are formatted correctly without modifying them
- `--include GLOB [GLOB ...]`: Glob pattern(s) for files to include
- `--extend-include GLOB [GLOB ...]`: Additional glob pattern(s) for files to include
- `--exclude GLOB [GLOB ...]`: Glob pattern(s) for files to exclude
- `--extend-exclude GLOB [GLOB ...]`: Additional glob pattern(s) for files to exclude
- `-v, --verbose`: Show included and ignored files during file discovery
- `--respect-gitignore`, `--no-respect-gitignore`: Toggle .gitignore-aware discovery (default: enabled)
- `--force-exclude`, `--no-force-exclude`: Apply include/exclude rules even to explicitly listed files
- `--help`: Show help message and exit

**Examples:**
```bash
# Format specific files
pydocfmt myfile.py another_file.py

# Format entire directory
pydocfmt src/

# Format current directory
pydocfmt

# Check formatting without changes
pydocfmt --check src/

# Custom line length
pydocfmt --line-length 100 src/

# Custom generated docstring indentation
pydocfmt --indent-style tab --indent-width 4 src/

# Include/exclude patterns
pydocfmt src/ --include "*.py" --exclude "test_*.py"

# Multiple include globs in one option
pydocfmt src/ --include "*.py" "*.pyi"

# Option values before positional paths
pydocfmt --include "*.py" "*.pyi" -- src/

# Show included and ignored files
pydocfmt -v src/

# Apply include, exclude, and gitignore rules to explicit files too
pydocfmt --force-exclude generated.py src/
```

### pycommentfmt

Format Python comments to ensure proper line length and readability.

```bash
pycommentfmt [OPTIONS] [FILES/DIRECTORIES]
```

If no files or directories are specified, `pycommentfmt` formats the current directory.

**Options:**
- `--line-length INTEGER`: Maximum line length for comments (default: 88)
- `--check`: Check if files are formatted correctly without modifying them
- `--include GLOB [GLOB ...]`: Glob pattern(s) for files to include
- `--extend-include GLOB [GLOB ...]`: Additional glob pattern(s) for files to include
- `--exclude GLOB [GLOB ...]`: Glob pattern(s) for files to exclude
- `--extend-exclude GLOB [GLOB ...]`: Additional glob pattern(s) for files to exclude
- `-v, --verbose`: Show included and ignored files during file discovery
- `--respect-gitignore`, `--no-respect-gitignore`: Toggle .gitignore-aware discovery (default: enabled)
- `--force-exclude`, `--no-force-exclude`: Apply include/exclude rules even to explicitly listed files
- `--help`: Show help message and exit

**Examples:**
```bash
# Format specific files
pycommentfmt myfile.py

# Format entire directory
pycommentfmt src/

# Format current directory
pycommentfmt

# Check formatting without changes
pycommentfmt --check src/

# Custom line length
pycommentfmt --line-length 79 src/

# Include/exclude patterns and verbose file discovery
pycommentfmt -v src/ --include "*.py" "*.pyi" --exclude "generated"
```

---

## Configuration

pydocformatter can be configured via `pyproject.toml`:

```toml
[tool.pydocformatter]
line-length = 88
indent-style = "space"
indent-width = 4
respect-gitignore = true
force-exclude = false
include = ["*.py", "*.pyi", "*.pyw"]
extend-exclude = ["generated"]

[tool.pydocformatter.pydocfmt]
line-length = 100

[tool.pydocformatter.pycommentfmt]
extend-exclude = ["legacy_comments.py"]
```

**Configuration Options:**
- `line-length`: Maximum line length (default: 88)
- `indent-style`: Generated docstring section indentation style for `pydocfmt`; one of `"space"` or `"tab"` (default: `"space"`)
- `indent-width`: Generated docstring section indentation width for `pydocfmt` (default: 4)
- `respect-gitignore`: Respect `.gitignore` during file discovery (default: `true`)
- `force-exclude`: Apply include/exclude rules to explicitly listed files (default: `false`)
- `include`: Glob patterns for files to include
- `extend-include`: Additional include glob patterns
- `exclude`: Glob patterns for files/directories to exclude
- `extend-exclude`: Additional exclude glob patterns

Settings are resolved as defaults, then shared table, then tool-specific table, then command-line options. The highest-precedence specified value wins for each key, including `extend-include` and `extend-exclude`.

`indent-style` and `indent-width` are used by `pydocfmt` only. They may be configured in the shared table or `[tool.pydocformatter.pydocfmt]`; `pycommentfmt` does not accept them as CLI options or in `[tool.pydocformatter.pycommentfmt]`.

For the full file-selection contract, including Ruff compatibility deltas and explicit file behavior, see [File Selection Compatibility Specification](docs/file-selection-spec.md).

---

## Examples

### Before and After: pydocfmt

**Before:**
```python
def calculate_mean(numbers):
    """Calculate the arithmetic mean of a list of numbers.
    
    This function calculates the arithmetic mean of a list of numbers and returns the result as a float value."""
    return sum(numbers) / len(numbers)
```

**After:**
```python
def calculate_mean(numbers):
    """Calculate the arithmetic mean of a list of numbers.
    
    This function calculates the arithmetic mean of a list of numbers and returns the
    result as a float value.
    """
    return sum(numbers) / len(numbers)
```

### Before and After: pycommentfmt

**Before:**
```python
# This is a very long comment that exceeds the line length limit and should be wrapped to multiple lines for better readability
x = 42
```

**After:**
```python
# This is a very long comment that exceeds the line length limit and should be
# wrapped to multiple lines for better readability
x = 42
```

---

## Integration

### Pre-commit

Add pydocformatter to your `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/pallgeuer/pydocformatter
    rev: v0.2.0  # Use the ref you want to point at
    hooks:
      - id: pydocfmt
        args: [--line-length=88]
      - id: pycommentfmt
        args: [--line-length=88]
```

**Available hooks:**
- `pydocfmt`: Format docstrings (modifies files)
- `pydocfmt-check`: Check docstring formatting (read-only)
- `pycommentfmt`: Format comments (modifies files)
- `pycommentfmt-check`: Check comment formatting (read-only)

**Common configurations:**
```yaml
# Basic usage
- id: pydocfmt
- id: pycommentfmt

# Custom line length
- id: pydocfmt
  args: [--line-length=100]

# Check only (for CI)
- id: pydocfmt-check
- id: pycommentfmt-check

# With file exclusions
- id: pydocfmt
  args: [--exclude, tests]
```

---

## Why pydocformatter?

- **Uncompromising:** Consistent formatting across your entire codebase
- **Fast:** Efficiently processes large codebases
- **Configurable:** Adapt to your team's style preferences
- **Reliable:** Extensively tested with comprehensive test suite
- **Simple:** Easy to integrate into existing workflows

---

## Security

For general security best practices when using pydocformatter:
- Always review changes made by pydocformatter before committing
- Keep pydocformatter updated to the latest version
- When processing untrusted code, consider running pydocformatter in an isolated environment

---

## Contributing

Contributions are welcome! We appreciate bug reports, feature requests, documentation improvements, and code contributions.

For detailed information on how to contribute, please see our [Contributing Guide](CONTRIBUTING.md).
For release history, see the [Changelog](CHANGELOG.md).

**Quick Start for Contributors:**
1. Fork the repository and clone your fork
2. Set up the development environment: `uv sync --group dev`
3. Install pre-commit hooks: `uv run pre-commit install`
4. Make your changes and add tests
5. Run the test suite: `uv run pytest -q`
6. Submit a pull request

For bug reports and feature requests, please [open an issue](https://github.com/pallgeuer/pydocformatter/issues).

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

Inspired by the excellent work of:
- [pyformatter](https://github.com/RikGhosh487/pyformatter) - Forked
- [Black](https://github.com/psf/black) - The uncompromising Python code formatter
- [isort](https://github.com/PyCQA/isort) - A Python utility to sort imports
- [docformatter](https://github.com/PyCQA/docformatter) - Formats docstrings to follow conventions
