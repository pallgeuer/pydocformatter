# too-many-blank-lines (PDF100)

Fix is always available.

## What it does
Checks for extra blank lines around docstring chunks.

## Why is this useful?
Predictable blank-line spacing makes summaries, descriptions, and sections visually distinct without adding vertical noise.

## Ruff compatibility
This rule is intended to replace the fixable extra-blank-line cases covered by Ruff's `D205`; `PDF105` handles summaries that still span multiple lines.

## Example
```pydocfmt-example
[input]
pass

[output=unchanged]
```

```python
def area(radius: float) -> float:
    """Return the area.


    The radius must be non-negative.
    """
```

Applying this rule produces:
```python
def area(radius: float) -> float:
    """Return the area.

    The radius must be non-negative.
    """
```
