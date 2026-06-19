# section-name-pluralization (PDF401)

Fix is sometimes available.

Rule is ignored if `docstring-convention` is `none` or `pep257`.

## What it does
PDF401 reports recognized Google and NumPy section names whose spelling uses a singular form when the plural form is preferred. Examples include `Arg` to `Args`, `Return` to `Returns`, `Warning` to `Warnings`, and NumPy `Other Param` to `Other Params`. It also reports parsed reStructuredText field names whose singular or plural spelling differs from the preferred Sphinx-style spelling: `returns` becomes `return`, `yields` becomes `yield`, and `raise` becomes `raises`.

The rule only targets structures parsed by the active convention. Google sections are ignored unless `docstring-convention = "google"`, NumPy sections are ignored unless `docstring-convention = "numpy"`, and reStructuredText fields are ignored unless `docstring-convention = "rest"`. It does not normalize equivalent section or field terms such as `Arguments` to `Args` or `parameter` to `param`; PDF402 handles that separately.

The fix changes only the section or field name text. It preserves indentation, colons, line endings, field arguments, underlines, and content. If a NumPy section name changes length, the underline may no longer match the section-name length after running only PDF401; PDF405 handles NumPy underline normalization separately. Concatenated docstrings and source mappings that cannot be safely rewritten are reported without a fix.

## Why is this useful?
Consistent plural section names make convention-aware docstrings easier to scan and reduce equivalent spellings for the same section type.

## Ruff compatibility
None.

## Examples
PDF401 pluralizes recognized Google section names:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(arg):
    """Return the value.

    Arg:
        arg: The value.

    Return:
        int: The value.
    """

[output]
def value(arg):
    """Return the value.

    Args:
        arg: The value.

    Returns:
        int: The value.
    """
```

PDF401 handles longer singular section names and narrative sections without changing equivalent terms. PDF402 handles term normalization separately:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(arg):
    """Return the value.

    Keyword Argument:
        arg: The value.

    Other Arg:
        other: Other value.

    Example:
        value(1)

    Warning:
        Be careful.
    """

[output]
def value(arg):
    """Return the value.

    Keyword Arguments:
        arg: The value.

    Other Args:
        other: Other value.

    Examples:
        value(1)

    Warnings:
        Be careful.
    """
```

PDF401 also pluralizes recognized NumPy section names. The output shows only the PDF401 fix, so the NumPy underlines are preserved even when the changed section names no longer match them:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
def value(arg):
    """Return the value.

    Parameter
    ---------
    arg : int
        The value.

    Other Param
    -----------
    other : str
        Other value.
    """

[output]
def value(arg):
    """Return the value.

    Parameters
    ---------
    arg : int
        The value.

    Other Params
    -----------
    other : str
        Other value.
    """
```

PDF401 normalizes preferred singular and plural spellings for parsed reStructuredText fields. It uses the preferred spelling even when the original field name has different capitalization:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def value(arg):
    """Return the value.

    :RETURNS: The value.
    :Yields: Streamed value.
    :raise ValueError: Bad value.
    """

[output]
def value(arg):
    """Return the value.

    :return: The value.
    :yield: Streamed value.
    :raises ValueError: Bad value.
    """
```

PDF401 leaves already plural but differently capitalized section names to PDF400, and leaves equivalent field terms to PDF402:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(arg):
    """Return the value.

    arguments:
        arg: The value.
    """

[output=unchanged]
```

PDF401 reports unsafe source mappings without applying a fix:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(arg):
    ("Return the value.\n\n"
     "Return:\n"
     "    int: The value.")

[output=unchanged]
[findings]
PDF401: Lines 2-4: Docstring section name 'Return' should use plural form 'Returns'
```

## Options
- `docstring-convention`: Enables Google and NumPy section recognition and reStructuredText field recognition. `none` and `pep257` ignore this rule.
