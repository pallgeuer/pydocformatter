import re
import textwrap
from collections.abc import Callable


def _format_param_section(
    buffer: list[str], indent: str, line_length: int, section_title: str
) -> list[str]:
    """Format a section with parameters in Google style docstrings.

    This function takes a list of lines in the specified section, applies the specified
    formatting, and returns the formatted lines.

    Acceptable formats include:
    - `param_name (type): Description`
    - `param_name: Description`

    Args:
        buffer (list[str]): The list of lines in the specified section.
        indent (str): The indentation to apply to each line.
        line_length (int): The maximum line length for formatting.

    Returns:
        list[str]: The formatted Args section as a list of lines.
    """
    result = [f"\n{indent}{section_title}:"]
    param_indent = indent + " " * 4
    continuation_indent = indent + " " * 8

    entry_re = re.compile(r"^\s*([a-zA-Z_][a-zA-Z0-9_]*)(?:\s*\(([^)]+)\))?:\s*(.*)$")

    current_arg: tuple[str, str | None] | None = None
    desc_lines: list[str] = []

    def flush() -> None:
        if current_arg is not None:
            name, type_ = current_arg
            desc = " ".join(desc_lines).strip()
            type_str = f" ({type_})" if type_ else ""
            first_line = f"{param_indent}{name}{type_str}: {desc}"
            wrapped = textwrap.wrap(
                first_line,
                width=line_length,
                initial_indent="",
                subsequent_indent=continuation_indent,
                break_long_words=False,
                break_on_hyphens=False,
            )
            for line in wrapped:
                result.append(f"{line}")

    for line in buffer:
        if not line.strip():
            continue
        match = entry_re.match(line.strip())
        if match:
            flush()
            current_arg = (match.group(1), match.group(2))
            desc_lines = [match.group(3)]
        elif current_arg:
            desc_lines.append(line.strip())

    flush()
    return [line + "\n" for line in result]


def _format_single_item_section(
    buffer: list[str], indent: str, line_length: int, section_title: str
) -> list[str]:
    """Format a section with a single item in Google style docstrings.

    This function formats a section that contains a single item, such as Returns or
    Yields, and returns the formatted lines.

    Acceptable formats include:
    - `type: Description`
    - `Description`

    Args:
        buffer (list[str]): The list of lines in the specified section.
        indent (str): The indentation to apply to each line.
        line_length (int): The maximum line length for formatting.
        section_title (str): The title of the section to format.

    Returns:
        list[str]: The formatted section as a list of lines.
    """
    result = [f"\n{indent}{section_title}:"]
    param_indent = indent + " " * 4
    continuation_indent = indent + " " * 8

    full_text = " ".join(line.strip() for line in buffer if line.strip())
    if not full_text:
        return [line + "\n" for line in result]

    match = re.match(r"^([^:]+):\s*(.*)$", full_text)
    if match:
        type_, desc = match.group(1).strip(), match.group(2).strip()
        first_line = f"{param_indent}{type_}: {desc}"
    else:
        first_line = f"{param_indent}{full_text}"

    wrapped = textwrap.wrap(
        first_line,
        width=line_length,
        initial_indent="",
        subsequent_indent=continuation_indent,
        break_long_words=False,
        break_on_hyphens=False,
    )
    for line in wrapped:
        result.append(f"{line}")

    return [line + "\n" for line in result]


def format_args_section(buffer: list[str], indent: str, line_length: int) -> list[str]:
    """Format the Args section of a Google style docstring."""
    return _format_param_section(buffer, indent, line_length, "Args")


def format_returns_section(
    buffer: list[str], indent: str, line_length: int
) -> list[str]:
    """Format the Returns section of a Google style docstring."""
    return _format_single_item_section(buffer, indent, line_length, "Returns")


def format_raises_section(
    buffer: list[str], indent: str, line_length: int
) -> list[str]:
    """Format the Raises section of a Google style docstring.

    This function formats the Raises section, which typically contains exceptions that
    the function may raise. It applies the specified formatting and returns the
    formatted lines.

    Args:
        buffer (list[str]): The list of lines in the Raises section.
        indent (str): The indentation to apply to each line.
        line_length (int): The maximum line length for formatting.

    Returns:
        list[str]: The formatted section as a list of lines.
    """
    result = [f"\n{indent}Raises:"]
    param_indent = indent + " " * 4
    continuation_indent = param_indent + " " * 8

    entry_re = re.compile(r"^\s*`?([a-zA-Z_][a-zA-Z0-9_\.]*)`?:\s*(.*)$")

    current_exc: str | None = None
    desc_lines: list[str] = []

    def flush() -> None:
        if current_exc is not None:
            exc = current_exc
            desc = " ".join(desc_lines).strip()
            first_line = f"{param_indent}`{exc}`: {desc}"
            wrapped = textwrap.wrap(
                first_line,
                width=line_length,
                initial_indent="",
                subsequent_indent=continuation_indent,
                break_long_words=False,
                break_on_hyphens=False,
            )
            for line in wrapped:
                result.append(f"{line}")

    for line in buffer:
        if not line.strip():
            continue
        match = entry_re.match(line.strip())
        if match:
            flush()
            current_exc = match.group(1)
            desc_lines = [match.group(2)]
        elif current_exc:
            desc_lines.append(line.strip())

    flush()
    return [line + "\n" for line in result]


