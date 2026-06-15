# docstring-trailing-whitespace (PDF102)

Fix is always available.

## What it does
Checks for spaces and tabs at the end of non-empty docstring lines when the line is followed by an evaluated newline. The fix removes only that trailing whitespace; it leaves the text content, quote style, string prefix, indentation, and line endings otherwise unchanged.

PDF102 only rewrites safely mapped simple docstring literals. It skips concatenated docstrings and simple literals where evaluated lines cannot be mapped back to physical source lines safely, such as docstrings that contain escaped newline sequences.

PDF102 does not change whitespace-only docstring lines; PDF103 owns those. It also does not remove spaces or tabs immediately before closing quotes on the final evaluated line when that line has non-empty content; PDF105 owns that quote-adjacent case. When a final non-empty line is followed by an evaluated newline before the closing quotes, PDF102 does remove trailing whitespace from that line.

## Why is this useful?
Trailing whitespace creates noisy diffs and can make otherwise identical docstrings compare differently.

## Ruff compatibility
This rule overlaps with Ruff's general trailing-whitespace checks, such as `W291`, but is scoped to safely rewritable docstring content handled by pydocformatter.

## Example
Trailing whitespace on non-empty docstring lines is removed:

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

Whitespace-only blank lines are not PDF102 findings, even when the same docstring has non-empty lines that PDF102 fixes:

```pydocfmt-example
[input]
def describe(value: int) -> str:
    """Return the description.  
      
    Keep the blank separator.	
    """

[output]
def describe(value: int) -> str:
    """Return the description.
      
    Keep the blank separator.
    """
```

Whitespace before closing quotes on the final non-empty content line is left for PDF105:

```pydocfmt-example
[input]
def area(radius: float) -> float:
    """Return the area.  """

[output=unchanged]
```

Trailing whitespace on the final non-empty line is fixed when that line is followed by an evaluated newline before the closing quotes:

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

Raw prefixes, quote delimiters, and literal backslashes are preserved when the docstring can be safely mapped:

```pydocfmt-example
[input]
def path_hint() -> str:
    r'''Return C:\temp.  
    Keep \n literal text.	
    '''

[output]
def path_hint() -> str:
    r'''Return C:\temp.
    Keep \n literal text.
    '''
```

Concatenated docstrings and docstrings with escaped newlines are skipped because the exact source line ownership is ambiguous for this rule:

```pydocfmt-example
[input]
def concatenated() -> None:
    ("Summary.  \n"
     "Body.  ")

def escaped_newline() -> None:
    """Summary.  \nBody.  """

[output=unchanged]
```

## Options
None.
