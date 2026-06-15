# section-header-line-break (PDF401)

Fix is sometimes available.

## What it does
Implementation pending. This rule is reserved for ensuring recognized docstring section headers are separated from their content by the line break required by the active docstring convention.

## Why is this useful?
Section headers that share a line with content are harder for humans and parsers to read reliably.

## Ruff compatibility
This rule is intended to replace Ruff's `D406`.

## Example
The pending implementation will eventually report section names that are not followed by a line break. For now, the rule is a no-op:

```pydocfmt-example
[input]
def value(arg):
    """Return the value.

    Args: arg: The value.
    """

[output=unchanged]
```

## Options
None.
