# no-blank-line-before-function-docstring (PDF204)

Fix is always available.

Rule is incompatible with `PDF205`.

## What it does
PDF204 removes blank lines immediately before function, method, and nested-function docstrings.

Only the adjacent blank-line run before the docstring statement is changed. Comments, decorators, function headers, and non-blank lines before the docstring are preserved. The rule applies to ordinary functions, async functions, methods, and nested functions. It does not apply to class docstrings, attribute docstrings, or simple-suite docstrings written on the same physical line as the function header.

## Why is this useful?
Keeping a function docstring directly attached to the function body follows the default PEP 257 and Ruff style.

## Ruff compatibility
This rule replaces Ruff's `D201`.

## Examples
The canonical fix removes blank lines before a function docstring:

```pydocfmt-example
[input]
def function():

    """Docstring."""
    return None

[output]
def function():
    """Docstring."""
    return None
```

Nested functions and methods are handled independently, while class docstring spacing is left to class-specific rules:

```pydocfmt-example
[input]
class Client:

    """Class docstring."""

    def method(self):

        """Method docstring."""

        def nested():

            """Nested docstring."""
            return None

        return nested()

[output]
class Client:

    """Class docstring."""

    def method(self):
        """Method docstring."""

        def nested():
            """Nested docstring."""
            return None

        return nested()
```

Comments and decorators are preserved; only the adjacent blank run before the docstring is removed:

```pydocfmt-example
[input]
@decorator
async def function():
    # Leading comment.

    """Docstring."""
    return None

[output]
@decorator
async def function():
    # Leading comment.
    """Docstring."""
    return None
```

Simple-suite docstrings are ignored because there is no physical blank-line gap to normalize:

```pydocfmt-example
[input]
def function(): """Docstring."""; return None

[output=unchanged]
```

## Options
None. `docstring-convention` does not change this rule's behavior.
