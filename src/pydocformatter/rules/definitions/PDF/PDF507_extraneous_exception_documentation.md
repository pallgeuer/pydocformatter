# extraneous-exception-documentation (PDF507)

Fix is not available.

## What it does
Implementation pending. This rule is reserved for reporting documented exceptions that are not explicitly raised by the function body.

## Why is this useful?
Extraneous exception documentation can misstate the failure modes of an API.

## Ruff compatibility
This rule is intended to replace Ruff's `DOC502`.

## Example
The pending implementation will eventually report extraneous exception documentation. For now, the rule is a no-op:

```pydocfmt-example
[input]
def value(arg):
    """Return the value.

    Raises:
        ValueError: If the value is invalid.
    """
    return arg

[output=unchanged]
```

## Options
None.
