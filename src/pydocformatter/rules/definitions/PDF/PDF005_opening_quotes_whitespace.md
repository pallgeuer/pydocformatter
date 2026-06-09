# opening-quotes-whitespace (PDF005)

Fix is always available.

## What it does
Checks for unnecessary whitespace between opening triple quotes and docstring content.

## Why is this useful?
Removing extra whitespace gives docstrings a predictable shape and avoids accidental leading spaces in the rendered text.

## Ruff compatibility
This rule is intended to replace the opening-quotes part of Ruff's `D210` when pydocformatter is responsible for docstring whitespace.

## Example
```python
def area(radius: float) -> float:
    """  Return the area."""
```

Applying this rule produces:
```python
def area(radius: float) -> float:
    """Return the area."""
```
