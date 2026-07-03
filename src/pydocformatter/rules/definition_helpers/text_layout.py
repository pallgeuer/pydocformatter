"""Display-width and balanced wrapping helpers."""

from __future__ import annotations

import dataclasses
import re
import textwrap

import pydocformatter.cli.settings_check as settings_check

_BALANCED_WRAP_MAX_CANDIDATES = 250_000
_BALANCED_WRAP_MAX_WORDS = 10_000
_URL_TOKEN_RE = re.compile(r"(?i)^(?:[a-z][a-z0-9+.-]*://|www\.)\S+$")
_URL_TOKEN_LEADING_PUNCTUATION = "([<{\"'"
_URL_TOKEN_TRAILING_PUNCTUATION = ".,;:!?)]}>\"'"


@dataclasses.dataclass(frozen=True)
class WordSpan:
    """Half-open word span in wrapped output.

    Attributes:
        start (int): Inclusive index of the first word in the span.
        end (int): Exclusive index immediately after the last word in the span.
    """

    start: int
    end: int


@dataclasses.dataclass(frozen=True)
class _LineScore:
    """Score contribution for one candidate wrapped line."""

    url_only_count: int
    slack_penalty: int
    break_score: int


@dataclasses.dataclass(frozen=True, order=True)
class _WrapScore:
    """Lexicographic score for a complete wrapped suffix."""

    line_count: int
    url_only_count: int
    slack_penalty: int
    break_score: int

    @classmethod
    def from_line(cls, line_score: _LineScore, remainder: "_WrapScore | None") -> "_WrapScore":
        """Return the total score after prepending one line."""
        if remainder is None:
            return cls(
                line_count=1,
                url_only_count=line_score.url_only_count,
                slack_penalty=line_score.slack_penalty,
                break_score=line_score.break_score,
            )
        return cls(
            line_count=1 + remainder.line_count,
            url_only_count=line_score.url_only_count + remainder.url_only_count,
            slack_penalty=line_score.slack_penalty + remainder.slack_penalty,
            break_score=line_score.break_score + remainder.break_score,
        )


class _UseGreedyWrap(Exception):
    """Signal that balanced wrapping exceeded its bounded search budget."""


def display_width(text: str, *, tab_width: int) -> int:
    """Return the display width after expanding tabs to configured stops.

    Args:
        text (str): Text whose rendered width should be measured.
        tab_width (int): Tab stop width used by wrapping and indentation calculations.

    Returns:
        int: Number of display columns occupied by the text.
    """
    return len(text.expandtabs(tab_width))


def leading_width(text: str) -> int:
    """Return the tab-expanded width of leading whitespace.

    Args:
        text (str): Text whose leading spaces and tabs should be measured.

    Returns:
        int: Display columns occupied by the leading whitespace prefix, using Python's default tab expansion.
    """
    return display_width(text[: len(text) - len(text.lstrip(" \t"))], tab_width=8)


def indent_unit(settings: settings_check.CheckSettings) -> str:
    """Return one generated indentation unit.

    Args:
        settings (settings_check.CheckSettings): Resolved indentation style and width settings.

    Returns:
        str: One tab or the configured number of spaces for generated indentation.
    """
    return "\t" if settings.indent_style == settings_check.IndentStyle.TAB else " " * settings.indent_width


def has_space_tab_content(text: str) -> bool:
    """Return whether text contains content other than spaces and tabs.

    Args:
        text (str): Text to inspect for semantic content.

    Returns:
        bool: Whether any character remains after stripping spaces and tabs.
    """
    return bool(text.strip(" \t"))


def strip_indent(text: str, width: int) -> str:
    """Strip up to a tab-expanded indentation width from text.

    Args:
        text (str): Raw line text whose indentation should be removed.
        width (int): Display-width indentation budget to remove.

    Returns:
        str: Text after removing up to `width` display columns of indentation.
    """
    stripped, _, _ = strip_indent_with_mapping(text, width)
    return stripped


