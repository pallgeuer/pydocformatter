# missing-parameter-documentation (PDF500)

Fix is not available.

Rule is ignored if `docstring-convention` is `none`, `numpy`, or `pep257`.

## What it does
Checks that function signature parameters are documented in parsed docstring parameter documentation.

By default, this rule reports missing parameters only when the docstring already has recognized parameter documentation. This makes the rule a consistency check for docstrings that have opted into parameter documentation. Broader modes can require parameter documentation for public docstrings with body content, or for all public docstrings.

Functions without docstrings are left to missing-docstring rules and are not reported by PDF500.

The rule compares positional-only, positional-or-keyword, keyword-only, `*args`, and `**kwargs` parameters. Leading `*` characters are ignored for matching, so `args` documents `*args` and `kwargs` documents `**kwargs`. Parameter names are otherwise matched exactly and case-sensitively.

Implicit `self` and `cls` parameters on class-owned non-static methods are not required. Parameters annotated with `Unpack[...]`, `typing.Unpack[...]`, or `typing_extensions.Unpack[...]` are also not required, including when those annotations are stringized.

## Why is this useful?
Documented parameters help callers understand accepted inputs without cross-checking implementation details.

## Ruff compatibility
This rule replaces Ruff's `D417`. Like Ruff, broad convention-based selections enable it for Google-style docstrings and ignore it for NumPy and PEP 257 conventions. Unlike Ruff, it can also use parsed reST parameter fields and can be configured to require parameter documentation beyond docstrings that already contain parameter sections.

## Examples
With the default `has-section` mode, a missing parameter is reported once parameter documentation is present:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(first, second):
    """Return the value.

    Args:
        first: First value.
    """

[output=unchanged]
[findings]
PDF500: Line 1: Function parameter 'second' is missing docstring documentation
```

The default mode uses all parsed parameter documentation for the docstring. Protected example text is not treated as parameter documentation:

````pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(first, second, third):
    """Return the value.

    Args:
        first: First value.
        second: Second value.

    ```text
    third: This is example text, not parameter documentation.
    ```
    """

[output=unchanged]
[findings]
PDF500: Line 1: Function parameter 'third' is missing docstring documentation
````

reST parameter fields are recognized under the reST convention:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def value(first, second):
    """Return the value.

    :param first: First value.
    """

[output=unchanged]
[findings]
PDF500: Line 1: Function parameter 'second' is missing docstring documentation
```

In `has-section` mode, `docstring-missing-documentation-public-only` does not suppress explicit parameter-section consistency checks. A private docstring without parameter documentation is still ignored, while a private docstring with incomplete parameter documentation is reported:

```pydocfmt-example
[settings]
docstring-convention = "google"
docstring-missing-documentation = "has-section"
docstring-missing-documentation-public-only = false

[input]
def _private_without_section(first):
    """Return the private value."""


def _private_with_section(first, second):
    """Return the private value.

    Args:
        first: First value.
    """

[output=unchanged]
[findings]
PDF500: Line 5: Function parameter 'second' is missing docstring documentation
```

NumPy parameter entries can document multiple parameters on one line. Missing parameters are reported on the physical signature line where the parameter appears:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
def value(
    first,
    /,
    second,
    *args,
    third,
    **kwargs,
):
    """Return the value.

    Parameters
    ----------
    first, args, kwargs : int
        Documented values.
    """

[output=unchanged]
[findings]
PDF500: Line 4: Function parameter 'second' is missing docstring documentation
PDF500: Line 6: Function parameter 'third' is missing docstring documentation
```

Broader activation modes can require parameter documentation even when a public docstring has no parameter section. The public-only setting only limits those broad checks; explicit parameter documentation is still checked for private definitions:

```pydocfmt-example
[settings]
docstring-convention = "google"
docstring-missing-documentation = "all-docstrings"
docstring-missing-documentation-public-only = true

[input]
def public(first):
    """Return the public value."""


def _private(first):
    """Return the private value."""


def _private_with_section(first, second):
    """Return the private value.

    Args:
        first: First value.
    """

[output=unchanged]
[findings]
PDF500: Line 1: Function parameter 'first' is missing docstring documentation
PDF500: Line 9: Function parameter 'second' is missing docstring documentation
```

The `non-summary-docstrings` mode reports public docstrings that contain more than only a summary. Summary-only public docstrings and private docstrings without parameter documentation are ignored when `docstring-missing-documentation-public-only` is `true`:

```pydocfmt-example
[settings]
docstring-convention = "google"
docstring-missing-documentation = "non-summary-docstrings"
docstring-missing-documentation-public-only = true

[input]
def summary_only(first):
    """Return the public value."""


def detailed(first):
    """Return the public value.

    More details.
    """


def _private_detailed(first):
    """Return the private value.

    More details.
    """

[output=unchanged]
[findings]
PDF500: Line 5: Function parameter 'first' is missing docstring documentation
```

With `non-summary-docstrings` and `docstring-missing-documentation-public-only = false`, private docstrings with body content are included in the broad check:

```pydocfmt-example
[settings]
docstring-convention = "google"
docstring-missing-documentation = "non-summary-docstrings"
docstring-missing-documentation-public-only = false

[input]
def _private_summary_only(first):
    """Return the private value."""


def _private_detailed(first):
    """Return the private value.

    More details.
    """

[output=unchanged]
[findings]
PDF500: Line 5: Function parameter 'first' is missing docstring documentation
```

With `all-docstrings` and `docstring-missing-documentation-public-only = false`, even private summary-only and empty docstrings are included in the broad check:

```pydocfmt-example
[settings]
docstring-convention = "google"
docstring-missing-documentation = "all-docstrings"
docstring-missing-documentation-public-only = false

[input]
def _private_summary_only(first):
    """Return the private value."""


def _private_empty(second):
    """"""

[output=unchanged]
[findings]
PDF500: Line 1: Function parameter 'first' is missing docstring documentation
PDF500: Line 5: Function parameter 'second' is missing docstring documentation
```

Implicit receivers and unpacked keyword parameter packs are not required:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
class Builder:
    def create(self, first, **kwargs: "typing.Unpack[Options]"):
        """Create a value.

        Args:
            first: First value.
        """

[output=unchanged]
```

## Options
- `docstring-convention`: Controls whether Google parameter sections, NumPy parameter sections, or reST parameter fields are parsed. `none`, `numpy`, and `pep257` ignore this rule by default; exact selection remains inert for `none` and `pep257`.
- `docstring-missing-documentation`: Controls when PDF500 is active. `has-section` reports only docstrings with recognized parameter documentation. `non-summary-docstrings` additionally reports public docstrings with more than just a summary. `all-docstrings` additionally reports all public docstrings.
- `docstring-missing-documentation-public-only`: When `true`, the broad parts of `non-summary-docstrings` and `all-docstrings` apply only to public functions and methods. Normal public names plus `__init__`, `__new__`, and `__call__` are public for this setting; other underscore and dunder names are private. Explicit parameter documentation is always checked, including for private functions.
