# pydocformatter docstring formatting (PDF)

## What it does
The PDF category contains rules that detect formatting issues in Python docstrings, including wrapping, indentation, whitespace, quote placement, and blank-line layout. Category preparation builds a convention-aware semantic block tree and explicit reflow regions for summaries, paragraphs, section entries, reST fields, lists, and block quotes. Reflow preserves recognized same-line Markdown and reStructuredText constructs as atomic source-aware tokens and retains explicit space or backslash hard breaks between independently wrapped segments.

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
Rules in this category cover literal and quote normalization, source-level formatting, blank-line layout, summary presence and first-line style, convention section style, consistency between docstrings and signatures or attribute inventories, and missing owner docstrings. Reflow rules operate on the semantic regions prepared for the selected convention, while structural rules normalize spacing, section syntax, and documented parameters, return values, yields, exceptions, and attributes. Recognized inline markup is indivisible regardless of URL balancing; ambiguous markup that would require reflow is reported without an unsafe fix. PDF101 owns hard-break-aware layout, while PDF102 preserves space hard breaks during trailing-whitespace cleanup. Signature-validation rules check both the presence and relative declaration order of parsed parameter documentation; partial documentation can be order-checked without requiring omitted parameters to be added.

Some PDF rules are ignored by broad selectors for every parsed `docstring-convention` value. Because ignored setting effects are restored by exact rule-code selection, those rules are effectively opt-in by exact code even when they are not listed as `require-explicit` rules. Rules that require parsed convention sections or entries can instead be disabled under `none` and `pep257`, where exact selection cannot restore them because there is no parsed target to check. The rule list shows these states as `Ignored` or `Disabled` in the convention columns; the `Explicit` column is reserved for rules controlled by `require-explicit`.

## Related tooling
Individual rule documentation describes relevant Ruff compatibility and differences.

## Code ranges
PDF rules are grouped by contiguous hundred ranges so related rules stay close together and future rules have predictable homes.

| Range    | Topic                                     | Notes                                                                                                                                                                    |
|:---------|:------------------------------------------|:-------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `PDF0xx` | Literal and quote normalization           | Docstring literal shape, quote style, and value-preserving string spelling.                                                                                              |
| `PDF1xx` | Core source formatting                    | Indentation, reflow, whitespace, quote placement, and one-line docstring layout.                                                                                         |
| `PDF2xx` | Blank lines and basic docstring structure | Excess or missing blank lines inside docstrings, blank-line spacing around docstring statements, empty docstrings, missing summaries, and ambiguous multiline summaries. |
| `PDF3xx` | Summary and entry wording style           | Summary punctuation, imperative mood, signature duplication, capitalization, first-word wording, and generic parameter or attribute documentation.                       |
| `PDF4xx` | Section style                             | Section names, headers, underlines, section content, section order, and section punctuation.                                                                             |
| `PDF5xx` | Docstring/signature validation            | Parameter presence, extraneous names, and relative declaration order plus return, yield, exception, and attribute documentation consistency.                             |
| `PDF6xx` | Owner docstring presence                  | Package, module, class, nested class, function, method, dunder method, `__init__`, and decorator-driven function docstring presence.                                     |
| `PDF7xx` | Typed entry completeness                  | Parsed owning-docstring entry descriptions, type presence policies, and conservative annotation/type mismatch checks.                                                    |

## Options
Docstring options below control visible formatting output, missing-documentation policy, decorator policies, and typed class-attribute policy. Convention and parser-selection settings are documented in the configuration reference rather than in rule Options sections.

| Setting                                          |       Default | Effect                                                                                        |
|--------------------------------------------------|--------------:|-----------------------------------------------------------------------------------------------|
| `line-length`                                    |          `88` | Maximum display width for docstring wrapping and one-line docstring checks.                   |
| `url-aware-wrapping`                             |        `true` | Balance line selection around destination-bearing tokens; markup atomicity is unconditional.  |
| `indent-style`                                   |       `space` | Indentation style used for generated docstring indentation.                                   |
| `indent-width`                                   |           `4` | Indentation width and tab display width used by generated docstring formatting.               |
| `docstring-blank-line-style`                     |       `blank` | Choose whether inserted or normalized blank docstring lines are blank or indentation-aligned. |
| `docstring-blank-line-after-last-section`        |       `false` | Keep one blank line after the final recognized section when enabled.                          |
| `docstring-missing-documentation`                | `has-section` | Select when missing parameter, return, yield, exception, and attribute docs are reported.     |
| `docstring-missing-documentation-public-only`    |        `true` | Limit broad missing documentation checks to public API names when enabled.                    |
| `docstring-require-init-attribute-documentation` |       `false` | Include supported `self.*` attributes in class missing-attribute documentation checks.        |
| `docstring-class-attribute-no-type-base-classes` |          list | Direct class bases whose class attribute entries should not include docstring types.          |
| `docstring-forbidden-function-decorators`        |          list | Report docstrings on functions decorated by configured no-docstring decorators.               |
| `docstring-optional-function-decorators`         |          list | Allow functions decorated by configured decorators to omit docstrings.                        |
| `docstring-property-decorators`                  |          list | Treat functions decorated by configured decorators as properties.                             |
