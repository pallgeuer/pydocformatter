# signature-summary (PDF303)

Fix is not available.

Rule is ignored if `docstring-convention` is `numpy`.

## What it does
Checks function and method docstring summaries that include the function name immediately followed by `(`.

PDF303 reports only when the name starts the first summary line or is preceded by a space, tab, semicolon, or comma. The comparison is case-sensitive and the opening parenthesis must immediately follow the function name, so `value(count)` is a signature summary but `Value(count)`, `module.value(count)`, and `value (count)` are not.

It skips module and class docstrings, empty docstrings, docstrings without a parsed summary, text after the first summary line, and parser-recognized structures such as sections, rest fields under the rest convention, headings, lists, doctests, code fences, block quotes, tables, directives, literal blocks, and verbatim blocks.

## Why is this useful?
Repeating a signature in the summary duplicates information already present in source and generated API documentation.

## Ruff compatibility
This rule replaces Ruff's `D402`. Like Ruff, it applies to functions and methods and is ignored by default for the NumPy convention.

The signature-matching heuristic is Ruff-compatible: it looks for the exact function name followed immediately by `(`, with either the start of the line or a space, tab, semicolon, or comma before the name. Unlike Ruff, PDF303 applies that heuristic only after pydocformatter has selected a parsed summary line. This means parser-recognized structures such as rest fields under the rest convention, lists, doctests, headings, and code blocks are protected instead of being checked as Ruff's first trimmed docstring line.

## Example
PDF303 reports summaries that repeat the function signature and leaves source unchanged:

```pydocfmt-example
[input]
def value(count: int) -> str:
    """value(count: int) -> str"""

[output=unchanged]
[findings]
PDF303: Line 2: Docstring summary should not include signature for function 'value'
```

The signature can also appear later in the first summary line after a supported separator:

```pydocfmt-example
[input]
def value(count: int) -> str:
    """Return; value(count)"""

def empty() -> None:
    """empty()"""

[output=unchanged]
[findings]
PDF303: Line 2: Docstring summary should not include signature for function 'value'
PDF303: Line 5: Docstring summary should not include signature for function 'empty'
```

Names that are not signature-like are accepted:

```pydocfmt-example
[input]
def value(count: int) -> str:
    """Return the value."""

def qualified(count: int) -> str:
    """module.qualified(count)"""

def spaced(count: int) -> str:
    """spaced (count)"""

def mismatched(count: int) -> str:
    """MISMATCHED(count)"""

[output=unchanged]
```

Only the first summary line is checked:

```pydocfmt-example
[input]
def value(count: int) -> str:
    """Return the value.
    value(count)
    """

[output=unchanged]
```

Rest fields are protected under the rest convention:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def value(count: int) -> str:
    """:return: value(count)"""

[output=unchanged]
```

Outside the rest convention, rest-looking text is summary text:

```pydocfmt-example
[settings]
docstring-convention = "none"

[input]
def value(count: int) -> str:
    """:return: value(count)"""

[output=unchanged]
[findings]
PDF303: Line 2: Docstring summary should not include signature for function 'value'
```

## Options
- `docstring-convention`: Ignores PDF303 for broad rule selections under the NumPy convention.
- `docstring-parse-*`: Controls whether generic structures such as headings, lists, doctests, code fences, block quotes, tables, directives, and literal blocks are protected from summary-style checks.
