# repeated-docstring-entry (PDF412)

Fix is not available.

Rule is disabled if `docstring-convention` is `none` or `pep257`.

## What it does
PDF412 reports parsed docstring entries that repeat within one docstring. It checks Google, NumPy, and named reStructuredText entries under the active convention, across the whole docstring rather than only within one section.

For parameter entries, leading `*` markers are ignored when comparing names, so `args` and `*args` match. Attribute, method, generic named field, and exception entries use the exact parsed name. Entries with multiple parsed names are checked name by name.

For reStructuredText fields, value fields and type fields are separate duplicate families. For example, `:param value:` and `:type value:` may appear together, but repeated `:param value:` or repeated `:type value:` entries are reported.

PDF412 is diagnostic only. It does not merge repeated entries or otherwise rewrite the docstring.

## Why is this useful?
Repeated entries split documentation for the same semantic item across multiple places and can make generated API documentation ambiguous. Reporting the later duplicate preserves the first entry and points to the repeated documentation that needs manual consolidation.

## Ruff compatibility
None.

## Examples
PDF412 reports repeated Google parameter entries. The first entry is allowed, and each later entry for the same parsed parameter name is reported:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(arg):
    """Return the value.

    Args:
        arg: The value.
        arg: More detail.
    """

[output=unchanged]
[findings]
PDF412: Line 6: Docstring parameter entry 'arg' repeats earlier entry
```

Entries are checked across the whole docstring, not just within one section:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(arg, option):
    """Return the value.

    Args:
        arg: The value.

    Keyword Args:
        arg: More detail.
        option: The option.
    """

[output=unchanged]
[findings]
PDF412: Line 8: Docstring parameter entry 'arg' repeats earlier entry
```

Google attribute, method, generic field, and exception entries are checked independently from parameter entries:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
class Example:
    """An example.

    Args:
        value: Constructor value.

    Attributes:
        value: The value.
        value: More detail.

    Methods:
        value: Return the value.
        value: Return it again.

    See Also:
        value: Related helper.
        value: Related helper again.
    """

[output=unchanged]
[findings]
PDF412: Line 9: Docstring attribute entry 'value' repeats earlier entry
PDF412: Line 13: Docstring method entry 'value' repeats earlier entry
PDF412: Line 17: Docstring field entry 'value' repeats earlier entry
```

Leading `*` markers are ignored for parameter names:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(*args, **kwargs):
    """Return the value.

    Args:
        *args: Positional values.
        args: More positional values.
        **kwargs: Keyword values.
        kwargs: More keyword values.
    """

[output=unchanged]
[findings]
PDF412: Line 6: Docstring parameter entry 'args' repeats earlier entry
PDF412: Line 8: Docstring parameter entry 'kwargs' repeats earlier entry
```

Exception entries use the exact parsed exception name. Backticks do not make a different parsed name, but different casing does:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(arg):
    """Return the value.

    Raises:
        ValueError: First error.
        valueError: Different parsed spelling.
        `ValueError`: More detail for the first error.
    """

[output=unchanged]
[findings]
PDF412: Line 7: Docstring exception entry 'ValueError' repeats earlier entry
```

NumPy entries with multiple parsed names are checked name by name:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
def value(arg, option):
    """Return the value.

    Parameters
    ----------
    arg, option : int
        The values.
    option : str
        More detail.
    """

[output=unchanged]
[findings]
PDF412: Line 8: Docstring parameter entry 'option' repeats earlier entry
```

Repeated names within one NumPy entry are also reported:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
def value(arg):
    """Return the value.

    Parameters
    ----------
    arg, arg : int
        The value.
    """

[output=unchanged]
[findings]
PDF412: Line 6: Docstring parameter entry 'arg' repeats earlier entry
```

Named reST value field aliases are reported as repeated entries:

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
[findings]
PDF412: Line 5: Docstring reST parameter entry 'arg' repeats earlier entry
```

For reST fields, value fields and type fields are separate duplicate families. A value field and type field for the same name are allowed:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def value(arg):
    """Return the value.

    :param arg: The value.
    :type arg: int
    """

[output=unchanged]
```

Repeated reST type fields are reported separately, and leading `*` markers are ignored for parameter type fields:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def value(arg):
    """Return the value.

    :type *arg: int
    :type arg: str
    """

[output=unchanged]
[findings]
PDF412: Line 5: Docstring reST parameter type entry 'arg' repeats earlier entry
```

Named reST attribute value fields and type fields are checked independently:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
class Example:
    """An example.

    :ivar value: The value.
    :vartype value: int
    :var value: More detail.
    :vartype value: str
    """

[output=unchanged]
[findings]
PDF412: Line 6: Docstring reST attribute entry 'value' repeats earlier entry
PDF412: Line 7: Docstring reST attribute type entry 'value' repeats earlier entry
```

Named reST exception aliases and exception lists are checked name by name. A single repeated entry is reported once even if more than one name in that entry has already appeared:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def value(arg):
    """Return the value.

    :raises ValueError, TypeError: First errors.
    :exception TypeError: More type error detail.
    :except ValueError, RuntimeError: More value error detail.
    :raise RuntimeError, RuntimeError: More runtime error detail.
    """

[output=unchanged]
[findings]
PDF412: Line 5: Docstring reST exception entry 'TypeError' repeats earlier entry
PDF412: Line 6: Docstring reST exception entry 'ValueError' repeats earlier entry
PDF412: Line 7: Docstring reST exception entry 'RuntimeError' repeats earlier entry
```

Repeated return and yield sections or non-named reST return/yield fields are outside PDF412 and are handled by PDF408:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(arg):
    """Return the value.

    Returns:
        int: The value.

    Returns:
        int: More detail.
    """

[output=unchanged]
```

Entry-like text inside protected structures is not counted when that structure parser is enabled:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(arg):
    """Return the value.

    Args:
        Example::

            arg: This is literal example text.

        arg: The value.
    """

[output=unchanged]
```

If the relevant `docstring-parse-*` protection is disabled, the same entry-like text can be parsed as an entry and later repeats can be reported:

```pydocfmt-example
[settings]
docstring-convention = "google"
docstring-parse-literal-blocks = false

[input]
def value(arg):
    """Return the value.

    Args:
        Example::

            arg: This is literal example text.

        arg: The value.
    """

[output=unchanged]
[findings]
PDF412: Line 9: Docstring parameter entry 'arg' repeats earlier entry
```

PDF412 reports repeated entries in non-simple docstring literals, but still does not fix them:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(arg):
    ("Return the value.\n\n"
     "Args:\n"
     "    arg: The value.\n"
     "    arg: More detail.")

[output=unchanged]
[findings]
PDF412: Lines 2-5: Docstring parameter entry 'arg' repeats earlier entry
```

## Options
None.
