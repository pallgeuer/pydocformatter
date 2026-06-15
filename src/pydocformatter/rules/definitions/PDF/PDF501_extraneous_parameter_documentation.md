# extraneous-parameter-documentation (PDF501)

Fix is not available.

## What it does
Implementation pending. This rule is reserved for reporting documented parameters that do not exist in the function signature.

## Why is this useful?
Extraneous parameter documentation can mislead callers and usually indicates stale docs after a signature change.

## Ruff compatibility
This rule is intended to replace Ruff's `DOC102`.

## Example
The pending implementation will eventually report extraneous documented parameters. For now, the rule is a no-op:

```pydocfmt-example
[input]
def value():
    """Return the value.

    Args:
        arg: The value.
    """

[output=unchanged]
```

## Options
None.
