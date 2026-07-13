# entry-description-first-word-capitalization (PDF310)

Fix is sometimes available.

Rule is disabled if `docstring-convention` is `none` or `pep257`.

## What it does
Checks that parsed docstring entry descriptions start with a capitalized first word when that capitalization is safe.

PDF310 checks Google, NumPy, and reStructuredText entries when the active convention parses them. It targets parameter, return, yield, exception, attribute, and method entry descriptions. For entries with multiline descriptions, the target is the first non-empty parsed description line. Protected nested structures such as lists and fenced code blocks are not folded into the entry description target.

Empty descriptions, generic reST fields, and reST type-only fields such as `:type:`, `:rtype:`, `:ytype:`, and `:vartype:` are skipped. Like PDF304, PDF310 only fixes lowercase ASCII words that contain lowercase ASCII letters or apostrophes after the first character. This means `timeout`, `don't`, `retry?`, and `retry...` can be fixed, while `"timeout"`, `timeout_value`, `timeout-value`, `URL`, `iOS`, `eBay`, `123`, and non-ASCII starts are left alone.

Unsafe source mappings are reported but not changed. This includes docstrings whose relevant logical text is formed through evaluated escape sequences and cannot be mapped cleanly back to one source slice.

## Why is this useful?
Capitalized entry descriptions scan consistently with summary lines and prose paragraphs.

## Ruff compatibility
None.

## Examples
Safe lowercase first words are capitalized:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def connect(timeout):
    """Connect.

    Args:
        timeout: timeout in seconds.
    """

[output]
def connect(timeout):
    """Connect.

    Args:
        timeout: Timeout in seconds.
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
        bool: whether connection succeeded.

    Raises:
        TimeoutError: if the connection times out.
    """

[output]
def connect(timeout):
    """Connect.

    Returns:
        bool: Whether connection succeeded.

    Raises:
        TimeoutError: If the connection times out.
    """
```

For multiline descriptions, only the first non-empty parsed description line is capitalized:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def connect(timeout):
    """Connect.

    Args:
        timeout:
            timeout in
            seconds.
    """

[output]
def connect(timeout):
    """Connect.

    Args:
        timeout:
            Timeout in
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
        mode: choose one.
            - fast
            - safe
        timeout: Timeout in seconds.
    """

[output]
def connect(mode):
    """Connect.

    Args:
        mode: Choose one.
            - fast
            - safe
        timeout: Timeout in seconds.
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
        timeout in seconds.

    Returns
    -------
    bool
        whether connection succeeded.
    """

[output]
def connect(timeout):
    """Connect.

    Parameters
    ----------
    timeout : int
        Timeout in seconds.

    Returns
    -------
    bool
        Whether connection succeeded.
    """
```

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def connect(timeout):
    """Connect.

    :param timeout: timeout in seconds.
    :returns: whether connection succeeded.
    """

[output]
def connect(timeout):
    """Connect.

    :param timeout: Timeout in seconds.
    :returns: Whether connection succeeded.
    """
```

Other safe ASCII first words are fixed in the same narrow way:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def connect(timeout, retries, pattern):
    r"""Connect.

    Args:
        timeout: don't wait forever.
        retries: retry? when needed.
        pattern: match \d+ values.
    """

[output]
def connect(timeout, retries, pattern):
    r"""Connect.

    Args:
        timeout: Don't wait forever.
        retries: Retry? when needed.
        pattern: Match \d+ values.
    """
```

Quoted, punctuated, numeric, mixed-case, all-uppercase, and already-capitalized words are skipped:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def connect(timeout, retries, url, platform, name, mode):
    """Connect.

    Args:
        timeout: "timeout" in seconds.
        retries: 3 retry attempts.
        url: URL used for requests.
        platform: iOS device.
        name: timeout_value token.
        mode: Already capitalized.
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
        timeout: timeout in seconds.
    """

[output=unchanged]
[findings]
PDF310: Lines 2-6: Docstring entry description first word 'timeout' should be capitalized
```

## Options
None.
