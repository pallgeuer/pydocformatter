# section-order (PDF407)

Fix is not available.

Rule is ignored if `docstring-convention` is `none` or `pep257`.

## What it does
PDF407 reports recognized Google and NumPy sections, plus rest fields under the rest convention, that appear after a later ordered item for the active convention. Duplicate sections and fields with the same order rank are allowed.

For Google docstrings, PDF407 orders parameter sections before return/yield sections before raise/warn sections. Other recognized Google sections, such as examples and notes, are unordered and do not affect diagnostics. For NumPy docstrings, PDF407 follows the conventional numpydoc section order used by Ruff-style section-order checks. For rest docstrings, PDF407 orders parameter fields before return/yield fields before exception fields.

## Why is this useful?
Consistent section order helps readers find parameters, returns, yields, raises, and related documentation quickly.

## Ruff compatibility
This rule is intended to replace Ruff's `D420`.

## Examples
PDF407 reports a Google parameter section that appears after a return section:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(arg):
    """Return the value.

    Returns:
        int: The value.

    Args:
        arg: The value.
    """

[output=unchanged]
[findings]
PDF407: Line 7: Docstring section 'Args' should appear before 'Returns'
```

Once a later ordered section has appeared, every earlier-ranked ordered section after it is reported:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(arg):
    """Return the value.

    Raises:
        ValueError: If the value is invalid.

    Returns:
        int: The value.

    Args:
        arg: The value.
    """

[output=unchanged]
[findings]
PDF407: Line 7: Docstring section 'Returns' should appear before 'Raises'
PDF407: Line 10: Docstring section 'Args' should appear before 'Raises'
```

Unordered Google sections, such as `Examples`, do not affect ordering and do not reset the highest ordered section already seen:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(arg):
    """Return the value.

    Returns:
        int: The value.

    Examples:
        value(1)

    Args:
        arg: The value.
    """

[output=unchanged]
[findings]
PDF407: Line 10: Docstring section 'Args' should appear before 'Returns'
```

Duplicate sections and sections with the same order rank are allowed:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(arg, option):
    """Return the value.

    Args:
        arg: The value.

    Keyword Args:
        option: The option.

    Returns:
        int: The value.

    Yields:
        int: Streamed values.
    """

[output=unchanged]
```

PDF407 also applies to NumPy sections using NumPy section order:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
def value(arg):
    """Return the value.

    Returns
    -------
    int
        The value.

    Parameters
    ----------
    arg : int
        The value.
    """

[output=unchanged]
[findings]
PDF407: Line 9: Docstring section 'Parameters' should appear before 'Returns'
```

PDF407 also applies to rest fields under the rest convention:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def value(arg):
    """Return the value.

    :returns: The value.
    :param arg: The value.
    """

[output=unchanged]
[findings]
PDF407: Line 5: Docstring field ':param arg:' should appear before ':returns:'
```

## Options
- `docstring-convention`: Enables Google and NumPy section recognition and rest field recognition. `none` and `pep257` ignore this rule.
