# entry-description-trailing-period (PDF308)

Fix is sometimes available.

Rule is ignored if `docstring-convention` is `google`.

## What it does
Checks that parsed docstring entry descriptions end with a period.

PDF308 checks Google, NumPy, and reStructuredText entries when the active convention parses them. It targets parameter, return, yield, exception, attribute, and method entry descriptions. For entries with multiline descriptions, the target is the final non-empty parsed description line. Protected nested structures such as lists and fenced code blocks are not folded into the entry description target.

Empty descriptions, generic reST fields, and reST type-only fields such as `:type:`, `:rtype:`, `:ytype:`, and `:vartype:` are skipped. Descriptions ending with a backslash are also skipped so path-like examples are not rewritten. The automatic fix only inserts a period at the end of the trimmed description target; descriptions ending with `,`, `?`, `!`, `:`, `;`, or `\u2026` are reported but not changed because appending another period would produce questionable punctuation.

Unsafe source mappings are reported but not changed. This includes docstrings whose relevant logical text is formed through evaluated escape sequences and cannot be mapped cleanly back to one source slice.

## Why is this useful?
Consistent entry description punctuation makes section bodies read like complete prose.

## Ruff compatibility
None.

## Examples
Missing periods are inserted at the end of parsed entry descriptions:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def connect(timeout):
    """Connect.

    Args:
        timeout: timeout in seconds
    """

[output]
def connect(timeout):
    """Connect.

    Args:
        timeout: timeout in seconds.
    """
```

Google return and exception entry descriptions are checked the same way:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def connect(timeout):
    """Connect.

    Returns:
        bool: whether connection succeeded

    Raises:
        TimeoutError: if the connection times out
    """

[output]
def connect(timeout):
    """Connect.

    Returns:
        bool: whether connection succeeded.

    Raises:
        TimeoutError: if the connection times out.
    """
```

For multiline descriptions, only the final non-empty parsed description line receives the inserted period:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def connect(timeout):
    """Connect.

    Args:
        timeout:
            timeout in
            seconds
    """

[output]
def connect(timeout):
    """Connect.

    Args:
        timeout:
            timeout in
            seconds.
    """
```

Nested protected structures do not become part of the description target:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def connect(mode):
    """Connect.

    Args:
        mode: choose one
            - fast
            - safe
        timeout: timeout in seconds.
    """

[output]
def connect(mode):
    """Connect.

    Args:
        mode: choose one.
            - fast
            - safe
        timeout: timeout in seconds.
    """
```

NumPy and reStructuredText entry descriptions are checked when those conventions are active:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
def connect(timeout):
    """Connect.

    Parameters
    ----------
    timeout : int
        timeout in seconds

    Returns
    -------
    bool
        whether connection succeeded
    """

[output]
def connect(timeout):
    """Connect.

    Parameters
    ----------
    timeout : int
        timeout in seconds.

    Returns
    -------
    bool
        whether connection succeeded.
    """
```

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def connect(timeout):
    """Connect.

    :param timeout: timeout in seconds
    :returns: whether connection succeeded
    """

[output]
def connect(timeout):
    """Connect.

    :param timeout: timeout in seconds.
    :returns: whether connection succeeded.
    """
```

Descriptions ending with non-period punctuation are reported but not changed:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def connect(timeout, retries):
    """Connect.

    Args:
        timeout: timeout in seconds?
        retries: retry count;
    """

[output=unchanged]
[findings]
PDF308: Line 5: Docstring entry description should end with a period
PDF308: Line 6: Docstring entry description should end with a period
```

Descriptions ending with a backslash are skipped:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def connect(path):
    """Connect.

    Args:
        path: base path \\
    """

[output=unchanged]
```

reST type-only fields, empty descriptions, and generic fields are skipped:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def connect(timeout):
    """Connect.

    :param timeout:
    :type timeout: int
    :meta private: generated
    """

[output=unchanged]
```

Unsafe escaped source mappings are reported but not fixed:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def connect(timeout):
    """Connect \u2603.

    Args:
        timeout: timeout in seconds
    """

[output=unchanged]
[findings]
PDF308: Lines 2-6: Docstring entry description should end with a period
```

## Options
- `docstring-convention`: Controls whether Google sections, NumPy sections, or reStructuredText fields are parsed. Broad selections ignore PDF308 under the Google convention, matching PDF300.
- `docstring-parse-*`: Controls whether generic nested structures such as lists, doctests, code fences, block quotes, tables, directives, and literal blocks are protected from entry-description punctuation checks.
