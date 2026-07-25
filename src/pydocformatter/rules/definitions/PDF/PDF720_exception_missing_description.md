# exception-missing-description (PDF720)

Fix is not available.

Rule is disabled if `docstring-convention` is `none` or `pep257`.

## What it does

Checks that each parsed named raised-exception entry includes a prose description. PDF720 checks Google `Raise` and `Raises` sections, NumPy `Raise` and `Raises` sections, and the reStructuredText `raise`, `raises`, `except`, and `exception` field aliases. It checks every parsed primary docstring and supported attached attribute docstring, not only function docstrings.

One finding represents one raw entry and targets its entry line, including every parsed exception name on a multi-name entry in the message. A same-line or indented continuation description satisfies the rule. Whitespace, names, and protected parser structures do not count as prose. Protected structures terminate Google and NumPy entry bodies, so later narrative does not leak backward into an otherwise empty entry. Malformed or nameless reStructuredText fields remain the responsibility of structural rules.

PDF720 is independent of whether the documented exception is raised by the function. PDF506 and PDF507 compare parsed exception documentation with explicit `raise` statements. Emitted-warning entries are a separate family checked by PDF721.

## Why is this useful?

An exception name identifies what can be raised, while its description explains the condition that causes it and helps callers respond correctly.

## Ruff compatibility

None.

## Examples

PDF720 reports Google exception entries without descriptions:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def parse(value):
    """Parse a value.

    Raises:
        ValueError:
        TypeError, LookupError:
        RuntimeError: The runtime state is invalid.
    """

[output=unchanged]
[findings]
PDF720: Line 5: Exception 'ValueError' docstring entry is missing a description
PDF720: Line 6: Exception 'TypeError, LookupError' docstring entry is missing a description
```

PDF720 checks bare and colon-form NumPy entries. An indented continuation is a description:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
def parse(value):
    """Parse a value.

    Raises
    ------
    ValueError
    TypeError
        The value has an invalid type.
    """

[output=unchanged]
[findings]
PDF720: Line 6: Exception 'ValueError' docstring entry is missing a description
```

All named reStructuredText exception aliases are supported. Multi-name fields produce one finding, while nameless fields are outside PDF720:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def parse(value):
    """Parse a value.

    :raises:
    :raises ValueError, TypeError:
    :except LookupError: The value is missing.
    """

[output=unchanged]
[findings]
PDF720: Line 5: Exception 'ValueError, TypeError' docstring entry is missing a description
```

Protected structures are not prose descriptions. Narrative after a protected structure is outside the terminated entry:

````pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def parse(value):
    """Parse a value.

    Raises:
        ValueError:
            ```text
            protected example
            ```
            Narrative after the protected block.
        TypeError: The type is invalid.
    """

[output=unchanged]
[findings]
PDF720: Line 5: Exception 'ValueError' docstring entry is missing a description
````

Parser settings determine which structures are protected. With fenced-code parsing disabled, the same indented text is ordinary parsed description content:

````pydocfmt-example
[settings]
docstring-convention = "google"
docstring-parse-code-fences = false

[input]
def parse(value):
    """Parse a value.

    Raises:
        ValueError:
            ```text
            ordinary parsed content
            ```
    """

[output=unchanged]
````

Raised exceptions and emitted warnings are separate entry families. PDF720 ignores an empty warning entry:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def parse(value):
    """Parse a value.

    Raises:
        ValueError: The value is invalid.

    Warns:
        RuntimeWarning:
    """

[output=unchanged]
```

Supported attached attribute docstrings are checked as well:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
value = 1
"""A module value.

Raises:
    ValueError:
"""

[output=unchanged]
[findings]
PDF720: Line 5: Exception 'ValueError' docstring entry is missing a description
```

## Options

None.
