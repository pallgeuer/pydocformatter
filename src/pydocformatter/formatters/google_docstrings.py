import re
import textwrap
from typing import Literal, Protocol

IndentStyle = Literal["space", "tab"]


class SectionFormatter(Protocol):
    """Callable interface for Google-style docstring section formatters."""

    def __call__(
        self,
        buffer: list[str],
        indent: str,
        *,
        line_length: int,
        indent_style: IndentStyle,
        indent_width: int,
    ) -> list[str]: ...


def _indent_unit(*, indent_style: IndentStyle, indent_width: int) -> str:
    """Return one generated indentation level."""
    return "\t" if indent_style == "tab" else " " * indent_width


def _visual_width(text: str, tab_width: int) -> int:
    """Return the visual column width of text with Ruff-style tab width."""
    width = 0
    for char in text:
        if char == "\t":
            width += tab_width
        else:
            width += 1
    return width


def _wrap_with_indents(
    text: str,
    first_indent: str,
    continuation_indent: str,
    *,
    line_length: int,
    indent_width: int,
) -> list[str]:
    """Wrap text while measuring tabs as configured indentation columns."""
    visual_first_indent = " " * _visual_width(first_indent, indent_width)
    visual_continuation_indent = " " * _visual_width(continuation_indent, indent_width)
    wrapped = textwrap.wrap(
        f"{visual_first_indent}{text}",
        width=line_length,
        initial_indent="",
        subsequent_indent=visual_continuation_indent,
        break_long_words=False,
        break_on_hyphens=False,
        drop_whitespace=True,
    )
    result: list[str] = []
    for index, wrapped_line in enumerate(wrapped):
        visual_indent = visual_first_indent if index == 0 else visual_continuation_indent
        actual_indent = first_indent if index == 0 else continuation_indent
        if wrapped_line.startswith(visual_indent):
            result.append(f"{actual_indent}{wrapped_line[len(visual_indent):]}")
        else:
            result.append(f"{actual_indent}{wrapped_line.lstrip()}")
    return result


def _format_param_section(
    buffer: list[str],
    indent: str,
    section_title: str,
    *,
    line_length: int,
    indent_style: IndentStyle,
    indent_width: int,
) -> list[str]:
    """Format a section with parameters in Google style docstrings.

    This function takes a list of lines in the specified section, applies the specified formatting, and returns the
    formatted lines.

    Acceptable formats include:
    - `param_name (type): Description`
    - `param_name: Description`

    Args:
        buffer (list[str]): The list of lines in the specified section.
        indent (str): Base indentation preserved from the docstring quote line.
        line_length (int): The maximum line length for formatting.
        indent_style (IndentStyle): Indentation style for generated section levels.
        indent_width (int): Width of one generated indentation level.

    Returns:
        list[str]: The formatted Args section as a list of lines.
    """
    result = [f"\n{indent}{section_title}:"]
    unit = _indent_unit(indent_style=indent_style, indent_width=indent_width)
    param_indent = indent + unit
    continuation_indent = indent + unit * 2

    entry_re = re.compile(r"^\s*([a-zA-Z_][a-zA-Z0-9_]*)(?:\s*\(([^)]+)\))?:\s*(.*)$")

    current_arg: tuple[str, str | None] | None = None
    desc_lines: list[str] = []

    def flush() -> None:
        if current_arg is not None:
            name, type_ = current_arg
            desc = " ".join(desc_lines).strip()
            type_str = f" ({type_})" if type_ else ""
            wrapped = _wrap_with_indents(
                f"{name}{type_str}: {desc}",
                param_indent,
                continuation_indent,
                line_length=line_length,
                indent_width=indent_width,
            )
            for wrapped_line in wrapped:
                result.append(f"{wrapped_line}")

    for buffer_line in buffer:
        if not buffer_line.strip():
            continue
        match = entry_re.match(buffer_line.strip())
        if match:
            flush()
            current_arg = (match.group(1), match.group(2))
            desc_lines = [match.group(3)]
        elif current_arg:
            desc_lines.append(buffer_line.strip())

    flush()
    return [line + "\n" for line in result]


