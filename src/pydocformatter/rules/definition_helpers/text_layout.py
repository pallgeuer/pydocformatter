"""Display-width and balanced wrapping helpers."""

# Future imports
from __future__ import annotations

# Standard library imports
import textwrap
import dataclasses

# First-party imports
from pydocformatter.cli import settings_check
from pydocformatter.rules.definition_helpers import ascii_whitespace, inline_markup


_BALANCED_WRAP_MAX_CANDIDATES = 250_000
_BALANCED_WRAP_MAX_WORDS = 10_000


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
    def from_line(cls, line_score: _LineScore, remainder: _WrapScore | None) -> _WrapScore:
        """Return the total score after prepending one line."""
        if remainder is None:
            return cls(line_count=1, url_only_count=line_score.url_only_count, slack_penalty=line_score.slack_penalty, break_score=line_score.break_score)
        return cls(
            line_count=1 + remainder.line_count,
            url_only_count=line_score.url_only_count + remainder.url_only_count,
            slack_penalty=line_score.slack_penalty + remainder.slack_penalty,
            break_score=line_score.break_score + remainder.break_score,
        )


class _UseGreedyWrapError(Exception):
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
    return display_width(text[: len(text) - len(text.lstrip(ascii_whitespace.SPACE_AND_TAB))], tab_width=8)


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
    return bool(text.strip(ascii_whitespace.SPACE_AND_TAB))


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
    while index < len(text) and text[index] in ascii_whitespace.SPACE_AND_TAB and column < width:
        column = ((column // 8) + 1) * 8 if text[index] == "\t" else column + 1
        index += 1
    virtual_prefix = max(column - width, 0)
    return " " * virtual_prefix + text[index:], index, virtual_prefix


def wrap_text(text: str, *, width: int, initial_indent: str = "", subsequent_indent: str = "", tab_width: int = 8, url_aware: bool = False) -> tuple[str, ...]:
    """Wrap normalized text using the shared modern-rule wrapping policy.

    Args:
        text (str): Whitespace-normalized prose to wrap.
        width (int): Maximum output line width in display columns.
        initial_indent (str): Prefix for the first output line.
        subsequent_indent (str): Prefix for continuation output lines.
        tab_width (int): Tab stop width used when measuring indentation.
        url_aware (bool): Whether destination-bearing tokens should use balanced line selection.

    Returns:
        tuple[str, ...]: Wrapped output lines including the requested indentation prefixes.
    """
    if width <= 0:
        return (f"{initial_indent}{text}",)
    scan = inline_markup.scan_text(text)
    return wrap_scanned_text(text, scan, width=width, initial_indent=initial_indent, subsequent_indent=subsequent_indent, tab_width=tab_width, url_aware=url_aware)


def wrap_scanned_text(
    text: str, scan: inline_markup.InlineScanResult, *, width: int, initial_indent: str = "", subsequent_indent: str = "", tab_width: int = 8, url_aware: bool = False
) -> tuple[str, ...]:
    """Wrap normalized text using an existing inline-markup scan.

    Args:
        text (str): Whitespace-normalized prose represented by `scan`.
        scan (inline_markup.InlineScanResult): Existing tokenization and ambiguity evidence for `text`.
        width (int): Maximum output line width in display columns.
        initial_indent (str): Prefix for the first output line.
        subsequent_indent (str): Prefix for continuation output lines.
        tab_width (int): Tab stop width used when measuring indentation.
        url_aware (bool): Whether destination-bearing tokens should use balanced line selection.

    Returns:
        tuple[str, ...]: Wrapped output lines including the requested indentation prefixes.
    """
    if width <= 0:
        return (f"{initial_indent}{text}",)
    if not any(token.kind is not None or (url_aware and token.url_like) for token in scan.tokens):
        wrapped = textwrap.wrap(text, width=width, initial_indent=initial_indent, subsequent_indent=subsequent_indent, break_long_words=False, break_on_hyphens=False)
        return tuple(wrapped) or (initial_indent.rstrip(),)
    return wrap_inline_tokens(scan.tokens, width=width, initial_indent=initial_indent, subsequent_indent=subsequent_indent, tab_width=tab_width, url_aware=url_aware)


def wrap_inline_tokens(
    tokens: tuple[inline_markup.InlineToken, ...],
    *,
    width: int,
    initial_indent: str = "",
    subsequent_indent: str = "",
    tab_width: int,
    initial_width: int | None = None,
    subsequent_width: int | None = None,
    final_suffix_width: int = 0,
    url_aware: bool = False,
) -> tuple[str, ...]:
    """Wrap indivisible inline tokens with shared greedy or balanced layout.

    Args:
        tokens (tuple[inline_markup.InlineToken, ...]): Indivisible source-aware tokens to group into lines.
        width (int): Fallback maximum line width in display columns.
        initial_indent (str): Prefix for the first output line.
        subsequent_indent (str): Prefix for continuation output lines.
        tab_width (int): Tab stop width used for source display measurements.
        initial_width (int | None): Optional first-line budget including `initial_indent`.
        subsequent_width (int | None): Optional continuation budget including `subsequent_indent`.
        final_suffix_width (int): Display width reserved on the final output line.
        url_aware (bool): Whether destination-bearing tokens should use balanced line selection.

    Returns:
        tuple[str, ...]: Wrapped lines with requested prefixes.
    """
    if not tokens:
        return (initial_indent.rstrip(),)
    rendered = tuple(token.value for token in tokens)
    if width <= 0 and initial_width is None and subsequent_width is None:
        return (f"{initial_indent}{' '.join(rendered)}",)
    spans = token_spans(
        tokens,
        width_words=tuple(token.source for token in tokens),
        width=width,
        initial_indent=initial_indent,
        subsequent_indent=subsequent_indent,
        tab_width=tab_width,
        initial_width=initial_width,
        subsequent_width=subsequent_width,
        final_suffix_width=final_suffix_width,
        url_aware=url_aware,
    )
    return tuple(_render_words(rendered[span.start : span.end], indent=initial_indent if index == 0 else subsequent_indent) for index, span in enumerate(spans))


def token_spans(
    tokens: tuple[inline_markup.InlineToken, ...],
    *,
    width_words: tuple[str, ...],
    width: int,
    initial_indent: str = "",
    subsequent_indent: str = "",
    tab_width: int,
    initial_width: int | None = None,
    subsequent_width: int | None = None,
    final_suffix_width: int = 0,
    url_aware: bool = False,
) -> tuple[WordSpan, ...]:
    """Return layout spans for indivisible source-aware tokens.

    Args:
        tokens (tuple[inline_markup.InlineToken, ...]): Tokens carrying destination-bearing classification.
        width_words (tuple[str, ...]): Source spellings used for display-width calculations.
        width (int): Fallback maximum line width.
        initial_indent (str): First-line prefix.
        subsequent_indent (str): Continuation prefix.
        tab_width (int): Tab stop width.
        initial_width (int | None): Optional first-line budget.
        subsequent_width (int | None): Optional continuation budget.
        final_suffix_width (int): Width reserved on the final line.
        url_aware (bool): Whether destination-bearing tokens activate balanced selection.

    Returns:
        tuple[WordSpan, ...]: Half-open token spans for rendered lines.

    Raises:
        ValueError: If tokens and source width spellings are not aligned.
    """
    if len(tokens) != len(width_words):
        raise ValueError("tokens and width_words must have the same length")
    values = tuple(token.value for token in tokens)
    if url_aware and any(token.url_like for token in tokens):
        return balanced_word_spans(
            values,
            width_words=width_words,
            width=width,
            initial_indent=initial_indent,
            subsequent_indent=subsequent_indent,
            tab_width=tab_width,
            initial_width=initial_width,
            subsequent_width=subsequent_width,
            final_suffix_width=final_suffix_width,
            url_words=tuple(token.url_like for token in tokens),
        )
    return _greedy_word_spans(
        values,
        width_words=width_words,
        width=width,
        initial_indent=initial_indent,
        subsequent_indent=subsequent_indent,
        tab_width=tab_width,
        initial_width=initial_width,
        subsequent_width=subsequent_width,
        final_suffix_width=final_suffix_width,
    )


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
    url_words: tuple[bool, ...] | None = None,
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
        url_words (tuple[bool, ...] | None): Optional destination-bearing classification aligned with `words`.

    Returns:
        tuple[WordSpan, ...]: Half-open word-index spans for each output line.

    Raises:
        ValueError: If `words` and `width_words` are not aligned.
    """
    if len(width_words) != len(words):
        raise ValueError("words and width_words must have the same length")
    if url_words is not None and len(url_words) != len(words):
        raise ValueError("words and url_words must have the same length")
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

    url_words = tuple(inline_markup.is_bare_url(word) for word in words) if url_words is None else url_words
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
                raise _UseGreedyWrapError
            if single_word or (limit > 0 and column <= limit):
                span = WordSpan(start, end)
                slack = max(limit - column, 0)
                candidates.append((span, _LineScore(url_only_count=int(single_word and url_words[start]), slack_penalty=0 if final_line else slack * slack, break_score=-end)))
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
        if chosen_score is None or chosen_end is None:
            raise _UseGreedyWrapError
        return chosen_score, chosen_end

    try:
        suffix_scores: list[_WrapScore | None] = [None] * (len(words) + 1)
        suffix_ends: list[int | None] = [None] * len(words)
        for start in range(len(words) - 1, -1, -1):
            suffix_scores[start], suffix_ends[start] = choose_best(start, first_line=False, suffix_scores=suffix_scores)
        _, first_end = choose_best(0, first_line=True, suffix_scores=suffix_scores)
    except _UseGreedyWrapError:
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
        if end is None:
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
