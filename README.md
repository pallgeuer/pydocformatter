# pydocformatter

[![CI](https://github.com/pallgeuer/pydocformatter/actions/workflows/unit-tests.yml/badge.svg)](https://github.com/pallgeuer/pydocformatter/actions)
[![CI](https://github.com/pallgeuer/pydocformatter/actions/workflows/pre-commit-checks.yml/badge.svg)](https://github.com/pallgeuer/pydocformatter/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**pydocformatter** is a fork of [pyformatter](https://github.com/RikGhosh487/pyformatter), and provides Python formatting tools that automatically format your docstrings and comments according to configurable style guidelines. It consists of two formatters:

- **pydocfmt**: Formats Python docstrings with support for Google-style docstrings
- **pycommentfmt**: Formats Python comments to ensure proper line length and readability

---

## Key Features

### pydocfmt
- **Google-style docstring formatting**: Complete support for Google docstring conventions
- **Multi-line summary handling**: Intelligently formats long summaries that span multiple lines
- **Smart section parsing**: Properly handles Args, Returns, Raises, Examples, and other sections
- **Code block preservation**: Maintains formatting within Examples sections with automatic fencing
- **Type annotation support**: Handles parameter type annotations gracefully
- **Blank line management**: Ensures proper spacing between summary, description, and sections

### pycommentfmt
- **Intelligent comment wrapping**: Respects line length while preserving meaning
- **Inline vs block comment handling**: Different formatting strategies for different comment types
- **Special comment preservation**: Maintains pylint, mypy, and other tool directives
- **Smart spacing**: Ensures consistent spacing between code and comments

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
  - [Editor Integration](#editor-integration)
- [Security](#security)
- [Contributing](#contributing)
- [License](#license)

---

## Installation

Install pydocformatter via pip:

```bash
pip install pydocformatter
```

Or install from source:

```bash
git clone https://github.com/pallgeuer/pydocformatter.git
cd pydocformatter
pip install -e .
```

---

## Quick Start

Format all Python files in your project:

```bash
# Format docstrings
pydocfmt src/

# Format comments  
pycommentfmt src/

# Check formatting without making changes
pydocfmt --check src/
pycommentfmt --check src/
```

---

## Command Line Usage

### pydocfmt

Format Python docstrings with intelligent Google-style docstring support.

```bash
pydocfmt [OPTIONS] [FILES/DIRECTORIES]
```

**Options:**
- `--line-length INTEGER`: Maximum line length for docstrings (default: 88)
- `--check`: Check if files are formatted correctly without modifying them
- `--include TEXT`: Regex pattern for files to include
- `--exclude TEXT`: Regex pattern for files to exclude
- `-v, --verbose`: Show included and ignored files during file discovery
- `--help`: Show help message and exit

**Examples:**
```bash
# Format specific files
pydocfmt myfile.py another_file.py

# Format entire directory
pydocfmt src/

# Check formatting without changes
pydocfmt --check src/

# Custom line length
pydocfmt --line-length 100 src/

# Include/exclude patterns
pydocfmt --include ".*\.py$" --exclude "test_.*\.py$" src/
```

### pycommentfmt

Format Python comments to ensure proper line length and readability.

```bash
pycommentfmt [OPTIONS] [FILES/DIRECTORIES]
```

**Options:**
- `--line-length INTEGER`: Maximum line length for comments (default: 88)
- `--check`: Check if files are formatted correctly without modifying them
- `--include TEXT`: Regex pattern for files to include
- `--exclude TEXT`: Regex pattern for files to exclude
- `-v, --verbose`: Show included and ignored files during file discovery
- `--help`: Show help message and exit

**Examples:**
```bash
# Format specific files
pycommentfmt myfile.py

# Format entire directory
pycommentfmt src/

# Check formatting without changes
pycommentfmt --check src/

# Custom line length
pycommentfmt --line-length 79 src/
```

---

## Configuration

pydocformatter can be configured via `pyproject.toml`:

```toml
[tool.pydocfmt]
line_length = 88
exclude = '(^|/)(\.github|\.eggs|\.git|\.hg|\.mypy_cache|\.tox|\.venv|htmlcov|__pycache__|_build|buck-out|build|dist|tests/data)(/|$)'

[tool.pycommentfmt]
line_length = 88
exclude = '(^|/)(\.github|\.eggs|\.git|\.hg|\.mypy_cache|\.tox|\.venv|htmlcov|__pycache__|_build|buck-out|build|dist|tests/data)(/|$)'
```

**Configuration Options:**
- `line_length`: Maximum line length (default: 88)
- `exclude`: Regex pattern for files/directories to exclude

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
  args: [--exclude=tests/.*]
```

### Editor Integration

pydocformatter works great with:
- **VS Code**: Use with the Python extension
- **PyCharm**: Configure as an external tool
- **Vim/Neovim**: Integrate with formatting plugins

---

## Why pydocformatter?

- **Uncompromising**: Consistent formatting across your entire codebase
- **Fast**: Efficiently processes large codebases
- **Configurable**: Adapt to your team's style preferences
- **Reliable**: Extensively tested with comprehensive test suite
- **Simple**: Easy to integrate into existing workflows

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

**Quick Start for Contributors:**
1. Fork the repository and clone your fork
2. Set up the development environment: `pip install -e . --dependency-groups dev`
3. Install pre-commit hooks: `pre-commit install`
4. Make your changes and add tests
5. Run the test suite: `python -m unittest discover -s tests -v`
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

---
