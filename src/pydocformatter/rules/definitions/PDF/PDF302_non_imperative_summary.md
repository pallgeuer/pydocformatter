# non-imperative-summary (PDF302)

Fix is not available.

## What it does
Implementation pending. This rule is reserved for reporting docstring summaries that do not appear to use imperative mood.

## Why is this useful?
Imperative summaries are the conventional style for many Python APIs because they describe what calling the object does.

## Ruff compatibility
This rule is intended to replace Ruff's `D401`.

## Example
The pending implementation will eventually report non-imperative summaries. For now, the rule is a no-op:

```pydocfmt-example
[input]
def value():
    """Returns the value."""

[output=unchanged]
```

## Options
None.
