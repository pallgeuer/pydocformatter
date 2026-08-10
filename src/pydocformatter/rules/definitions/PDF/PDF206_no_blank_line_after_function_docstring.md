# no-blank-line-after-function-docstring (PDF206)

Fix is always available.

Rule is ignored by broad selectors for all `docstring-convention` values.

Rule is incompatible with `PDF207`.

## What it does
PDF206 normally removes blank lines immediately after function, method, and nested-function docstrings when another statement follows in the same function body. As an exception, it requires exactly one blank line when the first syntactic body statement after the docstring is a nested function, async function, or class definition.

Only the adjacent blank-line run after the docstring statement is changed. Comments and following statements are preserved. Leading comments attached to a nested definition use the nested-definition exception, so the required blank line appears before those comments. The rule applies to ordinary functions, async functions, methods, and nested functions. It does not apply to class docstrings, attribute docstrings, simple-suite docstrings, or function bodies where the docstring is not followed by another body statement.

## Why is this useful?
This keeps function docstrings directly attached to ordinary executable body statements while retaining the conventional visual separation before nested definitions.

## Ruff compatibility
Disable Ruff's `D202` when PDF206 owns spacing after function docstrings. Both rules require no blank line before ordinary body statements, but they differ before nested definitions: D202 accepts either zero or one blank line, while PDF206 requires exactly one blank line and normalizes the source to match the Ruff formatter. PDF206 is convention opt-in by default because broad pydocformatter selection does not choose between the opposing PDF206 and PDF207 policies.

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

Nested definitions instead require exactly one blank line. The same exception applies to async and decorated nested functions and classes, and to leading comments attached to them:

```pydocfmt-example
[input]
def function():
    """Docstring."""
    # Explain the helper.
    def helper():
        return None

[output]
def function():
    """Docstring."""

    # Explain the helper.
    def helper():
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
