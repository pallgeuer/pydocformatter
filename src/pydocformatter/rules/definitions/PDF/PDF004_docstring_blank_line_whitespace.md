# docstring-blank-line-whitespace (PDF004)

Fix is always available.

## What it does
Checks for whitespace-only blank lines inside docstrings.

## Why is this useful?
Whitespace-only blank lines make diffs noisy and hide formatting changes that should be semantically empty.

## Ruff compatibility
This rule overlaps with Ruff's general blank-line whitespace checks, such as `W293`, but is scoped to docstring content handled by pydocformatter.

## Example
```python
def area(radius: float) -> float:
    """Return the area.
       
    The radius must be non-negative.
    """
```

Use instead:
```python
def area(radius: float) -> float:
    """Return the area.

    The radius must be non-negative.
    """
```
