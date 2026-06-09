# trailing-comment-formatting (PCF002)

Fix is always available.

## What it does
Checks each ordinary trailing comment independently. A fitting comment is normalized to exactly two spaces before `#`, one space after `#` for non-empty content, and no trailing whitespace. An empty trailing comment becomes `code  #` without a trailing space.

If the complete canonical code-plus-comment line exceeds `line-length`, PCF002 removes whitespace immediately before the comment, moves the comment directly above the physical code line at the code line's indentation, and wraps it as a standalone block. When that block would directly follow an existing same-indent standalone comment, a blank line keeps the independently authored comments separate. The rule generates the complete canonical block itself and therefore works when PCF001 is disabled.

Protected type comments and tool directives are never changed. Standalone paragraph, markup, doctest, and disabled-code settings do not apply to trailing comments.

Widths use tab-expanded columns with `indent-width` as the tab size. If indentation leaves no positive wrapping width, a non-empty overlong comment is still moved above the code but its text remains on one unwrapped line. Long words are not split. Source outside the replacement retains mixed line endings and the file's final-newline state.

## Why is this useful?
Canonical spacing keeps short trailing comments predictable. Extracting long comments prevents explanatory text from obscuring code and avoids producing a permanently overlong combined line.

## Ruff compatibility
Ruff can report overlong lines and spacing issues, but it does not extract and wrap trailing comments in this way. PCF002 leaves Ruff, type-checker, formatter, and security directives unchanged.

## Example
Fitting trailing comments receive canonical spacing and lose trailing whitespace, while empty comments remain inline:

```python
first = compute()#poor spacing
second = compute() #
```

Applying this rule produces:

```python
first = compute()  # poor spacing
second = compute()  #
```

The complete canonical code-plus-comment line determines whether a comment fits. Even a short comment moves when the code makes the combined line too long:

```python
very_long_variable_name = compute_expensive_value()  # why
```

Applying this rule produces:
```python
# why
very_long_variable_name = compute_expensive_value()
```

An overlong comment moves to the code line's indentation and wraps using the available width:

```python
if enabled:
    value = compute()  # This explanation has enough words to move and wrap.
```

Applying this rule produces:

```python
if enabled:
    # This explanation has enough words
    # to move and wrap.
    value = compute()
```

When a moved comment would touch an existing same-indent standalone comment, a blank line keeps the independently authored comments separate:

```python
# Existing note.
value = compute()  # This extracted explanation is too long to remain inline.
```

Applying this rule produces:

```python
# Existing note.

# This extracted explanation is too long to
# remain inline.
value = compute()
```

Protected type comments and tool directives remain byte-for-byte unchanged, regardless of line length or spacing:

```python
value = compute() # type: ignore
other = compute() # noqa
secret = compute() # nosec
```

Standalone structure and code-detection settings do not apply to trailing comments. Structure-like text is plain-wrapped after moving:

```python
value = compute()  # - This trailing text is too long to remain inline.
```

Applying this rule produces:

```python
# - This trailing text is too long to
# remain inline.
value = compute()
```

## Options
- `line-length`
- `line-ending`
- `indent-width`
