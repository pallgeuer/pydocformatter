# missing-yield-documentation (PDF504)

Fix is not available.

Rule is disabled if `docstring-convention` is `none` or `pep257`.

## What it does
Checks function and method docstrings for missing yield-value documentation when the function body has a meaningful yielded value.

A meaningful yield is `yield <expr>` where `<expr>` is not `None`, or any `yield from <expr>`. Bare `yield`, `yield None`, functions without docstrings, abstract methods, and stub functions are ignored. Nested functions, classes, and lambdas are ignored by the enclosing function and checked independently when they have their own docstrings.

Yield documentation is present when the active docstring parser finds a non-empty Google yield section, NumPy yield section, or reST yield field. In Google yield sections, bare `None` and `None.` entries are treated like `None:` entries.

By default, this rule reports missing yield documentation only when the docstring already has recognized yield documentation, such as an empty yield section. Broader shared missing-documentation modes can require yield documentation for public docstrings with body content, or for all public docstrings.

## Why is this useful?
Yield documentation explains each produced value in generator APIs.

## Ruff compatibility
This rule replaces Ruff's `DOC402`. It follows the same broad intent, while using pydocformatter's configured docstring parser and without Ruff's pydoclint-specific one-line-docstring option.

## Examples
This generator yields a meaningful value without documenting it:

```pydocfmt-example
[settings]
docstring-convention = "google"
docstring-missing-documentation = "all-docstrings"

[input]
def values():
    """Generate values."""
    yield 1

[output=unchanged]
[findings]
PDF504: Line 3: Function yield value is missing docstring documentation
```

The rule reports the first meaningful yield. Bare `yield`, `yield None`, and yields inside nested lambda bodies do not count as yielded values of the enclosing function:

```pydocfmt-example
[settings]
docstring-convention = "google"
docstring-missing-documentation = "all-docstrings"

[input]
def values(items):
    """Generate values."""
    yield
    yield None
    callback = lambda: (yield 1)
    yield from items

[output=unchanged]
[findings]
PDF504: Line 6: Function yield value is missing docstring documentation
```

Async generators are checked in the same way as synchronous generators:

```pydocfmt-example
[settings]
docstring-convention = "google"
docstring-missing-documentation = "all-docstrings"

[input]
async def values():
    """Generate values."""
    yield 1

[output=unchanged]
[findings]
PDF504: Line 3: Function yield value is missing docstring documentation
```

Recognized yield documentation satisfies the rule. Google sections, reST fields, and NumPy sections are all valid when the matching convention is active:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def google_values():
    """Generate values.

    Yields:
        int: A value.
    """
    yield 1


def none_values():
    """Generate values.

    Yields:
        None.
    """
    yield 2

[output=unchanged]
```

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def rest_values():
    """Generate values.

    :ytype: int
    """
    yield 1

[output=unchanged]
```

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
def numpy_values():
    """Generate values.

    Yields
    ------
    int
        A value.
    """
    yield 1

[output=unchanged]
```

The active convention controls which documentation is recognized. Under `none` and `pep257`, this rule is disabled even when selected explicitly:

```pydocfmt-example
[settings]
docstring-convention = "none"
docstring-missing-documentation = "all-docstrings"

[input]
def values():
    """Generate values.

    :yields: A value.
    """
    yield 1

[output=unchanged]
```

## Options
- `docstring-missing-documentation`: Controls whether missing yield documentation is reported only when yield documentation already exists, for non-summary docstrings, or for all eligible docstrings.
- `docstring-missing-documentation-public-only`: Limits broad missing-yield checks to public functions and methods when enabled.
