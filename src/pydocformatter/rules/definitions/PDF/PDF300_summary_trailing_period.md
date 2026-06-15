# summary-trailing-period (PDF300)

Fix is sometimes available.

## What it does
Implementation pending. This rule is reserved for requiring a docstring summary to end with a period specifically.

## Why is this useful?
Some projects prefer a strict PEP 257 summary sentence style where summaries consistently end in periods.

## Ruff compatibility
This rule is intended to replace Ruff's `D400`. Use `PDF301` for the broader terminal-punctuation form.

## Example
The pending implementation will eventually report summaries without a trailing period. For now, the rule is a no-op:

```pydocfmt-example
[input]
def value():
    """Return the value"""

[output=unchanged]
```

## Options
None.
