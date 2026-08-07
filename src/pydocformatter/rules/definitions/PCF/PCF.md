# pydocformatter comment formatting (PCF)

## What it does
The PCF category formats standalone and trailing Python comments, checks them for suspicious Unicode, and enforces optional suppression-selector representation policies. It collects comments losslessly with LibCST, classifies comments that must be protected from ordinary prose formatting, and provides physical placement, source-range, and shared bracket-directive information to the individual rules.

PCF rules never format shebangs or valid first- or second-line encoding cookies. Type comments and recognized tool directives are protected from ordinary comment formatting; trailing-comment spacing may still normalize the delimiter before `#`, and directive normalization may normalize safe marker spacing and machine-readable syntax from `#` onward in recognized directives. Protected tool directives include `noqa`, `nosec`, `nosemgrep`, `pydocfmt`, `pylint`, `pyright`, `mypy`, `ty:`, `ruff`, `flake8`, `fmt:`, `isort:`, `pragma`, PyCharm `noinspection`, PyCharm `language=`, and PyCharm `@formatter:` marker comments.

Comment widths use tab-expanded display columns. `indent-width` supplies the tab width; other Unicode code points count as one column. Generated comment lines use the resolved `line-ending`, while source outside an edited range retains its existing line endings and final-newline state. Recognized same-line Markdown and reStructuredText constructs are atomic in standalone formatting and PCF002's directly generated extracted blocks. Preserved reStructuredText directives use Unicode word-character components with isolated `-`, `_`, `+`, `.`, and `:` separators for namespaced types, allow one optional ASCII space before the two-colon delimiter, and require whitespace or the end of the line after it. Space and backslash hard breaks remain physical semantic boundaries in standalone comment units.

## Why is this useful?
Comments remain readable and consistently spaced without rewriting directives or requiring Ruff to perform transformations outside its formatter scope. Separate standalone and trailing rules allow either behavior to be selected or disabled independently.

## Rules
Rules in this category cover regular standalone comment formatting, regular trailing-comment spacing, safe directive normalization and stable semantic list deduplication, syntax-aware extraction of overlong trailing comments, unused pydocfmt suppression directives, suspicious Unicode safety, and mutually exclusive name-only or code-only suppression styles. PCF101 audits each distinct semantic pydocfmt selector once without changing suppression coverage. PCF102 converts known local codes to names and diagnoses exact Ruff codes; PCF103 applies the inverse local policy. Before ordinary standalone-run formatting, PCF000 normalizes regular standalone comments whose nonempty payload contains only ASCII space, tab, or form feed to a bare `#`. Standalone formatting is conservative by default, while optional settings enable paragraph joining, structured-markup handling, and broader disabled-code detection. Inline markup recognition is unconditional; `url-aware-wrapping` changes only balanced line selection. Ambiguous inline markup or suspicious Unicode on an otherwise extraction-eligible overlong line is reported without an unsafe semantic-body rewrite, making PCF000 and PCF002 usually fixable. Trailing-comment extraction only moves comments when the surrounding syntax and comment content are safe to rewrite, and its ambiguity guard remains active when content awareness is disabled.

Physical standalone runs contain consecutive, same-indent, regular, non-empty comments. Empty comments, including those normalized by PCF000's pre-run pass, hash-only separators, protected comments, indentation changes, and nonconsecutive source lines end a run. Standalone formatting may subdivide a run further according to its enabled structure settings.

## Related tooling
Ruff can report comment line-length, whitespace, ambiguous Unicode, selected invalid characters, unused suppressions, and rule codes in its own suppression comments. It does not provide equivalent configurable comment reflow, trailing-comment extraction, PCF201's explicit policy and indentation fixes, or PCF103's inverse code-preference policy. PCF102 intentionally leaves Ruff selector conversion diagnostic-only because pydocformatter does not own Ruff's rule catalog.

## Code ranges
PCF rules use separate ranges for general formatting, directives and suppressions, and character safety.

| Range    | Topic                        | Notes                                                                |
|:---------|:-----------------------------|:---------------------------------------------------------------------|
| `PCF0xx` | Comment formatting           | Standalone and trailing comment formatting and spacing.              |
| `PCF1xx` | Directives and suppressions  | Directive normalization, auditing, and representation policies.      |
| `PCF2xx` | ASCII and Unicode characters | ASCII-only and suspicious-Unicode comment character safety policies. |

## Options
Standalone paragraph joining remains disabled by default, so ordinary prose comments are formatted one physical line at a time. The options below control comment wrapping, structure handling, preservation, extraction safety, and code detection.

| Setting                                     |   Default | Effect                                                                                                                                            |
|---------------------------------------------|----------:|---------------------------------------------------------------------------------------------------------------------------------------------------|
| `line-length`                               |      `88` | Maximum display width for wrapped standalone comments and extracted trailing comments.                                                            |
| `indent-width`                              |       `4` | Tab display width used for comment wrapping and structure-prefix calculations.                                                                    |
| `url-aware-wrapping`                        |    `true` | Balance line selection around destination-bearing tokens; markup atomicity is unconditional.                                                      |
| `comment-join-standalone-lines`             |   `false` | Join consecutive ordinary prose lines into paragraphs before wrapping.                                                                            |
| `comment-format-list-items`                 |    `true` | Detect ordered and unordered list items and reflow them with hanging indentation.                                                                 |
| `comment-task-marker-mode`                  | `no-wrap` | Control recognized task markers with `none`, `no-wrap`, or `hanging`.                                                                             |
| `comment-task-markers`                      |      list | Exact uppercase task marker labels recognized before `:`.                                                                                         |
| `comment-preserve-headings`                 |    `true` | Preserve detected Markdown and reStructuredText headings unchanged.                                                                               |
| `comment-preserve-doctests`                 |    `true` | Preserve standalone doctest regions unchanged.                                                                                                    |
| `comment-preserve-code-fences`              |    `true` | Preserve fenced code regions in standalone comments unchanged.                                                                                    |
| `comment-format-block-quotes`               |    `true` | Detect Markdown block quotes and reflow text while retaining quote prefixes.                                                                      |
| `comment-preserve-tables`                   |    `true` | Preserve structurally detected Markdown pipe tables and reStructuredText grid or simple tables.                                                   |
| `comment-preserve-directives`               |    `true` | Preserve valid reStructuredText directives, including namespaced types, and their more-indented option/content lines.                             |
| `comment-trailing-extraction-syntax-aware`  |    `true` | Keep overlong trailing comments inline in decorators, compound headers, arguments, and continuation contexts.                                     |
| `comment-trailing-extraction-content-aware` |    `true` | Keep overlong trailing comments inline when enabled standalone comment structure/code detectors or the operator heuristic make extraction unsafe. |
| `comment-detect-code`                       |   `false` | Protect a whole standalone run, or keep extracted content inline, when the indentation or leading-keyword heuristic detects disabled code.        |
| `comment-detect-statements`                 |    `true` | Protect a whole standalone run, or keep extracted content inline, when text parses as Python containing a non-expression statement.               |
| `comment-detect-expressions`                |   `false` | Protect a whole standalone run, or keep extracted content inline, when text parses as a nontrivial Python expression.                             |
