# section-name-trailing-colon (PDF402)

Fix is sometimes available.

Rule is ignored if `docstring-convention` is `none`, `numpy`, or `pep257`.

## What it does
PDF402 reports recognized Google section names that are missing the required trailing colon. The fix adds one colon immediately after the stripped section name and removes spaces or tabs that appeared after the section name on that line.

The fix is available for safely mapped simple docstrings. Concatenated docstrings and source mappings that cannot be safely rewritten are reported without a fix.

## Why is this useful?
The colon is part of Google-style section header spelling and helps distinguish headers from ordinary prose.

## Ruff compatibility
This rule is intended to replace Ruff's `D416`.

## Examples
PDF402 adds a missing Google section-name colon:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(arg):
    """Return the value.

    Args
        arg: The value.
    """

[output]
def value(arg):
    """Return the value.

    Args:
        arg: The value.
    """
```

Multiple missing colons in one docstring are fixed together, and trailing spaces or tabs after the section name are removed:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(arg):
    """Return the value.

    Args
        arg: The value.

    Returns	
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

PDF402 does not capitalize section names while adding the colon. That is handled by PDF400:

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

    args:
        arg: The value.
    """
```

Already-colonized section names are left to whitespace rules, even if trailing whitespace remains on the line:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(arg):
    """Return the value.

    Args:   
        arg: The value.
    """

[output=unchanged]
```

PDF402 only applies to Google sections. NumPy-style section names do not require a trailing colon:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
def value(arg):
    """Return the value.

    Parameters
    ----------
    arg : int
        The value.
    """

[output=unchanged]
```

Concatenated docstrings are reported when a missing Google section colon can be parsed, but they are not safely rewritten:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(arg):
    ("Return the value.\n\n"
     "Args\n"
     "    arg: The value.")

[output=unchanged]
[findings]
PDF402: Lines 2-4
```

## Options
- `docstring-convention`: Enables Google section recognition. `none`, `numpy`, and `pep257` ignore this rule.
