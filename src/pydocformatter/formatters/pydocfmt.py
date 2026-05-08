import ast

import pydocformatter.formatters.google_docstrings as google_docstrings
import pydocformatter.utils as utils
from pydocformatter.config import FormatterSettings, IndentStyle


def process_docstring_node(
    node: ast.AST,
    output_lines: list[str],
    line_length: int,
    changed_lines: set[int],
    *,
    indent_style: IndentStyle = "space",
    indent_width: int = 4,
) -> bool:
    """Process a docstring node in the AST.

    This function formats the docstring of a node (Module, FunctionDef, AsyncFunctionDef, ClassDef)

    Args:
        node (ast.AST): The AST node to process.
        output_lines (list[str]): The list of output lines to modify.
        line_length (int): The maximum line length for formatting.
        changed_lines (set[int]): Set of 1-based line numbers whose docstring spans require formatting.
        indent_style (IndentStyle): Indentation style for generated docstring section levels. The base indentation from
            the opening quote line is preserved.
        indent_width (int): Width of one generated docstring indentation level, and the visual width used when measuring
            tabs.

    Returns:
        bool: True if the output_lines were modified, False otherwise.
    """
    if not isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return False

    docstring = ast.get_docstring(node)
    if not docstring:
        return False

    doc_node = node.body[0]
    if not isinstance(doc_node, ast.Expr) or not isinstance(getattr(doc_node, "value", None), ast.Constant):
        return False
    if doc_node.end_lineno is None:
        return False

    # Get raw string token bounds
    srow = doc_node.lineno - 1
    erow = doc_node.end_lineno - 1
    quote_line = output_lines[srow]

    indent = quote_line[: len(quote_line) - len(quote_line.lstrip())]
    docstring_content = docstring.strip()

    new_lines = google_docstrings.reflow(docstring_content, line_length, indent, indent_style, indent_width)
    new_docstring = "".join(new_lines)

    # Get original docstring
    original_docstring = "".join(output_lines[srow : erow + 1])

    if new_docstring == original_docstring:
        return False

    for i in range(srow, erow + 1):
        output_lines[i] = ""
    changed_lines.update(range(srow + 1, erow + 2))

    # Insert the new docstring
    output_lines[srow] = new_docstring
    return True


def format_docstrings(
    path: str,
    settings: FormatterSettings,
    check: bool,
) -> bool:
    """Format docstrings in a Python file.

    This function reads a Python file, formats its docstrings to ensure they comply with the specified line length. If
    `check` is True, it only checks if the file is formatted correctly. This function can format docstrings in Google
    style.

    Args:
        path (str): The path to the Python file.
        settings (FormatterSettings): Resolved settings for docstring formatting.
        check (bool): If True, only check if the file is formatted correctly.

    Returns:
        bool: True if the file was modified, False otherwise.

    Raises:
        `OSError`: If the file cannot be read or written.
        `SyntaxError`: If the file cannot be parsed as Python source.
        `UnicodeDecodeError`: If the file cannot be decoded as UTF-8.
    """
    with open(path, encoding="utf-8") as f:
        source = f.read()

    source_lines = source.splitlines(keepends=True)
    tree = ast.parse(source)
    output_lines = list(source_lines)
    modified = False
    changed_lines: set[int] = set()

    # AST walk to find docstrings
    for node in [tree] + list(ast.walk(tree)):
        if process_docstring_node(
            node,
            output_lines,
            settings.line_length,
            changed_lines,
            indent_style=settings.indent_style,
            indent_width=settings.indent_width,
        ):
            modified = True

    if check:
        if modified:
            print(utils.format_needs_formatting_message(path, "docstring", sorted(changed_lines)))
        return modified
    else:
        if modified:
            modified_content = "".join(output_lines)
            with open(path, "w", encoding="utf-8") as f:
                f.write(modified_content)
            return True
    return False
