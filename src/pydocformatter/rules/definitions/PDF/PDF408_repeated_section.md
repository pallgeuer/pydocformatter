# repeated-section (PDF408)

Fix is not available.

Rule is ignored if `docstring-convention` is `none` or `pep257`.

## What it does
PDF408 reports recognized Google and NumPy sections, plus non-named reST fields under the reST convention, that repeat within one docstring under the active convention. The first occurrence is allowed, and each later matching item is reported.

Known spelling variants for the same section are treated as repeats, such as Google `Args` and `Arguments`, Google `Example` and `Examples`, Google `Return` and `Returns`, Google `Warning` and `Warnings`, or NumPy `Other Parameters` and `Other Params`. Matching is case-insensitive. Google `Warns` documents emitted warnings and is distinct from the `Warning`/`Warnings` admonition sections.

Named reST parameter, attribute, exception, and named type field repetition is handled by PDF412 instead.

The rule only considers syntax that is recognized by the active convention. Google-style recognition is used only when `docstring-convention = "google"`, NumPy-style recognition is used only when `docstring-convention = "numpy"`, and reST fields are recognized only when `docstring-convention = "rest"`. For example, a repeated NumPy-only `Parameters` section is ignored under the Google convention, and a Google-style `Parameters:` line is ignored under the NumPy convention.

PDF408 is diagnostic only. It does not merge repeated sections or otherwise rewrite the docstring.

## Why is this useful?
Repeated sections split related documentation across multiple places, make convention-aware parsing ambiguous, and can hide later documentation from tools that expect one section of each semantic kind.

## Ruff compatibility
None.

## Examples
PDF408 reports repeated Google sections:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(arg):
    """Return the value.

    Args:
        arg: The value.

    Args:
        arg: More detail.
    """

[output=unchanged]
[findings]
PDF408: Line 7: Docstring section 'Args' repeats earlier section 'Args'
```

Every repeat after the first matching section is reported:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(arg):
    """Return the value.

    Args:
        arg: The value.

    Args:
        arg: More detail.

    Args:
        arg: Even more detail.
    """

[output=unchanged]
[findings]
PDF408: Line 7: Docstring section 'Args' repeats earlier section 'Args'
PDF408: Line 10: Docstring section 'Args' repeats earlier section 'Args'
```

Google spelling variants for the same semantic section are also reported:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(arg):
    """Return the value.

    Args:
        arg: The value.

    Arguments:
        arg: More detail.
    """

[output=unchanged]
[findings]
PDF408: Line 7: Docstring section 'Arguments' repeats earlier section 'Args'
```

Several alias families may be reported in one docstring:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(arg):
    """Return the value.

    Example:
        value(1)

    Examples:
        value(2)

    Return:
        int: The value.

    Returns:
        int: More detail.

    Warning:
        The value may be approximate.

    Warns:
        RuntimeWarning: If the value is approximate.

    Warnings:
        UserWarning: If the value is approximate.
    """

[output=unchanged]
[findings]
PDF408: Line 7: Docstring section 'Examples' repeats earlier section 'Example'
PDF408: Line 13: Docstring section 'Returns' repeats earlier section 'Return'
PDF408: Line 22: Docstring section 'Warnings' repeats earlier section 'Warning'
```

Different recognized sections are allowed, even when they share a related role or the same order rank:

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
    """

[output=unchanged]
```

Google section headers are still recognized if a separate style rule would add a missing colon:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(arg):
    """Return the value.

    Args
        arg: The value.

    Args:
        arg: More detail.
    """

[output=unchanged]
[findings]
PDF408: Line 7: Docstring section 'Args' repeats earlier section 'Args'
```

Section-like text inside protected structures is not counted when that structure parser is enabled:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(arg):
    """Return the value.

    Example::

        Args:
            arg: This is literal example text.

    Args:
        arg: The value.
    """

[output=unchanged]
```

If the relevant `docstring-parse-*` protection is disabled, the same section-like text can be parsed as a section and later repeats can be reported:

```pydocfmt-example
[settings]
docstring-convention = "google"
docstring-parse-literal-blocks = false

[input]
def value(arg):
    """Return the value.

    Example::

        Args:
            arg: This is literal example text.

    Args:
        arg: The value.
    """

[output=unchanged]
[findings]
PDF408: Line 9: Docstring section 'Args' repeats earlier section 'Args'
```

PDF408 also reports repeated NumPy sections:

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

    Parameters
    ----------
    option : int
        The option.
    """

[output=unchanged]
[findings]
PDF408: Line 9: Docstring section 'Parameters' repeats earlier section 'Parameters'
```

NumPy spelling variants for the same section are reported:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
def value(arg):
    """Return the value.

    Other Parameters
    ----------------
    arg : int
        The value.

    Other Params
    ------------
    option : int
        The option.
    """

[output=unchanged]
[findings]
PDF408: Line 9: Docstring section 'Other Params' repeats earlier section 'Other Parameters'
```

PDF408 also reports repeated non-named reST fields under the reST convention:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def value(arg):
    """Return the value.

    :returns: The value.
    :return: More detail.
    """

[output=unchanged]
[findings]
PDF408: Line 5: Docstring field ':return:' repeats earlier field ':returns:'
```

Non-named type fields and unknown fields repeat within their own field family:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def value(arg):
    """Return the value.

    :rtype: int
    :rtype: str
    :meta private: yes
    :meta public: yes
    :meta private: still private
    """

[output=unchanged]
[findings]
PDF408: Line 5: Docstring field ':rtype:' repeats earlier field ':rtype:'
PDF408: Line 8: Docstring field ':meta private:' repeats earlier field ':meta private:'
```

Repeated named reST entries are handled by PDF412 instead:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def value(arg):
    """Return the value.

    :param arg: The value.
    :parameter arg: More detail.
    """

[output=unchanged]
```

Convention recognition matters. A Google-style colon section is not counted as a NumPy section:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
def value(arg):
    """Return the value.

    Parameters:
        arg: The value.

    Parameters
    ----------
    arg : int
        More detail.
    """

[output=unchanged]
```

PDF408 reports repeated sections in non-simple docstring literals, but still does not fix them:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(arg):
    ("Return the value.\n\n"
     "Args:\n"
     "    arg: The value.\n\n"
     "Args:\n"
     "    arg: More detail.")

[output=unchanged]
[findings]
PDF408: Lines 2-6: Docstring section 'Args' repeats earlier section 'Args'
```

## Options
- `docstring-convention`: Enables Google and NumPy section recognition and reST field recognition. `none` and `pep257` ignore this rule.
- `docstring-parse-*`: Controls whether section-like text inside protected structures, such as literal blocks or code fences, is ignored as structure content or can be parsed as ordinary section text.
