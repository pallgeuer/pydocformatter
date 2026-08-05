# private-class-attribute-docstring-must-be-attached (PDF523)

Fix is not available.

Rule is disabled if `docstring-convention` is `none` or `pep257`, and ignored by broad selectors under `google`, `numpy`, and `rest`.

Rule is incompatible with `PDF514`, `PDF516`, and `PDF522`.

## What it does
Checks for private class attributes documented in class docstring attribute entries when private class attribute documentation must use attached docstrings.

PDF523 checks parsed Google `Attributes` sections, NumPy `Attributes` sections, and reStructuredText attribute fields when the matching convention is active. The documented name must also match a supported class-scope attribute or supported `self.*` attribute assigned in `__init__`. A slot-only member is excluded because its string literal cannot own an attached docstring. If the same name also has any real class or initializer assignment, including an annotation-only declaration, the ordinary attached-docstring policy applies.

PDF523 is a location policy: it reports inventory-backed private class attributes documented in the class docstring because attached docstrings are required. It conflicts with PDF514, whose broader owner-docstring prohibition overlaps its findings; PDF516, which forbids the required attached docstrings; and PDF522, the opposite owner-docstring policy.

## Why is this useful?
Attached docstrings let private implementation attributes be documented near their assignment without adding private details to the owner docstring's public attribute list.

## Ruff compatibility
Ruff's `RUF023` and `PLE0237` inspect slot order and non-slot assignments. PDF523 instead applies documentation placement policy and excludes slot-only names that cannot own attached docstrings.

## Examples
A private class attribute documented in the class docstring is reported:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
class Client:
    """HTTP client.

    Attributes:
        _token: Internal token.
    """

    _token: str

[output=unchanged]
[findings]
PDF523: Line 5: Private class attribute '_token' must use attached docstring, not class docstring documentation
```

NumPy entries are checked name by name. Stale documented names are left to PDF509 or PDF514, while repeated owner entries are reported independently:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
class Client:
    """HTTP client.

    Attributes
    ----------
    _token, timeout, _cache, _missing : object
        Client state.
    _token : str
        Repeated internal token.
    """

    _token: str
    timeout: float
    _cache: dict[str, object]

[output=unchanged]
[findings]
PDF523: Line 6: Private class attribute '_token' must use attached docstring, not class docstring documentation
PDF523: Line 6: Private class attribute '_cache' must use attached docstring, not class docstring documentation
PDF523: Line 8: Private class attribute '_token' must use attached docstring, not class docstring documentation
```

reStructuredText fields can document supported `self.*` assignments from `__init__`:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
class Client:
    """HTTP client.

    :ivar _token: Internal token.
    :vartype _cache: dict[str, object]
    """

    def __init__(self):
        self._token = ""
        self._cache = {}

[output=unchanged]
[findings]
PDF523: Line 4: Private class attribute '_token' must use attached docstring, not class docstring documentation
PDF523: Line 5: Private class attribute '_cache' must use attached docstring, not class docstring documentation
```

When the active convention does not parse attribute entries, class docstring attribute-looking text is ignored:

```pydocfmt-example
[settings]
docstring-convention = "pep257"

[input]
class Client:
    """HTTP client.

    Attributes:
        _token: Internal token.
    """

    _token: str

[output=unchanged]
```

A slot-only private member is exempt because no assignment can own its attached docstring. A separate real declaration of another slot name restores the ordinary placement requirement for that name:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
class Client:
    """Client.

    Attributes:
        _token: Authentication token.
        _cache: Internal cache.
    """

    __slots__ = ("_token", "_cache")
    _cache: dict[str, object]

[output=unchanged]
[findings]
PDF523: Line 6: Private class attribute '_cache' must use attached docstring, not class docstring documentation
```

## Options
None.
