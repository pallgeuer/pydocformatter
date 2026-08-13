# class-attribute-documentation-order (PDF528)

Fix is not available.

Rule is disabled if `docstring-convention` is `none` or `pep257`, and ignored by broad selectors under `google`, `numpy`, and `rest`.

## What it does
Checks that value-bearing attribute entries in an owning class docstring follow the first-seen source order of known class and instance attributes. PDF528 checks every class independently, including nested classes, and remains applicable when `source-context` is `fragment`.

The class inventory combines supported class-scope assignments and annotations, names in multi-target and tuple-unpacked assignments, the `__slots__` attribute and usable members from the final effective literal `__slots__` binding, and supported `self.*` assignments in `__init__`. These sources form one sequence in source order; names within one assignment retain written left-to-right, depth-first order. A name's first inventory occurrence establishes its position, so later assignments do not move it. The complete inventory is used regardless of missing-documentation settings, including `docstring-require-init-attribute-documentation`. Inherited attributes and assignments inside other methods are not part of the owning class's inventory.

The rule compares only the first value-bearing documentation occurrence of each known name. Partial documentation remains valid. Unknown names, wrong-case names, and repeated entries do not establish or reset the sequence; matching is case-sensitive. Google and NumPy attribute-section aliases form one sequence across the complete docstring, and names in a NumPy multi-name entry retain their written order. For reStructuredText docstrings, `:ivar:`, `:cvar:`, and `:var:` value fields establish positions, while type-only `:vartype:` fields do not. Entry-like text protected as examples, literal blocks, directives, or similar structures does not participate.

Every late first occurrence is reported against the known attribute with the latest source position among those documented before it. A reported occurrence does not reset that comparison point. Attached attribute docstrings, module and function docstrings, additional string literals, and classes without an owning class docstring are outside this rule. Use PDF529 to check module attribute documentation order.

Fixes are not offered because moving an entry safely can require moving multiline descriptions, nested content, blank lines, and paired reStructuredText fields together.

The rule is preference-sensitive because conceptual grouping or public API prominence can reasonably differ from source order. Under Google, NumPy, and reStructuredText conventions, broad selectors ignore PDF528 and exact `PDF528` selection opts into it.

## Why is this useful?
Keeping class attribute documentation aligned with declarations makes class docstrings easier to compare with source and exposes stale ordering after declarations move, without requiring every attribute to be documented.

## Ruff compatibility
Ruff has no direct class-attribute-documentation-order rule. Ruff's `RUF023` can sort literal `__slots__` members; when that changes source slot order, PDF528 checks documentation against the resulting order.

## Examples
A class attribute documented after a later declaration is reported on its docstring entry:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
class Limits:
    """Store limits.

    Attributes:
        high: Upper limit.
        low: Lower limit.
    """

    low = 0
    high = 100

[output=unchanged]
[findings]
PDF528: Line 6: Class docstring attribute 'low' should appear before 'high' to match the source declaration order
```

Class attributes, slot members, and initializer attributes use one combined first-seen source order:

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
    __slots__ = ("slot", "__dict__")

    def __init__(self):
        self.instance = 2

[output=unchanged]
[findings]
PDF528: Line 6: Class docstring attribute 'slot' should appear before 'instance' to match the source declaration order
PDF528: Line 7: Class docstring attribute 'direct' should appear before 'instance' to match the source declaration order
```

Omitted attributes need not be added. Unknown, wrong-case, and repeated names are ignored when comparing the known first occurrences:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
class Values:
    """Store selected values.

    Attributes:
        second: Second value.
        stale: Obsolete value.
        Second: Wrong-case name.
        second: Repeated second value.
        third: Third value.
    """

    first = 1
    second = 2
    third = 3

[output=unchanged]
```

Each late name in a NumPy multi-name entry receives a finding, even when the findings share a line:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
class Values:
    """Store values.

    Attributes
    ----------
    third, first, second : int
        Stored values.
    """

    first = 1
    second = 2
    third = 3

[output=unchanged]
[findings]
PDF528: Line 6: Class docstring attribute 'first' should appear before 'third' to match the source declaration order
PDF528: Line 6: Class docstring attribute 'second' should appear before 'third' to match the source declaration order
```

For reStructuredText, value fields establish order and type-only fields do not:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
class Values:
    """Store values.

    :vartype first: int
    :var second: Second value.
    :vartype second: int
    :var first: First value.
    """

    first = 1
    second = 2

[output=unchanged]
[findings]
PDF528: Line 7: Class docstring attribute 'first' should appear before 'second' to match the source declaration order
```

## Options
None.
