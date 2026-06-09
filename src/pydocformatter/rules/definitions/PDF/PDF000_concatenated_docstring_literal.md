# concatenated-docstring-literal (PDF000)

Fix is always available.

## What it does
Checks docstrings formed from implicitly concatenated string literals and replaces the complete expression with one triple-double-quoted string literal having the same evaluated value.

## Why is this useful?
Later docstring formatting rules can safely rewrite one literal instead of preserving boundaries between adjacent literals.

## Ruff compatibility
None.

## Example
The canonical case is a docstring composed of adjacent string literals:

```python
def function():
    "First part. " "Second part."
```

Applying this rule produces:

```python
def function():
    """First part. Second part."""
```

The replacement preserves the evaluated string value, including escapes and differences between raw and ordinary source literals:

```python
def paths():
    r"C:\Users" "\\" "name"

def controls():
    "First line\n" "Second line\tindented"
```

Applying this rule produces:

```python
def paths():
    """C:\\Users\\name"""

def controls():
    """First line
Second line\tindented"""
```

Parentheses and surrounding statement layout are retained while the complete concatenated string expression is replaced. Comments between the component literals disappear with those source-level boundaries:

```python
def function():
    (
        "Return the result "  # Introduce the result.
        "after validation."
    )
```

Applying this rule produces:

```python
def function():
    (
        """Return the result after validation."""
    )
```

Module, class, and function docstrings are all handled, including docstrings in single-line suites:

```python
"Package " "documentation."

class Client:
    "HTTP " "client."

    def close(self): "Close " "the client."; self._closed = True
```

Applying this rule produces:

```python
"""Package documentation."""

class Client:
    """HTTP client."""

    def close(self): """Close the client."""; self._closed = True
```

Only a string-valued first expression in a module, class, or function body is a docstring. Concatenated strings used elsewhere and already-simple docstrings are unchanged:

```python
def documented():
    """Already simple."""
    label = "first " "second"

def undocumented():
    initialize()
    "Not " "a docstring."
```

## Options
None.
