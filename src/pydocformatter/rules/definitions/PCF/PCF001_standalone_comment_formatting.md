# standalone-comment-formatting (PCF001)

Fix is always available.

## What it does
Checks ordinary standalone comments for canonical marker spacing, trailing whitespace, and wrapping at `line-length`. A standalone comment is a physical comment line that is not trailing code on the same line.

Canonical ordinary output uses one syntactic `#`, one following space for non-empty content, and normalized content without surrounding whitespace. Additional hashes are content and are retained, so `##Heading` becomes `# #Heading` unless heading preservation protects that line. Empty comments and hash-only comments are boundaries and remain unchanged. Long words and hyphenated words are never split.

PCF001 operates on physical runs of consecutive, same-indent, regular, non-empty standalone comments. Empty comments, hash-only separators, protected comments, blank lines, code lines, and indentation changes end a run. By default, each ordinary physical prose line is normalized and wrapped independently; consecutive ordinary lines are joined into paragraphs only when `comment-join-standalone-lines` is enabled.

Within a run, PCF001 first identifies enabled preserved structures, then applies enabled code detectors to the remaining semantic text, and finally formats the remaining list items, block quotes, paragraphs, or physical lines. Lines inside an explicitly preserved structure are excluded from code detection, so code in a fenced or directive region does not prevent adjacent prose from formatting. If any code detector matches another non-preserved line or multiline candidate, the entire physical standalone run remains unchanged.

When `comment-format-task-markers` is enabled, recognized task markers such as `TODO:`, `FIXME:`, and `HACK:` are formatted as independent units with hanging continuation indentation. Existing continuation lines are reflowed with the marker line only when they have the same base indentation and exactly enough spaces after the comment marker to align with the task-marker payload. Code-like task-marker payloads are normalized but not wrapped according to the enabled code-detection settings.

When indentation leaves no positive wrapping width, PCF001 still canonicalizes spacing but keeps the content on one line. It preserves the source's final-newline state and untouched mixed line endings. When `url-aware-wrapping` is enabled, URL tokens remain unbroken but surrounding prose may use less greedy line breaks.

## Why is this useful?
The conservative ordinary-prose default corrects clear spacing and line-length issues without merging separately authored lines. The structure and protection settings let projects reflow common comment prose while keeping doctests, code fences, tables, directives, headings, disabled code, and tool directives stable.

## Ruff compatibility
Ruff can report overlong comment lines and general whitespace issues, but does not provide equivalent configurable standalone-comment reflow. PCF001 complements those checks and should not be used to rewrite Ruff, type-checker, formatter, or security directives, which the PCF category protects.

## Examples
The canonical case normalizes marker spacing and wraps an ordinary standalone comment:

```pydocfmt-example
[settings]
line-length = 40

[input]
#bad spacing
# This standalone comment has enough words to wrap neatly around the configured limit.

[output]
# bad spacing
# This standalone comment has enough
# words to wrap neatly around the
# configured limit.
```

Ordinary physical prose lines are wrapped independently by default rather than joined with the next line:

```pydocfmt-example
[settings]
line-length = 40

[input]
# First physical line with enough words to require wrapping by itself.
# Second physical line stays separate.

[output]
# First physical line with enough words
# to require wrapping by itself.
# Second physical line stays separate.
```

When standalone-line joining is enabled, consecutive ordinary prose lines in one run become one paragraph before wrapping:

```pydocfmt-example
[settings]
line-length = 35
comment-join-standalone-lines = true

[input]
# First prose line.
# Second prose line with more words.

[output]
# First prose line. Second prose
# line with more words.
```

List-item and block-quote formatting retain structural prefixes and align wrapped lines:

```pydocfmt-example
[settings]
line-length = 34

[input]
# - A list item with enough words to wrap using hanging indentation.
#   Its continuation is joined to the same item.
# > A quoted paragraph with enough words
# > to wrap while retaining its prefix.

[output]
# - A list item with enough words
#   to wrap using hanging
#   indentation. Its continuation
#   is joined to the same item.
# > A quoted paragraph with enough
# > words to wrap while retaining
# > its prefix.
```

Task-marker comments use marker-width hanging indentation so continuation lines remain visually associated with the marker:

