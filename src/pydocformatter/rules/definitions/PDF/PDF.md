# pydocformatter docstring formatting (PDF)

## What it does
The PDF category contains rules that detect formatting issues in Python docstrings, including wrapping, indentation, whitespace, quote placement, and blank-line layout. Category preparation builds a convention-aware semantic block tree and explicit reflow regions for summaries, paragraphs, section entries, rest fields, lists, and block quotes.

`docstring-convention` is explicit and never auto-detected. Google sections, NumPy sections, and rest fields are parsed only under their matching convention. The `none` and `pep257` conventions do not interpret convention syntax. Independent `docstring-parse-*` settings control generic lists, headings, doctests, fences, quotes, tables, directives, and literal blocks.

## Why is this useful?
Consistent docstring formatting improves readability and keeps documentation stable across automated formatting runs.

## Rules
Rules in this category cover general docstring reflow as well as specific structural and whitespace corrections.

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

## Related tooling
Individual rule documentation describes relevant Ruff compatibility and differences.
