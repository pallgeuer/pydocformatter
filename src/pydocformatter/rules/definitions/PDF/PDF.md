# pydocformatter docstring formatting (PDF)

## What it does
The PDF category contains rules that detect formatting and safety issues in Python docstrings, including suspicious Unicode, wrapping, indentation, whitespace, quote placement, and blank-line layout. Category preparation builds a convention-aware semantic block tree and explicit reflow regions for summaries, paragraphs, section entries, reST fields, lists, and block quotes. Reflow preserves recognized same-line Markdown and reStructuredText constructs as atomic source-aware tokens and retains explicit space or backslash hard breaks between independently wrapped segments.

`docstring-convention` is explicit and never auto-detected. Google sections, NumPy sections, and reST fields are parsed only under their matching convention. The `none` and `pep257` conventions do not interpret convention syntax. The default `pep257` convention applies PEP 257/pydocstyle-compatible broad-rule carve-outs, while `none` is the stricter no-convention profile for generic rules that can act without convention parsing. Independent `docstring-parse-*` settings control generic lists, headings, doctests, fences, quotes, tables, directives, and literal blocks.

### Considered docstrings
PDF rules consider primary module, class, function, method, and nested-definition docstrings:

```python
"""Module docstring."""


class Client:
    """Class docstring."""

    def close(self):
        """Method docstring."""
```

PDF rules also inventory module attributes, class attributes, and `self.<name>` instance attributes assigned inside `__init__`. Adjacent attribute docstrings collected by common documentation tools are treated as documentation attached to those inventory entries. Supported forms include same-line docstrings, next-line docstrings, annotations without values, multi-target assignments, and tuple-unpacked assignments:

```python
module_value = 1
"""Module attribute docstring."""

module_name: str
"""Annotated module attribute docstring."""

first = second = 1
"""Shared docstring for both module attributes."""

primary, (fallback, *aliases) = endpoints
"""Shared docstring for tuple-unpacked module attributes."""


class Client:
    class_value = 1
    """Class attribute docstring."""

    def __init__(self, enabled):
        self.instance_value = 1; """Same-line instance attribute docstring."""  # fmt: skip
        self.instance_primary, _ = values
        """Tuple-unpacked instance attribute docstring."""
        if enabled:
            self.conditional_value = 1
            """Nested instance attribute docstring."""
```

For classes, the final effective direct class-body `__slots__` binding also contributes instance attributes when its value is a string literal or a tuple made entirely of string literals. Implicit string concatenation is supported. Mutable list values are not treated as proven inventory because later mutation or aliasing can change the runtime slot names. Usable identifier names retain literal order and exact decoded spelling without private-name mangling or keyword rejection; duplicates, `__dict__`, `__weakref__`, and non-identifier strings are ignored. Every exact class-scope rebinding or deletion is considered in source order, including structural pattern captures. Dynamic values, partially static containers, destructuring targets, and final conditional, compound-statement, captured, or deleted bindings do not contribute slot members; a later direct supported assignment can recover, while an annotation-only declaration does not rebind the previous value. Slots are not inherited into subclass inventories. Slot-only members cannot own adjacent docstrings; any real assignment of the same name supplies normal attachment semantics, and the first real annotation supplies type-comparison facts without changing the first-source order among records eligible under the consumer's instance policy. When instance records are excluded, a later real class declaration of the same name remains eligible and owns the inventory position.

Attribute documentation order uses the complete class inventory with instance records enabled, regardless of the missing-instance-documentation setting. Direct class attributes, the `__slots__` binding and its usable literal members, and supported initializer attributes form one first-seen source sequence. Names within supported multi-target assignments retain written left-to-right, depth-first order. Module order uses the corresponding direct module inventory.

PDF rules do not consider additional string literals after a primary docstring, local variable strings outside supported attribute locations, bytes literals, f-strings, list destructuring targets, unsupported tuple leaves, subscript targets, `cls.<name>` targets, or arbitrary object attributes:

```python
def function():
    """Primary docstring."""
    """Ignored additional string."""

    local_value = 1
    """Ignored local string."""


class Client:
    items[0] = 1
    """Ignored subscript target."""
```

## Why is this useful?
Consistent docstring formatting improves readability and keeps documentation stable across automated formatting runs.

## Rules
Rules in this category cover literal and quote normalization, suspicious Unicode, source-level formatting, blank-line layout, placeholder and summary presence, first-line style, convention section and entry style, consistency between docstrings and signatures or attribute inventories, and missing owner docstrings. Reflow rules operate on the semantic regions prepared for the selected convention, while structural rules normalize spacing, conservative type spelling, and section syntax or diagnose high-confidence malformed entry syntax, malformed reStructuredText directive introducers, indentation, and NumPy return-entry shape. Convention normalization owns ASCII spaces and tabs only; non-default whitespace and suspicious controls are preserved or left unchanged for PDF004 and source-preserving rules. Semantic rules validate documented parameters, return values, yields, raised exceptions, optional assertion-derived `AssertionError`, emitted warnings, methods, attributes, and one-to-one reStructuredText value/type field pairing. Wording rules diagnose generic parameter, attribute, return, yield, exception, warning, and method descriptions using family-specific conservative patterns. Recognized inline markup and accepted interior nonbreaking spaces are indivisible regardless of URL balancing; ambiguous markup and suspicious Unicode that would require payload reconstruction are reported without an unsafe fix. Valid and high-confidence malformed directive blocks are protected from prose reflow when directive parsing is enabled. PDF101 owns hard-break-aware layout, while PDF102 preserves space hard breaks during trailing-whitespace cleanup. Signature-validation rules check the presence, exact variadic spelling, and relative declaration order of parsed parameter documentation; attribute-validation rules can likewise compare value-bearing owner documentation with first-seen module or class inventory order. Partial documentation can be order-checked without requiring omitted names to be added. Summary and entry punctuation rules can insert missing periods, replace safely mapped semicolons and standalone commas with periods when the source mapping is exact, and leave potential structured-content introductions, structural colons, and expressive punctuation unchanged. Google and NumPy method signatures remain opaque, while legacy NumPy `name : type` and fallback typed Google method entries retain parsed type slots.

