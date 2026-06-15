# missing-yield-documentation (PDF504)

Fix is not available.

## What it does
Implementation pending. This rule is reserved for reporting generator functions that yield values but do not document those yielded values.

## Why is this useful?
Yield documentation explains each produced value in generator APIs.

## Ruff compatibility
This rule is intended to replace Ruff's `DOC402`.

## Example
The pending implementation will eventually report missing yield documentation. For now, the rule is a no-op:

```pydocfmt-example
[input]
def values():
    """Yield values."""
    yield 1

[output=unchanged]
```

## Options
None.
