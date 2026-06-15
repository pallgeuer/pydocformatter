# missing-return-documentation (PDF502)

Fix is not available.

## What it does
Implementation pending. This rule is reserved for reporting functions that return a value but do not document that return value.

## Why is this useful?
Return documentation explains the meaning of values that cannot always be inferred from annotations alone.

## Ruff compatibility
This rule is intended to replace Ruff's `DOC201`.

## Example
The pending implementation will eventually report missing return documentation. For now, the rule is a no-op:

```pydocfmt-example
[input]
def value():
    """Return the value."""
    return 1

[output=unchanged]
```

## Options
None.
