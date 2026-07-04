# blank-line-after-class-docstring (PDF211)

Fix is always available.

Rule is incompatible with `PDF210`.

## What it does
PDF211 requires exactly one blank line immediately after class docstrings when another statement follows in the same class body.

Only the adjacent blank-line run after the docstring statement is changed. Comments and following statements are preserved. The rule applies only to primary class docstrings. It does not apply to function docstrings, attribute docstrings, simple-suite class docstrings, or class bodies where the docstring is not followed by another body statement.

## Why is this useful?
Separating class docstrings from class attributes, methods, and nested classes follows the default PEP 257 and Ruff style.

## Ruff compatibility
This rule replaces Ruff's `D204`.

## Examples
The canonical fix inserts one blank line after a class docstring:

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

Excess blank lines are collapsed to one. For multiline docstrings, the blank line is placed after the closing quote line:

```pydocfmt-example
[input]
class Client:
    """Summary.

    Body.
    """
    value = 1

class Other:
    """Docstring."""


    def close(self):
        pass

[output]
class Client:
    """Summary.

    Body.
    """

    value = 1

class Other:
    """Docstring."""

    def close(self):
        pass
```

A following comment is treated as the next body statement, so the blank line is inserted before that comment:

```pydocfmt-example
[input]
class Client:
    """Docstring."""
    # Body comment.
    value = 1

[output]
class Client:
    """Docstring."""

    # Body comment.
    value = 1
```

Docstrings without a following body statement and simple-suite class docstrings are ignored:

```pydocfmt-example
[input]
class Client:
    """Docstring."""
    # Body comment.

class Simple: """Docstring."""; value = 1

[output=unchanged]
```

## Options
None. `docstring-convention` does not change this rule's behavior.
