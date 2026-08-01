# section-name-capitalization (PDF400)

Fix is usually available.

Rule is disabled if `docstring-convention` is `none` or `pep257`.

## What it does
PDF400 reports recognized Google and NumPy section names whose spelling differs from the canonical capitalization for the active docstring convention. Canonical section-name capitalization is title case, such as `Args`, `Keyword Args`, `Other Parameters`, and `See Also`. It also reports parsed reStructuredText field names that are not lowercase, including standard fields such as `:param:` and custom fields such as `:custom-field:`.

The rule only targets structures parsed by the active convention. Google sections are ignored unless `docstring-convention = "google"`, NumPy sections are ignored unless `docstring-convention = "numpy"`, and reStructuredText fields are ignored unless `docstring-convention = "rest"`. It does not add missing Google colons, pluralize singular section names, or normalize equivalent terms; those are handled by PDF404, PDF401, and PDF402 respectively.

The fix changes only the section or field name text. It preserves indentation, colons, underlines, line endings, field arguments, and section or field content. Concatenated docstrings and source mappings that cannot be safely rewritten are reported without a fix.

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

PDF400 handles mixed-case and singular recognized Google section names, but it does not pluralize them:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(arg):
    """Return the value.

    arg:
        arg: The value.

    wARnS:
        RuntimeWarning: May warn.
    """

[output]
def value(arg):
    """Return the value.

    Arg:
        arg: The value.

    Warns:
        RuntimeWarning: May warn.
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

PDF400 lowercases parsed reStructuredText field names when the reStructuredText convention is active:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def value(arg):
    """Return the value.

    :PARAM arg: The value.
    :Meta private: yes
    :CUSTOM-FIELD value: Preserved content.
    """

[output]
def value(arg):
    """Return the value.

    :param arg: The value.
    :meta private: yes
    :custom-field value: Preserved content.
    """
```

PDF400 does not add missing Google colons. That is handled by PDF404:

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
PDF400: Lines 2-4: Docstring section name 'args' should be capitalized as 'Args'
```

## Options
None.
