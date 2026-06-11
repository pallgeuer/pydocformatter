# incorrect-indentation (PDF002)

Fix is always available.

## What it does
Checks for indentation inside safely rewritable multi-line simple docstrings.

PDF002 leaves the first evaluated docstring line unchanged, so whitespace immediately after the opening quotes is handled by PDF005. For every later evaluated line, PDF002 first determines the docstring's canonical margin:

- For block-suite docstrings, the canonical margin is the raw indentation before the docstring's opening quotes.
- If the opening quotes are wrapped in harmless expression syntax and appear after only whitespace on their source line, the canonical margin is the literal's visual column.
- If harmless expression syntax appears before the opening quotes on the same source line, such as `("""...`, the canonical margin is the surrounding statement indentation.
- For single-line-suite docstrings, such as `def f(): """...`, the canonical margin is the line indentation plus one configured indent unit.
- For module docstrings at column zero, the canonical margin is empty.

Outside recognized Google or NumPy convention sections, PDF002 removes the minimum shared visual indentation from non-blank continuation lines and prefixes the canonical margin. This means over-indented and under-indented continuation lines are normalized without flattening meaningful relative indentation. Lists, doctests, code fences, literal blocks, directives, tables, block quotes, and other protected or preformatted structures keep their internal shape relative to the surrounding docstring.

Blank continuation lines may be empty or exactly the canonical margin. Empty and canonical blank lines are kept. Blank lines that start with the canonical margin plus extra whitespace are reduced to the canonical margin, and other whitespace-only blank lines become empty. PDF004 may still enforce a stricter blank-line whitespace preference later.

With `docstring-convention = "google"`, recognized section headers align to the canonical margin, entry first lines align one configured indent unit under it, and entry continuation lines align two configured indent units under it. With `docstring-convention = "numpy"`, recognized section headers, underline adornments, and entry declaration lines align to the canonical margin, and entry descriptions align one configured indent unit under it.

The configured `indent-style` and `indent-width` settings affect generated convention entry indentation and single-line-suite canonical margins. They do not replace the raw base indentation already used by the surrounding source line.

The rule skips single-line docstrings, concatenated docstrings, non-docstring string expressions, and simple docstrings whose evaluated lines cannot be mapped unambiguously to physical source lines. Non-raw multi-line docstrings containing backslash escapes are skipped conservatively because an escape sequence may contribute evaluated content at the boundary where indentation would otherwise be rewritten.

## Why is this useful?
Consistent indentation keeps docstrings easy to scan and helps documentation tools parse convention sections predictably.

## Ruff compatibility
This rule is intended to replace Ruff's `D207` and `D208` when pydocformatter is responsible for normalizing docstring indentation. Parenthesized docstrings whose opening quotes are indented on their own line intentionally use the quote column as the canonical margin.

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

Google sections can contain entries, non-entry content, protected blocks, and later sections. PDF002 normalizes each part according to its role:

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

Blank continuation lines are normalized only to PDF002's accepted states:

```pydocfmt-example
[input]
def describe():
    """Describe the value.

      
  
    Done.
    """

[output]
def describe():
    """Describe the value.

    

    Done.
    """
```

Generated convention indentation can use tabs while preserving the source line's existing base indentation:

```pydocfmt-example
[settings]
docstring-convention = "google"
indent-style = "tab"
indent-width = 2

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

Unsafe or irrelevant strings are left unchanged:

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

[output=unchanged]
```

## Options
- `indent-style`: Indentation style used for generated convention indentation units.
- `indent-width`: Indentation width used for generated convention indentation units and single-line-suite docstring margins.
- `docstring-convention`: Enables Google or NumPy section-aware indentation. With `none` or `pep257`, convention-looking text is treated as ordinary continuation content.
