# section-underline-format (PDF405)

Fix is usually available.

Rule is disabled if `docstring-convention` is `none`, `pep257`, `google`, or `rest`.

## What it does
PDF405 reports recognized NumPy sections whose underline is missing, separated from the section name by blank lines, uses the wrong adornment character, or does not match the section-name length. The target underline is a line of hyphens immediately after the section name, with the same evaluated indentation as the section name.

The fix inserts, moves, or replaces the underline in safely mapped simple docstrings. It maps the parsed section-name column back to evaluated source before copying the header prefix, so tabbed and mixed-indentation prefixes are preserved exactly. It removes only blank lines between the section name and a misplaced underline. Concatenated docstrings and unsafe source mappings are reported without a fix.

## Why is this useful?
NumPy-style section underlines are part of the section syntax. Normalizing them lets pydocformatter treat the header as one stable structure.

## Ruff compatibility
This rule is intended to replace Ruff's `D407`, `D408`, and `D409`.

## Examples
PDF405 normalizes a malformed NumPy section underline:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
def value(arg):
    """Return the value.

    Parameters
    ===
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

PDF405 also inserts missing underlines and moves misplaced underlines directly below the section name:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
def value(arg):
    """Return the value.

    Parameters

    ==========
    arg : int
        The value.

    Returns
    int
        The value.
    """

[output]
def value(arg):
    """Return the value.

    Parameters
    ----------
    arg : int
        The value.

    Returns
    -------
    int
        The value.
    """
```

The target underline uses the same indentation as the section name, even for malformed indented section headers:

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

[output]
def value(arg):
    """Return the value.

      Parameters
      ----------
    arg : int
        The value.
    """
```

PDF405 only runs for NumPy-style sections. With the Google convention, the same text is not a NumPy section for this rule:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(arg):
    """Return the value.

    Parameters
    ===
    arg : int
        The value.
    """

[output=unchanged]
```

Concatenated docstrings are reported when a malformed NumPy section is parsed, but they are not safely rewritten:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
def value(arg):
    ("Return the value.\n\n"
     "Parameters\n"
     "===\n"
     "arg : int\n"
     "    The value.")

[output=unchanged]
[findings]
PDF405: Lines 2-6: Docstring section 'Parameters' underline should be normalized
```

## Options
None.
