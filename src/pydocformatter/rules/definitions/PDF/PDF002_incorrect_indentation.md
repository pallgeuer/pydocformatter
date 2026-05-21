# incorrect-indentation (PDF002)

Fix is always available.

## What it does
Checks for docstring lines whose indentation does not match the surrounding docstring structure.

## Why is this useful?
Unexpected indentation makes docstrings harder to scan and can confuse tools that parse structured sections.

## Ruff compatibility
This rule is intended to replace Ruff's `D207` and `D208` when pydocformatter is responsible for normalizing docstring indentation.

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

## Options
- `indent-style`
- `indent-width`
