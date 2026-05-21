# reflow-required (PDF001)

Fix is always available.

## What it does
Checks for docstring paragraphs, section entries, and other free-text chunks that are not wrapped according to the configured line length.

## Why is this useful?
Consistent wrapping keeps docstrings readable in editors, terminals, and generated documentation while preserving the surrounding Python code.

## Ruff compatibility
This rule complements Ruff's docstring lint rules. Ruff reports many docstring style issues, while pydocformatter rewrites the docstring content that can be formatted mechanically.

## Example
```python
def area(radius: float) -> float:
    """Return the area for a circle with the supplied radius after validating that the radius is finite and non-negative."""
```

Use instead:
```python
def area(radius: float) -> float:
    """Return the area for a circle with the supplied radius after validating
    that the radius is finite and non-negative."""
```

## Options
- `line-length`
- `indent-style`
- `indent-width`
