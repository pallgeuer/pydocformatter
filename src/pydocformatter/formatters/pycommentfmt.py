import io
import re
import textwrap
import tokenize

import pydocformatter.utils as utils
from pydocformatter.config import FormatterSettings


def format_comments(
    path: str, settings: FormatterSettings, check: bool = False
) -> bool:
    """Format comments in a Python file.

    This function reads a Python file, formats its comments to ensure they comply with
    the specified line length. If `check` is True, it only checks if the file is
    formatted correctly.

    Args:
        path (str): The path to the Python file.
        settings (FormatterSettings): Resolved settings for comment formatting.
        check (bool): If True, only check if the file is formatted correctly.

    Returns:
        bool: True if the file was modified, False otherwise.

    Raises:
        `OSError`: If the file cannot be read or written.
        `tokenize.TokenError`: If Python tokenization fails.
        `UnicodeDecodeError`: If the file cannot be decoded as UTF-8.
    """
    with open(path, encoding="utf-8") as f:
        source = f.read()

    tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    lines = source.splitlines(keepends=True)
    output_lines = list(lines)

    SPECIAL_COMMENT_RE = re.compile(
        r"#\s*(noqa|type:\s*ignore|pylint|fmt:|pragma)", re.IGNORECASE
    )
    changed_lines: set[int] = set()

    comment_block: list[tuple[int, str]] = []
    last_srow = -2

    def is_code_comment(text: str) -> bool:
        """Check if the comment is a code-style comment."""
        return text.startswith("    ") or bool(
            re.match(r"\s*(if|for|while|def|class|try|except|print|return)\b", text)
        )

    def flush_comment_block() -> None:
        """Flush the current comment block to the output lines."""
        nonlocal comment_block
        if not comment_block:
            return

        srows = [block_row for block_row, _ in comment_block]
        base_line = lines[srows[0]]
        base_indent = base_line[: len(base_line) - len(base_line.lstrip())]

        # If it's a code-style block (e.g., '#    if x == y:"), preserve as-is
        if any(is_code_comment(c.lstrip("#")) for _, c in comment_block):
            return

        block_comment_text = " ".join(
            block_line.lstrip("#").strip() for _, block_line in comment_block
        )
        available_width = settings.line_length - len(base_indent) - 2
        wrapped_lines = textwrap.wrap(
            block_comment_text,
            width=available_width,
            break_long_words=False,
            break_on_hyphens=False,
        )
        new_lines = [
            f"{base_indent}# {wrapped_line}\n" for wrapped_line in wrapped_lines
        ]

        if any(
            lines[block_row] != new_lines[i]
            for i, block_row in enumerate(srows[: len(new_lines)])
        ):
            changed_lines.update(srows)

        for block_row in srows:
            output_lines[block_row] = ""
        output_lines[srows[0]] = "".join(new_lines)
        comment_block.clear()

    for tok_type, tok_str, (srow, scol), _, line in tokens:
        if tok_type != tokenize.COMMENT:
            flush_comment_block()
            continue

        if srow == 1 and tok_str.startswith("#!"):  # ignore shebang
            continue
        if srow <= 2 and "coding" in tok_str:  # ignore coding comments
            continue
        if SPECIAL_COMMENT_RE.match(tok_str):
            continue

        before_comment = line[:scol]
        is_inline = bool(before_comment.strip())
        comment_text = tok_str.lstrip("#").strip()

        if is_inline:
            flush_comment_block()
            code = before_comment.rstrip()
            inline_length = len(code) + 4 + len(comment_text)

            if inline_length <= settings.line_length:
                new_line = f"{code}  # {comment_text}\n"
                if new_line != lines[srow - 1]:
                    changed_lines.add(srow - 1)
                output_lines[srow - 1] = new_line
            else:
                indent = before_comment[
                    : len(before_comment) - len(before_comment.lstrip())
                ]
                available = settings.line_length - len(indent) - 2
                wrapped = textwrap.wrap(
                    comment_text,
                    width=available,
                    break_long_words=False,
                    break_on_hyphens=False,
                )
                new_comment_lines = [f"{indent}# {line}\n" for line in wrapped]
                output_lines[srow - 1] = "".join(new_comment_lines) + f"{code}\n"
                changed_lines.add(srow - 1)
        else:
            if srow == last_srow + 1:
                comment_block.append((srow - 1, tok_str))
            else:
                flush_comment_block()
                comment_block.append((srow - 1, tok_str))
            last_srow = srow

    flush_comment_block()

    if check:
        if changed_lines:
            line_numbers = sorted(i + 1 for i in changed_lines)
            print(utils.format_needs_formatting_message(path, "comment", line_numbers))
            return True
        return False
    else:
        modified_content = "".join(output_lines)
        if source != modified_content:
            with open(path, "w", encoding="utf-8") as f:
                f.write(modified_content)
            return True
        return False
