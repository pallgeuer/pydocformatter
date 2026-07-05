# missing-public-package-documentation (PDF600)

Fix is not available.

## What it does
Checks for public package initializer files that are missing a module docstring.

Package checks apply only to `__init__` Python source or stub files. A package path is public when no discovered package path component starts with an underscore.

## Why is this useful?
Public packages should describe their purpose and exported surface at the package boundary.

## Ruff compatibility
This rule replaces Ruff's `D104`.

## Examples
A public package initializer without a module docstring is reported:

```pydocfmt-example
[input=client/__init__.py]
DEFAULT_TIMEOUT = 30

[output=unchanged]
[findings]
PDF600: Line 1: Public package is missing docstring
```

A documented public package is accepted:

```pydocfmt-example
[input=client/__init__.py]
"""Client package."""

DEFAULT_TIMEOUT = 30

[output=unchanged]
```

Non-package modules are ignored by the package rule:

```pydocfmt-example
[input=client/session.py]
DEFAULT_TIMEOUT = 30

[output=unchanged]
```

Private package paths are handled by PDF601 instead:

```pydocfmt-example
[input=client/_internal/__init__.py]
DEFAULT_TIMEOUT = 30

[output=unchanged]
```

## Options
None.
