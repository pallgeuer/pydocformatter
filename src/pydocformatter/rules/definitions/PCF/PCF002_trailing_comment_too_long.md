# trailing-comment-too-long (PCF002)

Fix is always available.

## What it does
Checks for trailing comments that need spacing normalization or extraction into a wrapped standalone comment block.

## Why is this useful?
Long trailing comments make code lines hard to read. Moving the comment above the code keeps both the comment and the code within the configured line length.

## Ruff compatibility
Ruff can report overlong lines, but it does not provide an equivalent formatter rule for extracting or wrapping trailing comments. This rule complements Ruff's line-length checks.

## Example
```python
value = compute_value()  # This trailing comment is too long to keep next to the code at the configured line length.
```

Use instead:
```python
# This trailing comment is too long to keep next to the code at the configured
# line length.
value = compute_value()
```

## Options
- `line-length`