def format_yields_section(
    buffer: list[str], indent: str, line_length: int
) -> list[str]:
    """Format the Yields section of a Google style docstring."""
    return _format_single_item_section(buffer, indent, line_length, "Yields")


def format_examples_section(
    buffer: list[str], indent: str, line_length: int
) -> list[str]:
    """Format the Examples section of a Google style docstring.

    This function formats the Examples section, which typically contains usage examples
    of the function. It applies the specified formatting and returns the formatted
    lines.

    Args:
        buffer (list[str]): The list of lines in the Examples section.
        indent (str): The indentation to apply to each line.
        line_length (int): The maximum line length for formatting.

    Returns:
        list[str]: The formatted section as a list of lines.
    """
    result = [f"\n{indent}Examples:"]
    param_indent = indent + " " * 4
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
            non_empty_lines = [line for line in content_lines if line.strip()]

            if non_empty_lines:
                min_indent = min(
                    len(line) - len(line.lstrip()) for line in non_empty_lines
                )

                for line in content_lines:
                    if line.strip():
                        # Remove minimum indentation and add param_indent
                        relative_content = (
                            line[min_indent:]
                            if len(line) > min_indent
                            else line.lstrip()
                        )
                        result.append(f"{param_indent}{relative_content}")
                    else:
                        result.append("")

            result.append(f"{param_indent}{block[-1].strip()}")  # Closing ```
        else:
            # For unfenced blocks, wrap in ``` and preserve indentation
            result.append(f"{param_indent}```")

            # Find minimum indentation of non-empty lines
            non_empty_lines = [line for line in block if line.strip()]

            if non_empty_lines:
                min_indent = min(
                    len(line) - len(line.lstrip()) for line in non_empty_lines
                )

                for line in block:
                    if line.strip():
                        # Remove minimum indentation and add param_indent
                        relative_content = (
                            line[min_indent:]
                            if len(line) > min_indent
                            else line.lstrip()
                        )
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
    buffer: list[str], indent: str, line_length: int
) -> list[str]:
    """Format the Attributes section of a Google style docstring."""
    return _format_param_section(buffer, indent, line_length, "Attributes")


SECTION_HANDLERS: dict[str, Callable[[list[str], str, int], list[str]]] = {
    "Args": format_args_section,
    "Returns": format_returns_section,
    "Raises": format_raises_section,
    "Yields": format_yields_section,
    "Examples": format_examples_section,
    "Attributes": format_attributes_section,
}


def _extract_lists(paragraph: list[str]) -> list[list[str]]:
    """Extract lists from the buffer.

    This function splits a paragraph into alternating sections of text and list items.
    It returns a list of sublists where each sublist contains either text lines or list
    item lines (starting with '-').

    Args:
        paragraph (list[str]): The list of lines belonging to the paragraph.

    Returns:
        list[list[str]]: A list of sublists, alternating between text and list items.
    """
    if not paragraph:
        return []

    result: list[list[str]] = []
    current_group: list[str] = []

    def is_list_item(line: str) -> bool:
        return line.strip().startswith("-")

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


def reflow(docstring: str, line_length: int, indent: str) -> list[str]:
    """Reflow a Google style docstring to fit within the specified line length.

    This function takes a docstring, splits it into lines, and reflows each line to fit
    within the specified line length. It also handles indentation.

    Args:
        docstring (str): The docstring to reflow.
        line_length (int): The maximum line length.
        indent (str): The indentation to apply to each line.

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

    def add_section(name: str, lines: list[str]) -> None:
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
        sections.append((normalized_name, list(lines)))

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
        wrapped_summary = textwrap.wrap(
            summary_text,
            width=line_length - len(indent),
            break_long_words=False,
            drop_whitespace=True,
        )

        if wrapped_summary:
            # First line includes the opening triple quotes
            result.append(f'{indent}"""{wrapped_summary[0]}\n')
            # Subsequent summary lines
            for summary_line in wrapped_summary[1:]:
                result.append(f"{indent}{summary_line}\n")
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
                        wrapped = textwrap.wrap(
                            " ".join(section),
                            width=line_length - len(indent),
                            break_long_words=False,
                            drop_whitespace=True,
                        )
                        for wline in wrapped:
                            result.append(f"{indent}{wline}\n")

                result.append("\n")
                paragraph.clear()

    # Remove trailing empty line if no sections follow
    if result and result[-1].strip() == "":
        result.pop()

    # Step 3: Format sections
    for section_name, content in sections:
        formatter = SECTION_HANDLERS.get(section_name)
        if formatter:
            result.extend(formatter(content, indent, line_length))

    if result and len(result) == 1:
        result[0] = result[0].rstrip() + '"""\n'
    else:
        result.append(f'{indent}"""\n')
    return result
