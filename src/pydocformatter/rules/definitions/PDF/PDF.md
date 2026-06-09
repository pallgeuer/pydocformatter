# pydocformatter docstring formatting (PDF)

## What it does
The PDF category contains rules that detect formatting issues in Python docstrings, including wrapping, indentation, whitespace, quote placement, and blank-line layout. Category preparation builds a convention-aware semantic block tree and explicit reflow regions for summaries, paragraphs, section entries, lists, block quotes, and Sphinx fields.

`docstring-convention` is explicit and never auto-detected. Google and NumPy sections are parsed only under their matching convention. The `none` and `pep257` conventions do not interpret Google or NumPy section syntax. Independent `docstring-parse-*` settings control generic lists, headings, doctests, fences, quotes, tables, directives, literal blocks, and Sphinx fields.

## Why is this useful?
Consistent docstring formatting improves readability and keeps documentation stable across automated formatting runs.

## Rules
Rules in this category cover general docstring reflow as well as specific structural and whitespace corrections.

## Related tooling
Individual rule documentation describes relevant Ruff compatibility and differences.
