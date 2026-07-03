# entry-description-terminal-punctuation (PDF309)

Fix is sometimes available.

Rule is ignored if `docstring-convention` is `numpy` or `pep257`.

## What it does
Checks that parsed docstring entry descriptions end with terminal punctuation.

PDF309 checks Google, NumPy, and reStructuredText entries when the active convention parses them. It accepts periods, question marks, exclamation points, and Unicode ellipses (`\u2026`). For entries with multiline descriptions, the target is the final non-empty parsed description line. Protected nested structures such as lists and fenced code blocks are not folded into the entry description target.

Empty descriptions, generic reST fields, and reST type-only fields such as `:type:`, `:rtype:`, `:ytype:`, and `:vartype:` are skipped. Descriptions ending with a backslash are also skipped so path-like examples are not rewritten. The automatic fix inserts a period when punctuation is missing; descriptions ending with `,`, `:`, or `;` are reported but not changed because appending a period would produce questionable punctuation.

Unsafe source mappings are reported but not changed. This includes docstrings whose relevant logical text is formed through evaluated escape sequences and cannot be mapped cleanly back to one source slice.

## Why is this useful?
Consistent terminal punctuation keeps entry descriptions visually predictable while allowing questions and emphatic descriptions.

## Ruff compatibility
None.

## Examples
Missing terminal punctuation is fixed by inserting a period:

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

Periods, question marks, exclamation points, and Unicode ellipses are already valid terminal punctuation:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def connect(timeout, retries, backoff):
    """Connect.

    Args:
        timeout: timeout in seconds.
        retries: retry count?
        backoff: backoff seconds!
        status: waiting\u2026
    """

[output=unchanged]
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
        timeout: timeout in seconds?
    """

[output]
def connect(mode):
    """Connect.

    Args:
        mode: choose one.
            - fast
            - safe
        timeout: timeout in seconds?
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
        whether connection succeeded?
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
        whether connection succeeded?
    """
```

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def connect(timeout):
    """Connect.

    :param timeout: timeout in seconds
    :rtype: bool
    """

[output]
def connect(timeout):
    """Connect.

    :param timeout: timeout in seconds.
    :rtype: bool
    """
```

Comma, colon, and semicolon endings are reported but not changed:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def connect(timeout, retries, backoff):
    """Connect.

    Args:
        timeout: timeout in seconds,
        retries: retry count:
        backoff: backoff seconds;
    """

[output=unchanged]
[findings]
PDF309: Line 5: Docstring entry description should end with terminal punctuation
PDF309: Line 6: Docstring entry description should end with terminal punctuation
PDF309: Line 7: Docstring entry description should end with terminal punctuation
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
    """Connect.

    Args:
        timeout: timeout \u2603
    """

[output=unchanged]
[findings]
PDF309: Lines 2-6: Docstring entry description should end with terminal punctuation
```

## Options
- `docstring-convention`: Controls whether Google sections, NumPy sections, or reStructuredText fields are parsed. Broad selections ignore PDF309 under the NumPy and PEP 257 conventions, matching PDF301.
- `docstring-parse-*`: Controls whether generic nested structures such as lists, doctests, code fences, block quotes, tables, directives, and literal blocks are protected from entry-description punctuation checks.
