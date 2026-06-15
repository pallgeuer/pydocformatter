# section-underline (PDF402)

Fix is sometimes available.

## What it does
Implementation pending. This rule is reserved for normalizing NumPy-style section underlines, including missing underlines, misplaced underlines, and underline length mismatches.

## Why is this useful?
One underline rule lets pydocformatter treat a NumPy section header as one structure instead of splitting closely related underline diagnostics.

## Ruff compatibility
This rule is intended to replace Ruff's `D407`, `D408`, and `D409`.

## Example
The pending implementation will eventually report malformed section underlines. For now, the rule is a no-op:

```pydocfmt-example
[input]
def value(arg):
    """Return the value.

    Parameters
    ===
    arg : int
        The value.
    """

[output=unchanged]
```

## Options
None.