def _format_single_item_section(
    buffer: list[str],
    indent: str,
    section_title: str,
    *,
    line_length: int,
    indent_style: IndentStyle,
    indent_width: int,
) -> list[str]:
    """Format a section with a single item in Google style docstrings.

    This function formats a section that contains a single item, such as Returns or Yields, and returns the formatted
    lines.

    Acceptable formats include:
    - `type: Description`
    - `Description`

    Args:
        buffer (list[str]): The list of lines in the specified section.
        indent (str): Base indentation preserved from the docstring quote line.
        line_length (int): The maximum line length for formatting.
        section_title (str): The title of the section to format.
        indent_style (IndentStyle): Indentation style for generated section levels.
        indent_width (int): Width of one generated indentation level.

    Returns:
        list[str]: The formatted section as a list of lines.
    """
    result = [f"\n{indent}{section_title}:"]
    unit = _indent_unit(indent_style=indent_style, indent_width=indent_width)
    param_indent = indent + unit
    continuation_indent = indent + unit * 2

    full_text = " ".join(line.strip() for line in buffer if line.strip())
    if not full_text:
        return [line + "\n" for line in result]

    match = re.match(r"^([^:]+):\s*(.*)$", full_text)
    if match:
        type_, desc = match.group(1).strip(), match.group(2).strip()
        first_line = f"{type_}: {desc}"
    else:
        first_line = full_text

    wrapped = _wrap_with_indents(
        first_line,
        param_indent,
        continuation_indent,
        line_length=line_length,
        indent_width=indent_width,
    )
    for wrapped_line in wrapped:
        result.append(f"{wrapped_line}")

    return [line + "\n" for line in result]


def format_args_section(
    buffer: list[str],
    indent: str,
    *,
    line_length: int,
    indent_style: IndentStyle,
    indent_width: int,
) -> list[str]:
    """Format the Args section of a Google style docstring.

    Args:
        buffer (list[str]): Raw lines belonging to the Args section.
        indent (str): Base indentation preserved from the docstring quote line.
        line_length (int): Maximum line length used when wrapping entries.
        indent_style (IndentStyle): Indentation style for generated section levels.
        indent_width (int): Width of one generated indentation level.

    Returns:
        list[str]: Formatted section lines, each ending with a newline.
    """
    return _format_param_section(
        buffer,
        indent,
        "Args",
        line_length=line_length,
        indent_style=indent_style,
        indent_width=indent_width,
    )


def format_returns_section(
    buffer: list[str],
    indent: str,
    *,
    line_length: int,
    indent_style: IndentStyle,
    indent_width: int,
) -> list[str]:
    """Format the Returns section of a Google style docstring.

    Args:
        buffer (list[str]): Raw lines belonging to the Returns section.
        indent (str): Base indentation preserved from the docstring quote line.
        line_length (int): Maximum line length used when wrapping the return description.
        indent_style (IndentStyle): Indentation style for generated section levels.
        indent_width (int): Width of one generated indentation level.

    Returns:
        list[str]: Formatted section lines, each ending with a newline.
    """
    return _format_single_item_section(
        buffer,
        indent,
        "Returns",
        line_length=line_length,
        indent_style=indent_style,
        indent_width=indent_width,
    )


