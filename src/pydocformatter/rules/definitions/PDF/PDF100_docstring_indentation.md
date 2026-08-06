# docstring-indentation (PDF100)

Fix is always available.

## What it does
Checks for indentation inside safely rewritable multi-line simple docstrings.

PDF100 leaves the first evaluated docstring line unchanged, so whitespace immediately after the opening quotes is handled by PDF104. For every later evaluated line, PDF100 first determines the docstring's canonical margin:

- For block-suite docstrings, the canonical margin is the raw spaces and tabs before the docstring's opening quotes after any indentation form feed. Python treats a form feed in leading indentation as a column reset; pydocformatter preserves it outside the literal but never copies it into generated docstring content.
- If the opening quotes are wrapped in harmless expression syntax and appear after only whitespace on their source line, the canonical margin is the literal's visual column.
- If the docstring follows another small statement on the same source line, such as `value = 1; ("""...`, generated continuation lines use space indentation to the opening quote column as a hanging margin.
- If harmless expression syntax appears before the opening quotes without an earlier small statement on the same line, such as a standalone `("""...`, the canonical margin is the surrounding statement indentation.
- For single-line-suite docstrings, such as `def f(): """...`, the canonical margin is the line indentation plus one configured indent unit.
- For module docstrings at column zero, the canonical margin is empty.

Outside recognized Google or NumPy convention sections, PDF100 removes the minimum shared visual indentation from non-blank continuation lines and prefixes the canonical margin. This means over-indented and under-indented continuation lines are normalized without flattening meaningful relative indentation. Lists, doctests, code fences, literal blocks, directives, tables, block quotes, and other protected or preformatted structures keep their internal shape relative to the surrounding docstring.

When a reStructuredText field, list item, or block quote starts on the first evaluated line, PDF100 treats the canonical margin as an implicit base for its later lines. It rebases that margin while preserving the parser-recognized hanging or quote prefix, including its tab spelling. PDF101 can therefore wrap the structure without competing with PDF100 over its continuation indentation.

PDF100 leaves every spaces/tabs-only evaluated line unchanged, including ordinary blank lines and whitespace before opening or closing quotes. PDF103 solely owns that whitespace and applies the configured blank-line style without competing indentation normalization from PDF100.

With `docstring-convention = "google"`, recognized section headers align to the canonical margin, entry first lines align one configured indent unit under it, and entry continuation lines align two configured indent units under it. With `docstring-convention = "numpy"`, recognized section headers, underline adornments, and entry declaration lines align to the canonical margin, and entry descriptions align one configured indent unit under it.

PDF100 normalizes the absolute indentation of safely rewritable parsed lines. PDF415 separately diagnoses high-confidence relative nesting defects, such as a Google entry aligned with its section header or an immediate Google or NumPy description aligned with its entry. These rules are complementary: PDF415 can identify intended structure that malformed indentation prevented PDF100 from safely treating as a parsed entry or continuation.

The configured `indent-style` and `indent-width` settings affect generated convention entry indentation, single-line-suite canonical margins, and rewritten docstring line indentation. With `indent-style = "space"`, PDF100 expands tabs in rewritten docstring indentation to spaces while preserving visual indentation width. This does not rewrite indentation outside the docstring literal, such as the source indentation before the opening quotes.

The rule skips single-line docstrings, concatenated docstrings, non-docstring string expressions, and simple docstrings whose evaluated lines cannot be mapped unambiguously to physical source lines. Non-raw multi-line docstrings containing backslash escapes are skipped conservatively because an escape sequence may contribute evaluated content at the boundary where indentation would otherwise be rewritten.

## Why is this useful?
Consistent indentation keeps docstrings easy to scan and helps documentation tools parse convention sections predictably.

## Ruff compatibility
This rule is intended to replace Ruff's `D206`, `D207`, `D208`, `D214`, and `D215` when pydocformatter is responsible for normalizing docstring indentation. `D206`-style tab expansion applies only when `indent-style = "space"`; with `indent-style = "tab"`, generated docstring indentation may use tabs. Parenthesized docstrings whose opening quotes are indented on their own line intentionally use the quote column as the canonical margin.

## Examples
Plain continuation lines are aligned to the docstring's canonical margin:

```pydocfmt-example
[input]
def describe():
    """Describe the value.
      First detail.
      Second detail.
    """

[output]
def describe():
    """Describe the value.
    First detail.
    Second detail.
    """
```

Relative indentation inside ordinary continuation content is preserved:

