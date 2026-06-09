# standalone-comment-formatting (PCF001)

Fix is always available.

## What it does
Checks ordinary standalone comments for canonical marker spacing, trailing whitespace, and wrapping at `line-length`. By default, each physical comment line is normalized and wrapped independently. Consecutive lines are not joined unless `comment-join-standalone-lines` is enabled.

Canonical ordinary output uses one syntactic `#`, one following space, and normalized content. Additional hashes are content and are retained, so `##Heading` becomes `# #Heading` unless heading preservation is enabled. Empty and hash-only comments are boundaries and remain unchanged. Long words and hyphenated words are never split.

PCF001 first identifies enabled preserved structures, then applies enabled code detectors to the remaining semantic text, and finally formats the remaining list items, block quotes, paragraphs, or physical lines. Lines inside an explicitly preserved structure are excluded from code detection, so code in a fenced or directive region does not prevent adjacent prose from formatting. If any code detector matches another line or multiline candidate, the entire physical standalone run remains unchanged.

When indentation leaves no positive wrapping width, PCF001 still canonicalizes spacing but keeps the content on one line. It does not raise the invalid-width error possible in the legacy formatter. It also preserves the source's final-newline state and untouched mixed line endings.

## Why is this useful?
The conservative default corrects clear spacing and line-length issues without merging separately authored lines. Projects can opt into progressively richer prose and markup handling without making those heuristics mandatory for all users.

## Ruff compatibility
Ruff can report overlong comment lines and general whitespace issues, but does not provide equivalent configurable standalone-comment reflow. PCF001 complements those checks and should not be used to rewrite Ruff, type-checker, formatter, or security directives, which the PCF category protects.

## Example
Marker spacing is normalized, trailing whitespace is removed, and additional hashes remain comment content:

```python
# This standalone comment is long enough that it should be wrapped to keep the source readable at the configured line length.

## Heading
    #    An indented comment with excessive spacing.
```

Applying this rule produces:

```python
# This standalone comment is long enough that it should be wrapped to keep the
# source readable at the configured line length.

## Heading
    # An indented comment with excessive spacing.
```

By default, each physical comment line is wrapped independently rather than joined with the next line:

```python
# This first physical comment line has enough words that it needs to wrap by itself.
# This second physical line remains a separate line.
```

Applying this rule produces:
```python
# This first physical comment line has enough words that
# it needs to wrap by itself.
# This second physical line remains a separate line.
```

With `comment-join-standalone-lines = true`:
```python
# These two physical lines are treated as one prose
# paragraph before wrapping.
```

With `comment-format-list-items = true` and `comment-format-block-quotes = true`, structural prefixes are retained while their text is joined and wrapped:

```python
# - A long list item with a continuation that needs
#   reflowing onto appropriately aligned output lines.
# > A quoted paragraph with enough words
# > to wrap while retaining its prefix.
```

Applying this rule with these settings produces:

```python
# - A long list item with a continuation that needs reflowing
#   onto appropriately aligned output lines.
# > A quoted paragraph with enough words to wrap while
# > retaining its prefix.
```

Enabled preservation settings leave recognized markup regions unchanged while adjacent prose can still be formatted:

```python
# This prose before the fence has enough words that it needs to wrap onto another line.
# ```python
# value = compute()
# ```
```

Applying this rule with `comment-preserve-code-fences = true` produces:

```python
# This prose before the fence has enough words that it
# needs to wrap onto another line.
# ```python
# value = compute()
# ```
```

Enabled code detection protects the whole consecutive standalone run, including prose in that run:

```python
# value = compute()
# This prose is deliberately left unchanged even when it exceeds line-length.
```

The run remains unchanged with `comment-detect-statements = true`. Empty comments, hash-only separators, protected comments, code, blank lines, and indentation changes form boundaries, so joining never crosses them:

```python
# First paragraph line.
# Second paragraph line.
#
# A separate paragraph after a hash-only boundary.
value = compute()
# Another separate paragraph after code.
# noqa
# Another separate paragraph after a protected directive.
```

## Structure settings
- `comment-join-standalone-lines`: Joins adjacent ordinary lines with one space. Preserved structures, list items, and block quotes remain formatting boundaries.
- `comment-format-list-items`: Recognizes `-`, `+`, `*`, `1.`, and `1)` markers, including marker indentation and more-indented continuation lines. Each item is reflowed independently with hanging indentation.
- `comment-preserve-headings`: Preserves ATX headings and paired Setext/reStructuredText adornment headings unchanged.
- `comment-preserve-doctests`: Preserves from the first line whose semantic text starts with `>>>` through the end of the physical run. An empty comment separator ends the run.
- `comment-preserve-code-fences`: Preserves regions opened by at least three backticks or tildes through a matching fence containing no trailing text. An unclosed fence protects the remainder of the run.
- `comment-format-block-quotes`: Joins and wraps consecutive quote lines with the same one-or-more-`>` prefix while retaining that prefix on every output line.
- `comment-preserve-tables`: Requires structural delimiter rows. It recognizes Markdown pipe-table delimiter rows, reStructuredText grid borders, and reStructuredText simple-table borders rather than treating every pipe as a table.
- `comment-preserve-directives`: Recognizes `.. name::`, preserves that line, and preserves following lines whose content is more indented. Formatting resumes at the next same-level ordinary line.

## Code-detection settings
- `comment-detect-code` defaults to `false`. When enabled, a run is protected when raw content starts with at least four spaces or semantic text starts with `if`, `for`, `while`, `def`, `class`, `try`, `except`, `print`, or `return`.
- `comment-detect-statements` parses individual lines and a dedented multiline candidate. It protects successful parses containing assignments, imports, control-flow statements, definitions, or other non-expression statements.
- `comment-detect-expressions` protects calls, attribute or subscript access, operators, comparisons, comprehensions, container displays, lambdas, and similar nontrivial expressions. Bare names and scalar constants are deliberately excluded.

When list or block-quote formatting is enabled, those structural prefixes are removed before keyword or AST code detection. All positive code detections protect the whole physical run.

## Options
- `line-length`
- `line-ending`
- `indent-width`
- `comment-join-standalone-lines`
- `comment-format-list-items`
- `comment-preserve-headings`
- `comment-preserve-doctests`
- `comment-preserve-code-fences`
- `comment-format-block-quotes`
- `comment-preserve-tables`
- `comment-preserve-directives`
- `comment-detect-code`
- `comment-detect-statements`
- `comment-detect-expressions`