def format_raises_section(
    buffer: list[str],
    indent: str,
    *,
    line_length: int,
    indent_style: IndentStyle,
    indent_width: int,
) -> list[str]:
    """Format the Raises section of a Google style docstring.

    This function formats the Raises section, which typically contains exceptions that the function may raise. It
    applies the specified formatting and returns the formatted lines.

    Args:
        buffer (list[str]): The list of lines in the Raises section.
        indent (str): Base indentation preserved from the docstring quote line.
        line_length (int): The maximum line length for formatting.
        indent_style (IndentStyle): Indentation style for generated section levels.
        indent_width (int): Width of one generated indentation level.

    Returns:
        list[str]: The formatted section as a list of lines.
    """
    result = [f"\n{indent}Raises:"]
    unit = _indent_unit(indent_style=indent_style, indent_width=indent_width)
    param_indent = indent + unit
    continuation_indent = indent + unit * 2

    entry_re = re.compile(r"^\s*`?([a-zA-Z_][a-zA-Z0-9_.]*)`?:\s*(.*)$")

    current_exc: str | None = None
    desc_lines: list[str] = []

    def flush() -> None:
        if current_exc is not None:
            exc = current_exc
            desc = " ".join(desc_lines).strip()
            wrapped = _wrap_with_indents(
                f"`{exc}`: {desc}",
                param_indent,
                continuation_indent,
                line_length=line_length,
                indent_width=indent_width,
            )
            for wrapped_line in wrapped:
                result.append(f"{wrapped_line}")

    for buffer_line in buffer:
        if not buffer_line.strip():
            continue
        match = entry_re.match(buffer_line.strip())
        if match:
            flush()
            current_exc = match.group(1)
            desc_lines = [match.group(2)]
        elif current_exc:
            desc_lines.append(buffer_line.strip())

    flush()
    return [line + "\n" for line in result]


def format_yields_section(
    buffer: list[str],
    indent: str,
    *,
    line_length: int,
    indent_style: IndentStyle,
    indent_width: int,
) -> list[str]:
    """Format the Yields section of a Google style docstring.

    Args:
        buffer (list[str]): Raw lines belonging to the Yields section.
        indent (str): Base indentation preserved from the docstring quote line.
        line_length (int): Maximum line length used when wrapping the yielded-value description.
        indent_style (IndentStyle): Indentation style for generated section levels.
        indent_width (int): Width of one generated indentation level.

    Returns:
        list[str]: Formatted section lines, each ending with a newline.
    """
    return _format_single_item_section(
        buffer,
        indent,
        "Yields",
        line_length=line_length,
        indent_style=indent_style,
        indent_width=indent_width,
    )


# noinspection PyUnusedLocal
def format_examples_section(
    buffer: list[str],
    indent: str,
    *,
    line_length: int,
    indent_style: IndentStyle,
    indent_width: int,
) -> list[str]:
    """Format the Examples section of a Google style docstring.

    This function formats the Examples section, which typically contains usage examples of the function. It applies the
    specified formatting and returns the formatted lines.

    Args:
        buffer (list[str]): The list of lines in the Examples section.
        indent (str): Base indentation preserved from the docstring quote line.
        line_length (int): The maximum line length for formatting.
        indent_style (IndentStyle): Indentation style for generated section levels.
        indent_width (int): Width of one generated indentation level.

    Returns:
        list[str]: The formatted section as a list of lines.
    """
    result = [f"\n{indent}Examples:"]
    param_indent = indent + _indent_unit(indent_style=indent_style, indent_width=indent_width)
    block: list[str] = []

    def is_fenced_block(lines: list[str]) -> bool:
        """Check if the block is a fenced code block."""
        return bool(lines) and lines[0].strip() == "```" and lines[-1].strip() == "```"

    def flush_block() -> None:
        if not block:
            return

        if is_fenced_block(block):
            # For fenced blocks, preserve indentation within the fences
            result.append(f"{param_indent}{block[0].strip()}")  # Opening ```

            # Find minimum indentation of non-empty lines between fences
            content_lines = block[1:-1]  # Exclude opening and closing ```
            non_empty_lines = [content_line for content_line in content_lines if content_line.strip()]

            if non_empty_lines:
                min_indent = min(len(content_line) - len(content_line.lstrip()) for content_line in non_empty_lines)

                for content_line in content_lines:
                    if content_line.strip():
                        # Remove minimum indentation and add param_indent
                        relative_content = content_line[min_indent:] if len(content_line) > min_indent else content_line.lstrip()
                        result.append(f"{param_indent}{relative_content}")
                    else:
                        result.append("")

            result.append(f"{param_indent}{block[-1].strip()}")  # Closing ```
        else:
            # For unfenced blocks, wrap in ``` and preserve indentation
            result.append(f"{param_indent}```")

            # Find minimum indentation of non-empty lines
            non_empty_lines = [block_line for block_line in block if block_line.strip()]

            if non_empty_lines:
                min_indent = min(len(block_line) - len(block_line.lstrip()) for block_line in non_empty_lines)

                for block_line in block:
                    if block_line.strip():
                        # Remove minimum indentation and add param_indent
                        relative_content = block_line[min_indent:] if len(block_line) > min_indent else block_line.lstrip()
                        result.append(f"{param_indent}{relative_content}")
                    else:
                        result.append("")

            result.append(f"{param_indent}```")

        block.clear()

    for line in buffer:
        if line.strip():
            block.append(line.rstrip())
        elif block:
            flush_block()
            if result and not result[-1].endswith("\n"):
                result.append("")

    flush_block()

    return [line + "\n" if not line.endswith("\n") else line for line in result]


