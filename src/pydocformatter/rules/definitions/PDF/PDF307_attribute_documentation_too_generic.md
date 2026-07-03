# attribute-documentation-too-generic (PDF307)

Fix is not available.

Rule is ignored if `docstring-convention` is `none` or `pep257`.

## What it does
Checks attribute documentation whose description only restates the documented attribute name with generic filler such as "value", "attribute", or "field".

PDF307 checks both parsed owner-docstring attribute entries and adjacent attached attribute docstrings. Owner docstring entries include Google `Attributes` sections, NumPy `Attributes` sections, and reStructuredText `:ivar:`, `:cvar:`, and `:var:` fields when the matching convention is active. Attached attribute docstrings are checked for supported module attributes, class attributes, and `self.*` instance attributes assigned in `__init__`.

The rule is intentionally conservative. It reports only exact generic token sequences after case normalization and punctuation removal. For an attribute named `timeout`, generic descriptions include `timeout`, `The timeout.`, `The timeout value.`, `timeout attribute`, `timeout field`, `The attribute timeout.`, `The field timeout.`, `value of timeout`, and `The value of timeout.`.

Snake-case names are compared as word sequences, so `max_retries value` and `max retries value` are both generic for `max_retries`. Digits remain part of tokens, so `API2 token value` is generic for `api2_token`.

The rule skips multi-name owner-docstring entries, type-only entries, entries without descriptions, attached docstrings shared by multiple assignment targets, multi-line attached summaries, and descriptions that contain any meaningful word beyond the documented name and generic filler. It does not compare owner-docstring entries to the actual attribute inventory; it checks each parsed documentation entry itself.

## Why is this useful?
Attribute documentation should explain the attribute's role, units, source, constraints, or downstream use. Restating the attribute name gives readers no information beyond the assignment itself.

## Ruff compatibility
None.

## Examples
PDF307 reports an attached attribute docstring that only restates the attribute name:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
timeout = 30
"""The timeout value."""

[output=unchanged]
[findings]
PDF307: Line 2: Attribute 'timeout' documentation is too generic
```

The same check applies to attribute entries in owner docstrings. Generic entries are reported, while entries with concrete meaning are accepted:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
class Client:
    """Client.

    Attributes:
        timeout: The timeout value.
        max_retries: Maximum number of retry attempts.
        base_url:
            The base url
            value.
    """

[output=unchanged]
[findings]
PDF307: Line 5: Attribute 'timeout' documentation is too generic
PDF307: Line 7: Attribute 'base_url' documentation is too generic
```

Attached module, class, and `__init__` instance attribute docstrings are checked. Mixed tuple assignments with one supported target are checked, but attached docstrings shared by multiple documented targets are skipped:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
module_timeout = 30
"""The module timeout value."""

module_primary, module_fallback = endpoints
"""Value."""

class Client:
    class_timeout = 30
    """The class timeout value."""

    class_supported, helper.value = endpoints
    """The class supported value."""

    def __init__(self):
        self.instance_timeout = 30
        """The instance timeout value."""

[output=unchanged]
[findings]
PDF307: Line 2: Attribute 'module_timeout' documentation is too generic
PDF307: Line 9: Attribute 'class_timeout' documentation is too generic
PDF307: Line 12: Attribute 'class_supported' documentation is too generic
PDF307: Line 16: Attribute 'instance_timeout' documentation is too generic
```

Attached summaries that span multiple docstring lines are skipped because PDF307 only checks an attached attribute docstring when the summary is a single unambiguous line:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
timeout = 30
"""The timeout
value.
"""

retries = 3
"""Maximum number of retry attempts."""

[output=unchanged]
```

Descriptions with concrete meaning are accepted even when they contain generic words:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
class Client:
    timeout = 30
    """Request timeout in seconds."""

    token = ""
    """Value read from the client configuration."""

[output=unchanged]
```

NumPy entries are checked under the NumPy convention. Multi-name entries are skipped because one generic description cannot be assigned to one documented attribute unambiguously:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
class Client:
    """Client.

    Attributes
    ----------
    primary, fallback : str
        Value.
    timeout : float
        The timeout value.
    """

[output=unchanged]
[findings]
PDF307: Line 8: Attribute 'timeout' documentation is too generic
```

reStructuredText attribute field aliases are checked under the reST convention. Type-only fields such as `:vartype:` are not descriptions and are skipped:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
"""Module.

:ivar timeout: The timeout value.
:cvar token: The token value.
:var retries: Maximum number of retry attempts.
:vartype timeout: float
"""

[output=unchanged]
[findings]
PDF307: Line 3: Attribute 'timeout' documentation is too generic
PDF307: Line 4: Attribute 'token' documentation is too generic
```

Exact selection under `docstring-convention = "none"` still checks attached attribute docstrings, but convention-specific owner-docstring entries are not parsed:

```pydocfmt-example
[settings]
docstring-convention = "none"

[input]
"""Module.

Attributes:
    timeout: The timeout value.
"""

timeout = 30
"""The timeout value."""

[output=unchanged]
[findings]
PDF307: Line 8: Attribute 'timeout' documentation is too generic
```

## Options
- `docstring-convention`: Controls whether Google, NumPy, or reStructuredText owner-docstring attribute entries are parsed. Broad selections ignore PDF307 under `none` and `pep257`. Exact selection can restore the rule under those conventions; attached attribute docstrings can still be checked, but convention-specific owner entries are not parsed.
- `docstring-parse-list-items` and `docstring-parse-headings`: Can affect whether a single-line attached attribute docstring is treated as ordinary summary text or as a protected list item or heading. Protected structures are not checked as generic attached summaries.
