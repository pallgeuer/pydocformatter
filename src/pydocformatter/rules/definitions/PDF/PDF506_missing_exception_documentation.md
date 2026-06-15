# missing-exception-documentation (PDF506)

Fix is not available.

## What it does
Implementation pending. This rule is reserved for reporting explicitly raised exceptions that are not documented in the docstring.

## Why is this useful?
Exception documentation helps callers understand failure modes without reading the implementation.

## Ruff compatibility
This rule is intended to replace Ruff's `DOC501`.

## Example
The pending implementation will eventually report missing exception documentation. For now, the rule is a no-op:

```pydocfmt-example
[input]
def value(arg):
    """Return the value."""
    if arg < 0:
        raise ValueError("negative")
    return arg

[output=unchanged]
```

## Options
None.
