from __future__ import annotations

import textwrap

import pydocformatter.cli.settings_check as settings_check


def display_width(text: str, *, tab_width: int) -> int:
    """Return the display width after expanding tabs to configured stops."""
    return len(text.expandtabs(tab_width))


def leading_width(text: str) -> int:
    """Return the tab-expanded width of leading whitespace."""
    return display_width(text[: len(text) - len(text.lstrip(" \t"))], tab_width=8)


def indent_unit(settings: settings_check.CheckSettings) -> str:
    """Return one generated indentation unit."""
    return "\t" if settings.indent_style == settings_check.IndentStyle.TAB else " " * settings.indent_width


def has_space_tab_content(text: str) -> bool:
    """Return whether text contains content other than spaces and tabs."""
    return bool(text.strip(" \t"))


def strip_indent(text: str, width: int) -> str:
    """Strip up to a tab-expanded indentation width from text."""
    stripped, _, _ = strip_indent_with_mapping(text, width)
    return stripped


def strip_indent_with_mapping(text: str, width: int) -> tuple[str, int, int]:
    """Strip indentation and return the raw/virtual mapping for text column zero."""
    index = 0
    column = 0
    while index < len(text) and text[index] in " \t" and column < width:
        column = ((column // 8) + 1) * 8 if text[index] == "\t" else column + 1
        index += 1
    virtual_prefix = max(column - width, 0)
    return " " * virtual_prefix + text[index:], index, virtual_prefix


def wrap_text(text: str, *, width: int, initial_indent: str = "", subsequent_indent: str = "") -> tuple[str, ...]:
    """Wrap normalized text using the shared modern-rule wrapping policy."""
    if width <= 0:
        return (f"{initial_indent}{text}",)
    wrapped = textwrap.wrap(
        text,
        width=width,
        initial_indent=initial_indent,
        subsequent_indent=subsequent_indent,
        break_long_words=False,
        break_on_hyphens=False,
    )
    return tuple(wrapped) or (initial_indent.rstrip(),)
