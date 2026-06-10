# multiline-closing-quotes-same-line (PDF103)

Fix is always available.

Rule is ignored if `docstring-convention` is `none`, `google`, `numpy`, or `pep257`.

Rule is incompatible with `PDF104`.

## What it does
Checks for multi-line docstrings whose closing triple quotes should share a line with the last content line.

## Why is this useful?
Projects that prefer compact docstrings can avoid a delimiter-only closing line when the configured style allows it.

## Ruff compatibility
This rule is intended to provide the compact closing-quotes style not available from Ruff's `D209`.

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
    """Return the area.

    The radius must be non-negative."""
```
