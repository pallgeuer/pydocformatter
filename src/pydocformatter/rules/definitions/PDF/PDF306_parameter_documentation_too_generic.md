# parameter-documentation-too-generic (PDF306)

Fix is not available.

Rule is disabled if `docstring-convention` is `none` or `pep257`.

## What it does
Checks parsed parameter documentation whose description only restates the documented parameter name with generic filler such as "value", "parameter", or "argument".

PDF306 is intentionally conservative. It reports only exact generic token sequences after case normalization and punctuation removal. For a parameter named `timeout`, generic descriptions include `timeout`, `The timeout.`, `The timeout value.`, `timeout parameter`, `timeout argument`, `The parameter timeout.`, `The argument timeout.`, `value of timeout`, and `The value of timeout.`.

Snake-case names are compared as word sequences, so `max_retries value` and `max retries value` are both generic for `max_retries`. Digits remain part of tokens, so `API2 token value` is generic for `api2_token`. Leading `*` characters are ignored for name comparison, so `args value` is generic for `*args` and `kwargs parameter` is generic for `**kwargs`.

When a documented parameter entry matches a signature `*...` or `**...` parameter, PDF306 also reports variadic descriptions that say only that the parameter contains arguments. For `*...` parameters, generic forms include `args`, `arguments`, `positional args`, `positional arguments`, and `extra` or `additional` variants. For `**...` parameters, generic forms include `kwargs`, `arguments`, `keyword args`, `keyword arguments`, and `extra` or `additional` variants. Wrong-kind phrases such as `*args: Keyword arguments.` and `**kwargs: Positional arguments.` are not reported by PDF306.

The rule skips multi-name entries, type-only entries, entries without descriptions, and descriptions that contain any meaningful word beyond the documented name and generic filler. It checks each parsed documentation entry itself, using the function signature only to identify real `*...` and `**...` parameters for variadic argument phrase matching.

## Why is this useful?
Parameter documentation should explain accepted values, units, constraints, sources, or downstream behavior. Restating the parameter name adds noise without helping callers understand the interface.

## Ruff compatibility
None.

## Examples
PDF306 reports a parameter description that only restates the parameter name:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def connect(timeout):
    """Connect.

    Args:
        timeout: The timeout value.
    """

[output=unchanged]
[findings]
PDF306: Line 5: Parameter 'timeout' documentation is too generic
```

Several generic forms can be reported in the same docstring, while descriptions with concrete meaning are accepted:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def connect(timeout, max_retries, *args, **kwargs):
    """Connect.

    Args:
        timeout: The value of timeout.
        max_retries: max retries value.
        *args: Positional arguments.
        **kwargs: kwargs parameter.
    """

[output=unchanged]
[findings]
PDF306: Line 5: Parameter 'timeout' documentation is too generic
PDF306: Line 6: Parameter 'max_retries' documentation is too generic
PDF306: Line 7: Parameter '*args' documentation is too generic
PDF306: Line 8: Parameter '**kwargs' documentation is too generic
```

Variadic argument phrases are checked only when the documented entry matches a real variadic signature parameter. The check works with starless documentation names and arbitrary variadic parameter names:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def collect(*values, **options):
    """Collect.

    Args:
        values: The additional positional arguments.
        **options: Extra keyword args.
    """

[output=unchanged]
[findings]
PDF306: Line 5: Parameter 'values' documentation is too generic
PDF306: Line 6: Parameter '**options' documentation is too generic
```

Descriptions split across continuation lines are checked as one description, and only the entry line is reported:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def connect(base_url, timeout):
    """Connect.

    Args:
        base_url:
            The base url
            value.
        timeout:
            Request timeout in seconds.
    """

[output=unchanged]
[findings]
PDF306: Line 5: Parameter 'base_url' documentation is too generic
```

Descriptions with concrete meaning are accepted even when they contain generic words:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def connect(timeout, max_retries, token):
    """Connect.

    Args:
        timeout: Request timeout in seconds.
        max_retries: Maximum number of retry attempts.
        token: Value read from the client configuration.
    """

[output=unchanged]
```

NumPy entries are checked under the NumPy convention. Multi-name entries are skipped because one generic description cannot be assigned to one documented parameter unambiguously:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
def connect(primary, fallback, timeout):
    """Connect.

    Parameters
    ----------
    primary, fallback : str
        Value.
    timeout : float
        The timeout value.
    """

[output=unchanged]
[findings]
PDF306: Line 8: Parameter 'timeout' documentation is too generic
```

reStructuredText parameter field aliases are checked under the reST convention. Type-only fields are not descriptions and are skipped:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def connect(timeout, token, retries):
    """Connect.

    :arg timeout: The timeout value.
    :keyword token: The token value.
    :kwarg retries: Maximum number of retry attempts.
    :type token: str
    """

[output=unchanged]
[findings]
PDF306: Line 4: Parameter 'timeout' documentation is too generic
PDF306: Line 5: Parameter 'token' documentation is too generic
```

## Options
None.
