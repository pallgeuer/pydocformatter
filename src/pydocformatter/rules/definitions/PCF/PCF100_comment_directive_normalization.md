# comment-directive-normalization (PCF100)

Fix is always available.

## What it does
Normalizes safe marker spacing and machine-readable syntax in recognized directive comments. For trailing directives, the code before the directive is preserved exactly so PCF001 remains the owner of code-to-`#` delimiter spacing. For standalone directives, indentation is preserved. In both cases, directive content starts after one marker space.

PCF100 handles comments already classified as type comments or known tool directives by the PCF category. It normalizes recognized directive heads to lowercase, removes space before directive introducer colons, adds one space after directive colons where a value follows, and normalizes safe comma-separated lists for `type: ignore[...]`, `ty: ignore[...]`, `noqa`, `pydocfmt: noqa`, `pydocfmt: ignore[...]`, `pydocfmt: file-ignore[...]`, `ruff: noqa`, `flake8: noqa`, `pylint` enable/disable directives, PyCharm `noinspection` directives, and Ruff bracket directives such as `ruff: ignore[...]`, `ruff: disable[...]`, `ruff: enable[...]`, and `ruff: file-ignore[...]`. Safe list families remove repeated normalized items while preserving the first occurrence and existing order. Families with canonical uppercase selectors deduplicate after uppercasing; other families use exact trimmed spelling, so qualified and unqualified type-checker selectors remain distinct.

Ruff `disable[...]` and `enable[...]` range payloads are not deduplicated because Ruff pairs range boundaries by identical codes in identical order. PCF100 still normalizes their directive heads, bracket spacing, comma spacing, and accepted trailing commas without changing item order or multiplicity. Ruff-prefixed isort action comments such as `ruff: isort: skip_file` are normalized as nested directives. PyCharm `language=` injection comments normalize only the directive head and preserve the language ID and optional `prefix=`/`suffix=` payload. PyCharm `@formatter:on` and `@formatter:off` marker comments are normalized as individual directive lines only; they do not disable pydocformatter for a range of code.

For pydocfmt directives, this rule normalizes only the supported suppression forms: `pydocfmt: noqa`, `pydocfmt: ignore[...]`, and `pydocfmt: file-ignore[...]`. It normalizes a whitespace-only bracket payload to `[]`, preserves the spelling of invalid selector tokens, and removes terminal ASCII whitespace from recognized bracket directives. Comments using unrecognized pydocfmt actions such as `disable[...]` or `enable[...]` are not normalized.

Unknown or ambiguous payload text is preserved after safe prefix cleanup. Ordinary comments remain outside this rule.

## Why is this useful?
Tool directives are sensitive, so ordinary comment reflow should not rewrite them. A separate comment-directive-normalization rule lets projects canonicalize recognized directive syntax without enabling broader trailing-comment extraction or prose formatting.

## Ruff compatibility
Ruff may normalize some comment spacing through its formatter, and `RUF100` can report or remove duplicate and unused `noqa` codes. PCF100 remains independently selectable and covers normalized duplicates across multiple tools while deliberately preserving Ruff range-boundary payloads.

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
#PYDOCFMT : ignore [ pdf101, pcf000, ]
#ruff:ignore[F401,E501]
    # ruff : isort : SKIP_FILE
    #fmt : off
#noinspection PyTypeChecker,PyUnresolvedReferences
# LANGUAGE = SQL prefix=SELECT suffix=FROM table
# @formatter : OFF
#   pylint : disable-next = missing-docstring,unused-argument

[output]
# ruff: noqa
# pydocfmt: ignore[PDF101, PCF000]
# ruff: ignore[F401, E501]
    # ruff: isort: skip_file
    # fmt: off
# noinspection PyTypeChecker, PyUnresolvedReferences
# language=SQL prefix=SELECT suffix=FROM table
# @formatter:off
# pylint: disable-next=missing-docstring, unused-argument
```

Safe list families remove duplicates after applying their family-specific normalization. Canonically uppercased selectors therefore collapse case-only duplicates, while type-checker selectors with different qualified spellings remain distinct:

```pydocfmt-example
[input]
#noqa: f401,F401,e501,E501
#PYDOCFMT : ignore [ pdf101, PDF101, pcf000, ]
#PYDOCFMT : file-ignore [ foo_bar, foo_bar, FOO_BAR, future.rule ]
# type: ignore[assignment, ty:assignment, assignment]
# noinspection PyTypeChecker, PyTypeChecker, pytypechecker

[output]
# noqa: F401, E501
# pydocfmt: ignore[PDF101, PCF000]
# pydocfmt: file-ignore[foo_bar, FOO_BAR, future.rule]
# type: ignore[assignment, ty:assignment]
# noinspection PyTypeChecker, pytypechecker
```

Ruff range boundaries retain repeated selectors and their order so matching `disable` and `enable` payloads keep their pairing semantics:

```pydocfmt-example
[input]
#RUFF : disable [ E501, E501, F401, ]
value = 1
#RUFF : enable [ E501, F401, E501, ]

[output]
# ruff: disable[E501, E501, F401]
value = 1
# ruff: enable[E501, F401, E501]
```

Pydocfmt suppression directives use pydocfmt selector casing and safe list normalization:

```pydocfmt-example
[input]
#PYDOCFMT : noqa : pdf101,pcf000
#PYDOCFMT : ignore [ pdf101, pcf000, ]  # reason
#PYDOCFMT : file-ignore [ pdf, pcf101, ]
#PYDOCFMT : disable [ pdf101 ]

[output]
# pydocfmt: noqa: PDF101, PCF000
# pydocfmt: ignore[PDF101, PCF000]  # reason
# pydocfmt: file-ignore[PDF, PCF101]
# PYDOCFMT : disable [ pdf101 ]
```

Safe machine-readable payloads are normalized, while additional `#` payload text is preserved:

```pydocfmt-example
[input]
typed = compute()#TYPE : ignore[assignment,arg-type]
mixed = compute()#TYPE : ignore[arg-type,ty:invalid-argument-type]
ty_typed = compute()#TY : ignore[invalid-argument-type,unresolved-import]
ruffed = compute() # ruff : noqa : ruf100, f401
ruff_range = compute()#ruff : enable [ E741, F841, ]  # local reason
pycharm = compute()#NoInspection PyTypeChecker,PyUnresolvedReferences
linted = compute()#   PyLiNt : disable = missing-docstring,unused-argument  # local reason

[output]
typed = compute()# type: ignore[assignment, arg-type]
mixed = compute()# type: ignore[arg-type, ty:invalid-argument-type]
ty_typed = compute()# ty: ignore[invalid-argument-type, unresolved-import]
ruffed = compute() # ruff: noqa: RUF100, F401
ruff_range = compute()# ruff: enable[E741, F841]  # local reason
pycharm = compute()# noinspection PyTypeChecker, PyUnresolvedReferences
linted = compute()# pylint: disable=missing-docstring, unused-argument  # local reason
```

Directive normalization is independent of syntax-aware trailing-comment extraction. PCF100 still normalizes directives attached to decorators, arguments, and compound statement headers, but it does not move or wrap them:

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

Unknown directive-like comments are handled by ordinary comment formatting, not PCF100:

```pydocfmt-example
[input]
value = compute() #not-a-known-directive
# unknown-directive

[output=unchanged]
```

## Options
None.
