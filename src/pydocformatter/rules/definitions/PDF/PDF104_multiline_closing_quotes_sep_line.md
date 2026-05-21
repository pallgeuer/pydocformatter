# multiline-closing-quotes-sep-line (PDF104)

Fix is always available.

## What it does
Checks for multi-line docstrings whose closing triple quotes should be on their own line.

## Why is this useful?
Projects that prefer expanded docstrings can keep the closing delimiter visually separate from the content.

## Ruff compatibility
This rule is intended to replace Ruff's `D209` when pydocformatter is responsible for closing-quote placement. It conflicts with `PDF103`.

## Example
```python
def area(radius: float) -> float:
    """Return the area.

    The radius must be non-negative."""
```

Use instead:
```python
def area(radius: float) -> float:
    """Return the area.

    The radius must be non-negative.
    """
```
