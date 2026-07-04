# blank-line-before-function-docstring (PDF205)

Fix is always available.

Rule is ignored by broad selectors for all `docstring-convention` values. Select `PDF205` exactly to opt into this spacing style. If `PDF204` is also selected through a broader selector, ignore `PDF204` so the incompatible default style does not disable `PDF205`.

Rule is incompatible with `PDF204`.

## What it does
PDF205 requires exactly one blank line immediately before function, method, and nested-function docstrings.

Only the adjacent blank-line run before the docstring statement is changed. Comments, decorators, function headers, and non-blank lines before the docstring are preserved. The rule applies to ordinary functions, async functions, methods, and nested functions. It does not apply to class docstrings, attribute docstrings, or simple-suite docstrings written on the same physical line as the function header.

## Why is this useful?
Some projects prefer visually separating the function header and any leading body comments from the docstring statement.

## Ruff compatibility
None. This is the style-opposite companion to `PDF204`, which replaces Ruff's `D201`.

## Examples
The canonical fix inserts one blank line before a function docstring:

```pydocfmt-example
[input]
def function():
    """Docstring."""
    return None

[output]
def function():

    """Docstring."""
    return None
```

Excess blank lines are collapsed to one, and leading comments stay attached above the inserted separator:

```pydocfmt-example
[input]
def function():
    # Leading comment.


    """Docstring."""
    return None

[output]
def function():
    # Leading comment.

    """Docstring."""
    return None
```

Decorated async functions are handled the same way:

```pydocfmt-example
[input]
@decorator
async def function():
    """Docstring."""
    return None

[output]
@decorator
async def function():

    """Docstring."""
    return None
```

Attribute docstrings are ignored:

```pydocfmt-example
[input]
def function():
    value = 1
    """Attribute docstring."""
    return value

[output=unchanged]
```

## Options
None. `docstring-convention` does not change this rule's behavior. Broad selectors ignore this rule for every convention; select `PDF205` exactly to use it, and ignore `PDF204` if that incompatible companion is also selected.
