# exception-entry-normalization (PDF410)

Fix is sometimes available.

Rule is ignored if `docstring-convention` is `none` or `pep257`.

## What it does
PDF410 reports parsed exception and warning entries whose exception-name lists are not in canonical form.

The canonical spelling uses simple or dotted exception names without backtick code spans, with multiple exception names separated by commas. The fix removes single-backtick code spans around individual exception names or around a whole parsed exception-name list, converts pipe separators to commas, and normalizes unambiguous spacing around the parsed exception entry prefix.

Google `Raise`/`Raises` and `Warn`/`Warns` entries, NumPy exception and warning entries, and reST `raise`/`raises`/`except`/`exception` fields are supported under their matching conventions. Google `Warning` and `Warnings` admonition sections are not exception-entry sections for this rule. Nameless reST exception fields such as `:raises:` are left unchanged because their body is prose, not a parsed exception-name list.

The rule only rewrites entries that parse as simple or dotted exception names. It does not normalize arbitrary prose, malformed exception lists, double-backtick code spans, return/yield type expressions, or description text. Concatenated docstrings and source mappings that cannot be safely rewritten are reported without a fix.

## Why is this useful?
Consistent exception-entry spelling keeps convention-aware docstrings readable without wrapping exception names in backticks.

## Ruff compatibility
None.

## Examples
PDF410 normalizes Google exception and warning entries to no backticks. Most entries document one exception or warning per line (but multiple per line are supported):

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(arg):
    """Return the value.

    Raises:
        `ValueError` : Bad value.
        `errors.CustomError` : Custom bad value.

    Warns:
        `RuntimeWarning`: Bad warning.
        `UserWarning` : User-visible warning.
    """

[output]
def value(arg):
    """Return the value.

    Raises:
        ValueError: Bad value.
        errors.CustomError: Custom bad value.

    Warns:
        RuntimeWarning: Bad warning.
        UserWarning: User-visible warning.
    """
```

PDF410 also handles singular Google `Raise` and `Warn` sections, but it leaves Google `Warning` and `Warnings` admonitions alone:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(arg):
    """Return the value.

    Raise:
        `LookupError`|KeyError : Missing value.

    Warn:
        `RuntimeWarning` | UserWarning: Bad warning.

    Warning:
        `DeprecationWarning` | FutureWarning : This prose stays unchanged.
    """

[output]
def value(arg):
    """Return the value.

    Raise:
        LookupError, KeyError: Missing value.

    Warn:
        RuntimeWarning, UserWarning: Bad warning.

    Warning:
        `DeprecationWarning` | FutureWarning : This prose stays unchanged.
    """
```

PDF410 normalizes NumPy exception and warning entries, including bare-name entries with one exception or warning per line:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
def value(arg):
    """Return the value.

    Raises
    ------
    `ValueError`
        Bad value.
    errors.CustomError
        Custom bad value.

    Raise
    -----
    LookupError,KeyError : Missing value.

    Warnings
    --------
    `RuntimeWarning`
        Bad warning.
    UserWarning
        User-visible warning.
    """

[output]
def value(arg):
    """Return the value.

    Raises
    ------
    ValueError
        Bad value.
    errors.CustomError
        Custom bad value.

    Raise
    -----
    LookupError, KeyError: Missing value.

    Warnings
    --------
    RuntimeWarning
        Bad warning.
    UserWarning
        User-visible warning.
    """
```

PDF410 also supports multiple exception names in one entry when that is what the docstring already uses:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(arg):
    """Return the value.

    Raises:
        `ValueError` | errors.CustomError : Bad value.
    """

[output]
def value(arg):
    """Return the value.

    Raises:
        ValueError, errors.CustomError: Bad value.
    """
```

PDF410 normalizes reST exception field aliases, including single exception entries and a whole exception-name list wrapped in one code span:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def value(arg):
    """Return the value.

    :raises   `LookupError` : Missing value.
    :raise `ValueError | errors.CustomError` : Bad value.
    :except RuntimeError|TypeError:
    """

[output]
def value(arg):
    """Return the value.

    :raises LookupError: Missing value.
    :raise ValueError, errors.CustomError: Bad value.
    :except RuntimeError, TypeError:
    """
```

PDF410 leaves malformed exception-like prose, ambiguous separators, and nameless reST exception fields unchanged:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def value(arg):
    """Return the value.

    :raises: `ValueError` | TypeError if parsing fails.
    :raises ValueError || TypeError: Ambiguous separator.
    """

[output=unchanged]
```

PDF410 reports unsafe source mappings without applying a fix:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(arg):
    ("Return the value.\n\n"
     "Raises:\n"
     "    `ValueError` | TypeError : Bad value.")

[output=unchanged]
[findings]
PDF410: Lines 2-4: Docstring exception entry should use canonical spelling
```

## Options
- `docstring-convention`: Controls whether Google sections, NumPy sections, or reST fields are recognized. Ignores PDF410 when set to `none` or `pep257`.
- `docstring-parse-*`: Parser protection settings can affect whether entry-like text inside structures such as code fences and literal blocks is opaque or can be parsed as convention entries.
