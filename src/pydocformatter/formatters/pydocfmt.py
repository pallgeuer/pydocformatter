import ast
import dataclasses
import io
import re
import textwrap
import tokenize
import typing

import pydocformatter.formatters.google_docstrings as google_docstrings
import pydocformatter.rules.line_endings as line_endings
import pydocformatter.utils.misc as misc
from pydocformatter.cli.settings_check import CheckSettings, IndentStyle


@dataclasses.dataclass(frozen=True, init=False)
class SourceFormatResult:
    """Formatting result for Python source text.

    Attributes:
        original_source (str): Source text before formatting.
        source (str): Source text after formatting, or the original source in check mode.
        docstring_changed_lines (tuple[int, ...]): One-based line numbers of docstrings that would change or changed.
        comment_changed_lines (tuple[int, ...]): One-based line numbers of comments that would change or changed.
    """

    original_source: str
    source: str
    docstring_changed_lines: tuple[int, ...]
    comment_changed_lines: tuple[int, ...]

    def __init__(
        self,
        source: str,
        docstring_changed_lines: tuple[int, ...],
        comment_changed_lines: tuple[int, ...],
        original_source: str | None = None,
    ) -> None:
        """Initialize source formatting details.

        Args:
            source (str): Source text after formatting, or original source in check mode.
            docstring_changed_lines (tuple[int, ...]): One-based line numbers of docstrings that would change or
                changed.
            comment_changed_lines (tuple[int, ...]): One-based line numbers of comments that would change or changed.
            original_source (str | None): Source text before formatting, defaulting to `source`.
        """
        object.__setattr__(self, "original_source", source if original_source is None else original_source)
        object.__setattr__(self, "source", source)
        object.__setattr__(self, "docstring_changed_lines", docstring_changed_lines)
        object.__setattr__(self, "comment_changed_lines", comment_changed_lines)

    @property
    def modified(self) -> bool:
        """Return whether formatting changed the source.

        Returns:
            bool: True if any docstring or comment lines changed.
        """
        return bool(self.docstring_changed_lines or self.comment_changed_lines)


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
    settings: CheckSettings,
    *,
    line_ending: str,
) -> tuple[str, tuple[int, ...]]:
    """Format docstrings in Python source and return changed line numbers.

    Args:
        source (str): Python source text to format.
        settings (CheckSettings): Resolved formatter settings.
        line_ending (str): Concrete line ending to use for generated docstring lines.

    Returns:
        tuple[str, tuple[int, ...]]: Formatted source and one-based changed line numbers.

    Raises:
        `SyntaxError`: If the source cannot be parsed as Python.
    """
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
    settings: CheckSettings,
    *,
    line_ending: str,
) -> tuple[str, tuple[int, ...]]:
    """Format comments in Python source and return changed line numbers.

    Args:
        source (str): Python source text to format.
        settings (CheckSettings): Resolved formatter settings.
        line_ending (str): Concrete line ending to use for generated comment lines.

    Returns:
        tuple[str, tuple[int, ...]]: Formatted source and one-based changed line numbers.

    Raises:
        `tokenize.TokenError`: If Python tokenization fails.
    """
    tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    lines = source.splitlines(keepends=True)
    output_lines = list(lines)

    special_comment_re = re.compile(r"#\s*(noqa|type:\s*ignore|pylint|fmt:|pragma)", re.IGNORECASE)
    changed_lines: set[int] = set()

    comment_block: list[tuple[int, str]] = []
    last_srow = -2

    def is_code_comment(text: str) -> bool:
        """Return whether the comment resembles disabled code."""
        return text.startswith("    ") or bool(re.match(r"\s*(if|for|while|def|class|try|except|print|return)\b", text))

    def flush_comment_block() -> None:
        """Flush the current standalone comment block to the output lines."""
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


def format_file(path: str, settings: CheckSettings, fix: bool, *, output: typing.TextIO | None) -> bool:
    """Format docstrings and comments in a Python file.

    This function reads a Python file once, formats docstrings first, then formats comments. If `fix` is False, it only
    checks if the file is formatted correctly.

    Args:
        path (str): The path to the Python file.
        settings (CheckSettings): Resolved settings for formatting.
        fix (bool): If True, write formatting changes to the file.
        output (typing.TextIO | None): Stream for check-mode diagnostics, or stdout if None.

    Returns:
        bool: True if the file was modified or needs formatting, False otherwise.

    Raises:
        `OSError`: If the file cannot be read or written.
        `SyntaxError`: If the file cannot be parsed as Python source.
        `tokenize.TokenError`: If Python tokenization fails.
        `UnicodeDecodeError`: If the file cannot be decoded as UTF-8.
    """
    result = format_file_source(path, settings=settings, fix=fix)

    if not fix:
        print_source_diagnostics(path, result, output=output)
    return result.modified


