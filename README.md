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
- **Single config table:** Reads `[tool.pydocfmt]` from auto-discovered `pyproject.toml` files
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
- `--diff`: Print a unified diff for fixes without writing changed files
- `--show-settings`: Show resolved settings without formatting files
- `--show-rules`: Show active rules without formatting files
- `--show-files`: Show file-selection decisions without formatting files
- `-o`, `--output-file FILE`: Write diagnostics and show output to a file instead of stdout

**Formatting:**
- `--output-format {grouped}`: Output format for rule findings (default: grouped)
- `--legacy`, `--no-legacy`: Toggle the legacy formatter implementation (default: disabled)
- `--line-length LENGTH`: Maximum line length for docstrings and comments (default: 88)
- `--line-ending {auto,lf,cr-lf,native}`: Line ending to use when rewriting files (default: auto)
- `--indent-style {space,tab}`: Indentation style for generated docstring sections (default: space)
- `--indent-width WIDTH`: Generated docstring indentation width and comment tab width (default: 4)

**Docstring formatting:**
- `--docstring-convention {none,google,numpy,pep257}`: Convention used to parse semantic docstring sections (default: none)
- `--docstring-parse-list-items`, `--no-docstring-parse-list-items`: Toggle parsing docstring list items (default: enabled)
- `--docstring-parse-headings`, `--no-docstring-parse-headings`: Toggle parsing docstring headings (default: enabled)
- `--docstring-parse-doctests`, `--no-docstring-parse-doctests`: Toggle parsing and protecting doctest regions (default: enabled)
- `--docstring-parse-code-fences`, `--no-docstring-parse-code-fences`: Toggle parsing and protecting fenced code blocks (default: enabled)
- `--docstring-parse-block-quotes`, `--no-docstring-parse-block-quotes`: Toggle parsing Markdown block quotes (default: enabled)
- `--docstring-parse-tables`, `--no-docstring-parse-tables`: Toggle parsing and protecting tables (default: enabled)
- `--docstring-parse-directives`, `--no-docstring-parse-directives`: Toggle parsing reStructuredText directives (default: enabled)
- `--docstring-parse-literal-blocks`, `--no-docstring-parse-literal-blocks`: Toggle parsing reStructuredText literal blocks (default: enabled)
- `--docstring-parse-sphinx-fields`, `--no-docstring-parse-sphinx-fields`: Toggle parsing Sphinx fields (default: enabled)

**Comment formatting:**
- `--comment-join-standalone-lines`, `--no-comment-join-standalone-lines`: Toggle joining standalone prose lines before wrapping (default: disabled)
- `--comment-format-list-items`, `--no-comment-format-list-items`: Toggle list-item detection and hanging-indented reflow (default: enabled)
- `--comment-preserve-headings`, `--no-comment-preserve-headings`: Toggle preserving Markdown and reStructuredText headings (default: enabled)
- `--comment-preserve-doctests`, `--no-comment-preserve-doctests`: Toggle preserving standalone doctest regions (default: enabled)
- `--comment-preserve-code-fences`, `--no-comment-preserve-code-fences`: Toggle preserving fenced code regions (default: enabled)
- `--comment-format-block-quotes`, `--no-comment-format-block-quotes`: Toggle prefix-preserving block-quote reflow (default: enabled)
- `--comment-preserve-tables`, `--no-comment-preserve-tables`: Toggle preserving detected Markdown and reStructuredText tables (default: enabled)
- `--comment-preserve-directives`, `--no-comment-preserve-directives`: Toggle preserving reStructuredText directives and their indented bodies (default: enabled)
- `--comment-detect-code`, `--no-comment-detect-code`: Toggle the disabled-code indentation and leading-keyword heuristic (default: disabled)
- `--comment-detect-statements`, `--no-comment-detect-statements`: Toggle parseable Python statement detection (default: enabled)
- `--comment-detect-expressions`, `--no-comment-detect-expressions`: Toggle nontrivial Python expression detection (default: disabled)

**Rule Selection:**
- `--select RULE`: Comma-separated rule selector(s) to enable
- `--ignore RULE`: Comma-separated rule selector(s) to ignore
- `--extend-select RULE`: Comma-separated additional rule selector(s) to enable
- `--per-file-ignores RULE_TOML`: TOML inline table mapping file patterns to ignored rule selectors
- `--extend-per-file-ignores RULE_TOML`: TOML inline table mapping file patterns to additional ignored rule selectors
- `--fixable RULE`: Comma-separated rule selector(s) eligible for automatic fixes
- `--unfixable RULE`: Comma-separated rule selector(s) ineligible for automatic fixes
- `--extend-fixable RULE`: Comma-separated additional rule selector(s) eligible for automatic fixes

