import ast
import io
import re
import textwrap
import tokenize

import pydocformatter.formatters.google_docstrings as google_docstrings
import pydocformatter.utils.diagnostics as diagnostics
import pydocformatter.utils.line_endings as line_endings
from pydocformatter.config import FormatterSettings, IndentStyle


def _matches_ignoring_line_endings(left: str, right: str) -> bool:
    """Return whether two strings differ only by line-ending style."""
    return line_endings.normalize_line_endings(left, line_ending="\n") == line_endings.normalize_line_endings(right, line_ending="\n")


def process_docstring_node(
    node: ast.AST,
    output_lines: list[str],
    changed_lines: set[int],
    *,
    line_length: int,
    line_ending: str,
    indent_style: IndentStyle,
    indent_width: int,
) -> bool:
    """Process a docstring node in the AST.

    This function formats the docstring of a node (Module, FunctionDef, AsyncFunctionDef, ClassDef)

    Args:
        node (ast.AST): The AST node to process.
        output_lines (list[str]): The list of output lines to modify.
        line_length (int): The maximum line length for formatting.
        changed_lines (set[int]): Set of 1-based line numbers whose docstring spans require formatting.
        line_ending (str): Concrete line ending to use for generated docstring lines.
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

    new_lines = google_docstrings.reflow(
        docstring_content,
        indent,
        line_length=line_length,
        indent_style=indent_style,
        indent_width=indent_width,
    )
    new_docstring = line_endings.normalize_line_endings("".join(new_lines), line_ending=line_ending)

    # Get original docstring
    original_docstring = "".join(output_lines[srow : erow + 1])

    if _matches_ignoring_line_endings(new_docstring, original_docstring):
        return False

    for i in range(srow, erow + 1):
        output_lines[i] = ""
    changed_lines.update(range(srow + 1, erow + 2))

    # Insert the new docstring
    output_lines[srow] = new_docstring
    return True


def format_docstrings_in_source(
    source: str,
    settings: FormatterSettings,
    *,
    line_ending: str,
) -> tuple[str, tuple[int, ...]]:
    """Format docstrings in Python source and return changed line numbers."""
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
            changed_lines,
            line_length=settings.line_length,
            line_ending=line_ending,
            indent_style=settings.indent_style,
            indent_width=settings.indent_width,
        ):
            modified = True

    if not modified:
        return source, ()

    return "".join(output_lines), tuple(sorted(changed_lines))


def format_comments_in_source(
    source: str,
    settings: FormatterSettings,
    *,
    line_ending: str,
) -> tuple[str, tuple[int, ...]]:
    """Format comments in Python source and return changed line numbers."""
    tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    lines = source.splitlines(keepends=True)
    output_lines = list(lines)

    special_comment_re = re.compile(r"#\s*(noqa|type:\s*ignore|pylint|fmt:|pragma)", re.IGNORECASE)
    changed_lines: set[int] = set()

    comment_block: list[tuple[int, str]] = []
    last_srow = -2

    def is_code_comment(text: str) -> bool:
        """Check if the comment is a code-style comment."""
        return text.startswith("    ") or bool(re.match(r"\s*(if|for|while|def|class|try|except|print|return)\b", text))

    def flush_comment_block() -> None:
        """Flush the current comment block to the output lines."""
        nonlocal comment_block
        if not comment_block:
            return

        srows = [block_row for block_row, _ in comment_block]
        base_line = lines[srows[0]]
        base_indent = base_line[: len(base_line) - len(base_line.lstrip())]

        if any(is_code_comment(c.lstrip("#")) for _, c in comment_block):
            comment_block.clear()
            return

        block_comment_text = " ".join(block_line.lstrip("#").strip() for _, block_line in comment_block)
        available_width = settings.line_length - len(base_indent) - 2
        wrapped_lines = textwrap.wrap(
            block_comment_text,
            width=available_width,
            break_long_words=False,
            break_on_hyphens=False,
        )
        new_lines = [f"{base_indent}# {wrapped_line}{line_ending}" for wrapped_line in wrapped_lines]
        original_block = "".join(lines[block_row] for block_row in srows)
        new_block = "".join(new_lines)

        if _matches_ignoring_line_endings(original_block, new_block):
            comment_block.clear()
            return

        for block_row in srows:
            output_lines[block_row] = ""
        output_lines[srows[0]] = new_block
        changed_lines.update(block_row + 1 for block_row in srows)
        comment_block.clear()

    for tok_type, tok_str, (srow, scol), _, line in tokens:
        if tok_type != tokenize.COMMENT:
            flush_comment_block()
            continue

        if srow == 1 and tok_str.startswith("#!"):
            continue
        if srow <= 2 and "coding" in tok_str:
            continue
        if special_comment_re.match(tok_str):
            continue

        before_comment = line[:scol]
        is_inline = bool(before_comment.strip())
        comment_text = tok_str.lstrip("#").strip()

        if is_inline:
            flush_comment_block()
            code = before_comment.rstrip()
            inline_length = len(code) + 4 + len(comment_text)

            if inline_length <= settings.line_length:
                new_line = f"{code}  # {comment_text}{line_ending}"
                if not _matches_ignoring_line_endings(new_line, lines[srow - 1]):
                    changed_lines.add(srow)
                    output_lines[srow - 1] = new_line
            else:
                indent = before_comment[: len(before_comment) - len(before_comment.lstrip())]
                available = settings.line_length - len(indent) - 2
                wrapped = textwrap.wrap(
                    comment_text,
                    width=available,
                    break_long_words=False,
                    break_on_hyphens=False,
                )
                new_comment_lines = [f"{indent}# {line}{line_ending}" for line in wrapped]
                new_line = "".join(new_comment_lines) + f"{code}{line_ending}"
                if not _matches_ignoring_line_endings(new_line, lines[srow - 1]):
                    output_lines[srow - 1] = new_line
                    changed_lines.add(srow)
        else:
            if not comment_text:
                flush_comment_block()
                continue
            if srow == last_srow + 1:
                comment_block.append((srow - 1, tok_str))
            else:
                flush_comment_block()
                comment_block.append((srow - 1, tok_str))
            last_srow = srow

    flush_comment_block()

    if not changed_lines:
        return source, ()
    return "".join(output_lines), tuple(sorted(changed_lines))


def format_file(
    path: str,
    settings: FormatterSettings,
    fix: bool,
) -> bool:
    """Format docstrings and comments in a Python file.

    This function reads a Python file once, formats docstrings first, then formats comments. If `fix` is False, it only
    checks if the file is formatted correctly.

    Args:
        path (str): The path to the Python file.
        settings (FormatterSettings): Resolved settings for formatting.
        fix (bool): If True, write formatting changes to the file.

    Returns:
        bool: True if the file was modified or needs formatting, False otherwise.

    Raises:
        `OSError`: If the file cannot be read or written.
        `SyntaxError`: If the file cannot be parsed as Python source.
        `tokenize.TokenError`: If Python tokenization fails.
        `UnicodeDecodeError`: If the file cannot be decoded as UTF-8.
    """
    with open(path, encoding="utf-8", newline="") as file:
        source = file.read()

    line_ending = line_endings.resolve_line_ending(source, line_ending=settings.line_ending)
    docstring_source, docstring_changed_lines = format_docstrings_in_source(source, settings, line_ending=line_ending)

    if not fix:
        _, comment_changed_lines = format_comments_in_source(source, settings, line_ending=line_ending)
        if docstring_changed_lines:
            print(diagnostics.format_needs_formatting_message(path, "docstring", list(docstring_changed_lines)))
        if comment_changed_lines:
            print(diagnostics.format_needs_formatting_message(path, "comment", list(comment_changed_lines)))
        return bool(docstring_changed_lines or comment_changed_lines)

    formatted_source, comment_changed_lines = format_comments_in_source(docstring_source, settings, line_ending=line_ending)
    if docstring_changed_lines or comment_changed_lines:
        with open(path, "w", encoding="utf-8", newline="") as file:
            file.write(formatted_source)
        return True
    return False


def format_docstrings(
    path: str,
    settings: FormatterSettings,
    check: bool,
) -> bool:
    """Format only docstrings in a Python file."""
    with open(path, encoding="utf-8", newline="") as file:
        source = file.read()

    line_ending = line_endings.resolve_line_ending(source, line_ending=settings.line_ending)
    formatted_source, changed_lines = format_docstrings_in_source(source, settings, line_ending=line_ending)

    if check:
        if changed_lines:
            print(diagnostics.format_needs_formatting_message(path, "docstring", list(changed_lines)))
        return bool(changed_lines)

    if source != formatted_source:
        with open(path, "w", encoding="utf-8", newline="") as file:
            file.write(formatted_source)
        return True
    return False