```pydocfmt-example
[input]
def describe():
    """Describe the value.
        - first item
            nested detail
        >>> value
            output
    """

[output]
def describe():
    """Describe the value.
    - first item
        nested detail
    >>> value
        output
    """
```

Parenthesized docstrings whose opening quotes are indented on a separate line use the quote column as their canonical margin:

```pydocfmt-example
[input]
def describe():
    (
        """Describe the value.
          First detail.
          Second detail.
        """
    )

[output]
def describe():
    (
        """Describe the value.
        First detail.
        Second detail.
        """
    )
```

Module docstrings use an empty canonical margin, and simple statement suites use one configured indent unit after the line indentation:

```pydocfmt-example
[settings]
indent-width = 2

[input]
"""Module summary.
    Body.
"""

def describe(): """Describe the value.
Under-indented detail.
  """

[output]
"""Module summary.
Body.
"""

def describe(): """Describe the value.
  Under-indented detail.
  """
```

Google sections use configured entry and continuation indentation:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def describe(value):
    """Describe the value.

      Args:
          value: Input value.
              Continued description.
    """

[output]
def describe(value):
    """Describe the value.

    Args:
        value: Input value.
            Continued description.
    """
```

Google sections can contain entries, non-entry content, protected blocks, and later sections. PDF100 normalizes each part according to its role:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
def describe(value):
    """Describe the value.

      Args:
          value: Input value.

          - allowed choice
              nested detail

          other: Other value.

      Returns:
          str: Result.
    """

[output]
def describe(value):
    """Describe the value.

    Args:
        value: Input value.

        - allowed choice
            nested detail

        other: Other value.

    Returns:
        str: Result.
    """
```

NumPy section headers, adornments, entries, and descriptions use NumPy indentation:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
def describe(value):
    """Describe the value.

      Parameters
      ----------
        value : int
            Input value.
    """

[output]
def describe(value):
    """Describe the value.

    Parameters
    ----------
    value : int
        Input value.
    """
```

NumPy sections align section headers, adornments, and declarations to the canonical margin while keeping descriptions one indent unit deeper:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
def describe(value):
    """Describe the value.

      Parameters
      ----------
        value : int
            Input value.

            - allowed choice
              nested detail

      Returns
      -------
        str
            Result.
    """

[output]
def describe(value):
    """Describe the value.

    Parameters
    ----------
    value : int
        Input value.

    - allowed choice
      nested detail

    Returns
    -------
    str
        Result.
    """
```

Blank continuation lines are left unchanged for PDF103:

```pydocfmt-example
[input]
def describe():
    """Describe the value.

      
  
    Done.
    """

[output=unchanged]
```

Generated convention indentation can use tabs while preserving the source line's existing base indentation:

```pydocfmt-example
[settings]
indent-style = "tab"
indent-width = 2
docstring-convention = "google"

[input]
class Example:
    def method(self, value):
        """Describe the value.

          Args:
              value: Input value.
                  Continued description.
        """

[output]
class Example:
    def method(self, value):
        """Describe the value.

        Args:
        	value: Input value.
        		Continued description.
        """
```

With space indentation configured, tabs in rewritten docstring indentation are expanded to spaces while tabs inside the content are kept:

```pydocfmt-example
[input]
def describe():
    """Describe the value.
	First detail.
		Second detail	with tabbed content.
    """

[output]
def describe():
    """Describe the value.
    First detail.
            Second detail	with tabbed content.
    """
```

With no convention parsing, convention-looking text is ordinary content and only shared-margin normalization applies:

```pydocfmt-example
[settings]
docstring-convention = "none"

[input]
def describe(value):
    """Describe the value.

      Args:
        value: Input value.
    """

[output]
def describe(value):
    """Describe the value.

    Args:
      value: Input value.
    """
```

Concatenated docstrings, single-line docstrings, and non-docstring strings are left unchanged. Safely mapped escapes do not prevent indentation fixes:

```pydocfmt-example
[input]
def single_line():
    """Single-line docstrings are skipped."""

def concatenated():
    ("first line "
     "second line")

def escaped_content():
    """Summary.
      \x41 content.
    """

def not_a_docstring():
    value = 1
    """This string expression is not the first statement.
      It is not rewritten.
    """

[output]
def single_line():
    """Single-line docstrings are skipped."""

def concatenated():
    ("first line "
     "second line")

def escaped_content():
    """Summary.
    \x41 content.
    """

def not_a_docstring():
    value = 1
    """This string expression is not the first statement.
      It is not rewritten.
    """
```

## Options
- `indent-style`: Indentation style used for generated docstring indentation.
- `indent-width`: Indentation width used for generated docstring indentation and indentation measurement.
