# pydocformatter comment formatting (PCF)

## What it does
The PCF category formats ordinary standalone and trailing Python comments. It collects comments losslessly with LibCST, classifies comments that must be protected, and provides physical placement and source-range information to the individual rules.

PCF rules never format shebangs, valid first- or second-line encoding cookies, type comments, or recognized tool directives. Protected tool directives include `noqa`, `nosec`, `nosemgrep`, `pylint`, `pyright`, `mypy`, `ruff`, `flake8`, `fmt:`, `isort:`, and `pragma` comments.

Comment widths use tab-expanded display columns. `indent-width` supplies the tab width; other Unicode code points count as one column. Generated comment lines use the resolved `line-ending`, while source outside an edited range retains its existing line endings and final-newline state.

## Why is this useful?
Comments remain readable and consistently spaced without rewriting directives or requiring Ruff to perform transformations outside its formatter scope. Separate standalone and trailing rules allow either behavior to be selected or disabled independently.

## Rules
- `PCF001` formats regular standalone comments. Its default physical-line behavior is conservative, while optional settings enable paragraph joining, structured-markup handling, and broader disabled-code detection.
- `PCF002` normalizes regular trailing comments and moves overlong trailing comments above their code. It does not depend on `PCF001` and does not apply standalone-structure heuristics.

Physical standalone runs contain consecutive, same-indent, regular, non-empty comments. Empty comments, hash-only separators, protected comments, indentation changes, and nonconsecutive source lines end a run. PCF001 may subdivide a run further according to its enabled structure settings.

## Code ranges
PCF rules currently occupy one contiguous range because the category covers comment formatting only.

| Range    | Topic              | Notes                                             |
|:---------|:-------------------|:--------------------------------------------------|
| `PCF0xx` | Comment formatting | Standalone and trailing comment formatting rules. |

## Related tooling
Ruff can report comment line-length and whitespace issues, but does not provide equivalent configurable comment reflow and trailing-comment extraction.

## Settings
Standalone paragraph joining remains disabled by default, so ordinary prose comments are formatted one physical line at a time. List items and block quotes are formatted by default, fenced code is preserved, and Python statements are protected from prose formatting.

| Setting                         | Default | Effect                                                                                                        |
|---------------------------------|--------:|---------------------------------------------------------------------------------------------------------------|
| `comment-join-standalone-lines` | `false` | Join consecutive ordinary prose lines into paragraphs before wrapping.                                        |
| `comment-format-list-items`     |  `true` | Detect ordered and unordered list items and reflow them with hanging indentation.                             |
| `comment-preserve-headings`     |  `true` | Preserve detected Markdown and reStructuredText headings unchanged.                                           |
| `comment-preserve-doctests`     |  `true` | Preserve a doctest region from its first `>>>` prompt to the physical-run boundary.                           |
| `comment-preserve-code-fences`  |  `true` | Preserve backtick- or tilde-fenced code regions closed by a fence without trailing text.                      |
| `comment-format-block-quotes`   |  `true` | Detect Markdown block quotes and reflow text while retaining quote prefixes.                                  |
| `comment-preserve-tables`       |  `true` | Preserve structurally detected Markdown pipe tables and reStructuredText grid or simple tables.               |
| `comment-preserve-directives`   |  `true` | Preserve reStructuredText directives and their more-indented option/content lines.                            |
| `comment-detect-code`           | `false` | Protect a whole run when the indentation or leading-keyword heuristic detects disabled code.                  |
| `comment-detect-statements`     |  `true` | Protect a whole run when individual or multiline text parses as Python containing a non-expression statement. |
| `comment-detect-expressions`    | `false` | Protect a whole run when text parses as a nontrivial Python expression.                                       |
