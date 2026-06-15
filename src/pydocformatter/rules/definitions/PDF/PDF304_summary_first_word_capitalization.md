# summary-first-word-capitalization (PDF304)

Fix is sometimes available.

## What it does
Implementation pending. This rule is reserved for requiring the first word of a docstring summary to start with a capital letter when that capitalization can be determined safely.

## Why is this useful?
Consistent summary capitalization makes docstrings scan like complete prose.

## Ruff compatibility
This rule is intended to replace Ruff's `D403`.

## Example
The pending implementation will eventually report uncapitalized summary starts. For now, the rule is a no-op:

```pydocfmt-example
[input]
def value():
    """return the value."""

[output=unchanged]
```

## Options
None.