def format_attributes_section(
    buffer: list[str],
    indent: str,
    *,
    line_length: int,
    indent_style: IndentStyle,
    indent_width: int,
) -> list[str]:
    """Format the Attributes section of a Google style docstring.

    Args:
        buffer (list[str]): Raw lines belonging to the Attributes section.
        indent (str): Base indentation preserved from the docstring quote line.
        line_length (int): Maximum line length used when wrapping entries.
        indent_style (IndentStyle): Indentation style for generated section levels.
        indent_width (int): Width of one generated indentation level.

    Returns:
        list[str]: Formatted section lines, each ending with a newline.
    """
    return _format_param_section(
        buffer,
        indent,
        "Attributes",
        line_length=line_length,
        indent_style=indent_style,
        indent_width=indent_width,
    )


# noinspection PyTypeChecker
SECTION_HANDLERS: dict[str, SectionFormatter] = {
    "Args": format_args_section,
    "Returns": format_returns_section,
    "Raises": format_raises_section,
    "Yields": format_yields_section,
    "Examples": format_examples_section,
    "Attributes": format_attributes_section,
}


def _extract_lists(paragraph: list[str]) -> list[list[str]]:
    """Extract lists from the buffer.

    This function splits a paragraph into alternating sections of text and list items. It returns a list of sublists
    where each sublist contains either text lines or list item lines (starting with '-').

    Args:
        paragraph (list[str]): The list of lines belonging to the paragraph.

    Returns:
        list[list[str]]: A list of sublists, alternating between text and list items.
    """
    if not paragraph:
        return []

    result: list[list[str]] = []
    current_group: list[str] = []

    def is_list_item(item_line: str) -> bool:
        return item_line.strip().startswith("-")

    current_is_list = is_list_item(paragraph[0])

    for line in paragraph:
        line_is_list = is_list_item(line)

        # If the type changes (text to list or list to text), start a new group
        if line_is_list != current_is_list:
            if current_group:
                result.append(current_group)
            current_group = [line]
            current_is_list = line_is_list
        else:
            current_group.append(line)

    # Add the final group
    if current_group:
        result.append(current_group)

    return result


