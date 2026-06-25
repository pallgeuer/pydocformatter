# pydocformatter docstring formatting (PDF)

## What it does
The PDF category contains rules that detect formatting issues in Python docstrings, including wrapping, indentation, whitespace, quote placement, and blank-line layout. Category preparation builds a convention-aware semantic block tree and explicit reflow regions for summaries, paragraphs, section entries, reST fields, lists, and block quotes.

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

PDF rules also consider attribute docstrings collected by common documentation tools. Supported forms are module attributes, class attributes, and `self.<name>` instance attributes assigned inside `__init__`, including same-line docstrings, next-line docstrings, annotations without values, and multi-target assignments:

```python
module_value = 1
"""Module attribute docstring."""

module_name: str
"""Annotated module attribute docstring."""

first = second = 1
"""Shared docstring for both module attributes."""


class Client:
    class_value = 1
    """Class attribute docstring."""

    def __init__(self, enabled):
        self.instance_value = 1; """Same-line instance attribute docstring."""
        if enabled:
            self.conditional_value = 1
            """Nested instance attribute docstring."""
```

PDF rules do not consider additional string literals after a primary docstring, local variable strings outside supported attribute locations, bytes literals, f-strings, unpacking targets, subscript targets, `cls.<name>` targets, or arbitrary object attributes:

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
Rules in this category cover literal and quote normalization, source-level formatting, blank-line layout, first-line style, convention section style, and consistency between docstrings and signatures. Reflow rules operate on the semantic regions prepared for the selected convention, while structural rules normalize spacing, section syntax, and documented parameters, return values, yields, and exceptions.

## Related tooling
Individual rule documentation describes relevant Ruff compatibility and differences.

## Code ranges
PDF rules are grouped by contiguous hundred ranges so related rules stay close together and future rules have predictable homes.

| Range    | Topic                            | Notes                                                                                                |
|:---------|:---------------------------------|:-----------------------------------------------------------------------------------------------------|
| `PDF0xx` | Literal and quote normalization  | Docstring literal shape, quote style, and value-preserving string spelling.                          |
| `PDF1xx` | Core source formatting           | Indentation, reflow, whitespace, quote placement, and one-line docstring layout.                     |
| `PDF2xx` | Blank lines and empty docstrings | Excess or missing blank lines, empty docstrings, and ambiguous multiline summaries.                  |
| `PDF3xx` | First-line style                 | Summary punctuation, imperative mood, signature duplication, capitalization, and first-word wording. |
| `PDF4xx` | Section style                    | Section names, headers, underlines, section content, section order, and section punctuation.         |
| `PDF5xx` | Docstring/signature validation   | Parameter, return, yield, and exception documentation consistency.                                   |

## Options
Docstring options control which convention-specific structures are parsed, which generic structures are protected or reflowed, and how selected formatting and documentation checks behave.

| Setting                                       |       Default | Effect                                                                                  |
|-----------------------------------------------|--------------:|-----------------------------------------------------------------------------------------|
| `docstring-convention`                        |      `pep257` | Parse Google sections, NumPy sections, or reStructuredText fields only when selected.   |
| `docstring-parse-list-items`                  |        `true` | Parse list items as distinct structures for reflow and protection.                      |
| `docstring-parse-headings`                    |        `true` | Parse Markdown and reStructuredText headings as protected structures.                   |
| `docstring-parse-doctests`                    |        `true` | Parse doctest regions as protected structures.                                          |
| `docstring-parse-code-fences`                 |        `true` | Parse fenced code blocks as protected structures.                                       |
| `docstring-parse-block-quotes`                |        `true` | Parse Markdown block quotes for prefix-preserving reflow.                               |
| `docstring-parse-tables`                      |        `true` | Parse Markdown and reStructuredText tables as protected structures.                     |
| `docstring-parse-directives`                  |        `true` | Parse reStructuredText directives and their bodies as protected structures.             |
| `docstring-parse-literal-blocks`              |        `true` | Parse reStructuredText literal blocks as protected structures.                          |
| `docstring-blank-line-style`                  |       `blank` | Choose whether inserted blank lines are blank or aligned to the docstring indentation.  |
| `docstring-blank-line-after-last-section`     |       `false` | Keep one blank line after the final recognized Google or NumPy section when enabled.    |
| `docstring-missing-documentation`             | `has-section` | Select which missing parameter, return, yield, and exception documentation is reported. |
| `docstring-missing-documentation-public-only` |        `true` | Limit missing documentation checks to public API names when enabled.                    |
