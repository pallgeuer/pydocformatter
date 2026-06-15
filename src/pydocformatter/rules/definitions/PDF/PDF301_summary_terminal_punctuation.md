# summary-terminal-punctuation (PDF301)

Fix is sometimes available.

## What it does
Implementation pending. This rule is reserved for requiring a docstring summary to end with terminal punctuation, accepting a period, question mark, or exclamation point.

## Why is this useful?
Terminal punctuation keeps summary lines sentence-like without forcing every valid question or exclamation into a period.

## Ruff compatibility
This rule is intended to replace Ruff's `D415`. Use `PDF300` for the stricter period-only form.

## Example
The pending implementation will eventually report summaries without terminal punctuation. For now, the rule is a no-op:

```pydocfmt-example
[input]
def value():
    """Return the value"""

[output=unchanged]
```

## Options
None.
