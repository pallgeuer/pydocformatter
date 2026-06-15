# missing-parameter-documentation (PDF500)

Fix is not available.

## What it does
Implementation pending. This rule is reserved for reporting function parameters that are present in the signature but missing from the docstring parameter documentation.

## Why is this useful?
Documented parameters help callers understand accepted inputs without cross-checking implementation details.

## Ruff compatibility
This rule is intended to replace Ruff's `D417`.

## Example
The pending implementation will eventually report undocumented parameters. For now, the rule is a no-op:

```pydocfmt-example
[input]
def value(arg):
    """Return the value."""

[output=unchanged]
```

## Options
None.
