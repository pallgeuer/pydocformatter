# method-missing-description (PDF723)

Fix is not available.

Rule is disabled if `docstring-convention` is `none`, `pep257`, or `rest`.

## What it does
Checks that each parsed named entry in a Google or NumPy `Methods` section includes a prose description. PDF723 checks only primary class docstrings, including nested and function-local classes.

One finding represents one parsed method entry and targets its entry head. Google `name(signature):` and NumPy `name(signature)` forms accept balanced signatures as opaque text, so parameter annotations, defaults, quoted delimiters, and nested containers inside a signature are not reinterpreted as docstring type syntax. The existing Google `name:` and NumPy `name : type` forms remain accepted for compatibility. Same-line and indented continuation descriptions satisfy the rule. Whitespace and protected structures such as lists, code blocks, tables, and directives do not count as prose. Parser-protection settings determine which structures remain protected.

PDF723 does not check whether the documented method exists on the class. Unknown or future method names therefore remain in scope. Empty sections, malformed entries, repeated entries, and description wording remain the responsibility of their corresponding structural and style rules.

## Why is this useful?
A method name or signature identifies an operation but does not explain its purpose, behavior, or role in the class API.

## Ruff compatibility
None.

## Examples
PDF723 reports a Google method entry without a description:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
class Client:
    """Coordinate remote operations.

    Methods:
        connect():
        close(): Close the active connection.
    """

[output=unchanged]
[findings]
PDF723: Line 5: Method 'connect' docstring entry is missing a description
```

Bare Google method names remain accepted for compatibility:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
class Client:
    """Coordinate remote operations.

    Methods:
        connect:
        close: Close the active connection.
    """

[output=unchanged]
[findings]
PDF723: Line 5: Method 'connect' docstring entry is missing a description
```

NumPy method entries use a balanced signature head and still require prose:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
class Client:
    """Coordinate remote operations.

    Methods
    -------
    connect(timeout=30)
    close()
        Close the active connection.
    """

[output=unchanged]
[findings]
PDF723: Line 6: Method 'connect' docstring entry is missing a description
```

Legacy NumPy type-bearing method names remain accepted without signature parentheses:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
class Client:
    """Coordinate remote operations.

    Methods
    -------
    connect : Callable[[], None]
    close : Callable[[], None]
        Close the active connection.
    """

[output=unchanged]
[findings]
PDF723: Line 6: Method 'connect' docstring entry is missing a description
```

An empty inline description and a nested list do not count as prose descriptions:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
class Client:
    """Coordinate remote operations.

    Methods:
        connect():
        close():
            - flush pending requests
        future_method(): Reserved for a future transport.
    """

[output=unchanged]
[findings]
PDF723: Line 5: Method 'connect' docstring entry is missing a description
PDF723: Line 6: Method 'close' docstring entry is missing a description
```

Only primary class docstrings have method-inventory semantics. A `Methods` section in a function docstring is outside the rule's owner scope:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def describe_client():
    """Describe a client.

    Methods:
        connect():
    """

[output=unchanged]
```

## Options
None.
