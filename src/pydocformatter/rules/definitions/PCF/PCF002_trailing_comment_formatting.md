# trailing-comment-formatting (PCF002)

Fix is always available.

## What it does
Checks each ordinary trailing comment independently. A fitting comment is normalized to exactly two spaces before `#`, one space after `#` for non-empty content, and no trailing whitespace. An empty trailing comment becomes `code  #` without a trailing space.

If the complete canonical code-plus-comment line exceeds `line-length`, PCF002 usually removes whitespace immediately before the comment, moves the comment directly above the physical code line at the code line's indentation, and wraps it as a standalone block. When `comment-syntax-aware-trailing-extraction` is enabled, overlong comments in decorators, compound statement headers, arguments, and parenthesized or continuation contexts remain inline to preserve their physical association. That safety setting only suppresses extraction; PCF002 still canonicalizes trailing-comment spacing in those positions when spacing is not already canonical.

Syntax-aware extraction applies to function, class, loop, conditional, `with`, `try`/`except`/`else`/`finally`, `match`, and `case` headers, plus decorators, arguments, and parenthesized or continuation contexts. It does not protect ordinary trailing comments merely because they appear inside a compound statement body.

When a moved block would directly follow an existing same-indent standalone comment, a blank line keeps the independently authored comments separate. The rule generates the complete canonical block itself and therefore works when PCF001 is disabled.

Protected type comments and tool directives are never changed by PCF002. Use PCF003 to normalize safe spacing around known trailing directives. Standalone paragraph, markup, doctest, and disabled-code settings do not apply to trailing comments.

Widths use tab-expanded columns with `indent-width` as the tab size. If indentation leaves no positive wrapping width, a non-empty overlong comment is still moved above the code but its text remains on one unwrapped line. Long words are not split. Source outside the replacement retains mixed line endings and the file's final-newline state. When `url-aware-wrapping` is enabled, URL tokens remain unbroken but surrounding prose may use less greedy line breaks.

## Why is this useful?
Canonical spacing keeps short trailing comments predictable. Extracting long comments prevents explanatory text from obscuring code and avoids producing a permanently overlong combined line.

## Ruff compatibility
Ruff can report overlong lines and spacing issues, but it does not extract and wrap trailing comments in this way. PCF002 leaves Ruff, type-checker, formatter, and security directives unchanged.

## Examples
The canonical case normalizes fitting trailing comments in place. Additional hashes after the syntactic `#` are preserved as comment content:

```pydocfmt-example
[input]
first = compute()#poor spacing
second = compute() #
third = compute()  ### heading-like content

[output]
first = compute()  # poor spacing
second = compute()  #
third = compute()  # ## heading-like content
```

An overlong trailing comment moves above the code and wraps as a standalone block even when PCF001 is disabled:

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

An overlong indented trailing comment moves to the code line's indentation and wraps using the available width:

```pydocfmt-example
[settings]
line-length = 32

[input]
if enabled:
    value = compute()  # This explanation has enough words to move and wrap.

[output]
if enabled:
    # This explanation has
    # enough words to move and
    # wrap.
    value = compute()
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

Spacing is still normalized in syntax-sensitive positions even when extraction is suppressed:

```pydocfmt-example
[settings]
line-length = 32

[input]
if enabled:# explanation long enough to move above the header
    pass

[output]
if enabled:  # explanation long enough to move above the header
    pass
```

Ordinary body comments are not treated as syntax-sensitive just because they appear under a compound statement:

```pydocfmt-example
[settings]
line-length = 36

[input]
match value:
    case 1:
        result = compute()  # explanation long enough to move above this statement

[output]
match value:
    case 1:
        # explanation long enough to
        # move above this statement
        result = compute()
```

Set `comment-syntax-aware-trailing-extraction` to `false` to restore extraction in those positions:

```pydocfmt-example
[settings]
line-length = 32
comment-syntax-aware-trailing-extraction = false

[input]
if enabled:  # explanation long enough to move above the header
    pass
match value:  # explanation long enough to move above the match header
    case 1:  # explanation long enough to move above the case header
        pass

[output]
# explanation long enough to
# move above the header
if enabled:
    pass
# explanation long enough to
# move above the match header
match value:
    # explanation long enough to
    # move above the case header
    case 1:
        pass
```

When a moved comment would touch an existing same-indent standalone comment, a blank line keeps the independently authored comments separate:

```pydocfmt-example
[settings]
line-length = 34

[input]
# Existing note.
value = compute()  # Extracted explanation has enough words to require moving above code.

[output]
# Existing note.

# Extracted explanation has enough
# words to require moving above
# code.
value = compute()
```

Protected type comments and tool directives remain byte-for-byte unchanged, regardless of line length or spacing:

```pydocfmt-example
[input]
value = compute() # type: ignore
other = compute() # noqa
secret = compute() # nosec

[output=unchanged]
```

Standalone structure and code-detection settings do not apply to trailing comments. Structure-like text is plain-wrapped after moving:

```pydocfmt-example
[settings]
line-length = 30

[input]
value = compute()  # - alpha beta gamma delta epsilon
other = compute()  # > alpha beta gamma delta epsilon

[output]
# - alpha beta gamma delta
# epsilon
value = compute()
# > alpha beta gamma delta
# epsilon
other = compute()
```

## Options
- `line-length`
- `line-ending`
- `indent-width`
- `url-aware-wrapping`
- `comment-syntax-aware-trailing-extraction`
