# multiline-opening-quotes-sep-line (PDF102)

Fix is always available.

Rule is ignored if `docstring-convention` is `none`, `google`, `numpy`, or `pep257`.

Rule is incompatible with `PDF101`.

## What it does
Checks for multi-line docstrings whose opening triple quotes should be on their own line.

## Why is this useful?
Projects that prefer expanded docstrings can keep delimiters visually separate from the content.

## Ruff compatibility
This rule is intended to replace Ruff's `D212` or `D213` when the configured pydocformatter style puts opening quotes on a separate line.

## Example
```python
def area(radius: float) -> float:
    """Return the area.

    The radius must be non-negative.
    """
```

Applying this rule produces:
```python
def area(radius: float) -> float:
    """
    Return the area.

    The radius must be non-negative.
    """
```
