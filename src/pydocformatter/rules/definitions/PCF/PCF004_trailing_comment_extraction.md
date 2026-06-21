# trailing-comment-extraction (PCF004)

Fix is always available.

## What it does
Checks overlong ordinary trailing comments after canonical spacing. When the complete canonical code-plus-comment line exceeds `line-length`, PCF004 can remove whitespace immediately before the comment, move the comment directly above the physical code line at the code line's indentation, and wrap it as a standalone block.

When `comment-trailing-extraction-syntax-aware` is enabled, overlong comments in decorators, compound statement headers, arguments, and parenthesized or continuation contexts remain inline to preserve their physical association. Syntax-aware extraction applies to function, class, loop, conditional, `with`, `try`/`except`/`else`/`finally`, `match`, and `case` headers, plus decorators, arguments, and parenthesized or continuation contexts. It does not protect ordinary trailing comments merely because they appear inside a compound statement body.

When `comment-trailing-extraction-content-aware` is enabled, overlong comments remain inline if their content would be unsafe to reinterpret as standalone comment text. The unsafe-content check respects the existing standalone comment settings: list-like text is unsafe when `comment-format-list-items` is enabled, table-like text is unsafe when `comment-preserve-tables` is enabled, and the same pattern applies to enabled headings, doctests, code fences, block quotes, directives, and code-detection settings. Disabling one detector only removes that detector from the safety check; if the same text also matches another enabled detector, it still remains inline. Within this content-aware check, leading symbolic operator-like tokens such as `-`, `*`, `>`, `|`, `+`, comparison operators, and arrows are always unsafe, even when a matching structure setting is disabled. Ordinary prose that starts with words such as `and`, `or`, or `not` can still extract.

When a moved block would directly follow an existing same-indent standalone comment, a blank line keeps the independently authored comments separate. The rule generates the complete canonical block itself and therefore works when PCF001 is disabled.

Widths use tab-expanded columns with `indent-width` as the tab size. If indentation leaves no positive wrapping width, a non-empty overlong comment is still moved above the code but its text remains on one unwrapped line. Long words are not split. Source outside the replacement retains mixed line endings and the file's final-newline state. When `url-aware-wrapping` is enabled, URL tokens remain unbroken but surrounding prose may use less greedy line breaks.

## Why is this useful?
Extracting ordinary long comments prevents explanatory text from obscuring code, while rule selection and safety settings let projects keep harmless spacing normalization without enabling comment movement.

## Ruff compatibility
Ruff can report overlong lines and spacing issues, but it does not extract and wrap trailing comments in this way. PCF004 leaves Ruff, type-checker, formatter, and security directives unchanged.

## Examples
An overlong trailing comment moves above the code and wraps as a standalone block:

```pydocfmt-example
[settings]
line-length = 42

[input]
value = compute()  # This trailing comment has enough words that it must move above the code line.

[output]
# This trailing comment has enough words
# that it must move above the code line.
value = compute()
```

The complete canonical code-plus-comment line determines whether a comment fits. Even a short comment moves when the code makes the combined line too long:

```pydocfmt-example
[settings]
line-length = 40

[input]
very_long_variable_name = compute_expensive_value()  # why

[output]
# why
very_long_variable_name = compute_expensive_value()
```

Syntax-aware extraction keeps overlong comments inline where moving them would weaken their association with nearby syntax:

```pydocfmt-example
[settings]
line-length = 32

[input]
if enabled:  # explanation long enough to move above the header
    pass
@decorator  # explanation long enough to move above the decorator
def function(
    value,  # explanation long enough to move above the argument
):
    pass

[output=unchanged]
```

When extraction is suppressed, PCF004 leaves the original inline spacing unchanged. PCF002 owns trailing code-to-`#` delimiter spacing, and PCF003 owns directive normalization for recognized directives that remain inline:

```pydocfmt-example
[settings]
line-length = 32

[input]
if enabled:# explanation long enough to move above the header
    pass

[output=unchanged]
```

