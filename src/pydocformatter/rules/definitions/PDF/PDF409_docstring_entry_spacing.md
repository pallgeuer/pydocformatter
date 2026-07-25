# docstring-entry-spacing (PDF409)

Fix is sometimes available.

Rule is disabled if `docstring-convention` is `none` or `pep257`.

## What it does
PDF409 reports recognized convention entries and reST fields whose nominal prefix spacing is not canonical for the active docstring convention.

For Google docstrings, the fix normalizes parsed parameter, attribute, method, field, return, yield, exception, and warning entry prefixes. Starred parameters and dotted names are preserved. For NumPy docstrings, the fix normalizes comma-separated entry names and spacing around the name/type colon, including exception and warning entries that use a same-line description. For reST docstrings, the fix normalizes spacing around field names, field arguments, colons, and same-line descriptions.

The rule only targets entries and fields parsed under the active convention. It does not normalize arbitrary prose or malformed entry-like text, reflow continuation lines, or semantically rewrite type expressions beyond trimming leading and trailing whitespace around parsed type text. For parsed exception and warning entries, PDF409 normalizes prefix spacing but preserves exception-list spelling such as backticks and pipe separators; PDF410 handles canonical exception-name spelling. Concatenated docstrings and source mappings that cannot be safely rewritten are reported without a fix.

## Why is this useful?
Consistent entry-prefix spacing makes convention-aware docstrings easier to scan and avoids low-value diffs from hand-spaced parameter, type, and field syntax.

## Ruff compatibility
None.

## Examples
PDF409 normalizes the prefix of Google convention entries:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(arg):
    """Return the value.

    Args:
        arg   ( int ) : The value.
    """

[output]
def value(arg):
    """Return the value.

    Args:
        arg (int): The value.
    """
```

PDF409 preserves Google entry semantics while normalizing starred parameters, dotted names, return and yield types, raised exceptions, and emitted warnings:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def collect(*args, **kwargs):
    """Collect values.

    Args:
        *args   ( tuple[str, ...] ) : Positional values.
        **kwargs   ( dict[str, object] ) :
        model.value : Dotted value.

    Yields:
        tuple[ int, int ] : Pair.

    Raises:
        ValueError   : Bad value.

    Warns:
        `RuntimeWarning` | UserWarning   : Possibly unstable.
    """

[output]
def collect(*args, **kwargs):
    """Collect values.

    Args:
        *args (tuple[str, ...]): Positional values.
        **kwargs (dict[str, object]):
        model.value: Dotted value.

    Yields:
        tuple[ int, int ]: Pair.

    Raises:
        ValueError: Bad value.

    Warns:
        `RuntimeWarning` | UserWarning: Possibly unstable.
    """
```

PDF409 normalizes NumPy comma-separated parameter names and type separators plus warning-entry prefix spacing, but leaves continuation descriptions alone:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
def value(first, second):
    """Return the value.

    Parameters
    ----------
    first,second:int
        The values.
        Keep   description   spacing.

    Warns
    -----
    `RuntimeWarning` | UserWarning  :  Possibly unstable.
    """

[output]
def value(first, second):
    """Return the value.

    Parameters
    ----------
    first, second : int
        The values.
        Keep   description   spacing.

    Warns
    -----
    `RuntimeWarning` | UserWarning: Possibly unstable.
    """
```

PDF409 normalizes reST parameter, type, return, yield, and exception fields:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def value(arg, other):
    """Return the value.

    :param   int   arg : The value.
    :param other: Another value.
    :type other:list[str]
    :returns  : Result.
    :rtype:list[str]
    :yield   item : Next item.
    :raises   ValueError : Bad value.
    """

[output]
def value(arg, other):
    """Return the value.

    :param int arg: The value.
    :param other: Another value.
    :type other: list[str]
    :returns: Result.
    :rtype: list[str]
    :yield item: Next item.
    :raises ValueError: Bad value.
    """
```

PDF409 normalizes spacing around parsed exception and warning entries but leaves exception-name list spelling to PDF410:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def value(arg):
    """Return the value.

    :raises   `ValueError` | TypeError : Bad value.
    """

[output]
def value(arg):
    """Return the value.

    :raises `ValueError` | TypeError: Bad value.
    """
```

PDF409 does not rewrite malformed entry-like text or protected structures:

````pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(arg):
    """Return the value.

    Args:
        arg   ( int ) Description missing colon.

        ```text
        protected   ( int ) : Not an entry.
        ```
    """

[output=unchanged]
````

Parser settings can expose otherwise protected entry-like text:

```pydocfmt-example
[settings]
docstring-convention = "google"
docstring-parse-literal-blocks = false

[input]
def value(arg):
    """Return the value.

    Args:
        Example::

            literal   ( int ) : Entry-like text.
    """

[output]
def value(arg):
    """Return the value.

    Args:
        Example::

            literal (int): Entry-like text.
    """
```

PDF409 is ignored when no supported docstring convention is active:

```pydocfmt-example
[settings]
docstring-convention = "none"

[input]
def value(arg):
    """Return the value.

    Args:
        arg   ( int ) : The value.
    """

[output=unchanged]
```

PDF409 reports unsafe source mappings without applying a fix:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(arg):
    ("Return the value.\n\n"
     "Args:\n"
     "    arg   (int) : The value.")

[output=unchanged]
[findings]
PDF409: Lines 2-4: Docstring convention entry spacing should be normalized
```

## Options
None.
