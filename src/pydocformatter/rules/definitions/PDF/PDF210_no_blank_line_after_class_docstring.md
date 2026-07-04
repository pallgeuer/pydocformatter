# no-blank-line-after-class-docstring (PDF210)

Fix is always available.

Rule is ignored by broad selectors for all `docstring-convention` values. Select `PDF210` exactly to opt into this spacing style. If `PDF211` is also selected through a broader selector, ignore `PDF211` so the incompatible default style does not disable `PDF210`.

Rule is incompatible with `PDF211`.

## What it does
PDF210 removes blank lines immediately after class docstrings when another statement follows in the same class body.

Only the adjacent blank-line run after the docstring statement is changed. Comments and following statements are preserved. The rule applies only to primary class docstrings. It does not apply to function docstrings, attribute docstrings, simple-suite class docstrings, or class bodies where the docstring is not followed by another body statement.

## Why is this useful?
Some projects prefer keeping class docstrings directly attached to the following class body.

## Ruff compatibility
None. This is the style-opposite companion to `PDF211`, which replaces Ruff's `D204`.

## Examples
The canonical fix removes blank lines after a class docstring:

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

Comments are preserved. Multiline docstrings are targeted by their opening line, but the edit is made after the closing quote line:

```pydocfmt-example
[input]
class Client:
    """Summary.

    Body.
    """

    value = 1

class Other:
    """Docstring."""

    # Body comment.
    value = 1

[output]
class Client:
    """Summary.

    Body.
    """
    value = 1

class Other:
    """Docstring."""
    # Body comment.
    value = 1
```

Docstrings without a following body statement are ignored, even if a trailing body comment follows:

```pydocfmt-example
[input]
class Client:
    """Docstring."""

    # Body comment.

[output=unchanged]
```

## Options
None. `docstring-convention` does not change this rule's behavior. Broad selectors ignore this rule for every convention; select `PDF210` exactly to use it, and ignore `PDF211` if that incompatible companion is also selected.
