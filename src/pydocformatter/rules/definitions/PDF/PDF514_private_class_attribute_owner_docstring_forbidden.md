# private-class-attribute-owner-docstring-forbidden (PDF514)

Fix is not available.

Rule is disabled if `docstring-convention` is `none` or `pep257`.

Rule is incompatible with `PDF522` and `PDF523`.

## What it does
Checks for private attributes documented in class docstring attribute documentation.

PDF514 checks Google `Attributes` sections, NumPy `Attributes` sections, and reStructuredText `:ivar:`, `:cvar:`, `:var:`, and `:vartype:` fields when the matching convention is active. Attribute names beginning with `_` are private, including dunder-style names such as `__slots__`.

The rule checks parsed primary class docstrings only. It does not require the private attribute to exist in the class inventory, and it reports repeated private entries independently. Nested class docstrings are checked as their own class docstrings. Module docstrings, function docstrings, and additional string literals after a primary class docstring are not class owner docstrings for this rule.

PDF514 forbids private class attributes in class docstring attribute entries regardless of whether the attribute exists. Projects that require private class attributes in owner docstrings should select PDF522 instead of PDF514; projects that require attached docstrings should select PDF523 instead of PDF514.

## Why is this useful?
Private attributes are implementation details and should usually stay out of owner docstrings that describe the public class API.

## Ruff compatibility
None.

## Examples
A private class attribute documented in the class docstring is reported:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
class Client:
    """HTTP client.

    Attributes:
        _token (str): Internal token.
        timeout (float): Request timeout.
    """

    _token: str
    timeout: float

[output=unchanged]
[findings]
PDF514: Line 5: Class docstring documents private attribute '_token'
```

NumPy and reStructuredText attribute entries are checked under their active conventions:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
class Client:
    """HTTP client.

    Attributes
    ----------
    _token, timeout, __slots__ : object
        Client state.
    _token : str
        Repeated internal token.
    """

[output=unchanged]
[findings]
PDF514: Line 6: Class docstring documents private attribute '_token'
PDF514: Line 6: Class docstring documents private attribute '__slots__'
PDF514: Line 8: Class docstring documents private attribute '_token'
```

reStructuredText attribute value and type fields are checked under the `rest` convention:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
class Client:
    """HTTP client.

    :ivar _token: Internal token.
    :vartype _cache: dict[str, object]
    :ivar timeout: Request timeout.
    """

[output=unchanged]
[findings]
PDF514: Line 4: Class docstring documents private attribute '_token'
PDF514: Line 5: Class docstring documents private attribute '_cache'
```

Nested class docstrings are checked independently:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
class Outer:
    """Outer client.

    Attributes:
        _outer: Outer state.
    """

    class Inner:
        """Inner client.

        Attributes:
            _inner: Inner state.
        """

[output=unchanged]
[findings]
PDF514: Line 5: Class docstring documents private attribute '_outer'
PDF514: Line 12: Class docstring documents private attribute '_inner'
```

Only primary class docstrings are checked. Module docstrings, function docstrings, and later string literals are ignored by PDF514:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
"""Module.

Attributes:
    _module_token: Internal token.
"""

class Client:
    """HTTP client."""

    """Attributes:
    _class_token: Internal token.
    """

    def configure(self):
        """Configure.

        Attributes:
            _function_token: Internal token.
        """

[output=unchanged]
```

Private attribute-looking text is ignored when the active convention does not parse it as attribute documentation:

```pydocfmt-example
[settings]
docstring-convention = "pep257"

[input]
class Client:
    """HTTP client.

    Attributes:
        _token (str): Internal token.
    """

[output=unchanged]
```

## Options
None.
