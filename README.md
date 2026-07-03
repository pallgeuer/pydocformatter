# pydocformatter

[![CI](https://github.com/pallgeuer/pydocformatter/actions/workflows/unit-tests.yml/badge.svg)](https://github.com/pallgeuer/pydocformatter/actions)
[![CI](https://github.com/pallgeuer/pydocformatter/actions/workflows/pre-commit-checks.yml/badge.svg)](https://github.com/pallgeuer/pydocformatter/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**pydocformatter** provides a Ruff-style Python formatter, `pydocfmt`, for formatting docstrings and comments. It is designed to be maximally compatible with [Ruff](https://docs.astral.sh/ruff/).

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
- **Special comment preservation:** Maintains pylint, mypy, ty, noqa, pragma, and formatter directives
- **Smart spacing:** Ensures consistent spacing between code and comments

### File Selection and Configuration
- **Ruff-style file selection:** Supports glob-based include/exclude rules, default excludes, `force-exclude`, and `.gitignore`-aware discovery
- **Ruff-style configuration:** Reads `[tool.pydocfmt]` and its docstring/comment subtables from auto-discovered `pyproject.toml` files
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

**Run:**
- `--output-format {grouped}`: Output format for rule findings (default: grouped)
- `--parallelism JOBS`: File-level parallelism, as a worker count, CPU ratio, or `0` for all logical CPUs subject to platform process-pool limits (default: 0.0)

**Formatting:**
- `--line-length LENGTH`: Maximum line length for docstrings and comments (default: 88)
- `--url-aware-wrapping`, `--no-url-aware-wrapping`: Toggle URL-aware wrapping balance without splitting URLs (default: enabled)
- `--line-ending {auto,lf,cr-lf,native}`: Line ending to use when rewriting files (default: auto)
- `--indent-style {space,tab}`: Indentation style for generated docstring sections (default: space)
- `--indent-width WIDTH`: Generated docstring indentation width and comment tab width (default: 4)

**Docstring formatting:**
- `--docstring-convention {none,pep257,google,numpy,rest}`: Convention used to parse semantic docstring sections (default: pep257)
- `--docstring-blank-line-style {blank,aligned}`: Whitespace style for blank docstring lines (default: blank)
- `--docstring-blank-line-after-last-section`, `--no-docstring-blank-line-after-last-section`: Toggle keeping one blank line after the last recognized Google or NumPy docstring section (default: disabled)
- `--docstring-missing-documentation {has-section,non-summary-docstrings,all-docstrings}`: When missing-documentation rules report missing documentation (default: has-section)
- `--docstring-missing-documentation-public-only`, `--no-docstring-missing-documentation-public-only`: Toggle limiting broad missing-documentation checks to public API definitions (default: enabled)
- `--docstring-require-init-attribute-documentation`, `--no-docstring-require-init-attribute-documentation`: Toggle requiring supported `self.*` attributes assigned in `__init__` for class missing-attribute documentation checks (default: disabled)
- `--docstring-parse-list-items`, `--no-docstring-parse-list-items`: Toggle parsing docstring list items (default: enabled)
- `--docstring-parse-headings`, `--no-docstring-parse-headings`: Toggle parsing docstring headings (default: enabled)
- `--docstring-parse-doctests`, `--no-docstring-parse-doctests`: Toggle parsing and protecting doctest regions (default: enabled)
- `--docstring-parse-code-fences`, `--no-docstring-parse-code-fences`: Toggle parsing and protecting fenced code blocks (default: enabled)
- `--docstring-parse-block-quotes`, `--no-docstring-parse-block-quotes`: Toggle parsing Markdown block quotes (default: enabled)
- `--docstring-parse-tables`, `--no-docstring-parse-tables`: Toggle parsing and protecting tables (default: enabled)
- `--docstring-parse-directives`, `--no-docstring-parse-directives`: Toggle parsing reStructuredText directives (default: enabled)
- `--docstring-parse-literal-blocks`, `--no-docstring-parse-literal-blocks`: Toggle parsing reStructuredText literal blocks (default: enabled)

**Comment formatting:**
- `--comment-join-standalone-lines`, `--no-comment-join-standalone-lines`: Toggle joining standalone prose lines before wrapping (default: disabled)
- `--comment-format-list-items`, `--no-comment-format-list-items`: Toggle list-item detection and hanging-indented reflow (default: enabled)
- `--comment-format-task-markers`, `--no-comment-format-task-markers`: Toggle task-marker detection and hanging-indented reflow (default: enabled)
- `--comment-preserve-headings`, `--no-comment-preserve-headings`: Toggle preserving Markdown and reStructuredText headings (default: enabled)
- `--comment-preserve-doctests`, `--no-comment-preserve-doctests`: Toggle preserving standalone doctest regions (default: enabled)
- `--comment-preserve-code-fences`, `--no-comment-preserve-code-fences`: Toggle preserving fenced code regions (default: enabled)
- `--comment-format-block-quotes`, `--no-comment-format-block-quotes`: Toggle prefix-preserving block-quote reflow (default: enabled)
- `--comment-preserve-tables`, `--no-comment-preserve-tables`: Toggle preserving detected Markdown and reStructuredText tables (default: enabled)
- `--comment-preserve-directives`, `--no-comment-preserve-directives`: Toggle preserving reStructuredText directives and their indented bodies (default: enabled)
- `--comment-trailing-extraction-syntax-aware`, `--no-comment-trailing-extraction-syntax-aware`: Toggle keeping overlong trailing comments inline in syntax-sensitive positions (default: enabled)
- `--comment-trailing-extraction-content-aware`, `--no-comment-trailing-extraction-content-aware`: Toggle keeping overlong trailing comments inline when content is unsafe to reinterpret as standalone comments (default: enabled)
- `--comment-detect-code`, `--no-comment-detect-code`: Toggle the disabled-code indentation and leading-keyword heuristic (default: disabled)
- `--comment-detect-statements`, `--no-comment-detect-statements`: Toggle parseable Python statement detection (default: enabled)
- `--comment-detect-expressions`, `--no-comment-detect-expressions`: Toggle nontrivial Python expression detection (default: disabled)

**Rule Selection:**
- `--select RULE`: Comma-separated rule selector(s) to enable
- `--ignore RULE`: Comma-separated rule selector(s) to ignore
- `--extend-select RULE`: Comma-separated additional rule selector(s) to enable
- `--require-explicit RULE`: Comma-separated rule selector(s) that require exact rule-code selection
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

pydocformatter can be configured via `pyproject.toml` (exhaustive example):

```toml
[tool.pydocfmt]
output-format = "grouped"
line-length = 88
url-aware-wrapping = true
line-ending = "auto"
indent-style = "space"
indent-width = 4
parallelism = 0.0
select = ["ALL"]
ignore = []
extend-select = []
require-explicit = ["PCF005", "PDF003"]
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

[tool.pydocfmt.docstring]
convention = "pep257"
blank-line-style = "blank"
blank-line-after-last-section = false
missing-documentation = "has-section"
missing-documentation-public-only = true
require-init-attribute-documentation = false
parse-list-items = true
parse-headings = true
parse-doctests = true
parse-code-fences = true
parse-block-quotes = true
parse-tables = true
parse-directives = true
parse-literal-blocks = true

[tool.pydocfmt.comment]
join-standalone-lines = false
format-list-items = true
format-task-markers = true
preserve-headings = true
preserve-doctests = true
preserve-code-fences = true
format-block-quotes = true
preserve-tables = true
preserve-directives = true
trailing-extraction-syntax-aware = true
trailing-extraction-content-aware = true
detect-code = false
detect-statements = true
detect-expressions = false

[tool.pydocfmt.per-file-settings]
"tests/**/*.py" = { docstring-missing-documentation = "has-section" }
```

For TOML configuration, `[tool.pydocfmt.docstring]` and `[tool.pydocfmt.comment]` are the intended way to specify docstring and comment settings. Flat hyphenated forms such as `docstring-convention = "google"` also work for compatibility, but do not specify both forms for the same setting in one configuration.

Use `pydocfmt config` to list supported settings and their accepted values. For the full configuration contract, see [Settings Specification](docs/settings_spec.md). File discovery is specified in [File Selection Specification](docs/file_selection_spec.md), and rule selectors, per-file ignores, and fixability are specified in [Rule Selection Specification](docs/rule_selection_spec.md).

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
    rev: v1.0.0
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
- [pyformatter](https://github.com/RikGhosh487/pyformatter) - Project inspiration
- [Black](https://github.com/psf/black) - The uncompromising Python code formatter
- [isort](https://github.com/PyCQA/isort) - A Python utility to sort imports
- [docformatter](https://github.com/PyCQA/docformatter) - Formats docstrings to follow conventions
