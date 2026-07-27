# orphan-rest-type-field (PDF722)

Fix is not available.

Rule is disabled if `docstring-convention` is `none`, `pep257`, `google`, or `numpy`.

## What it does
Checks that each parsed reStructuredText parameter, return, yield, or attribute type field has a corresponding value field in the same docstring.

Fields pair one-to-one by semantic kind and normalized name regardless of relative order. Parameter names ignore leading `*` markers, while attribute and named-yield fields match exactly.

## Why is this useful?
An orphan type field supplies type information without the value description that explains what the documented item means. Reporting the structural mismatch directly is clearer than treating the type text as prose.

## Ruff compatibility
None.

## Examples
A parameter type field without a corresponding value field is reported:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def convert(value):
    """Convert a value.

    :type value: int
    """

[output=unchanged]
[findings]
PDF722: Line 4: reST type field ':type value:' has no corresponding parameter value field
```

Return, yield, and attribute type fields use their own value-field families:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
"""Module values.

:rtype: int
:ytype item: str
:vartype timeout: float
"""

[output=unchanged]
[findings]
PDF722: Line 3: reST type field ':rtype:' has no corresponding return value field
PDF722: Line 4: reST type field ':ytype item:' has no corresponding yield value field
PDF722: Line 5: reST type field ':vartype timeout:' has no corresponding attribute value field
```

Accepted aliases, field order, and variadic parameter spellings pair successfully:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def collect(*args, **kwargs):
    """Collect values.

    :type args: tuple[object, ...]
    :argument *args: Positional values.
    :kwarg **kwargs: Keyword values.
    :type kwargs: dict[str, object]
    """

[output=unchanged]
```

Pairing is one-to-one, so a surplus repeated type field is orphaned:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def convert(value):
    """Convert a value.

    :type value: int
    :param value: Value to convert.
    :type value: str
    """

[output=unchanged]
[findings]
PDF722: Line 6: reST type field ':type value:' has no corresponding parameter value field
```

Value fields pair structurally even when their descriptions are empty. PDF500, PDF502, PDF504, PDF508, and PDF510 decide whether that empty value field satisfies their own documentation-presence policy, while PDF700, PDF704, PDF708, PDF712, and PDF716 can report its missing description:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def convert(value):
    """Convert a value.

    :type value: int
    :param value:
    :rtype: str
    :return:
    :ytype item: bytes
    :yield item:
    :vartype timeout: float
    :var timeout:
    """
    yield value

[output=unchanged]
```

Pairing never crosses semantic families. Named yields and attributes also match case-sensitively and exactly:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
"""Values.

:ytype item: str
:yield other: Other value.
:vartype Timeout: float
:var timeout: Request timeout.
:type value: int
:var value: Stored value.
"""

[output=unchanged]
[findings]
PDF722: Line 3: reST type field ':ytype item:' has no corresponding yield value field
PDF722: Line 5: reST type field ':vartype Timeout:' has no corresponding attribute value field
PDF722: Line 7: reST type field ':type value:' has no corresponding parameter value field
```

Fields pair only within one parsed docstring. An owner docstring type field cannot pair with a value field in an adjacent attribute docstring:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
"""Module values.

:vartype timeout: float
"""

timeout = 1.0
""":var timeout: Request timeout."""

[output=unchanged]
[findings]
PDF722: Line 3: reST type field ':vartype timeout:' has no corresponding attribute value field
```

Malformed fields are owned by the malformed-entry rule and are not parsed as orphan candidates:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def convert(value):
    """Convert a value.

    :type: int
    """

[output=unchanged]
```

## Options
None.
