# empty-section (PDF403)

Fix is not available.

## What it does
Implementation pending. This rule is reserved for reporting recognized docstring sections that contain no meaningful content.

## Why is this useful?
Empty sections imply documentation exists where readers will find none.

## Ruff compatibility
This rule is intended to replace Ruff's `D414`.

## Example
The pending implementation will eventually report empty sections. For now, the rule is a no-op:

```pydocfmt-example
[input]
def value(arg):
    """Return the value.

    Args:
    """

[output=unchanged]
```

## Options
None.
