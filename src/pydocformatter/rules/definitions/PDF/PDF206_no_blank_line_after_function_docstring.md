# no-blank-line-after-function-docstring (PDF206)

Fix is always available.

Rule is ignored by broad selectors for all `docstring-convention` values.

Rule is incompatible with `PDF207`.

## What it does
PDF206 removes blank lines immediately after function, method, and nested-function docstrings when another statement follows in the same function body.

Only the adjacent blank-line run after the docstring statement is changed. Comments and following statements are preserved. The rule applies to ordinary functions, async functions, methods, and nested functions. It does not apply to class docstrings, attribute docstrings, simple-suite docstrings, or function bodies where the docstring is not followed by another body statement.

## Why is this useful?
Some projects prefer keeping function docstrings directly attached to executable body statements.

## Ruff compatibility
This rule replaces Ruff's `D202`. It is exact opt-in by default because broad pydocformatter selection follows Black-compatible spacing after function docstrings.

## Examples
The canonical fix removes blank lines after a function docstring:

```pydocfmt-example
[input]
def function():
    """Docstring."""

    return None

[output]
def function():
    """Docstring."""
    return None
```

A blank line before a following comment is still adjacent to the docstring and is removed. Multiline docstrings are targeted by their opening line, but the edit is made after the closing quote line:

```pydocfmt-example
[input]
def function():
    """Summary.

    Body.
    """

    return None

def other():
    """Docstring."""

    # Body comment.
    return None

[output]
def function():
    """Summary.

    Body.
    """
    return None

def other():
    """Docstring."""
    # Body comment.
    return None
```

Docstrings without a following body statement are ignored, even if a trailing body comment follows:

```pydocfmt-example
[input]
def function():
    """Docstring."""

    # Body comment.

[output=unchanged]
```

## Options
None.
