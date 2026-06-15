# section-order (PDF404)

Fix is not available.

## What it does
Implementation pending. This rule is reserved for reporting recognized docstring sections that appear out of the order expected by the active docstring convention.

## Why is this useful?
Consistent section order helps readers find parameters, returns, yields, raises, and related documentation quickly.

## Ruff compatibility
This rule is intended to replace Ruff's `D420`.

## Example
The pending implementation will eventually report out-of-order sections. For now, the rule is a no-op:

```pydocfmt-example
[input]
def value(arg):
    """Return the value.

    Returns:
        int: The value.

    Args:
        arg: The value.
    """

[output=unchanged]
```

## Options
None.
