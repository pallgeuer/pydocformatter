# no-blank-line-before-class-docstring (PDF208)

Fix is always available.

Rule is incompatible with `PDF209`.

## What it does
PDF208 removes blank lines immediately before class docstrings.

Only the adjacent blank-line run before the docstring statement is changed. Comments, decorators, class headers, and non-blank lines before the docstring are preserved. The rule applies only to primary class docstrings. It does not apply to function docstrings, attribute docstrings, or simple-suite class docstrings written on the same physical line as the class header.

## Why is this useful?
Keeping a class docstring directly attached to the class body follows Ruff's default class-docstring spacing convention.

## Ruff compatibility
This rule replaces Ruff's `D211`.

## Examples
The canonical fix removes blank lines before a class docstring:

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

Comments are preserved; only the adjacent blank-line run before the docstring is removed:

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

Function docstrings and attribute docstrings are ignored:

```pydocfmt-example
[input]
class Client:
    value = 1
    """Attribute docstring."""

def function():

    """Function docstring."""
    return None

[output=unchanged]
```

## Options
None. `docstring-convention` does not change this rule's behavior.