def reflow(
    docstring: str,
    indent: str,
    *,
    line_length: int,
    indent_style: IndentStyle,
    indent_width: int,
) -> list[str]:
    """Reflow a Google style docstring to fit within the specified line length.

    This function takes a docstring, splits it into lines, and reflows each line to fit within the specified line
    length. It also handles indentation.

    Args:
        docstring (str): The docstring to reflow.
        line_length (int): The maximum line length.
        indent (str): Base indentation preserved from the docstring quote line.
        indent_style (IndentStyle): Indentation style for generated section levels.
        indent_width (int): Width of one generated indentation level.

    Returns:
        list[str]: The reflowed docstring as a list of lines.
    """
    lines = docstring.strip().splitlines()
    result: list[str] = []
    buffer: list[str] = []
    current_section: str | None = None
    sections: list[tuple[str, list[str]]] = []
    section_re = re.compile(
        r"^(Arg(s)?|Return(s)?|Raise(s)?|Yield(s)?|Example(s)?|Attribute(s)?):\s*$",
        re.IGNORECASE,
    )

    def add_section(name: str, section_lines: list[str]) -> None:
        # Normalize section names to plural forms to match SECTION_HANDLERS
        normalized_name = name.capitalize()
        if normalized_name in [
            "Arg",
            "Return",
            "Raise",
            "Yield",
            "Example",
            "Attribute",
        ]:
            normalized_name += "s"
        sections.append((normalized_name, list(section_lines)))

    # Step 1: Parse summary + description + sections
    i = 0
    summary_lines: list[str] = []
    description_lines: list[str] = []

    # Parse summary (consecutive non-empty lines from the start)
    while i < len(lines) and lines[i].strip():
        summary_lines.append(lines[i].strip())
        i += 1

    # Skip blank lines between summary and description
    while i < len(lines) and lines[i].strip() == "":
        i += 1

    # Parse description (everything before sections)
    while i < len(lines):
        match = section_re.match(lines[i].strip())
        if match:
            break
        description_lines.append(lines[i].strip())
        i += 1

    # Section parsing
    while i < len(lines):
        line = lines[i].strip()
        match = section_re.match(line)
        if match:
            if current_section:
                add_section(current_section, buffer)
                buffer.clear()
            current_section = match.group(1)
        elif current_section:
            buffer.append(lines[i])
        i += 1
    if current_section:
        add_section(current_section, buffer)

    # Step 2: Format summary and description
    if summary_lines:
        # Join all summary lines and wrap them
        summary_text = " ".join(summary_lines)
        wrapped_summary = _wrap_with_indents(
            summary_text,
            f'{indent}"""',
            indent,
            line_length=line_length,
            indent_width=indent_width,
        )

        if wrapped_summary:
            # First line includes the opening triple quotes
            result.append(f"{wrapped_summary[0]}\n")
            # Subsequent summary lines
            for summary_line in wrapped_summary[1:]:
                result.append(f"{summary_line}\n")
        else:
            result.append(f'{indent}"""\n')
    else:
        result.append(f'{indent}"""\n')

    if description_lines:
        result.append("\n")
        paragraph: list[str] = []
        for line in description_lines + [""]:
            if line.strip():
                paragraph.append(line.strip())
            elif paragraph:
                # Split paragraph into alternating text and list sections
                desc_paragraphs = _extract_lists(paragraph)

                for section in desc_paragraphs:
                    if section and section[0].strip().startswith("-"):
                        # This is a list section - format as list items
                        for item in section:
                            result.append(f"{indent}{item.strip()}\n")
                    else:
                        # This is a text section - wrap normally
                        wrapped = _wrap_with_indents(
                            " ".join(section),
                            indent,
                            indent,
                            line_length=line_length,
                            indent_width=indent_width,
                        )
                        for wline in wrapped:
                            result.append(f"{wline}\n")

                result.append("\n")
                paragraph.clear()

    # Remove trailing empty line if no sections follow
    if result and result[-1].strip() == "":
        result.pop()

    # Step 3: Format sections
    for section_name, content in sections:
        formatter = SECTION_HANDLERS.get(section_name)
        if formatter:
            result.extend(
                formatter(
                    content,
                    indent,
                    line_length=line_length,
                    indent_style=indent_style,
                    indent_width=indent_width,
                )
            )

    if result and len(result) == 1:
        result[0] = result[0].rstrip() + '"""\n'
    else:
        result.append(f'{indent}"""\n')
    return result
