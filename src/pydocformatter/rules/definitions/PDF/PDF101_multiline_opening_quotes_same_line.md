# multiline-opening-quotes-same-line (PDF101)

Fix is always available.

Rule is ignored if `docstring-convention` is `numpy` or `pep257`.

Rule is incompatible with `PDF102`.

## What it does
Checks for multi-line docstrings whose opening triple quotes should share a line with the first content line.

## Why is this useful?
Projects that prefer compact docstrings can keep the opening delimiter and summary together while still allowing multi-line bodies.

## Ruff compatibility
This rule is intended to replace Ruff's `D212` or `D213` when the configured pydocformatter style keeps opening quotes on the summary line.

## Example
```python
def area(radius: float) -> float:
    """
    Return the area.

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
