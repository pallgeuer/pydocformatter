# extraneous-return-documentation (PDF503)

Fix is not available.

Rule is ignored if `docstring-convention` is `none` or `pep257`.

## What it does
Checks function and method docstrings for return documentation on functions that do not return a meaningful ordinary value.

A meaningful return is `return <expr>` where `<expr>` is not `None`. Functions with no meaningful return, only bare `return`, or any top-level `yield` are treated as not having a normal return value to document. Non-empty return documentation is allowed for explicit `return None` only when the function is not a generator. Functions without docstrings, abstract methods, and stub functions are ignored. Nested functions, classes, and lambdas are ignored by the enclosing function and checked independently when they have their own docstrings.

The rule reports each recognized Google or NumPy return section at the section header, and each parsed reST return field at the field line. Empty return sections and empty reST return fields are still extraneous when the function does not return a meaningful ordinary value. In Google return sections, bare `None` and `None.` entries are treated like `None:` entries.

## Why is this useful?
Extraneous return sections can imply a result where the function does not return one, or can confuse generator stop values with ordinary function returns.

## Ruff compatibility
This rule replaces Ruff's `DOC202`. It follows the same broad intent, while using pydocformatter's configured docstring parser and without Ruff's pydoclint-specific one-line-docstring option.

## Examples
This function documents a return value but never returns one:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def log(value):
    """Log a value.

    Returns:
        None: Nothing.
    """
    print(value)

[output=unchanged]
[findings]
PDF503: Line 4: Docstring has return documentation for a function that does not return
```

Functions with only bare returns do not have an ordinary return value to document. Empty return sections are still stale documentation and are reported even when the function also explicitly returns `None`:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def maybe_stop(flag):
    """Stop if needed.

    Returns:
    """
    if flag:
        return
    return None

[output=unchanged]
[findings]
PDF503: Line 4: Docstring has return documentation for a function that does not return
```

Generator functions are treated as yield-value APIs for this rule. A `return` value in a generator is a stop value, not an ordinary function return to document:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def values():
    """Generate values.

    Yields:
        int: A value.

    Returns:
        int: Stop value.
    """
    yield 1
    return 2

[output=unchanged]
[findings]
PDF503: Line 7: Docstring has return documentation for a generator; generator return values are stop values, not ordinary returns
```

Bare `yield` and `yield None` still make a function a generator, so return documentation is reported as generator return documentation even when no meaningful values are yielded:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def values():
    """Generate values.

    Returns:
        int: Stop value.
    """
    yield None
    return 2

[output=unchanged]
[findings]
PDF503: Line 4: Docstring has return documentation for a generator; generator return values are stop values, not ordinary returns
```

When a function has a meaningful ordinary return, return documentation is allowed:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value():
    """Return a value.

    Returns:
        int: The value.
    """
    return 1

[output=unchanged]
```

The active convention controls what counts as return documentation. Outside the reST convention, reST-looking return fields are ordinary text and are not reported:

```pydocfmt-example
[settings]
docstring-convention = "none"

[input]
def value():
    """Do work.

    :returns: The value.
    """

[output=unchanged]
```

## Options
- `docstring-convention`: Controls whether Google return sections, NumPy return sections, or reST return fields such as `:returns:` and `:rtype:` are recognized. `none` and `pep257` ignore this rule by default.