def format_file_source(
    path: str,
    *,
    settings: CheckSettings,
    fix: bool,
    write: bool = True,
) -> SourceFormatResult:
    """Format a Python file and return source-level formatting details, optionally writing fixes.

    Args:
        path (str): Path to the Python source file.
        settings (CheckSettings): Resolved formatter settings.
        fix (bool): Whether formatting changes should be applied.
        write (bool): Whether fixed source should be written back to disk.

    Returns:
        SourceFormatResult: Source-level formatting result.

    Raises:
        `OSError`: If the file cannot be read or written.
        `SyntaxError`: If the file cannot be parsed as Python source.
        `tokenize.TokenError`: If Python tokenization fails.
        `UnicodeDecodeError`: If the file cannot be decoded as UTF-8.
    """
    with open(path, encoding="utf-8", newline="") as file:
        source = file.read()

    result = format_source(source, settings, fix=fix)

    if fix and write and result.modified:
        with open(path, "w", encoding="utf-8", newline="") as file:
            file.write(result.source)
    return result


def format_source(source: str, settings: CheckSettings, fix: bool) -> SourceFormatResult:
    """Format Python source text and return changed line details.

    Args:
        source (str): Python source text to format.
        settings (CheckSettings): Resolved formatter settings.
        fix (bool): Whether formatting changes should be applied to returned source.

    Returns:
        SourceFormatResult: Source-level formatting result.

    Raises:
        `SyntaxError`: If the source cannot be parsed as Python.
        `tokenize.TokenError`: If Python tokenization fails.
    """
    line_ending = line_endings.resolve_line_ending(source, line_ending=settings.line_ending)
    docstring_source, docstring_changed_lines = format_docstrings_in_source(source, settings, line_ending=line_ending)

    if not fix:
        _, comment_changed_lines = format_comments_in_source(source, settings, line_ending=line_ending)
        return SourceFormatResult(original_source=source, source=source, docstring_changed_lines=docstring_changed_lines, comment_changed_lines=comment_changed_lines)

    formatted_source, comment_changed_lines = format_comments_in_source(docstring_source, settings, line_ending=line_ending)
    return SourceFormatResult(original_source=source, source=formatted_source, docstring_changed_lines=docstring_changed_lines, comment_changed_lines=comment_changed_lines)


def print_source_diagnostics(
    path: str,
    result: SourceFormatResult,
    *,
    output: typing.TextIO | None,
) -> None:
    """Print check-mode diagnostics for a source formatting result.

    Args:
        path (str): Display path for diagnostics.
        result (SourceFormatResult): Source formatting result to report.
        output (typing.TextIO | None): Output stream, or stdout when None.
    """
    for message in source_diagnostic_messages(path, result):
        print(message, file=output)


def format_needs_formatting_message(
    path: str,
    subject: str,
    line_numbers: list[int],
) -> str:
    """Build a compact per-file check message with line or line-range details.

    Args:
        path (str): File path to include in the diagnostic.
        subject (str): Formatting subject, such as `docstring` or `comment`.
        line_numbers (list[int]): Sorted 1-based line numbers that need formatting.

    Returns:
        str: Human-readable diagnostic message for check mode.
    """
    label = "lines" if len(line_numbers) > 1 else "line"
    formatted_ranges = misc.format_line_ranges(line_numbers)
    return f"{path}: Needs {subject} formatting on {label} {formatted_ranges}"


def source_diagnostic_messages(
    path: str,
    result: SourceFormatResult,
) -> tuple[str, ...]:
    """Return check-mode diagnostics for a source formatting result.

    Args:
        path (str): Display path for diagnostics.
        result (SourceFormatResult): Source formatting result to report.

    Returns:
        tuple[str, ...]: Diagnostic messages for docstring and comment formatting needs.
    """
    messages: list[str] = []
    if result.docstring_changed_lines:
        messages.append(format_needs_formatting_message(path, "docstring", list(result.docstring_changed_lines)))
    if result.comment_changed_lines:
        messages.append(format_needs_formatting_message(path, "comment", list(result.comment_changed_lines)))
    return tuple(messages)


def format_docstrings(
    path: str,
    settings: CheckSettings,
    check: bool,
) -> bool:
    """Format only docstrings in a Python file.

    Args:
        path (str): Path to the Python source file.
        settings (CheckSettings): Resolved formatter settings.
        check (bool): Whether to only report needed formatting instead of writing fixes.

    Returns:
        bool: True if the file was modified or needs docstring formatting.

    Raises:
        `OSError`: If the file cannot be read or written.
        `SyntaxError`: If the file cannot be parsed as Python source.
        `UnicodeDecodeError`: If the file cannot be decoded as UTF-8.
    """
    with open(path, encoding="utf-8", newline="") as file:
        source = file.read()

    line_ending = line_endings.resolve_line_ending(source, line_ending=settings.line_ending)
    formatted_source, changed_lines = format_docstrings_in_source(source, settings, line_ending=line_ending)

    if check:
        if changed_lines:
            print(format_needs_formatting_message(path, "docstring", list(changed_lines)))
        return bool(changed_lines)

    if source != formatted_source:
        with open(path, "w", encoding="utf-8", newline="") as file:
            file.write(formatted_source)
        return True
    return False
