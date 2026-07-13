# blank-line-before-class-docstring (PDF209)

Fix is always available.

Rule is ignored by broad selectors for all `docstring-convention` values.

Rule is incompatible with `PDF208`.

## What it does
PDF209 requires exactly one blank line immediately before class docstrings.

Only the adjacent blank-line run before the docstring statement is changed. Comments, decorators, class headers, and non-blank lines before the docstring are preserved. The rule applies only to primary class docstrings. It does not apply to function docstrings, attribute docstrings, or simple-suite class docstrings written on the same physical line as the class header.

## Why is this useful?
This supports the class-docstring spacing style used by projects that prefer one blank line between the class header or leading body comments and the docstring.

## Ruff compatibility
This rule replaces Ruff's `D203`. Like Ruff, it is incompatible with the no-blank-line-before-class-docstring style.

## Examples
The canonical fix inserts one blank line before a class docstring:

```pydocfmt-example
[input]
class Client:
    """Docstring."""
    value = 1

[output]
class Client:

    """Docstring."""
    value = 1
```

Excess blank lines are collapsed to one, and leading comments stay attached above the separator:

```pydocfmt-example
[input]
class Client:
    # Leading comment.


    """Docstring."""
    value = 1

[output]
class Client:
    # Leading comment.

    """Docstring."""
    value = 1
```

Decorated classes are handled the same way:

```pydocfmt-example
[input]
@decorator
class Client:
    """Docstring."""
    value = 1

[output]
@decorator
class Client:

    """Docstring."""
    value = 1
```

Function docstrings are ignored:

```pydocfmt-example
[input]
def function():
    """Docstring."""
    return None

[output=unchanged]
```

## Options
None.
