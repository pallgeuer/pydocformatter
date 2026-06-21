# trailing-comment-spacing (PCF002)

Fix is always available.

## What it does
Checks each trailing comment independently. The spacing between code and the opening `#` is normalized to exactly two spaces. Ordinary trailing comments are also normalized to one space after `#` for non-empty content and no trailing whitespace. An empty ordinary trailing comment becomes `code  #` without a trailing space.

PCF002 never moves or wraps comments and does not consult `line-length`. Use PCF004 for overlong trailing-comment extraction. For protected type comments and tool directives, PCF002 only normalizes the spacing before the opening `#`, strips trailing line whitespace, and otherwise preserves the directive text from `#` onward. Use PCF003 to normalize safe marker spacing and syntax from `#` onward for known trailing directives.

Only the text from the start of the physical line through the comment token is replaced. The existing line ending after that physical line, source outside the replacement, mixed line endings, and the file's final-newline state are retained.

## Why is this useful?
Canonical spacing keeps harmless trailing-comment cleanup independently selectable from comment movement.

## Ruff compatibility
Ruff can normalize some spacing around comments, but pydocformatter keeps ordinary trailing-comment spacing separate from directive normalization and extraction so each action can be selected independently.

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

Empty trailing comments canonicalize to `code  #`, and surrounding whitespace is removed without adding a marker-space payload:

```pydocfmt-example
[input]
value = compute() #
other = compute()#

[output]
value = compute()  #
other = compute()  #
```

PCF002 only normalizes spacing, even when the resulting line is overlong and PCF004 would be needed to move it:

```pydocfmt-example
[settings]
line-length = 42

[input]
value = compute()#This trailing comment has enough words that extraction would move it.

[output]
value = compute()  # This trailing comment has enough words that extraction would move it.
```

Protected type comments and tool directives only have the code-to-`#` delimiter normalized. Directive text from `#` onward is preserved:

```pydocfmt-example
[input]
value = compute() # type: ignore
other = compute()#noqa
secret = compute() #   nosec reason

[output]
value = compute()  # type: ignore
other = compute()  #noqa
secret = compute()  #   nosec reason
```

## Options
None.
