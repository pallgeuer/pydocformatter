# pydocformatter

[![CI](https://github.com/pallgeuer/pydocformatter/actions/workflows/unit-tests.yml/badge.svg)](https://github.com/pallgeuer/pydocformatter/actions)
[![CI](https://github.com/pallgeuer/pydocformatter/actions/workflows/pre-commit-checks.yml/badge.svg)](https://github.com/pallgeuer/pydocformatter/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**pydocformatter** is a fork (with very significant subsequent rewrites and development) of [pyformatter](https://github.com/RikGhosh487/pyformatter), which provides a Python formatter, `pydocfmt`, for formatting docstrings and comments. It is designed to be maximally compatible with [Ruff](https://docs.astral.sh/ruff/).

---

## Key Features

### Docstrings
- **Google-style docstring formatting:** Support for Google docstring conventions
- **Multi-line summary handling:** Formats long summaries that span multiple lines
- **Smart section parsing:** Handles Args, Returns, Raises, Examples, and other sections
- **Code block preservation:** Maintains formatting within Examples sections with automatic fencing
- **Type annotation support:** Handles parameter type annotations gracefully
- **Blank line management:** Ensures proper spacing between summary, description, and sections

### Comments
- **Comment wrapping:** Respects line length while preserving meaning
- **Inline and block comment handling:** Applies appropriate formatting to each comment shape
- **Special comment preservation:** Maintains pylint, mypy, noqa, pragma, and formatter directives
- **Smart spacing:** Ensures consistent spacing between code and comments

### File Selection and Configuration
- **Ruff-style file selection:** Supports glob-based include/exclude rules, default excludes, `force-exclude`, and `.gitignore`-aware discovery
- **Single config table:** Reads `[tool.pydocfmt]` from `pyproject.toml`
- **File-selection preview:** Reports included and ignored files, including excluded directories and gitignored paths
- **Line-aware check diagnostics:** Reports affected files with line numbers and compressed line ranges in check mode

---

## Installation

Install pydocformatter via pip:

```bash
pip install pydocformatter
```

---

## Quick Start

Check formatting without making changes:

```bash
pydocfmt check
```

Format all Python files in your project:

```bash
pydocfmt check --fix
```

---

## Command Line Usage

Format Python docstrings and comments:

```bash
pydocfmt check --fix [OPTIONS] [FILES/DIRECTORIES]
```

Check Python docstrings and comments without changing files:

```bash
pydocfmt check [OPTIONS] [FILES/DIRECTORIES]
```

If no files or directories are specified, `pydocfmt check` checks the current directory.

**Options:**
- `--help`: Show help message and exit
- `--fix`, `--no-fix`: Toggle applying fixes instead of only checking
- `-e`, `--exit-zero`: Exit with status code `0`, even when formatting violations are detected
- `--exit-non-zero-on-fix`: Exit with a non-zero status code if `--fix` modifies any files
- `--show-files`: Show file-selection decisions without formatting files
- `--show-settings`: Show resolved settings without formatting files
- `--line-length INTEGER`: Maximum line length for docstrings and comments (default: 88)
- `--line-ending {auto,lf,cr-lf,native}`: Line ending to use when rewriting files (default: auto)
- `--indent-style {space,tab}`: Indentation style for generated docstring sections (default: space)
- `--indent-width INTEGER`: Indentation width for generated docstring sections (default: 4)
- `--include GLOB`: Comma-separated glob pattern(s) for files to include
- `--extend-include GLOB`: Comma-separated additional glob pattern(s) for files to include
- `--exclude GLOB`: Comma-separated glob pattern(s) for files to exclude
- `--extend-exclude GLOB`: Comma-separated additional glob pattern(s) for files to exclude
- `--respect-gitignore`, `--no-respect-gitignore`: Toggle .gitignore-aware discovery (default: enabled)
- `--force-exclude`, `--no-force-exclude`: Apply include/exclude rules even to explicitly listed files
- `--experimental`, `--no-experimental`: Toggle the experimental rule-based formatter implementation (default: disabled)
- `--output-format {grouped}`: Output format for rule findings (default: grouped)

**Examples:**

```bash
# Format current directory
pydocfmt check --fix

# Format specific files
pydocfmt check --fix myfile.py another_file.py

# Format an entire directory
pydocfmt check --fix src/

# Check formatting without changes
pydocfmt check src/

# Custom line length
pydocfmt check --fix --line-length 100 src/

# Custom rewritten line ending
pydocfmt check --fix --line-ending lf src/

# Custom generated docstring indentation
pydocfmt check --fix --indent-style tab --indent-width 4 src/

# Include/exclude patterns
pydocfmt check --fix src/ --include "*.py" --exclude "test_*.py"

# Multiple include globs in one option value
pydocfmt check --fix src/ --include "*.py,*.pyi"

# Show resolved settings
pydocfmt check --show-settings

# Show included and ignored files
pydocfmt check --show-files src/

# Apply include, exclude, and gitignore rules to explicit files too
pydocfmt check --fix --force-exclude generated.py src/
```

---

## Configuration

pydocformatter can be configured via `pyproject.toml` (example):

```toml
[tool.pydocfmt]
line-length = 88
line-ending = "auto"
indent-style = "space"
indent-width = 4
include = ["*.py", "*.pyi", "*.pyw"]
extend-exclude = ["generated"]
respect-gitignore = true
force-exclude = false
experimental = false
output-format = "grouped"
select = ["ALL"]
ignore = []
fixable = ["ALL"]
unfixable = []

[tool.pydocfmt.per-file-ignores]
"tests/*.py" = ["PCF001"]
```

**Configuration Options:**
- `line-length`: Maximum line length for docstrings and comments (default: 88)
- `line-ending`: Line ending to use when rewriting files; one of `"auto"`, `"lf"`, `"cr-lf"`, or `"native"` (default: `"auto"`)
- `indent-style`: Generated docstring section indentation style; one of `"space"` or `"tab"` (default: `"space"`)
- `indent-width`: Generated docstring section indentation width (default: 4)
- `include`: Glob patterns for files to include
- `extend-include`: Additional include glob patterns
- `exclude`: Glob patterns for files/directories to exclude
- `extend-exclude`: Additional exclude glob patterns
- `respect-gitignore`: Respect `.gitignore` during file discovery (default: `true`)
- `force-exclude`: Apply include/exclude rules to explicitly listed files (default: `false`)
- `experimental`: Use the experimental rule-based formatter implementation (default: `false`)
- `output-format`: Output format for rule findings; currently only `"grouped"` is supported (default: `"grouped"`)
- `select`: Rule selectors to enable (default: `["ALL"]`)
- `extend-select`: Additional rule selectors to enable
- `ignore`: Rule selectors to ignore
- `fixable`: Rule selectors eligible for automatic fixes (default: `["ALL"]`)
- `extend-fixable`: Additional rule selectors eligible for automatic fixes
- `unfixable`: Rule selectors ineligible for automatic fixes
- `per-file-ignores`: File-pattern-specific ignored rule selectors
- `extend-per-file-ignores`: Additional file-pattern-specific ignored rule selectors

Settings are resolved as defaults, then `[tool.pydocfmt]`, then command-line options. The highest-precedence specified value wins for each key, including `extend-include` and `extend-exclude`.

For the full file-selection contract, see [File Selection Compatibility Specification](docs/file_selection_spec.md).

---

## Examples

### Before

```python
def calculate_mean(numbers):
    """Calculate the arithmetic mean of a list of numbers.
    
    This function calculates the arithmetic mean of a list of numbers and returns the result as a float value."""
    
    # This is a very long comment that exceeds the line length limit and should be wrapped to multiple lines for better readability
    return sum(numbers) / len(numbers)
```

### After

```python
def calculate_mean(numbers):
    """
    Calculate the arithmetic mean of a list of numbers.
    
    This function calculates the arithmetic mean of a list of numbers and returns the
    result as a float value.
    """
    
    # This is a very long comment that exceeds the line length limit and should be
    # wrapped to multiple lines for better readability
    return sum(numbers) / len(numbers)
```

---

## Integration

### Pre-commit

Add pydocformatter to your `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/pallgeuer/pydocformatter
    rev: v0.3.0
    hooks:
      - id: pydocfmt
        args: [--line-length=88]
```

**Available hooks:**
- `pydocfmt`: Format docstrings and comments (modifies files)
- `pydocfmt-check`: Check docstring and comment formatting (read-only)

**Common configurations:**

```yaml
# Basic usage
- id: pydocfmt

# Custom line length
- id: pydocfmt
  args: [--line-length=100]

# Check only (for CI)
- id: pydocfmt-check

# With file exclusions
- id: pydocfmt
  args: [--exclude, tests]
```

---

## Why pydocformatter?

- **Compatible:** Designed to work alongside [Ruff](https://docs.astral.sh/ruff/)
- **Uncompromising:** Consistent formatting across your entire codebase
- **Fast:** Efficiently processes large codebases
- **Configurable:** Adapt to your team's style preferences
- **Reliable:** Extensively tested with comprehensive test suite
- **Simple:** Easy to integrate into existing workflows

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

Inspired by the excellent work of:
- [pyformatter](https://github.com/RikGhosh487/pyformatter) - Forked with very significant subsequent rewrites and development
- [Black](https://github.com/psf/black) - The uncompromising Python code formatter
- [isort](https://github.com/PyCQA/isort) - A Python utility to sort imports
- [docformatter](https://github.com/PyCQA/docformatter) - Formats docstrings to follow conventions