**File Selection:**
- `--include GLOB`: Comma-separated glob pattern(s) for files to include
- `--extend-include GLOB`: Comma-separated additional glob pattern(s) for files to include
- `--exclude GLOB`: Comma-separated glob pattern(s) for files to exclude
- `--extend-exclude GLOB`: Comma-separated additional glob pattern(s) for files to exclude
- `--respect-gitignore`, `--no-respect-gitignore`: Toggle .gitignore-aware discovery (default: enabled)
- `--force-exclude`, `--no-force-exclude`: Apply exclude rules even to explicitly listed files

**Miscellaneous:**
- `--stdin-filename FILENAME`: File name to use when checking or fixing source from stdin
- `-e`, `--exit-zero`: Exit with status code `0`, even when formatting violations are detected
- `--exit-non-zero-on-fix`: Exit with a non-zero status code if `--fix` modifies any files

**Global Options:**
- `--config CONFIG`: Path to a TOML configuration file, or a TOML `<KEY> = <VALUE>` setting override
- `--isolated`: Ignore auto-discovered configuration files

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

# Check source from stdin
cat myfile.py | pydocfmt check - --stdin-filename myfile.py

# Write diagnostics to a file
pydocfmt check src/ --output-file pydocfmt.txt

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

# Show active rules
pydocfmt check --show-rules

# Override one setting without editing pyproject.toml
pydocfmt check --config "line-length = 100" src/

# Use a dedicated config file
pydocfmt check --config pydocfmt.toml src/

# Ignore pyproject.toml while applying an inline override
pydocfmt check --isolated --config "line-length = 100" src/

# Show included and ignored files
pydocfmt check --show-files src/

