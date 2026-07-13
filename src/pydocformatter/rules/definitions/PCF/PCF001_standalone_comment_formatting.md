# standalone-comment-formatting (PCF001)

Fix is always available.

## What it does
Checks ordinary standalone comments for canonical marker spacing, trailing whitespace, and wrapping at `line-length`. A standalone comment is a physical comment line that is not trailing code on the same line.

Canonical ordinary output uses one syntactic `#`, one following space for non-empty content, and normalized content without surrounding whitespace. Additional hashes are content and are retained, so `##Heading` becomes `# #Heading` unless heading preservation protects that line. Empty comments and hash-only comments are boundaries and remain unchanged. Long words and hyphenated words are never split.

PCF001 operates on physical runs of consecutive, same-indent, regular, non-empty standalone comments. Empty comments, hash-only separators, protected comments, blank lines, code lines, and indentation changes end a run. By default, each ordinary physical prose line is normalized and wrapped independently; consecutive ordinary lines are joined into paragraphs only when `comment-join-standalone-lines` is enabled. Joined paragraphs do not cross standalone colon-ended label lines, while lowercase colon-ended lines can complete unfinished preceding prose.

Within a run, PCF001 first identifies enabled preserved structures, then applies enabled code detectors to the remaining semantic text, and finally formats the remaining list items, block quotes, paragraphs, or physical lines. Lines inside an explicitly preserved structure are excluded from code detection, so code in a fenced or directive region does not prevent adjacent prose from formatting. If any code detector matches another non-preserved line or multiline candidate, the entire physical standalone run remains unchanged.

When `comment-task-marker-mode` is `no-wrap`, recognized task markers such as `TODO:`, `FIXME:`, and `HACK:` are formatted as independent units but are not wrapped. When it is `hanging`, recognized task-marker units use hanging continuation indentation. Existing continuation lines belong to the same unit only when they have the same base indentation and exactly enough spaces after the comment marker to align with the task-marker payload. Code-like task-marker payloads in `hanging` mode are normalized but not wrapped according to the enabled code-detection settings. Set `comment-task-marker-mode` to `none` for no task-marker-specific handling.

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

Colon-ended label lines stop standalone-line joining before adjacent prose:

```pydocfmt-example
[settings]
line-length = 80
comment-join-standalone-lines = true

[input]
# Summary.
# Accepted values:
# pending, active, disabled.

[output=unchanged]
```

A lowercase colon-ended line can still complete unfinished preceding prose, but following prose starts a separate unit:

```pydocfmt-example
[settings]
line-length = 80
comment-join-standalone-lines = true

[input]
# This sentence has been split
# with a colon:
# following prose continues here.

[output]
# This sentence has been split with a colon:
# following prose continues here.
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

Task-marker comments use `no-wrap` mode by default. The marker spacing is normalized, but the payload is not wrapped even when it exceeds `line-length`:

```pydocfmt-example
[settings]
line-length = 30

[input]
#TODO: alpha beta gamma delta epsilon zeta eta theta

[output]
# TODO: alpha beta gamma delta epsilon zeta eta theta
```

Set `comment-task-marker-mode` to `hanging` to reflow task-marker payloads with marker-width hanging indentation so continuation lines remain visually associated with the marker:

```pydocfmt-example
[settings]
line-length = 30
comment-task-marker-mode = "hanging"

[input]
#TODO: alpha beta gamma delta epsilon zeta eta theta

[output]
# TODO: alpha beta gamma delta
#       epsilon zeta eta theta
```

Set `comment-task-marker-mode` to `none` to treat task markers as ordinary comment text, so wrapping uses ordinary continuation indentation:

```pydocfmt-example
[settings]
line-length = 30
comment-task-marker-mode = "none"

[input]
#TODO: alpha beta gamma delta epsilon zeta eta theta

[output]
# TODO: alpha beta gamma delta
# epsilon zeta eta theta
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
- `line-length`: Maximum display width used when wrapping generated standalone comment lines.
- `indent-width`: Tab display width used for wrapping and structure-prefix calculations.
- `url-aware-wrapping`: Keeps URL tokens unbroken while balancing surrounding prose when wrapping.
- `comment-join-standalone-lines`: Joins adjacent ordinary prose comments into paragraphs before wrapping.
- `comment-format-list-items`: Detects ordered and unordered list items and reflows them with hanging indentation.
- `comment-format-block-quotes`: Detects Markdown block quotes and reflows text while retaining quote prefixes.
- `comment-task-marker-mode`: Controls whether recognized task markers are ordinary text, normalized without wrapping, or wrapped with hanging indentation.
- `comment-task-markers`: Defines the uppercase task marker labels recognized before `:`.
- `comment-preserve-headings`: Preserves detected Markdown and reStructuredText heading comments unchanged.
- `comment-preserve-doctests`: Preserves standalone doctest comment regions unchanged.
- `comment-preserve-code-fences`: Preserves fenced code regions in standalone comments unchanged.
- `comment-preserve-tables`: Preserves detected Markdown and reStructuredText tables unchanged.
- `comment-preserve-directives`: Preserves reStructuredText directives and their indented bodies unchanged.
- `comment-detect-code`: Protects whole standalone runs when the indentation or leading-keyword heuristic detects disabled code.
- `comment-detect-statements`: Protects whole standalone runs when comment text parses as Python containing a non-expression statement.
- `comment-detect-expressions`: Protects whole standalone runs when comment text parses as a nontrivial Python expression.
