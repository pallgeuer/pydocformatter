# attribute-documentation-order (PDF528)

Fix is not available.

Rule is disabled if `docstring-convention` is `none` or `pep257`, and ignored by broad selectors under `google`, `numpy`, and `rest`.

## What it does
Checks that value-bearing attribute entries in module and class docstrings follow the first-seen source order of known attributes. The rule compares only documented known names, so partial documentation remains valid and unknown names do not affect the sequence. Only the first documentation occurrence of each known name participates.

Class order uses one source sequence containing direct class attributes, members from the final effective literal `__slots__` declaration, and supported `self.*` assignments in `__init__`. The `__slots__` binding itself remains a normal known attribute, while usable literal members enter immediately after it in literal order. Private and dunder names participate when voluntarily documented. Multi-target assignments use their written left-to-right, depth-first target order.

For reStructuredText docstrings, only value fields such as `:ivar:`, `:cvar:`, and `:var:` establish positions. Type-only `:vartype:` companions do not establish or move an attribute's position. Attached attribute docstrings, function docstrings, inherited attributes, and unsupported assignment forms are outside this rule.

Every late first occurrence is reported against the highest-ranked known attribute documented before it. Fixes are not offered because moving an entry safely can require moving multiline descriptions, nested content, blank lines, and paired reStructuredText fields together.

The rule is preference-sensitive because conceptual grouping or public API prominence can reasonably differ from source order. Under Google, NumPy, and reStructuredText conventions, broad selectors ignore PDF528 and exact `PDF528` selection opts into it. The rule is disabled under `none` and `pep257`, where attribute entries are not parsed.

## Why is this useful?
Keeping attribute documentation aligned with declarations makes owner docstrings easier to compare with source and exposes stale ordering after declarations move, without requiring every attribute to be documented.

## Ruff compatibility
Ruff has no direct attribute-documentation-order rule. Ruff's `RUF023` can sort literal `__slots__` members; when that changes source slot order, PDF528 checks documentation against the resulting order.

## Examples
A module attribute documented after a later declaration is reported:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
"""Module limits.

Attributes:
    high: Upper limit.
    low: Lower limit.
"""

low = 0
high = 100

[output=unchanged]
[findings]
PDF528: Line 5: Docstring attribute 'low' should appear before 'high' to match the source declaration order
```

Class attributes, slot members, and initializer attributes use one first-seen source order:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
class State:
    """Store state.

    Attributes:
        instance: Instance value.
        slot: Slotted value.
        direct: Direct value.
    """

    direct = 1
    __slots__ = ("slot",)

    def __init__(self):
        self.instance = 2

[output=unchanged]
[findings]
PDF528: Line 6: Docstring attribute 'slot' should appear before 'instance' to match the source declaration order
PDF528: Line 7: Docstring attribute 'direct' should appear before 'instance' to match the source declaration order
```

Partial documentation and unknown or repeated names do not reset the known-name sequence:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
"""Module values.

Attributes
----------
third, stale, first, third, second : int
    Stored values.
"""

first = 1
second = 2
third = 3

[output=unchanged]
[findings]
PDF528: Line 5: Docstring attribute 'first' should appear before 'third' to match the source declaration order
PDF528: Line 5: Docstring attribute 'second' should appear before 'third' to match the source declaration order
```

Partial documentation is valid when the documented known names retain their relative source order. Unknown names are ignored, and later assignments do not move an attribute from its first-seen position:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
"""Module values.

Attributes:
    first: First documented value.
    external: Value supplied dynamically.
    third: Third documented value.
"""

first = 1
second = 2
third = 3
first = 4

[output=unchanged]
```

In reStructuredText docstrings, only value fields determine attribute order; an earlier type field does not count as an attribute's first occurrence:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
"""Module values.

:vartype first: int
:var second: Second value.
:vartype second: int
:var first: First value.
"""

first = 1
second = 2

[output=unchanged]
[findings]
PDF528: Line 6: Docstring attribute 'first' should appear before 'second' to match the source declaration order
```

## Options
None.
