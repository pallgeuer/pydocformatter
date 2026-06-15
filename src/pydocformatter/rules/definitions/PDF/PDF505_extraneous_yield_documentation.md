# extraneous-yield-documentation (PDF505)

Fix is not available.

## What it does
Implementation pending. This rule is reserved for reporting yield documentation on functions that do not yield values.

## Why is this useful?
Extraneous yield sections can make an ordinary function look like a generator.

## Ruff compatibility
This rule is intended to replace Ruff's `DOC403`.

## Example
The pending implementation will eventually report extraneous yield documentation. For now, the rule is a no-op:

```pydocfmt-example
[input]
def value():
    """Return the value.

    Yields:
        int: The value.
    """
    return 1

[output=unchanged]
```

## Options
None.
