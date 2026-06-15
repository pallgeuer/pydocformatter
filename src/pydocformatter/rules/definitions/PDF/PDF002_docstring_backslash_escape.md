# docstring-backslash-escape (PDF002)

Fix is sometimes available.

## What it does
Implementation pending. This rule is reserved for docstring literals whose source contains backslash escapes that should be expressed with an equivalent raw string prefix when that rewrite is value-preserving.

## Why is this useful?
Raw docstrings make paths, regular expressions, and escaped markup easier to read while avoiding accidental escape interpretation.

## Ruff compatibility
This rule is intended to replace Ruff's `D301`, while keeping pydocformatter fixes value-preserving.

## Example
The pending implementation will eventually report backslash escapes that should use a raw docstring. For now, the rule is a no-op:

```pydocfmt-example
[input]
def path():
    """Return C:\\temp."""

[output=unchanged]
```

## Options
None.