Convention profiles choose among antagonistic PDF policies such as zero or one blank line and required or forbidden documented types. Each profile broadly selects at most one rule from an incompatible pair and may select neither. Some rules are therefore ignored by broad selectors for every `docstring-convention` value while remaining restorable by exact rule-code or rule-name selection. Rules that require parsed convention sections or entries can instead be disabled under `none` and `pep257`, where exact selection cannot restore them because there is no parsed target to check. These convention opt-in rules are distinct from globally opt-in rules controlled by `require-explicit`; the rule list reports convention effects separately and reserves the `Require explicit` column for that setting.

## Related tooling
Individual rule documentation describes relevant Ruff compatibility and differences.

## Code ranges
PDF rules are grouped by contiguous hundred ranges so related rules stay close together and future rules have predictable homes.

| Range    | Topic                                     | Notes                                                                                                                                                                                                   |
|:---------|:------------------------------------------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `PDF0xx` | Literal normalization and safety          | Docstring literal shape, quote style, value-preserving string spelling, and suspicious Unicode.                                                                                                         |
| `PDF1xx` | Core source formatting                    | Indentation, reflow, whitespace, quote placement, and one-line docstring layout.                                                                                                                        |
| `PDF2xx` | Blank lines and basic docstring structure | Excess or missing blank lines inside docstrings, blank-line spacing around docstring statements, empty or placeholder docstrings, missing summaries, and ambiguous multiline summaries.                 |
| `PDF3xx` | Summary and entry wording style           | Summary punctuation, imperative mood, signature duplication, capitalization, first-word wording, and conservative generic entry descriptions.                                                           |
| `PDF4xx` | Convention structure                      | Section names, headers, underlines, content, order, entry and directive syntax, entry indentation, NumPy return shape, spacing, punctuation, and conservative type spelling.                            |
| `PDF5xx` | Docstring/signature validation            | Parameter and attribute presence, extraneous names, configured variadic spelling, relative declaration order, and return, yield, exception, or attribute documentation consistency.                     |
| `PDF6xx` | Owner docstring presence                  | Package, module, class, nested class, function, method, dunder method, `__init__`, and decorator-driven function docstring presence.                                                                    |
| `PDF7xx` | Entry completeness and type consistency   | Parsed parameter, return, yield, exception, warning, attribute, and method descriptions, reStructuredText value/type pairing, type presence policies, and conservative annotation/type mismatch checks. |

## Options

Docstring options below control visible formatting output, missing-documentation policy, decorator policies, and typed class-attribute policy. Convention and parser-selection settings are generally documented in the configuration reference; an individual rule page also lists a parser setting when the settings audit identifies it as a direct rule option or selection dependency, as for PDF418.

| Setting                                          |       Default | Effect                                                                                                          |
|--------------------------------------------------|--------------:|-----------------------------------------------------------------------------------------------------------------|
| `line-length`                                    |          `88` | Maximum display width for docstring wrapping and one-line docstring checks.                                     |
| `url-aware-wrapping`                             |        `true` | Balance line selection around destination-bearing tokens; markup atomicity is unconditional.                    |
| `indent-style`                                   |       `space` | Indentation style used for generated docstring indentation.                                                     |
| `indent-width`                                   |           `4` | Indentation width and tab display width used by generated docstring formatting.                                 |
| `docstring-blank-line-style`                     |       `blank` | Choose whether inserted or normalized blank docstring lines are blank or indentation-aligned.                   |
| `docstring-blank-line-after-last-section`        |       `false` | Keep one blank line after the final recognized section when enabled.                                            |
| `docstring-missing-documentation`                | `has-section` | Select when missing parameter, return, yield, exception, and attribute docs are reported.                       |
| `docstring-missing-documentation-public-only`    |        `true` | Limit broad missing documentation checks to public API names when enabled.                                      |
| `docstring-require-init-attribute-documentation` |       `false` | Include supported `self.*` attributes and literal slot members in class missing-attribute documentation checks. |
| `docstring-include-assertion-errors`             |       `false` | Treat syntactic assertions as possible `AssertionError` occurrences for PDF506 and PDF507.                      |
| `docstring-class-attribute-no-type-base-classes` |          list | Direct class bases whose class attribute entries should not include docstring types.                            |
| `docstring-forbidden-function-decorators`        |          list | Report docstrings on functions decorated by configured no-docstring decorators.                                 |
| `docstring-optional-function-decorators`         |          list | Allow functions decorated by configured decorators to omit docstrings.                                          |
| `docstring-placeholder-markers`                  |          list | Whole-docstring markers reported as unfinished documentation by PDF213.                                         |
| `docstring-property-decorators`                  |          list | Treat functions decorated by configured decorators as properties.                                               |
