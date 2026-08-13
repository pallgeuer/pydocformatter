# missing-private-module-documentation (PDF603)

Fix is not available.

Rule must by default be explicitly selected, unless it is removed from `require-explicit`.

Rule applies only when `source-context` is `module`.

## What it does
Checks for private modules that are missing a module docstring.

A module is private when its module path contains an underscore-prefixed component. Package initializers are handled by the package rules instead.

## Why is this useful?
Private modules can still benefit from local documentation when a project chooses to require it.

## Ruff compatibility
None.

## Examples
A private module without a module docstring is reported:

```pydocfmt-example
[input=client/_session.py]
VALUE = 1

[output=unchanged]
[findings]
PDF603: Line 1: Private module is missing docstring
```

A public module inside a private package path is also private:

```pydocfmt-example
[input=client/_internal/session.py]
VALUE = 1

[output=unchanged]
[findings]
PDF603: Line 1: Private module is missing docstring
```

A documented private module is accepted:

```pydocfmt-example
[input=client/_session.py]
"""Private session helpers."""

VALUE = 1

[output=unchanged]
```

Public modules are handled by PDF602 instead:

```pydocfmt-example
[input]
VALUE = 1

[output=unchanged]
```

## Options
None.
