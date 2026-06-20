# directive-spacing (PCF003)

Fix is always available.

## What it does
Normalizes safe spacing around recognized trailing directive comments. The code before the directive is separated from `#` by exactly two spaces, and the directive content starts after one marker space.

PCF003 only handles trailing comments already classified as type comments or known tool directives by the PCF category. It preserves directive payload spelling after the marker space, including case, colon spacing, arguments, and any tool-specific content, while removing surrounding directive whitespace. Unknown or ambiguous directives remain outside this rule.

Only trailing directives are changed. Standalone directives remain protected from comment formatting, and ordinary trailing comments are handled by PCF002 rather than PCF003.

## Why is this useful?
Tool directives are sensitive, so ordinary trailing-comment reflow should not rewrite them. A separate directive-spacing rule lets projects canonicalize the harmless spacing around known directives without enabling broader trailing-comment extraction or reflow behavior.

## Ruff compatibility
Ruff may normalize some comment spacing through its formatter, but pydocformatter keeps this as an independently selectable PCF rule so directive spacing can be controlled separately from ordinary trailing-comment formatting.

## Examples
Compact known directives get canonical marker spacing without changing the directive payload:

```pydocfmt-example
[input]
value = compute()#noqa
other = compute() # nosec
typed = compute() #TYPE : ignore[assignment]

[output]
value = compute()  # noqa
other = compute()  # nosec
typed = compute()  # TYPE : ignore[assignment]
```

Tool-specific payload text is preserved after the single marker space, including casing, unusual colon spacing, options, and additional `#` characters. Surrounding directive whitespace is normalized:

```pydocfmt-example
[input]
linted = compute()#   PyLiNt : disable = missing-docstring  # local reason
ruffed = compute() #   ruff: noqa: F401

[output]
linted = compute()  # PyLiNt : disable = missing-docstring  # local reason
ruffed = compute()  # ruff: noqa: F401
```

Directive spacing is independent of syntax-aware trailing-comment extraction. PCF003 still normalizes directives attached to decorators, arguments, and compound statement headers, but it does not move or wrap them:

```pydocfmt-example
[settings]
line-length = 8

[input]
@decorator#noqa
def function(
    value,# type: ignore[arg-type]
):
    if enabled:#nosec
        pass

[output]
@decorator  # noqa
def function(
    value,  # type: ignore[arg-type]
):
    if enabled:  # nosec
        pass
```

Unknown directive-like trailing comments are handled by ordinary trailing-comment formatting, not PCF003:

```pydocfmt-example
[input]
value = compute() #not-a-known-directive
#noqa

[output=unchanged]
```

## Options
None.
