# comment-directive-normalization (PCF003)

Fix is always available.

## What it does
Normalizes safe marker spacing and machine-readable syntax in recognized directive comments. For trailing directives, the code before the directive is preserved exactly so PCF002 remains the owner of code-to-`#` delimiter spacing. For standalone directives, indentation is preserved. In both cases, directive content starts after one marker space.

PCF003 handles comments already classified as type comments or known tool directives by the PCF category. It normalizes recognized directive heads to lowercase, removes space before directive introducer colons, adds one space after directive colons where a value follows, and normalizes safe comma-separated lists for `type: ignore[...]`, `ty: ignore[...]`, `noqa`, `ruff: noqa`, `flake8: noqa`, and `pylint` enable/disable directives.

Unknown or ambiguous payload text is preserved after safe prefix cleanup. Ordinary comments remain outside this rule.

## Why is this useful?
Tool directives are sensitive, so ordinary comment reflow should not rewrite them. A separate comment-directive-normalization rule lets projects canonicalize recognized directive syntax without enabling broader trailing-comment extraction or prose formatting.

## Ruff compatibility
Ruff may normalize some comment spacing through its formatter, but pydocformatter keeps this as an independently selectable PCF rule so directive syntax normalization can be controlled separately from ordinary comment formatting.

## Examples
Compact known directives get canonical marker spacing and directive-head spelling:

```pydocfmt-example
[input]
value = compute()#noqa
other = compute() #   nosec
typed = compute() #TYPE : ignore[assignment]
ty_typed = compute() #TY : ignore[invalid-argument-type]

[output]
value = compute()# noqa
other = compute() # nosec
typed = compute() # type: ignore[assignment]
ty_typed = compute() # ty: ignore[invalid-argument-type]
```

Standalone directives are normalized without changing indentation:

```pydocfmt-example
[input]
#ruff: noqa
    #fmt : off
#   pylint : disable-next = missing-docstring,unused-argument

[output]
# ruff: noqa
    # fmt: off
# pylint: disable-next=missing-docstring, unused-argument
```

Safe machine-readable payloads are normalized, while additional `#` payload text is preserved:

```pydocfmt-example
[input]
typed = compute()#TYPE : ignore[assignment,arg-type]
mixed = compute()#TYPE : ignore[arg-type,ty:invalid-argument-type]
ty_typed = compute()#TY : ignore[invalid-argument-type,unresolved-import]
ruffed = compute() # ruff : noqa : ruf100, f401
linted = compute()#   PyLiNt : disable = missing-docstring,unused-argument  # local reason

[output]
typed = compute()# type: ignore[assignment, arg-type]
mixed = compute()# type: ignore[arg-type, ty:invalid-argument-type]
ty_typed = compute()# ty: ignore[invalid-argument-type, unresolved-import]
ruffed = compute() # ruff: noqa: RUF100, F401
linted = compute()# pylint: disable=missing-docstring, unused-argument  # local reason
```

Directive normalization is independent of syntax-aware trailing-comment extraction. PCF003 still normalizes directives attached to decorators, arguments, and compound statement headers, but it does not move or wrap them:

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
@decorator# noqa
def function(
    value,# type: ignore[arg-type]
):
    if enabled:# nosec
        pass
```

Unknown directive-like comments are handled by ordinary comment formatting, not PCF003:

```pydocfmt-example
[input]
value = compute() #not-a-known-directive
# unknown-directive

[output=unchanged]
```

## Options
None.
