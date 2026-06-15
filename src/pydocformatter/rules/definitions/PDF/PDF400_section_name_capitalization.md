# section-name-capitalization (PDF400)

Fix is sometimes available.

## What it does
Implementation pending. This rule is reserved for normalizing recognized docstring section names to the capitalization expected by the active docstring convention.

## Why is this useful?
Consistent section names make convention-aware parsing and rendered documentation more predictable.

## Ruff compatibility
This rule is intended to replace Ruff's `D405`.

## Example
The pending implementation will eventually report incorrectly capitalized section names. For now, the rule is a no-op:

```pydocfmt-example
[input]
def value(arg):
    """Return the value.

    args:
        arg: The value.
    """

[output=unchanged]
```

## Options
None.
