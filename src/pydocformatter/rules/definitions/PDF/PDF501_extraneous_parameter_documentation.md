# extraneous-parameter-documentation (PDF501)

Fix is not available.

Rule is ignored if `docstring-convention` is `none` or `pep257`.

## What it does
Checks that parsed docstring parameter documentation only names parameters that exist in the function signature.

The rule compares parsed Google, NumPy, and reST parameter entries against positional-only, positional-or-keyword, keyword-only, `*args`, and `**kwargs` parameters. Leading `*` characters are ignored for comparison, so `args` documents `*args` and `kwargs` documents `**kwargs`. Parameter names are otherwise matched exactly and case-sensitively.

For `**kwargs: Unpack[Options]`, `typing.Unpack[Options]`, and `typing_extensions.Unpack[Options]`, same-module class-based `TypedDict` keys from `Options` are also accepted as documented keyword names. If the unpack target cannot be resolved locally, PDF501 conservatively suppresses extraneous-parameter findings for that function to avoid false positives for valid imported `TypedDict` keys.

Unlike PDF500, this rule does not have public/private activation settings. Any parsed parameter entry is checked whenever the owning function has a signature.

## Why is this useful?
Extraneous parameter documentation can mislead callers and usually indicates stale docs after a signature change.

## Ruff compatibility
This rule replaces Ruff's `DOC102`. Unlike Ruff, it participates in pydocformatter's shared convention-aware docstring parser.

## Examples
An entry is reported when it documents a parameter that is not present in the signature:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(first):
    """Return the value.

    Args:
        first: First value.
        second: Second value.
    """

[output=unchanged]
[findings]
PDF501: Line 6: Docstring documents parameter 'second' that is not in the function signature
```

The rule uses all parsed parameter documentation for a docstring. Protected example text is ignored, while parsed reST parameter fields are still checked:

````pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
def value(first):
    """Return the value.

    :param first: First value.

    ```text
    :param second: This is example text, not parameter documentation.
    ```

    :param third: Stale value.
    """

[output=unchanged]
[findings]
PDF501: Line 10: Docstring documents parameter 'third' that is not in the function signature
````

NumPy entries can name multiple parameters on one line. Each absent documented name is reported, even when multiple findings point to the same physical line:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
def value(first):
    """Return the value.

    Parameters
    ----------
    first, second, third : int
        Values.
    """

[output=unchanged]
[findings]
PDF501: Line 6: Docstring documents parameter 'second' that is not in the function signature
PDF501: Line 6: Docstring documents parameter 'third' that is not in the function signature
```

Signature shape is normalized before comparison, so positional-only parameters, keyword-only parameters, `*args`, and `**kwargs` can all be documented by their starless names:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def value(first, /, second, *args, third, **kwargs):
    """Return the value.

    Args:
        first: First value.
        second: Second value.
        args: Extra positional values.
        third: Third value.
        kwargs: Extra keyword values.
    """

[output=unchanged]
```

Implicit receivers are still real signature parameters for this rule. Documenting `self` or `cls` is allowed because those names are present in the method signature:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
class Builder:
    def create(self, first):
        """Create a value.

        Args:
            self: Receiver.
            first: First value.
        """

[output=unchanged]
```

reST fields are parsed only under the reST convention. With another convention, reST-looking text is ordinary docstring content and is not checked by this rule:

```pydocfmt-example
[settings]
docstring-convention = "none"

[input]
def value(first):
    """Return the value.

    :param second: Ordinary text outside the reST convention.
    """

[output=unchanged]
```

## Options
- `docstring-convention`: Controls whether Google parameter sections, NumPy parameter sections, or reST parameter fields are parsed. `none` and `pep257` ignore this rule by default, and convention syntax is ordinary content under those conventions.
