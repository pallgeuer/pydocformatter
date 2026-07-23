# docstring-trailing-whitespace (PDF102)

Fix is always available.

## What it does
Checks accidental spaces and tabs at the end of non-empty docstring lines when the line is followed by an evaluated newline. A terminal run of at least two evaluated ASCII spaces is an intentional Markdown hard break and is preserved exactly, including longer runs and Python source spellings such as `\x20\x20`. If tabs immediately precede the preserved final space run, PDF102 removes only those tabs; spaces before the tabs are retained as ordinary content. One trailing space, tabs, and mixed suffixes not ending in at least two spaces are removed.

An odd terminal run of evaluated backslashes is a backslash hard break owned by reflow. It is not trailing whitespace and PDF102 leaves it unchanged. Whitespace-only lines, final lines without an evaluated newline, and whitespace immediately before same-line closing quotes remain outside PDF102's ownership.

PDF102 only reports changes with a complete safe source edit, which is why its fix availability remains `Always`. A lossless source map lets it fix trailing whitespace immediately before either physical newlines or value-producing newline escapes such as `\n`, while preserving unrelated escapes, source continuations, prefixes, delimiters, and line endings exactly. This includes continuations embedded inside the source spelling of a line and continuations between removable tabs or spaces in its trailing suffix. It skips concatenated docstrings and simple literals containing unsupported escape spellings.

PDF102 does not change whitespace-only docstring lines; PDF103 owns those. It also does not remove spaces or tabs immediately before closing quotes on the final evaluated line when that line has non-empty content; PDF105 owns that quote-adjacent case. When a final non-empty line is followed by an evaluated newline before the closing quotes, PDF102 does remove trailing whitespace from that line.

## Why is this useful?
Trailing whitespace creates noisy diffs and can make otherwise identical docstrings compare differently.

## Ruff compatibility
This rule overlaps with Ruff's general `W291` trailing-whitespace check, but intentionally preserves space-based Markdown hard breaks. Ruff can still report or remove those spaces, so disable or scope `W291` for such docstrings, or use backslash hard breaks when both tools must coexist.

## Examples
Trailing whitespace on non-empty docstring lines is removed (`\x20` is used instead of a literal space for easier understanding of the examples):

```pydocfmt-example
[input]
def area(radius: float) -> float:
    """Return the area.\x20
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
    """Return the description.\x20
      
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
    """Return the area.\x20
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

Two-space and longer space-based hard breaks retain their exact source spelling, while a preceding escaped tab is removed without shortening the final space run:

```pydocfmt-example
[input]
def hard_breaks() -> None:
    """Two spaces.\x20\x20
    Three spaces.\x20\x20\x20
    Escaped tab before break.\t\x20\x20
    Continue here."""

[output]
def hard_breaks() -> None:
    """Two spaces.\x20\x20
    Three spaces.\x20\x20\x20
    Escaped tab before break.\x20\x20
    Continue here."""
```

Escaped logical newlines receive exact source-local fixes, while concatenated docstrings remain unchanged:

```pydocfmt-example
[input]
def concatenated() -> None:
    ("Summary. \n"
     "Body. ")

def escaped_newline() -> None:
    """Summary. \nBody.  """

[output]
def concatenated() -> None:
    ("Summary. \n"
     "Body. ")

def escaped_newline() -> None:
    """Summary.\nBody.  """
```

## Options
None.
