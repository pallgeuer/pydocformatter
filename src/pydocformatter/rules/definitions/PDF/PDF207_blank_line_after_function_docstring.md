# blank-line-after-function-docstring (PDF207)

Fix is always available.

Rule is ignored by broad selectors for all `docstring-convention` values.

Rule is incompatible with `PDF206`.

## What it does
PDF207 requires exactly one blank line immediately after function, method, and nested-function docstrings when another statement follows in the same function body.

Only the adjacent blank-line run after the docstring statement is changed. Comments and following statements are preserved. The rule applies to ordinary functions, async functions, methods, and nested functions. It does not apply to class docstrings, attribute docstrings, simple-suite docstrings, or function bodies where the docstring is not followed by another body statement.

## Why is this useful?
Some projects prefer visually separating function docstrings from executable body statements.

## Ruff compatibility
This is the style-opposite companion to `PDF206`, which replaces Ruff's `D202`.

## Examples
The canonical fix inserts one blank line after a function docstring:

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

Excess blank lines are collapsed to one. For multiline docstrings, the blank line is placed after the closing quote line:

```pydocfmt-example
[input]
def function():
    """Summary.

    Body.
    """
    return None

def other():
    """Docstring."""


    return None

[output]
def function():
    """Summary.

    Body.
    """

    return None

def other():
    """Docstring."""

    return None
```

A following comment is treated as the next body statement, so the blank line is inserted before that comment:

```pydocfmt-example
[input]
def function():
    """Docstring."""
    # Body comment.
    return None

[output]
def function():
    """Docstring."""

    # Body comment.
    return None
```

Docstrings without a following body statement and simple-suite docstrings are ignored:

```pydocfmt-example
[input]
def function():
    """Docstring."""
    # Body comment.

def simple(): """Docstring."""; return None

[output=unchanged]
```

## Options
None.
