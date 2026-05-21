# standalone-comment-too-long (PCF001)

Fix is always available.

## What it does
Checks for standalone comment blocks that need wrapping or spacing normalization.

## Why is this useful?
Formatted standalone comments stay readable at the configured line length without changing nearby code.

## Ruff compatibility
Ruff does not provide an equivalent formatter rule for standalone comment wrapping. This rule complements Ruff's linting by formatting comments that pydocformatter can safely rewrite.

## Example
```python
# This standalone comment is long enough that it should be wrapped to keep the source readable at the configured line length.
```

Use instead:
```python
# This standalone comment is long enough that it should be wrapped to keep the
# source readable at the configured line length.
```

## Options
- `line-length`
