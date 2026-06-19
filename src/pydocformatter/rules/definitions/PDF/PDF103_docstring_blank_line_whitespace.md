# docstring-blank-line-whitespace (PDF103)

Fix is always available.

## What it does
Checks for whitespace-only blank lines inside safely rewritable docstrings. A blank docstring line is an evaluated docstring line whose content contains only spaces and tabs.

By default, PDF103 makes ordinary blank docstring lines truly blank. With `docstring-blank-line-style = "aligned"`, ordinary blank lines are aligned to the docstring's base/quote indentation. A whitespace-only final line before same-line closing quotes is always aligned so the closing quotes remain at the docstring margin.

PDF103 owns whitespace-only opening quote lines and whitespace-only closing quote lines. PDF104 and PDF105 only handle quote-adjacent whitespace when the same line also contains non-empty docstring content. PDF102 owns trailing spaces and tabs on non-empty docstring lines.

PDF103 only rewrites safely mapped simple docstring literals. It skips concatenated docstrings and simple literals where evaluated lines cannot be mapped back to physical source lines safely, such as docstrings that contain escaped newline sequences.

## Why is this useful?
Whitespace-only blank lines make diffs noisy and hide formatting changes that should be semantically empty.

## Ruff compatibility
This rule overlaps with Ruff's general blank-line whitespace checks, such as `W293`, but is scoped to safely rewritable docstring content handled by pydocformatter.

## Examples
By default, ordinary whitespace-only blank lines become truly blank:

```pydocfmt-example
[input]
def area(radius: float) -> float:
    """Return the area.
       
    The radius must be non-negative.
    """

[output]
def area(radius: float) -> float:
    """Return the area.

    The radius must be non-negative.
    """
```

Multiple blank-line forms in one docstring are fixed together. Ordinary blank lines become empty, while a whitespace-only final line before same-line closing quotes is aligned:

```pydocfmt-example
[input]
def describe(value: int) -> str:
    """Return the description.
   
	 
    More detail.
      """

[output]
def describe(value: int) -> str:
    """Return the description.


    More detail.
    """
```

Aligned mode keeps blank lines at the docstring margin:

```pydocfmt-example
[settings]
docstring-blank-line-style = "aligned"

[input]
def area(radius: float) -> float:
    """Return the area.

    The radius must be non-negative.
    """

[output]
def area(radius: float) -> float:
    """Return the area.
    
    The radius must be non-negative.
    """
```

For simple-suite docstrings, aligned blank lines use one configured indent unit beyond the suite indentation:

```pydocfmt-example
[settings]
indent-width = 2
docstring-blank-line-style = "aligned"

[input]
def area(radius: float) -> float: """Return the area.

The radius must be non-negative.
  """

[output]
def area(radius: float) -> float: """Return the area.
  
The radius must be non-negative.
  """
```

Whitespace-only opening quote lines are PDF103 findings, not PDF104 findings:

```pydocfmt-example
[input]
def area(radius: float) -> float:
    """   
    Return the area.
    """

[output]
def area(radius: float) -> float:
    """
    Return the area.
    """
```

Whitespace-only closing quote lines are always aligned, even when the default `blank` style is used:

```pydocfmt-example
[input]
def area(radius: float) -> float:
    """Return the area.
      """

[output]
def area(radius: float) -> float:
    """Return the area.
    """
```

Non-empty lines with trailing whitespace are left for PDF102 or PDF105:

```pydocfmt-example
[input]
def area(radius: float) -> float:
    """Return the area.  
    The radius must be non-negative.  """

[output=unchanged]
```

Raw prefixes, quote delimiters, and literal backslashes are preserved when the docstring can be safely mapped:

```pydocfmt-example
[input]
def path_hint() -> str:
    r'''Return C:\temp.
      
    '''

[output]
def path_hint() -> str:
    r'''Return C:\temp.

    '''
```

Concatenated docstrings and docstrings with escaped newlines are skipped because the exact source line ownership is ambiguous for this rule:

```pydocfmt-example
[input]
def concatenated() -> None:
    ("Summary.\n"
     "   \n"
     "Body.")

def escaped_newline() -> None:
    """Summary.\n   \nBody."""

[output=unchanged]
```

## Options
- `docstring-blank-line-style`: Controls whether ordinary blank docstring lines are made truly blank (`blank`) or aligned to the docstring's base/quote indentation (`aligned`).
