# missing-return-documentation (PDF502)

Fix is not available.

## What it does
Checks function and method docstrings for missing return-value documentation when the function body has a meaningful return value.

A meaningful return is `return <expr>` where `<expr>` is not `None`. Bare `return`, `return None`, any generator function, functions without docstrings, abstract methods, and stub functions are ignored. A function is a generator for this rule if it contains any top-level `yield`, including bare `yield` and `yield None`. Nested functions, classes, and lambdas are ignored by the enclosing function and checked independently when they have their own docstrings.

Return documentation is present when the active docstring parser finds a non-empty Google return section, NumPy return section, or rest return field. In Google return sections, bare `None` and `None.` entries are treated like `None:` entries.

By default, this rule reports missing return documentation only when the docstring already has recognized return documentation, such as an empty return section. Broader shared missing-documentation modes can require return documentation for public docstrings with body content, or for all public docstrings.

## Why is this useful?
Return documentation explains the meaning of values that cannot always be inferred from annotations alone.

## Ruff compatibility
This rule replaces Ruff's `DOC201`. It follows the same broad intent, while using pydocformatter's configured docstring parser and without Ruff's pydoclint-specific one-line-docstring or property-decorator options.

## Examples
This function returns a meaningful value without documenting it:

```pydocfmt-example
[settings]
docstring-convention = "google"
docstring-missing-documentation = "all-docstrings"

[input]
def calculate(value):
    """Calculate a value."""
    return value + 1

[output=unchanged]
[findings]
PDF502: Line 3: Function return value is missing docstring documentation
```

The rule reports the first meaningful return in each checked function. Bare `return`, `return None`, and generator stop values are not ordinary return-value documentation targets:

```pydocfmt-example
[settings]
docstring-convention = "google"
docstring-missing-documentation = "all-docstrings"

[input]
def value(flag):
    """Return a value."""
    if flag == "skip":
        return
    if flag == "empty":
        return None
    return flag


def generator():
    """Generate values."""
    yield 1
    return 2


def empty_generator():
    """Generate no values."""
    yield None
    return 3

[output=unchanged]
[findings]
PDF502: Line 7: Function return value is missing docstring documentation
```

Recognized return documentation satisfies the rule. Google sections, rest fields, and NumPy sections are all valid when the matching convention is active:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def google_value():
    """Return a value.

    Returns:
        int: The value.
    """
    return 1


def none_value():
    """Return a value.

    Returns:
        None.
    """
    return 2

[output=unchanged]
```

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def rest_value():
    """Return a value.

    :rtype: int
    """
    return 1

[output=unchanged]
```

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
def numpy_value():
    """Return a value.

    Returns
    -------
    int
        The value.
    """
    return 1

[output=unchanged]
```

The active convention controls which documentation is recognized. Outside the rest convention, a rest-looking return field is ordinary text and does not document the return value:

```pydocfmt-example
[settings]
docstring-convention = "none"
docstring-missing-documentation = "all-docstrings"

[input]
def value():
    """Return a value.

    :returns: The value.
    """
    return 1

[output=unchanged]
[findings]
PDF502: Line 6: Function return value is missing docstring documentation
```

## Options
- `docstring-convention`: Controls whether Google return sections, NumPy return sections, or rest return fields such as `:returns:` and `:rtype:` are recognized.
- `docstring-missing-documentation`: Controls when missing return documentation is reported. `has-section` reports only docstrings with recognized return documentation. `non-summary-docstrings` additionally reports public docstrings with more than just a summary. `all-docstrings` additionally reports all public docstrings.
- `docstring-missing-documentation-public-only`: When `true`, the broad parts of `non-summary-docstrings` and `all-docstrings` apply only to public functions and methods. Explicit return documentation is always checked, including for private functions.
