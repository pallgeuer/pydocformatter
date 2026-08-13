# module-attribute-documentation-order (PDF529)

Fix is not available.

Rule is disabled if `docstring-convention` is `none` or `pep257`, and ignored by broad selectors under `google`, `numpy`, and `rest`.

Rule applies only when `source-context` is `module`.

## What it does
Checks that value-bearing attribute entries in the module docstring follow the first-seen source order of known module attributes. The inventory includes supported module-scope assignments and annotations, names in multi-target assignments, and tuple-unpacked assignment leaves. Names within one assignment retain written left-to-right, depth-first order. A name's first inventory occurrence establishes its position, so later assignments do not move it.

The rule compares only the first value-bearing documentation occurrence of each known name. Partial documentation remains valid. Unknown names, wrong-case names, and repeated entries do not establish or reset the sequence; matching is case-sensitive. Google and NumPy attribute-section aliases form one sequence across the complete docstring, and names in a NumPy multi-name entry retain their written order. For reStructuredText docstrings, `:ivar:`, `:cvar:`, and `:var:` value fields establish positions, while type-only `:vartype:` fields do not. Entry-like text protected as examples, literal blocks, directives, or similar structures does not participate.

Every late first occurrence is reported against the known attribute with the latest source position among those documented before it. A reported occurrence does not reset that comparison point. Attached attribute docstrings, class and function docstrings, and additional string literals are outside this rule. Use PDF528 to check class attribute documentation order. PDF529 is module-only, so exact selection does not make it run when `source-context` is `fragment`.

Fixes are not offered because moving an entry safely can require moving multiline descriptions, nested content, blank lines, and paired reStructuredText fields together.

The rule is preference-sensitive because conceptual grouping or public API prominence can reasonably differ from source order. Under Google, NumPy, and reStructuredText conventions, broad selectors ignore PDF529 and exact `PDF529` selection opts into it.

## Why is this useful?
Keeping module attribute documentation aligned with declarations makes module docstrings easier to compare with source and exposes stale ordering after declarations move, without requiring every attribute to be documented.

## Ruff compatibility
None.

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
PDF529: Line 5: Module docstring attribute 'low' should appear before 'high' to match the source declaration order
```

Multi-target assignments use their written left-to-right, depth-first target order:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
"""Module values.

Attributes:
    fourth: Fourth value.
    third: Third value.
    second: Second value.
    first: First value.
"""

first = second = 1
third, (fourth, *rest) = values

[output=unchanged]
[findings]
PDF529: Line 5: Module docstring attribute 'third' should appear before 'fourth' to match the source declaration order
PDF529: Line 6: Module docstring attribute 'second' should appear before 'fourth' to match the source declaration order
PDF529: Line 7: Module docstring attribute 'first' should appear before 'fourth' to match the source declaration order
```

Omitted attributes need not be added. Unknown, wrong-case, and repeated names are ignored when comparing the known first occurrences:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
"""Selected module values.

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
"""Module values.

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
PDF529: Line 5: Module docstring attribute 'first' should appear before 'third' to match the source declaration order
PDF529: Line 5: Module docstring attribute 'second' should appear before 'third' to match the source declaration order
```

For reStructuredText, value fields establish order and type-only fields do not:

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
PDF529: Line 6: Module docstring attribute 'first' should appear before 'second' to match the source declaration order
```

Fragment source has no semantic module owner, so the module-only rule remains disabled even when selected by its exact code:

```pydocfmt-example
[settings]
docstring-convention = "google"
source-context = "fragment"

[input]
"""Example fragment.

Attributes:
    second: Second value.
    first: First value.
"""

first = 1
second = 2

[output=unchanged]
```

## Options
None.
