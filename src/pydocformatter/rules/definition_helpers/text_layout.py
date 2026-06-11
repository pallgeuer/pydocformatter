from __future__ import annotations

import textwrap


def display_width(text: str, *, tab_width: int) -> int:
    """Return the display width after expanding tabs to configured stops."""
    return len(text.expandtabs(tab_width))


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
