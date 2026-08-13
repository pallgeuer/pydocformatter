# missing-public-module-documentation (PDF602)

Fix is not available.

Rule applies only when `source-context` is `module`.

## What it does
Checks for public modules that are missing a module docstring.

Package initializers are handled by the package rules instead. A module path is public when no discovered module or package path component starts with an underscore.

## Why is this useful?
Public modules should describe their purpose and exported surface.

## Ruff compatibility
This rule replaces Ruff's `D100`.

## Examples
A public module without a module docstring is reported:

```pydocfmt-example
[input]
VALUE = 1

[output=unchanged]
[findings]
PDF602: Line 1: Public module is missing docstring
```

A documented public module is accepted:

```pydocfmt-example
[input]
"""Session management."""

VALUE = 1

[output=unchanged]
```

Package initializers are ignored by the module rule:

```pydocfmt-example
[input=client/__init__.py]
VALUE = 1

[output=unchanged]
```

Private module paths are handled by PDF603 instead:

```pydocfmt-example
[input=client/_session.py]
VALUE = 1

[output=unchanged]
```

## Options
None.
