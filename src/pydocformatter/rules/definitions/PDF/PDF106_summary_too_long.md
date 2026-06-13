# summary-too-long (PDF106)

Fix is not available.

## What it does
Checks for docstring summaries that still span multiple lines after formatting.

## Why is this useful?
A multi-line summary can be ambiguous: it may be a long summary that needs rewriting by a human, or a missing blank line between the summary and description.

## Ruff compatibility
This rule is intended to cover the non-fixable part of Ruff's `D205` behavior after pydocformatter has normalized fixable blank-line spacing.

## Example
```pydocfmt-example
[input]
pass

[output=unchanged]
```

```python
def area(radius: float) -> float:
    """Return the area for a circle
    after validating the radius.
    """
```

Applying this rule produces:
```python
def area(radius: float) -> float:
    """Return the area for a circle after validating the radius."""
```

## Options
- `line-length`