# Apply exclude rules to explicit files too
pydocfmt check --fix --force-exclude generated.py src/
```

---

## Configuration

pydocformatter can be configured via `pyproject.toml` (example):

```toml
[tool.pydocfmt]
output-format = "grouped"
legacy = false
line-length = 88
line-ending = "auto"
indent-style = "space"
indent-width = 4
docstring-convention = "none"
docstring-parse-list-items = true
docstring-parse-headings = true
docstring-parse-doctests = true
docstring-parse-code-fences = true
docstring-parse-block-quotes = true
docstring-parse-tables = true
docstring-parse-directives = true
docstring-parse-literal-blocks = true
docstring-parse-sphinx-fields = true
comment-join-standalone-lines = false
comment-format-list-items = true
comment-preserve-headings = true
comment-preserve-doctests = true
comment-preserve-code-fences = true
comment-format-block-quotes = true
comment-preserve-tables = true
comment-preserve-directives = true
comment-detect-code = false
comment-detect-statements = true
comment-detect-expressions = false
select = ["ALL"]
ignore = []
extend-select = []
per-file-ignores = {"tests/*.py" = ["PCF001"]}
extend-per-file-ignores = {}
fixable = ["ALL"]
unfixable = []
extend-fixable = []
include = ["*.py", "*.pyi", "*.pyw"]
extend-include = []
exclude = [".venv", "dist"]
extend-exclude = ["generated"]
respect-gitignore = true
force-exclude = false
```

**Configuration Options:**
- `output-format`: Output format for rule findings; currently only `"grouped"` is supported (default: `"grouped"`)
- `legacy`: Use the legacy formatter implementation (default: `false`)
- `line-length`: Maximum line length for docstrings and comments (default: 88)
- `line-ending`: Line ending to use when rewriting files; one of `"auto"`, `"lf"`, `"cr-lf"`, or `"native"` (default: `"auto"`)
- `indent-style`: Generated docstring section indentation style; one of `"space"` or `"tab"` (default: `"space"`)
- `indent-width`: Generated docstring section indentation width and tab expansion width used when measuring comments (default: 4)
- `docstring-convention`: Docstring convention; one of `"none"`, `"google"`, `"numpy"`, or `"pep257"` (default: `"none"`)
- `docstring-parse-list-items`: Parse docstring list items as distinct structures (default: `true`)
- `docstring-parse-headings`: Parse Markdown and reStructuredText docstring headings (default: `true`)
- `docstring-parse-doctests`: Parse and protect doctest regions in docstrings (default: `true`)
- `docstring-parse-code-fences`: Parse and protect fenced code blocks in docstrings (default: `true`)
- `docstring-parse-block-quotes`: Parse Markdown block quotes in docstrings (default: `true`)
- `docstring-parse-tables`: Parse and protect Markdown and reStructuredText tables in docstrings (default: `true`)
- `docstring-parse-directives`: Parse reStructuredText directives and their bodies in docstrings (default: `true`)
- `docstring-parse-literal-blocks`: Parse and protect reStructuredText literal blocks in docstrings (default: `true`)
- `docstring-parse-sphinx-fields`: Parse Sphinx docstring fields into semantic entries (default: `true`)
- `comment-join-standalone-lines`: Join consecutive standalone prose comment lines before wrapping (default: `false`)
- `comment-format-list-items`: Detect ordered and unordered standalone comment list items and reflow them with hanging indentation (default: `true`)
- `comment-preserve-headings`: Preserve detected Markdown and reStructuredText comment headings unchanged (default: `true`)
- `comment-preserve-doctests`: Preserve standalone doctest comment regions from the first `>>>` prompt to the physical-run boundary (default: `true`)
- `comment-preserve-code-fences`: Preserve backtick- and tilde-fenced standalone comment regions (default: `true`)
- `comment-format-block-quotes`: Detect and reflow Markdown block quotes while retaining quote prefixes (default: `true`)
- `comment-preserve-tables`: Preserve structurally detected Markdown pipe tables and reStructuredText grid/simple tables (default: `true`)
- `comment-preserve-directives`: Preserve reStructuredText directives and their more-indented option/content lines (default: `true`)
- `comment-detect-code`: Protect whole standalone runs matching the disabled-code indentation or leading-keyword heuristic (default: `false`)
- `comment-detect-statements`: Protect whole standalone runs containing parseable Python non-expression statements (default: `true`)
- `comment-detect-expressions`: Protect whole standalone runs containing parseable nontrivial Python expressions (default: `false`)
- `select`: Rule selectors to enable (default: `["ALL"]`)
- `ignore`: Rule selectors to ignore
- `extend-select`: Additional rule selectors to enable
- `per-file-ignores`: File-pattern-specific ignored rule selectors
- `extend-per-file-ignores`: Additional file-pattern-specific ignored rule selectors
- `fixable`: Rule selectors eligible for automatic fixes (default: `["ALL"]`)
- `unfixable`: Rule selectors ineligible for automatic fixes
- `extend-fixable`: Additional rule selectors eligible for automatic fixes
- `include`: Glob patterns for files to include
- `extend-include`: Additional include glob patterns
- `exclude`: Glob patterns for files/directories to exclude
- `extend-exclude`: Additional exclude glob patterns
- `respect-gitignore`: Respect `.gitignore` during file discovery (default: `true`)
- `force-exclude`: Apply exclude rules to explicitly listed files (default: `false`)

When `respect-gitignore` is enabled, pydocfmt aborts if gitignore filtering cannot be checked, because continuing without that filter could format files that should stay ignored.

The `comment-*` settings affect the rule-based formatter. PCF001 defaults to formatting each standalone physical line independently; joining and structured-markup interpretation are opt-in. See `pydocfmt rule PCF001` and `pydocfmt rule PCF002` for exact detector precedence and protected-comment behavior.

The `docstring-convention` setting never auto-detects a convention. Google and NumPy sections are only parsed when their matching convention is selected; `none` and `pep257` leave those section syntaxes as ordinary content. The `docstring-parse-*` settings control generic semantic structures independently.

Settings are resolved per path as defaults, then the closest containing `pyproject.toml` with `[tool.pydocfmt]`, then explicit `--config` files, then inline `--config` setting overrides, then dedicated command-line options. Parent config files are not merged into child config files. The highest-precedence specified value wins for each key, including `extend-include` and `extend-exclude`.

`--config PATH` accepts either a pyproject-style file containing `[tool.pydocfmt]` or a dedicated config file with pydocfmt settings at top level. `--isolated` ignores auto-discovered configuration files; it can be combined with inline `--config` setting overrides but not with `--config PATH`.

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