def strip_indent_with_mapping(text: str, width: int) -> tuple[str, int, int]:
    """Strip indentation and return the raw/virtual mapping for text column zero.

    Args:
        text (str): Raw line text whose indentation should be removed.
        width (int): Display-width indentation budget to remove.

    Returns:
        tuple[str, int, int]: Stripped text, raw source index where stripped text begins, and virtual spaces retained
            for a partially consumed tab.
    """
    index = 0
    column = 0
    while index < len(text) and text[index] in " \t" and column < width:
        column = ((column // 8) + 1) * 8 if text[index] == "\t" else column + 1
        index += 1
    virtual_prefix = max(column - width, 0)
    return " " * virtual_prefix + text[index:], index, virtual_prefix


def is_url_token(text: str) -> bool:
    """Return whether text is a URL-like wrapping token.

    Args:
        text (str): Wrapping token to classify after trimming surrounding punctuation.

    Returns:
        bool: Whether the token should be kept intact by URL-aware wrapping.
    """
    candidate = text.lstrip(_URL_TOKEN_LEADING_PUNCTUATION).rstrip(_URL_TOKEN_TRAILING_PUNCTUATION)
    return _URL_TOKEN_RE.match(candidate) is not None


def wrap_text(text: str, *, width: int, initial_indent: str = "", subsequent_indent: str = "", tab_width: int = 8, url_aware: bool = False) -> tuple[str, ...]:
    """Wrap normalized text using the shared modern-rule wrapping policy.

    Args:
        text (str): Whitespace-normalized prose to wrap.
        width (int): Maximum output line width in display columns.
        initial_indent (str): Prefix for the first output line.
        subsequent_indent (str): Prefix for continuation output lines.
        tab_width (int): Tab stop width used when measuring indentation.
        url_aware (bool): Whether URL tokens should remain intact and line breaks should be balanced around them.

    Returns:
        tuple[str, ...]: Wrapped output lines including the requested indentation prefixes.
    """
    if width <= 0:
        return (f"{initial_indent}{text}",)
    words = tuple(text.split())
    if url_aware and any(is_url_token(word) for word in words):
        spans = balanced_word_spans(
            words,
            width_words=words,
            width=width,
            initial_indent=initial_indent,
            subsequent_indent=subsequent_indent,
            tab_width=tab_width,
        )
        return tuple(_render_words(words[span.start : span.end], indent=initial_indent if index == 0 else subsequent_indent) for index, span in enumerate(spans))
    wrapped = textwrap.wrap(
        text,
        width=width,
        initial_indent=initial_indent,
        subsequent_indent=subsequent_indent,
        break_long_words=False,
        break_on_hyphens=False,
    )
    return tuple(wrapped) or (initial_indent.rstrip(),)


def balanced_word_spans(
    words: tuple[str, ...],
    *,
    width_words: tuple[str, ...],
    width: int,
    initial_indent: str = "",
    subsequent_indent: str = "",
    tab_width: int,
    initial_width: int | None = None,
    subsequent_width: int | None = None,
    final_suffix_width: int = 0,
) -> tuple[WordSpan, ...]:
    """Return URL-aware balanced word spans without splitting tokens.

    Args:
        words (tuple[str, ...]): Original tokens to group into output lines.
        width_words (tuple[str, ...]): Tokens used for width scoring, aligned one-to-one with `words`.
        width (int): Maximum line width in display columns.
        initial_indent (str): Prefix measured for the first output line when explicit widths are not supplied.
        subsequent_indent (str): Prefix measured for continuation lines when explicit widths are not supplied.
        tab_width (int): Tab stop width used when measuring indentation.
        initial_width (int | None): Optional precomputed content width for the first output line.
        subsequent_width (int | None): Optional precomputed content width for continuation lines.
        final_suffix_width (int): Display width reserved on the final line for suffix text.

    Returns:
        tuple[WordSpan, ...]: Half-open word-index spans for each output line.

    Raises:
        ValueError: If `words` and `width_words` are not aligned.
    """
    if len(width_words) != len(words):
        raise ValueError("words and width_words must have the same length")
    if not words:
        return (WordSpan(0, 0),)
    if width <= 0 and initial_width is None and subsequent_width is None:
        return tuple(WordSpan(index, index + 1) for index in range(len(words)))
    if len(words) > _BALANCED_WRAP_MAX_WORDS:
        return _greedy_word_spans(
            words,
            width_words=width_words,
            width=width,
            initial_indent=initial_indent,
            subsequent_indent=subsequent_indent,
            tab_width=tab_width,
            initial_width=initial_width,
            subsequent_width=subsequent_width,
            final_suffix_width=final_suffix_width,
        )

    url_words = tuple(is_url_token(word) for word in words)
    candidate_count = 0

    def line_limit(*, first_line: bool, final_line: bool) -> int:
        limit = (width if initial_width is None else initial_width) if first_line else (width if subsequent_width is None else subsequent_width)
        if final_line:
            limit -= final_suffix_width
        return limit

    def candidate_lines(start: int, *, first_line: bool) -> tuple[tuple[WordSpan, _LineScore], ...]:
        nonlocal candidate_count
        candidates: list[tuple[WordSpan, _LineScore]] = []
        indent = initial_indent if first_line else subsequent_indent
        column = display_width(indent, tab_width=tab_width)
        for end in range(start + 1, len(words) + 1):
            if end > start + 1:
                column += 1
            column = advance_display_column(column, width_words[end - 1], tab_width=tab_width)
            final_line = end == len(words)
            limit = line_limit(first_line=first_line, final_line=final_line)
            single_word = end == start + 1
            candidate_count += 1
            if candidate_count > _BALANCED_WRAP_MAX_CANDIDATES:
                raise _UseGreedyWrap
            if single_word or (limit > 0 and column <= limit):
                span = WordSpan(start, end)
                slack = max(limit - column, 0)
                candidates.append(
                    (
                        span,
                        _LineScore(
                            url_only_count=int(single_word and url_words[start]),
                            slack_penalty=0 if final_line else slack * slack,
                            break_score=-end,
                        ),
                    )
                )
            elif final_suffix_width >= 0:
                # Once a prefix overflows, longer prefixes cannot fit under nonnegative suffix reservation.
                break
        return tuple(candidates)

    def choose_best(start: int, *, first_line: bool, suffix_scores: list[_WrapScore | None]) -> tuple[_WrapScore, int]:
        chosen_score: _WrapScore | None = None
        chosen_end: int | None = None
        for span, line_score in candidate_lines(start, first_line=first_line):
            remainder_score = None if span.end == len(words) else suffix_scores[span.end]
            if remainder_score is None and span.end != len(words):
                continue
            score = _WrapScore.from_line(line_score, remainder_score)
            if chosen_score is None or score < chosen_score:
                chosen_score = score
                chosen_end = span.end
        assert chosen_score is not None and chosen_end is not None
        return chosen_score, chosen_end

    try:
        suffix_scores: list[_WrapScore | None] = [None] * (len(words) + 1)
        suffix_ends: list[int | None] = [None] * len(words)
        for start in range(len(words) - 1, -1, -1):
            suffix_scores[start], suffix_ends[start] = choose_best(start, first_line=False, suffix_scores=suffix_scores)
        _, first_end = choose_best(0, first_line=True, suffix_scores=suffix_scores)
    except _UseGreedyWrap:
        return _greedy_word_spans(
            words,
            width_words=width_words,
            width=width,
            initial_indent=initial_indent,
            subsequent_indent=subsequent_indent,
            tab_width=tab_width,
            initial_width=initial_width,
            subsequent_width=subsequent_width,
            final_suffix_width=final_suffix_width,
        )

    spans = [WordSpan(0, first_end)]
    start = first_end
    while start < len(words):
        end = suffix_ends[start]
        assert end is not None
        spans.append(WordSpan(start, end))
        start = end
    return tuple(spans)


def _greedy_word_spans(
    words: tuple[str, ...],
    *,
    width_words: tuple[str, ...],
    width: int,
    initial_indent: str,
    subsequent_indent: str,
    tab_width: int,
    initial_width: int | None,
    subsequent_width: int | None,
    final_suffix_width: int,
) -> tuple[WordSpan, ...]:
    """Return greedy word spans as a bounded fallback for very large inputs."""
    spans: list[WordSpan] = []
    start = 0
    first_line = True
    while start < len(words):
        indent = initial_indent if first_line else subsequent_indent
        column = display_width(indent, tab_width=tab_width)
        chosen_end = start + 1
        for end in range(start + 1, len(words) + 1):
            if end > start + 1:
                column += 1
            column = advance_display_column(column, width_words[end - 1], tab_width=tab_width)
            final_line = end == len(words)
            limit = (width if initial_width is None else initial_width) if first_line else (width if subsequent_width is None else subsequent_width)
            if final_line:
                limit -= final_suffix_width
            single_word = end == start + 1
            if single_word or (limit > 0 and column <= limit):
                chosen_end = end
            elif final_suffix_width >= 0:
                # Once a prefix overflows, longer prefixes cannot fit under nonnegative suffix reservation.
                break
        spans.append(WordSpan(start, chosen_end))
        start = chosen_end
        first_line = False
    return tuple(spans)


def advance_display_column(column: int, text: str, *, tab_width: int) -> int:
    """Return the display column after rendering text from an existing column.

    Args:
        column (int): Starting display column.
        text (str): Text to render from the starting column.
        tab_width (int): Tab stop width used when advancing over tabs.

    Returns:
        int: Display column immediately after the rendered text.
    """
    for char in text:
        if char == "\t":
            column = ((column // tab_width) + 1) * tab_width if tab_width > 0 else column
        else:
            column += 1
    return column


def _render_words(words: tuple[str, ...], *, indent: str) -> str:
    """Render a wrapped line from normalized words."""
    return indent.rstrip() if not words else f"{indent}{' '.join(words)}"
