# docstring-trailing-whitespace (PDF003)

Fix is always available.

## What it does
Checks for trailing whitespace on non-empty docstring lines.

## Why is this useful?
Trailing whitespace creates noisy diffs and can make otherwise identical docstrings compare differently.

## Ruff compatibility
This rule overlaps with Ruff's general trailing-whitespace checks, such as `W291`, but is scoped to docstring content handled by pydocformatter.

## Example
```python
def area(radius: float) -> float:
    """Return the area.   """
```

Applying this rule produces:
```python
def area(radius: float) -> float:
    """Return the area."""
```
