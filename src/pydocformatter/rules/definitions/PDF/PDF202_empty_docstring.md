# empty-docstring (PDF202)

Fix is not available.

## What it does
Implementation pending. This rule is reserved for reporting docstrings that contain no meaningful content after indentation and whitespace normalization.

## Why is this useful?
An empty docstring looks documented to tooling while conveying no useful information to readers.

## Ruff compatibility
This rule is intended to replace Ruff's `D419`.

## Example
The pending implementation will eventually report empty docstrings. For now, the rule is a no-op:

```pydocfmt-example
[input]
def value():
    """"""

[output=unchanged]
```

## Options
None.
