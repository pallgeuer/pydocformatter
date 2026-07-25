# warning-missing-description (PDF721)

Fix is not available.

Rule is disabled if `docstring-convention` is `none`, `pep257`, or `rest`.

## What it does

Checks that each parsed named emitted-warning entry includes a prose description. PDF721 checks Google and NumPy `Warn` and `Warns` sections. It checks every parsed primary docstring and supported attached attribute docstring, not only function docstrings.

One finding represents one raw entry and targets its entry line, including every parsed warning name on a multi-name entry in the message. A same-line or indented continuation description satisfies the rule. Whitespace, names, and protected parser structures do not count as prose. Protected structures terminate entry bodies, so later narrative does not leak backward into an otherwise empty entry.

Google and NumPy `Warning` and `Warnings` caution sections are narrative content and are intentionally not treated as emitted-warning entries. Raised-exception entries are a separate family checked by PDF720.

## Why is this useful?

A warning class identifies the emitted category, while its description explains when callers should expect the warning and whether they need to take action.

## Ruff compatibility

None.

## Examples

PDF721 reports Google emitted-warning entries without descriptions:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def parse(value):
    """Parse a value.

    Warns:
        RuntimeWarning:
        UserWarning, FutureWarning:
        DeprecationWarning: The legacy form is deprecated.
    """

[output=unchanged]
[findings]
PDF721: Line 5: Warning 'RuntimeWarning' docstring entry is missing a description
PDF721: Line 6: Warning 'UserWarning, FutureWarning' docstring entry is missing a description
```

PDF721 checks NumPy emitted-warning sections. An indented continuation is a description:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
def parse(value):
    """Parse a value.

    Warns
    -----
    RuntimeWarning
    FutureWarning
        Future behavior will change.
    """

[output=unchanged]
[findings]
PDF721: Line 6: Warning 'RuntimeWarning' docstring entry is missing a description
```

Protected structures are not prose descriptions:

````pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def parse(value):
    """Parse a value.

    Warns:
        RuntimeWarning:
            ```text
            protected example
            ```
        FutureWarning: Future behavior will change.
    """

[output=unchanged]
[findings]
PDF721: Line 5: Warning 'RuntimeWarning' docstring entry is missing a description
````

Parser settings determine which structures are protected. With list-item parsing disabled, an indented list item is ordinary parsed description content:

```pydocfmt-example
[settings]
docstring-convention = "google"
docstring-parse-list-items = false

[input]
def parse(value):
    """Parse a value.

    Warns:
        RuntimeWarning:
            - ordinary parsed content
    """

[output=unchanged]
```

Google and NumPy caution sections are not emitted-warning documentation:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
def parse(value):
    """Parse a value.

    Warnings
    --------
    Experimental behavior may change.
    """

[output=unchanged]
```

Warning and exception entries are separate families. PDF721 ignores an empty raised-exception entry:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def parse(value):
    """Parse a value.

    Raises:
        ValueError:

    Warns:
        RuntimeWarning: A fallback was used.
    """

[output=unchanged]
```

Supported attached attribute docstrings are checked as well:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
value = 1
"""A module value.

Warns
-----
RuntimeWarning
"""

[output=unchanged]
[findings]
PDF721: Line 6: Warning 'RuntimeWarning' docstring entry is missing a description
```

## Options

None.
