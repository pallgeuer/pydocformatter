# missing-private-package-documentation (PDF601)

Fix is not available.

Rule must by default be explicitly selected, unless it is removed from `require-explicit`.

Rule applies only when `source-context` is `module`.

## What it does
Checks for private package initializer files that are missing a module docstring.

Package checks apply only to `__init__` Python source or stub files. A package path is private when any discovered package path component starts with an underscore.

## Why is this useful?
Private packages can still benefit from local documentation when a project chooses to require it.

## Ruff compatibility
None.

## Examples
A private package initializer without a module docstring is reported:

```pydocfmt-example
[input=client/_internal/__init__.py]
DEFAULT_TIMEOUT = 30

[output=unchanged]
[findings]
PDF601: Line 1: Private package is missing docstring
```

An underscore-prefixed top-level package is also private:

```pydocfmt-example
[input=_client/__init__.py]
DEFAULT_TIMEOUT = 30

[output=unchanged]
[findings]
PDF601: Line 1: Private package is missing docstring
```

A documented private package is accepted:

```pydocfmt-example
[input=client/_internal/__init__.py]
"""Internal client helpers."""

DEFAULT_TIMEOUT = 30

[output=unchanged]
```

Public package paths are handled by PDF600 instead:

```pydocfmt-example
[input=client/__init__.py]
DEFAULT_TIMEOUT = 30

[output=unchanged]
```

## Options
None.
