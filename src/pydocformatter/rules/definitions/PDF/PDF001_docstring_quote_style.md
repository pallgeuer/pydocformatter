# docstring-quote-style (PDF001)

Fix is sometimes available.

## What it does
Implementation pending. This rule is reserved for normalizing docstring quote style to triple double quotes when that can be done without changing the evaluated docstring value.

## Why is this useful?
Keeping one docstring delimiter style makes later docstring formatting rules easier to reason about and keeps source style consistent.

## Ruff compatibility
This rule is intended to replace Ruff's `D300`.

## Example
The pending implementation will eventually report triple-single-quoted docstrings. For now, the rule is a no-op:

```pydocfmt-example
[input]
def value():
    '''Return the value.'''

[output=unchanged]
```

## Options
None.
