# section-name-capitalization (PDF400)

Fix is sometimes available.

Rule is ignored if `docstring-convention` is `none` or `pep257`.

## What it does
PDF400 reports recognized Google and NumPy section names whose spelling differs from the canonical capitalization for the active docstring convention. It only targets section names parsed by the active convention, so Google sections are ignored unless `docstring-convention = "google"` and NumPy sections are ignored unless `docstring-convention = "numpy"`.

The fix changes only the section name text. It preserves indentation, colons, underlines, line endings, and section content. Concatenated docstrings and source mappings that cannot be safely rewritten are reported without a fix.

## Why is this useful?
Consistent section names make convention-aware parsing and rendered documentation more predictable.

## Ruff compatibility
This rule is intended to replace Ruff's `D405`.

## Examples
PDF400 capitalizes recognized Google section names:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(arg):
    """Return the value.

    args:
        arg: The value.
    """

[output]
def value(arg):
    """Return the value.

    Args:
        arg: The value.
    """
```

PDF400 also applies to NumPy sections when the NumPy convention is active. It changes the section name only and leaves the underline and section body intact:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
def value(arg):
    """Return the value.

    parameters
    ----------
    arg : int
        The value.
    """

[output]
def value(arg):
    """Return the value.

    Parameters
    ----------
    arg : int
        The value.
    """
```

PDF400 does not add missing Google colons. That is handled by PDF402:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(arg):
    """Return the value.

    args
        arg: The value.
    """

[output]
def value(arg):
    """Return the value.

    Args
        arg: The value.
    """
```

Only section names recognized by the active convention are targeted. With the Google convention, NumPy-style section text is ordinary prose for this rule:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(arg):
    """Return the value.

    parameters
    ----------
    arg : int
        The value.
    """

[output=unchanged]
```

Concatenated docstrings are reported when section names can be parsed, but they are not safely rewritten:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(arg):
    ("Return the value.\n\n"
     "args:\n"
     "    arg: The value.")

[output=unchanged]
[findings]
PDF400: Lines 2-4
```

## Options
- `docstring-convention`: Enables Google and NumPy section recognition. `none` and `pep257` ignore this rule.
