# type-spelling-normalization (PDF416)

Fix is usually available.

Rule is disabled if `docstring-convention` is `none` or `pep257`.

## What it does
PDF416 conservatively normalizes three spelling defects in parsed Google, NumPy, and reST type slots: a trailing period, redundant AST-equivalent outer parentheses, and exact lowercase `none`.

The rule operates only on type slots already exposed by convention parsing. Google and NumPy method signatures remain opaque, while legacy NumPy entries such as `run : Callable[[], None]` and fallback typed Google method entries such as starred names retain a type slot. reST type fields remain eligible even when they are orphaned from a value field. PDF409 owns outer entry spacing, and PDF411 owns internal type-token spacing.

The transformations compose in order: a trailing period and any spaces or tabs immediately before it are removed only when the remaining text is a conservative type expression or quoted forward reference, outer parentheses are then removed repeatedly only while the current and candidate expressions have identical conservative ASTs, and final exact `none` becomes `None`. ASCII spaces and tabs exposed inside each removed parenthesis layer are discarded in the same pass. Only the semantic spelling is replaced, so spaces and tabs surrounding a convention type slot remain available to PDF409. Whitespace beyond ASCII space and tab, form feeds, vertical tabs, and other suspicious controls prevent PDF416 normalization so PDF004 remains authoritative.

The rule trusts convention parsing when classifying type slots. In particular, every bare NumPy return or yield entry head is a type slot, so simple identifier spellings such as `Widget.` and `Nothing.` are normalized to `Widget` and `Nothing`. The rule does not modernize typing spellings, change arbitrary capitalization, normalize calls or top-level sequences, or recover malformed unparsed entries. The accepted bare Google `None.` return or yield form remains unchanged; NumPy and reStructuredText type slots spelled `None.` are normalized to `None`.

Source mappings that cannot be safely rewritten are reported without a fix.

## Why is this useful?
Removing obvious type-slot spelling defects improves consistency and prevents accidental type mismatches without imposing a target-version-dependent typing style.

## Ruff compatibility
None.

## Examples
PDF416 combines supported Google type spelling fixes. This is the canonical case:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def lookup(key):
    """Look up a value.

    Args:
        key (((str))): Lookup key.

    Returns:
        none.: No matching value.
    """

[output]
def lookup(key):
    """Look up a value.

    Args:
        key (str): Lookup key.

    Returns:
        None: No matching value.
    """
```

NumPy attributes and legacy type-bearing method entries expose type slots, while signature-shaped method entries remain opaque:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
class Client:
    """Connect to a service.

    Attributes
    ----------
    timeout : ((float)).
        Connection timeout.

    Methods
    -------
    connect(value: none)
        Connect to the service.
    close : ((Callable[[], None])).
        Close the client.
    """

[output]
class Client:
    """Connect to a service.

    Attributes
    ----------
    timeout : float
        Connection timeout.

    Methods
    -------
    connect(value: none)
        Connect to the service.
    close : Callable[[], None]
        Close the client.
    """
```

reStructuredText inline parameter types, type fields, and orphan type fields are normalized independently. Value-field prose is not a type slot, and quoted forward references support trailing-period removal but not parenthesis removal:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def lookup(key):
    """Look up a value.

    :param ((str)). key: Lookup key.
    :type key: none.
    :rtype: "Value".
    :ytype grouped: ("Item")
    :ytype orphan: ((Iterator[str]))
    :returns: list[str]. in prose.
    """

[output]
def lookup(key):
    """Look up a value.

    :param str key: Lookup key.
    :type key: None
    :rtype: "Value"
    :ytype grouped: ("Item")
    :ytype orphan: Iterator[str]
    :returns: list[str]. in prose.
    """
```

Broader typing preferences and unsupported expressions remain unchanged:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
def lookup():
    """Look up a value.

    Returns
    -------
    Optional[List[str]]
        Matching values.
    """

[output=unchanged]
```

Source mappings that cannot be rewritten safely still produce a non-fixable finding:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def lookup(key):
    ("Look up a value.\n\n"
     "Args:\n"
     "    key (((str))): Lookup key.")

[output=unchanged]
[findings]
PDF416: Lines 2-4: Docstring type spelling should be normalized from '((str))' to 'str'
```

## Options
None.
