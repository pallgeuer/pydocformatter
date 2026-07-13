# pydocformatter comment formatting (PCF)

## What it does
The PCF category formats standalone and trailing Python comments. It collects comments losslessly with LibCST, classifies comments that must be protected from ordinary prose formatting, and provides physical placement and source-range information to the individual rules.

PCF rules never format shebangs or valid first- or second-line encoding cookies. Type comments and recognized tool directives are protected from ordinary comment formatting; trailing-comment spacing may still normalize the delimiter before `#`, and directive normalization may normalize safe marker spacing and machine-readable syntax from `#` onward in recognized directives. Protected tool directives include `noqa`, `nosec`, `nosemgrep`, `pydocfmt`, `pylint`, `pyright`, `mypy`, `ty:`, `ruff`, `flake8`, `fmt:`, `isort:`, `pragma`, PyCharm `noinspection`, PyCharm `language=`, and PyCharm `@formatter:` marker comments.

Comment widths use tab-expanded display columns. `indent-width` supplies the tab width; other Unicode code points count as one column. Generated comment lines use the resolved `line-ending`, while source outside an edited range retains its existing line endings and final-newline state.

## Why is this useful?
Comments remain readable and consistently spaced without rewriting directives or requiring Ruff to perform transformations outside its formatter scope. Separate standalone and trailing rules allow either behavior to be selected or disabled independently.

## Rules
Rules in this category cover regular standalone comment formatting, regular trailing-comment spacing, safe directive normalization, syntax-aware extraction of overlong trailing comments, and unused pydocfmt suppression directives. Standalone formatting is conservative by default, while optional settings enable paragraph joining, structured-markup handling, and broader disabled-code detection. Trailing-comment extraction only moves comments when the surrounding syntax and comment content are safe to rewrite.

Physical standalone runs contain consecutive, same-indent, regular, non-empty comments. Empty comments, hash-only separators, protected comments, indentation changes, and nonconsecutive source lines end a run. Standalone formatting may subdivide a run further according to its enabled structure settings.

## Related tooling
Ruff can report comment line-length and whitespace issues, but does not provide equivalent configurable comment reflow and trailing-comment extraction.

## Code ranges
PCF rules currently occupy one contiguous range because the category covers comment formatting only.

| Range    | Topic              | Notes                                             |
|:---------|:-------------------|:--------------------------------------------------|
| `PCF0xx` | Comment formatting | Standalone and trailing comment formatting rules. |

## Options
Standalone paragraph joining remains disabled by default, so ordinary prose comments are formatted one physical line at a time. The options below control comment wrapping, structure handling, preservation, extraction safety, and code detection.

| Setting                                     |   Default | Effect                                                                                                                                            |
|---------------------------------------------|----------:|---------------------------------------------------------------------------------------------------------------------------------------------------|
| `line-length`                               |      `88` | Maximum display width for wrapped standalone comments and extracted trailing comments.                                                            |
| `indent-width`                              |       `4` | Tab display width used for comment wrapping and structure-prefix calculations.                                                                    |
| `url-aware-wrapping`                        |    `true` | Keep URL tokens unbroken while balancing surrounding prose when wrapping.                                                                         |
| `comment-join-standalone-lines`             |   `false` | Join consecutive ordinary prose lines into paragraphs before wrapping.                                                                            |
| `comment-format-list-items`                 |    `true` | Detect ordered and unordered list items and reflow them with hanging indentation.                                                                 |
| `comment-task-marker-mode`                  | `no-wrap` | Control recognized task markers with `none`, `no-wrap`, or `hanging`.                                                                             |
| `comment-task-markers`                      |      list | Exact uppercase task marker labels recognized before `:`.                                                                                         |
| `comment-preserve-headings`                 |    `true` | Preserve detected Markdown and reStructuredText headings unchanged.                                                                               |
| `comment-preserve-doctests`                 |    `true` | Preserve standalone doctest regions unchanged.                                                                                                    |
| `comment-preserve-code-fences`              |    `true` | Preserve fenced code regions in standalone comments unchanged.                                                                                    |
| `comment-format-block-quotes`               |    `true` | Detect Markdown block quotes and reflow text while retaining quote prefixes.                                                                      |
| `comment-preserve-tables`                   |    `true` | Preserve structurally detected Markdown pipe tables and reStructuredText grid or simple tables.                                                   |
| `comment-preserve-directives`               |    `true` | Preserve reStructuredText directives and their more-indented option/content lines.                                                                |
| `comment-trailing-extraction-syntax-aware`  |    `true` | Keep overlong trailing comments inline in decorators, compound headers, arguments, and continuation contexts.                                     |
| `comment-trailing-extraction-content-aware` |    `true` | Keep overlong trailing comments inline when enabled standalone comment structure/code detectors or the operator heuristic make extraction unsafe. |
| `comment-detect-code`                       |   `false` | Protect a whole standalone run, or keep extracted content inline, when the indentation or leading-keyword heuristic detects disabled code.        |
| `comment-detect-statements`                 |    `true` | Protect a whole standalone run, or keep extracted content inline, when text parses as Python containing a non-expression statement.               |
| `comment-detect-expressions`                |   `false` | Protect a whole standalone run, or keep extracted content inline, when text parses as a nontrivial Python expression.                             |
