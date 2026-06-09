# docstring-should-be-one-line (PDF106)

Fix is always available.

## What it does
Checks for docstrings with one content line that can fit on a single physical line including the triple quotes.

## Why is this useful?
Single-line docstrings are easier to scan when their complete content fits comfortably on one line.

## Ruff compatibility
This rule is intended to replace Ruff's `D200` while respecting the configured line length before collapsing a docstring.

## Example
```python
def area(radius: float) -> float:
    """
    Return the area.
    """
```

Applying this rule produces:
```python
def area(radius: float) -> float:
    """Return the area."""
```

## Options
- `line-length`
