# entry-description-too-generic (PDF312)

Fix is not available.

Rule is disabled if `docstring-convention` is `none` or `pep257`.

## What it does
PDF312 reports parsed return, yield, exception, warning, and method descriptions that exactly match a small inventory of content-free phrases.

| Entry     | Unnamed descriptions                     | Name-bearing descriptions                                                  |
|-----------|------------------------------------------|----------------------------------------------------------------------------|
| Return    | `The return value`, `The returned value` | `The <name> value`, `The <name> return value`, `The <name> returned value` |
| Yield     | `The yielded value`                      | `The <name> value`, `The <name> yielded value`                             |
| Exception | `The exception`, `The error`             | `The <name> exception`, `The <name> error`                                 |
| Warning   | `The warning`                            | `The <name> warning`                                                       |
| Method    | `The method`                             | `The <name> method`                                                        |

The comparison ignores surrounding ASCII spaces and tabs, ASCII capitalization, and final periods, question marks, or exclamation marks. Name-bearing phrases normalize variadic stars, underscores, and qualified-name dots consistently with PDF306 and PDF307. Leading or trailing underscores may be preserved or omitted only when the documented name has the corresponding boundary. Internal punctuation, markup, additional words, names containing non-ASCII characters, non-space/tab whitespace, suspicious controls, and non-ASCII characters trimmed from the original description boundary prevent a match.

Return, yield, exception, and warning entries are checked only in function-owned docstrings. Method entries are checked only in class-owned docstrings. Missing descriptions, protected-only bodies, malformed entries, and reST type-only fields remain the responsibility of their structural and completeness rules.

## Why is this useful?
Phrases such as `The return value` and `The run method` repeat the entry's role or name without explaining its meaning or behavior.

## Ruff compatibility
None.

## Examples
PDF312 reports an exact generic return description. This is the canonical case:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def count():
    """Count records.

    Returns:
        int: The return value.
    """

[output=unchanged]
[findings]
PDF312: Line 5: Return documentation is too generic
```

Class-owned method entries support both unnamed and name-bearing generic phrases:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
class Worker:
    """Run queued work.

    Methods:
        run: The method.
        close: The close method.
    """

[output=unchanged]
[findings]
PDF312: Line 5: Method documentation is too generic
PDF312: Line 6: Method documentation is too generic
```

Named NumPy return entries are checked against their documented names:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
def count():
    """Count records.

    Returns
    -------
    count : int
        The count value.
    """

[output=unchanged]
[findings]
PDF312: Line 6: Return documentation is too generic
```

reStructuredText return, yield, and exception value fields are checked, while type-only fields are not prose descriptions:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def values():
    """Produce values.

    :return: The returned value.
    :yield item: The item value.
    :raises ValueError: The ValueError exception.
    :rtype: The return value
    :ytype item: The yielded value
    """

[output=unchanged]
[findings]
PDF312: Line 4: Return documentation is too generic
PDF312: Line 5: Yield documentation is too generic
PDF312: Line 6: Exception documentation is too generic
```

Internal punctuation, markup, or additional semantic words prevent a match:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def count():
    """Count records.

    Returns:
        int: The return value in bytes.

    Yields:
        str: `The yielded value`.

    Raises:
        ValueError: The error: invalid input.
    """

[output=unchanged]
```

## Options
None.