Content-aware extraction keeps standalone-like and operator-like text inline by default:

```pydocfmt-example
[settings]
line-length = 30

[input]
value = compute()  # - alpha beta gamma delta epsilon
other = compute()  # >>> alpha beta gamma delta epsilon

[output=unchanged]
```

Disabling the relevant standalone structure setting allows that structure-like content to extract, unless it is still operator-like or matches another enabled detector:

```pydocfmt-example
[settings]
line-length = 30
comment-preserve-doctests = false
comment-format-list-items = false
comment-format-block-quotes = false

[input]
value = compute()  # - alpha beta gamma delta epsilon
other = compute()  # >>> alpha beta gamma delta epsilon

[output]
value = compute()  # - alpha beta gamma delta epsilon
# >>> alpha beta gamma delta
# epsilon
other = compute()
```

Standalone settings affect the content-safety check directly. Here table preservation is disabled, so the table-like trailing comment can move; list formatting is also disabled, but the `-` marker still stays inline because it is operator-like:

```pydocfmt-example
[settings]
line-length = 24
comment-preserve-tables = false
comment-format-list-items = false

[input]
table = compute()  # :--- | ---:
bullet = compute()  # - alpha beta gamma delta epsilon

[output]
# :--- | ---:
table = compute()
bullet = compute()  # - alpha beta gamma delta epsilon
```

Set both extraction safety settings to `false` to restore aggressive extraction:

```pydocfmt-example
[settings]
line-length = 32
comment-trailing-extraction-syntax-aware = false
comment-trailing-extraction-content-aware = false

[input]
if enabled:  # explanation long enough to move above the header
    pass
value = compute()  # - alpha beta gamma delta epsilon

[output]
# explanation long enough to
# move above the header
if enabled:
    pass
# - alpha beta gamma delta
# epsilon
value = compute()
```

## Options
Wrapping and line-generation settings:

- `line-length`: Maximum display width for deciding whether the canonical code-plus-comment line is overlong and for wrapping the extracted standalone block.
- `line-ending`: Line ending used between generated lines inside the extracted replacement block.
- `indent-width`: Tab display width used when measuring the original inline line and the available standalone comment width.
- `url-aware-wrapping`: When enabled, URL tokens remain unbroken while surrounding prose may be balanced across lines.

Extraction safety settings:

- `comment-trailing-extraction-syntax-aware`: When enabled, keep overlong trailing comments inline in decorators, compound statement headers, arguments, and continuation contexts.
- `comment-trailing-extraction-content-aware`: When enabled, keep overlong trailing comments inline when their content matches an enabled standalone structure/code detector or the content-aware operator-like heuristic.

Content-safety detector settings:

- `comment-format-list-items`: When enabled, list-like trailing content is unsafe to extract; leading `-`, `*`, and related operator-like tokens remain unsafe even when list formatting is disabled.
- `comment-preserve-headings`: When enabled, ATX headings and heading-adornment lines are unsafe to extract. Text that also looks like a table remains unsafe while table preservation is enabled.
- `comment-preserve-doctests`: When enabled, trailing content starting with `>>>` is unsafe to extract.
- `comment-preserve-code-fences`: When enabled, trailing content starting with a Markdown code fence is unsafe to extract.
- `comment-format-block-quotes`: When enabled, block-quote-like trailing content is unsafe to extract; leading `>` is also operator-like and remains unsafe when block-quote formatting is disabled.
- `comment-preserve-tables`: When enabled, Markdown pipe-table delimiter rows and reStructuredText grid or simple-table border rows are unsafe to extract.
- `comment-preserve-directives`: When enabled, reStructuredText directive-like trailing content is unsafe to extract.
- `comment-detect-code`: When enabled, disabled-code-like trailing content is unsafe to extract.
- `comment-detect-statements`: When enabled, trailing content that parses as a Python statement is unsafe to extract.
- `comment-detect-expressions`: When enabled, trailing content that parses as a nontrivial Python expression is unsafe to extract.