```pydocfmt-example
[settings]
line-length = 30
comment-detect-statements = false

[input]
#TODO: alpha beta gamma delta epsilon zeta eta theta

[output]
# TODO: alpha beta gamma delta
#       epsilon zeta eta theta
```

Preserved regions stay unchanged while adjacent prose still formats:

````pydocfmt-example
[settings]
line-length = 40

[input]
# Prose before a fence with enough words that it must wrap onto another line.
# ```python
#     value = compute()
# ```

[output]
# Prose before a fence with enough words
# that it must wrap onto another line.
# ```python
#     value = compute()
# ```
````

Enabled statement detection protects the whole consecutive standalone run, including prose in that run:

```pydocfmt-example
[settings]
line-length = 30

[input]
# value = compute()
# prose that would otherwise wrap onto another line

[output=unchanged]
```

Standalone-line joining does not cross code, blank lines, protected comments, hash-only separators, or indentation boundaries:

```pydocfmt-example
[settings]
line-length = 80
comment-join-standalone-lines = true

[input]
# first line
value = 1
# second line

# third line
# noqa
# fourth line
###
# fifth line
if value:
    # sixth line
    pass
# seventh line

[output=unchanged]
```

## Options
Wrapping settings:

- `line-length`: Maximum display width used when wrapping generated comment lines.
- `line-ending`: Line ending used for generated comment lines.
- `indent-width`: Tab display width used for wrapping calculations.
- `url-aware-wrapping` defaults to `true`. When enabled, URL tokens remain unbroken while surrounding prose may be balanced across lines.

Structure settings:

- `comment-join-standalone-lines` defaults to `false`. When enabled, adjacent ordinary prose lines are joined with one space. Preserved structures, list items, and block quotes remain formatting boundaries.
- `comment-format-list-items` defaults to `true`. It recognizes `-`, `+`, `*`, `1.`, and `1)` markers, including marker indentation and more-indented continuation lines. Each item is reflowed independently with hanging indentation.
- `comment-format-task-markers` defaults to `true`. It recognizes uppercase `TODO`, `FIXME`, `XXX`, `HACK`, `BUG`, `DEBUG`, `NOTE`, `OPTIMIZE`, and `REVIEW` markers followed by `:` and reflows their payloads with hanging indentation.
- `comment-preserve-headings` defaults to `true`. It preserves ATX headings and paired Setext/reStructuredText adornment headings unchanged.
- `comment-preserve-doctests` defaults to `true`. It preserves from the first line whose semantic text starts with `>>>` through the end of the physical run. An empty comment separator ends the run.
- `comment-preserve-code-fences` defaults to `true`. It preserves regions opened by at least three backticks or tildes through a matching fence containing no trailing text. An unclosed fence protects the remainder of the run.
- `comment-format-block-quotes` defaults to `true`. It joins and wraps consecutive quote lines with the same one-or-more-`>` prefix while retaining that prefix on every output line.
- `comment-preserve-tables` defaults to `true`. It requires structural delimiter rows. It recognizes Markdown pipe-table delimiter rows, reStructuredText grid borders, and reStructuredText simple-table borders rather than treating every pipe as a table.
- `comment-preserve-directives` defaults to `true`. It recognizes `.. name::`, preserves that line, and preserves following lines whose content is more indented. Formatting resumes at the next same-level ordinary line.

Code-detection settings:

- `comment-detect-code` defaults to `false`. When enabled, a run is protected when raw content starts with at least four spaces or semantic text starts with `if`, `for`, `while`, `def`, `class`, `try`, `except`, `print`, or `return`.
- `comment-detect-statements` defaults to `true`. It parses individual lines and a dedented multiline candidate. It protects successful parses containing assignments, imports, control-flow statements, definitions, or other non-expression statements.
- `comment-detect-expressions` defaults to `false`. It protects calls, attribute or subscript access, operators, comparisons, comprehensions, container displays, lambdas, and similar nontrivial expressions. Bare names and scalar constants are deliberately excluded.

When list or block-quote formatting is enabled, those structural prefixes are removed before keyword or AST code detection. All positive code detections protect the whole physical run.
