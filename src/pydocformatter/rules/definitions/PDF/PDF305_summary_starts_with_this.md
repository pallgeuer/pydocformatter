# summary-starts-with-this (PDF305)

Fix is not available.

## What it does
Implementation pending. This rule is reserved for reporting docstring summaries that start with the word "This".

## Why is this useful?
Summaries that begin with "This" are often indirect and can usually be rewritten more concisely around the action or object being documented.

## Ruff compatibility
This rule is intended to replace Ruff's `D404`.

## Example
The pending implementation will eventually report summaries that start with "This". For now, the rule is a no-op:

```pydocfmt-example
[input]
def value():
    """This returns the value."""

[output=unchanged]
```

## Options
None.
