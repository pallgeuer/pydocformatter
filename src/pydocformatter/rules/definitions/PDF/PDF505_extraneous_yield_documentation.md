# extraneous-yield-documentation (PDF505)

Fix is not available.

## What it does
Checks function and method docstrings for yield documentation on functions that do not yield a meaningful value.

A meaningful yield is `yield <expr>` where `<expr>` is not `None`, or any `yield from <expr>`. Functions with no meaningful yield or only bare `yield` are treated as not having a yielded value to document. Non-empty yield documentation is allowed for explicit `yield None`. Functions without docstrings, abstract methods, and stub functions are ignored. Nested functions, classes, and lambdas are ignored by the enclosing function and checked independently when they have their own docstrings.

The rule reports each recognized Google or NumPy yield section at the section header, and each parsed Sphinx yield field at the field line. Empty yield sections are still extraneous when the function does not yield a meaningful value. In Google yield sections, bare `None` and `None.` entries are treated like `None:` entries.

## Why is this useful?
Extraneous yield sections can make an ordinary function look like a generator.

## Ruff compatibility
This rule replaces Ruff's `DOC403`. It follows the same broad intent, while using pydocformatter's configured docstring parser and without Ruff's pydoclint-specific one-line-docstring option.

## Examples
This ordinary function documents yielded values:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value():
    """Return the value.

    Yields:
        int: A value.
    """
    return 1

[output=unchanged]
[findings]
PDF505: Line 4: Docstring has a yield section for a function that does not yield a meaningful value
```

Functions with only bare yields do not have yielded values to document. Empty yield sections are still stale documentation and are reported even when the function also explicitly yields `None`:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def values():
    """Generate nothing.

    Yields:
    """
    yield
    yield None

[output=unchanged]
[findings]
PDF505: Line 4: Docstring has a yield section for a function that does not yield a meaningful value
```

A yield inside a lambda belongs to the lambda body, not to the enclosing function:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def callback():
    """Create a callback.

    Yields:
        int: A value.
    """
    return lambda: (yield 1)

[output=unchanged]
[findings]
PDF505: Line 4: Docstring has a yield section for a function that does not yield a meaningful value
```

When a function has a meaningful yield or `yield from`, yield documentation is allowed:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def direct():
    """Generate values.

    Yields:
        int: A value.
    """
    yield 1


def delegated(values):
    """Generate values.

    Yields:
        int: A value.
    """
    yield from values

[output=unchanged]
```

The active parser controls what counts as yield documentation. With Sphinx field parsing disabled, Sphinx-looking yield fields are ordinary text and are not reported:

```pydocfmt-example
[settings]
docstring-convention = "none"
docstring-parse-sphinx-fields = false

[input]
def values():
    """Do work.

    :yields: A value.
    """

[output=unchanged]
```

## Options
- `docstring-convention`: Controls whether Google or NumPy yield sections are recognized.
- `docstring-parse-sphinx-fields`: Controls whether Sphinx yield fields such as `:yields:` and `:ytype:` are recognized.
