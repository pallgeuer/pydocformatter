# closing-quotes-whitespace (PDF006)

Fix is always available.

## What it does
Checks for unnecessary whitespace between docstring content and closing triple quotes.

## Why is this useful?
Removing extra whitespace gives docstrings a predictable shape and avoids accidental trailing spaces in the rendered text.

## Ruff compatibility
This rule is intended to replace the closing-quotes part of Ruff's `D210` when pydocformatter is responsible for docstring whitespace.

## Example
```pydocfmt-example
[input]
pass

[output=unchanged]
```

```python
def area(radius: float) -> float:
    """Return the area.  """
```

Applying this rule produces:
```python
def area(radius: float) -> float:
    """Return the area."""
```
