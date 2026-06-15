# signature-summary (PDF303)

Fix is not available.

## What it does
Implementation pending. This rule is reserved for reporting function and method docstring summaries that duplicate the function signature.

## Why is this useful?
Repeating a signature in the summary usually duplicates information already present in source and generated API documentation.

## Ruff compatibility
This rule is intended to replace Ruff's `D402`.

## Example
The pending implementation will eventually report signature-like summaries. For now, the rule is a no-op:

```pydocfmt-example
[input]
def value(count: int) -> str:
    """value(count: int) -> str"""

[output=unchanged]
```

## Options
None.
