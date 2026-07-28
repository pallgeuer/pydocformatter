"""Conservative inline-markup and hard-break analysis.

Attributes:
    FENCE_RE (re.Pattern[str]): Line-leading Markdown fence opener or closer with optional trailing text.
"""

# Future imports
from __future__ import annotations

# Standard library imports
import re
import enum
import dataclasses
from collections.abc import Sequence
from typing import Protocol

# First-party imports
from pydocformatter.rules.definition_helpers import ascii_whitespace, unicode_safety


_BARE_URL_RE = re.compile(r"(?i)^(?:[a-z][a-z0-9+.-]*://|www\.)\S+$")
_AUTOLINK_URI_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]{1,31}:[^\x00-\x20<>]*$")
_AUTOLINK_EMAIL_RE = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$")
_ROLE_NAME_RE = re.compile(r"[A-Za-z0-9]+(?:[-_+:.][A-Za-z0-9]+)*")
_PLAIN_SCAN_SPECIAL_RE = re.compile(f"[{re.escape('[<`|' + ''.join(chr(code_point) for code_point in sorted(unicode_safety.EVERYWHERE_CODE_POINTS | unicode_safety.INDENTATION_ONLY_CODE_POINTS)))}]")
FENCE_RE = re.compile(r"^[ \t]*(?P<fence>`{3,}|~{3,})(?P<info>.*)$")
_URL_LEADING_PUNCTUATION = "([<{\"'"
_URL_TRAILING_PUNCTUATION = ".,;:!?)]}>\"'"
_MARKDOWN_DESTINATION_MAX_DEPTH = 3


class SourceFragment(Protocol):
    """Evaluated character and its exact source spelling."""

    @property
    def value(self) -> str:
        """Evaluated character represented by the fragment."""
        ...

    @property
    def source(self) -> str:
        """Exact source spelling that produces the character."""
        ...


class InlineMarkupKind(enum.Enum):
    """Recognized inline construct families.

    Attributes:
        MARKDOWN_CODE: Same-line Markdown backtick code span.
        MARKDOWN_LINK: Inline or full/collapsed reference-style Markdown link or image.
        AUTOLINK: CommonMark-style URI or email autolink.
        REST_INTERPRETED: reStructuredText interpreted text or phrase reference.
        REST_ROLE: Prefix- or suffix-role reStructuredText interpreted text.
        REST_LITERAL: Double-backtick reStructuredText inline literal.
        REST_SUBSTITUTION: reStructuredText substitution reference.
        MIXED: One punctuation envelope containing multiple recognized families.
    """

    MARKDOWN_CODE = "markdown-code"
    MARKDOWN_LINK = "markdown-link"
    AUTOLINK = "autolink"
    REST_INTERPRETED = "rest-interpreted"
    REST_ROLE = "rest-role"
    REST_LITERAL = "rest-literal"
    REST_SUBSTITUTION = "rest-substitution"
    MIXED = "mixed"


class InlineRewriteBarrierKind(enum.Enum):
    """Reasons that prevent safe canonical inline rewriting.

    Attributes:
        SUSPICIOUS_UNICODE: Explicit suspicious Unicode policy evidence.
        INCOMPLETE_MARKDOWN_IMAGE_LABEL: Unterminated Markdown image label.
        INCOMPLETE_MARKDOWN_INLINE_DESTINATION: Unterminated Markdown inline destination.
        MALFORMED_MARKDOWN_ANGLE_DESTINATION: Invalid Markdown angle-bracket destination.
        INCOMPLETE_MARKDOWN_ANGLE_DESTINATION: Unterminated Markdown angle-bracket destination.
        MARKDOWN_DESTINATION_NESTING_EXCEEDED: Markdown destination nesting beyond the supported depth.
        MALFORMED_MARKDOWN_INLINE_DESTINATION: Invalid Markdown inline destination.
        UNSUPPORTED_MARKDOWN_LINK_TITLE: Markdown link title using an unsupported delimiter.
        MALFORMED_MARKDOWN_LINK_TITLE: Invalid Markdown link title.
        INCOMPLETE_MARKDOWN_LINK_TITLE: Unterminated Markdown link title.
        INCOMPLETE_MARKDOWN_INLINE_LINK: Unterminated Markdown inline link.
        INCOMPLETE_MARKDOWN_REFERENCE_LABEL: Unterminated Markdown reference label.
        INCOMPLETE_AUTOLINK: Unterminated URI or email autolink.
        INCOMPLETE_REST_PREFIX_ROLE: Unterminated reStructuredText prefix role.
        MALFORMED_REST_PREFIX_ROLE: Invalid reStructuredText prefix role.
        UNCLOSED_INLINE_BACKTICK_SPAN: Inline backtick span without a closer.
        EMPTY_INLINE_BACKTICK_SPAN: Inline backtick span without content.
        INCOMPLETE_REST_SUFFIX_ROLE: Unterminated reStructuredText suffix role.
    """

    SUSPICIOUS_UNICODE = "suspicious-unicode"
    INCOMPLETE_MARKDOWN_IMAGE_LABEL = "incomplete Markdown image label"
    INCOMPLETE_MARKDOWN_INLINE_DESTINATION = "incomplete Markdown inline destination"
    MALFORMED_MARKDOWN_ANGLE_DESTINATION = "malformed Markdown angle destination"
    INCOMPLETE_MARKDOWN_ANGLE_DESTINATION = "incomplete Markdown angle destination"
    MARKDOWN_DESTINATION_NESTING_EXCEEDED = "Markdown destination nesting exceeds the supported depth"
    MALFORMED_MARKDOWN_INLINE_DESTINATION = "malformed Markdown inline destination"
    UNSUPPORTED_MARKDOWN_LINK_TITLE = "unsupported Markdown link title"
    MALFORMED_MARKDOWN_LINK_TITLE = "malformed Markdown link title"
    INCOMPLETE_MARKDOWN_LINK_TITLE = "incomplete Markdown link title"
    INCOMPLETE_MARKDOWN_INLINE_LINK = "incomplete Markdown inline link"
    INCOMPLETE_MARKDOWN_REFERENCE_LABEL = "incomplete Markdown reference label"
    INCOMPLETE_AUTOLINK = "incomplete autolink"
    INCOMPLETE_REST_PREFIX_ROLE = "incomplete reStructuredText prefix role"
    MALFORMED_REST_PREFIX_ROLE = "malformed reStructuredText prefix role"
    UNCLOSED_INLINE_BACKTICK_SPAN = "unclosed inline backtick span"
    EMPTY_INLINE_BACKTICK_SPAN = "empty inline backtick span"
    INCOMPLETE_REST_SUFFIX_ROLE = "incomplete reStructuredText suffix role"


class HardBreakKind(enum.Enum):
    """Supported explicit line-boundary markers.

    Attributes:
        SPACES: A terminal run of at least two evaluated ASCII spaces.
        BACKSLASH: An odd-length terminal run of evaluated backslashes.
    """

    SPACES = "spaces"
    BACKSLASH = "backslash"


@dataclasses.dataclass(frozen=True)
class InlineToken:
    """One indivisible wrapping token with source spelling.

    Attributes:
        value (str): Evaluated token text used for syntax recognition.
        source (str): Exact source spelling used for output and width calculation.
        kind (InlineMarkupKind | None): Recognized construct family, or None for ordinary prose.
        url_like (bool): Whether URL-aware balancing should treat this token as destination-bearing.
    """

    value: str
    source: str
    kind: InlineMarkupKind | None = None
    url_like: bool = False


@dataclasses.dataclass(frozen=True)
class InlineRewriteBarrier:
    """Evidence that a source span prevents safe canonical rewriting.

    Attributes:
        start (int): Inclusive evaluated-text offset where evidence begins.
        end (int): Exclusive evaluated-text offset covered by the evidence.
        kind (InlineRewriteBarrierKind): Typed reason for blocking canonical rewriting.
        line_index (int): Zero-based input-line index containing the evidence.
    """

    start: int
    end: int
    kind: InlineRewriteBarrierKind
    line_index: int = 0


@dataclasses.dataclass(frozen=True)
class InlineScanResult:
    """Wrapping tokens and rewrite barriers for one logical line.

    Attributes:
        tokens (tuple[InlineToken, ...]): Indivisible source-aware tokens in source order.
        barriers (tuple[InlineRewriteBarrier, ...]): Evidence that prevents a safe canonical rewrite.
    """

    tokens: tuple[InlineToken, ...]
    barriers: tuple[InlineRewriteBarrier, ...] = ()

    @property
    def rewrite_blocked(self) -> bool:
        """Whether any evidence prevents canonical rewriting.

        Returns:
            bool: Whether canonical rewriting is blocked.
        """
        return bool(self.barriers)


@dataclasses.dataclass(frozen=True)
class HardBreak:
    """Exact terminal source suffix that preserves a semantic line break.

    Attributes:
        kind (HardBreakKind): Space- or backslash-based boundary syntax.
        start (int): Evaluated line offset where the preserved suffix begins.
        value (str): Evaluated suffix text.
        source (str): Exact source spelling of the suffix.
    """

    kind: HardBreakKind
    start: int
    value: str
    source: str


@dataclasses.dataclass(frozen=True)
class InlineLayoutLine:
    """One logical line prepared for shared inline layout scanning.

    Attributes:
        fragments (tuple[SourceFragment, ...]): Source-aware characters from semantic content through the physical line
            suffix.
        content_end (int): Exclusive fragment offset after content eligible to join with the next logical line.
        has_following_newline (bool): Whether the logical or physical line has a following newline separator.
    """

    fragments: tuple[SourceFragment, ...]
    content_end: int
    has_following_newline: bool


@dataclasses.dataclass(frozen=True)
class InlineLayoutSegment:
    """One scanned layout segment ending at an optional semantic hard break.

    Attributes:
        text (str): Whitespace-normalized source-identical text used by ordinary wrapping.
        scan (InlineScanResult): Indivisible tokens and rewrite barriers accumulated across joined logical lines.
        hard_break (HardBreak | None): Exact suffix that terminates the segment.
    """

    text: str
    scan: InlineScanResult
    hard_break: HardBreak | None


@dataclasses.dataclass(frozen=True)
class InlineLayoutScanResult:
    """Shared layout segments and aggregate rewrite barriers.

    Attributes:
        segments (tuple[InlineLayoutSegment, ...]): Ordered segments split at semantic hard breaks.
        barriers (tuple[InlineRewriteBarrier, ...]): Stable unique rewrite barriers across every segment.
    """

    segments: tuple[InlineLayoutSegment, ...]
    barriers: tuple[InlineRewriteBarrier, ...]

    @property
    def rewrite_blocked(self) -> bool:
        """Whether any barrier prevents a safe canonical rewrite.

        Returns:
            bool: Whether at least one segment contains a rewrite barrier.
        """
        return bool(self.barriers)


@dataclasses.dataclass(frozen=True)
class _Construct:
    """Recognized evaluated-text span before punctuation-envelope expansion."""

    start: int
    end: int
    kind: InlineMarkupKind
    url_like: bool = False


@dataclasses.dataclass(frozen=True)
class _ParseResult:
    """One scanner decision at a candidate delimiter."""

    construct: _Construct | None = None
    barrier: InlineRewriteBarrier | None = None


@dataclasses.dataclass(frozen=True)
class _DelimiterIndex:
    """Linear-time delimiter matches and successors for one logical line."""

    backtick_closers: dict[int, int]
    bracket_closers: dict[int, int]
    next_angle_open: tuple[int, ...]
    next_angle_close: tuple[int, ...]
    escaped: tuple[bool, ...]


@dataclasses.dataclass
class _Envelope:
    """One whitespace-delimited envelope around recognized constructs."""

    start: int
    end: int
    kinds: set[InlineMarkupKind]
    url_like: bool


def scan_text(text: str) -> InlineScanResult:
    """Scan one evaluated/source-identical logical line.

    Args:
        text (str): Same-line prose to split into indivisible wrapping tokens.

    Returns:
        InlineScanResult: Recognized tokens and conservative rewrite barriers.
    """
    if _PLAIN_SCAN_SPECIAL_RE.search(text) is None:
        return InlineScanResult(tokens=tuple(InlineToken(value=word, source=word, url_like=is_bare_url(word)) for word in text.split()))
    return scan_fragments(tuple(_TextFragment(value=char, source=char) for char in text))


def scan_fragments(fragments: Sequence[SourceFragment]) -> InlineScanResult:
    """Scan source-aware evaluated characters from one logical line.

    Args:
        fragments (Sequence[SourceFragment]): One-character evaluated fragments aligned with exact source spellings.

    Returns:
        InlineScanResult: Indivisible tokens and evidence-gated rewrite barriers.

    Raises:
        ValueError: If a fragment does not represent exactly one evaluated character.
    """
    for fragment in fragments:
        if len(fragment.value) != 1:
            raise ValueError("Inline-markup fragments must each represent one evaluated character")
    text = "".join(fragment.value for fragment in fragments)
    unicode_barriers = tuple(
        InlineRewriteBarrier(start=occurrence.offset, end=occurrence.offset + 1, kind=InlineRewriteBarrierKind.SUSPICIOUS_UNICODE) for occurrence in unicode_safety.suspicious_unicode_occurrences(text)
    )
    if not any(char in text for char in "[<`|"):
        return InlineScanResult(tokens=_plain_tokens(fragments, text=text), barriers=unicode_barriers)
    if FENCE_RE.fullmatch(text) is not None:
        return InlineScanResult(tokens=_tokens_for_constructs(fragments, text=text, constructs=[]), barriers=unicode_barriers)
    delimiter_index = _delimiter_index(text)
    first_nonwhitespace = len(text) - len(text.lstrip())
    constructs: list[_Construct] = []
    barriers: list[InlineRewriteBarrier] = list(unicode_barriers)
    index = 0
    while index < len(text):
        if text[index] == "`" and not delimiter_index.escaped[index]:
            run_length = _delimiter_run_length(text, index, "`")
            if run_length >= 3 and index == first_nonwhitespace and (index + run_length == len(text) or text[index + run_length].isspace()) and index not in delimiter_index.backtick_closers:
                index += run_length
                continue
        result = _parse_at(text, index, delimiter_index=delimiter_index)
        if result.construct is not None:
            constructs.append(result.construct)
            index = result.construct.end
            continue
        if result.barrier is not None:
            barriers.append(result.barrier)
            index = result.barrier.end
            continue
        index += 1
    return InlineScanResult(tokens=_tokens_for_constructs(fragments, text=text, constructs=constructs), barriers=tuple(_deduplicate_barriers(barriers)))


def terminal_hard_break(fragments: Sequence[SourceFragment], *, has_following_newline: bool) -> HardBreak | None:
    """Return a recognized evaluated line-boundary suffix.

    Args:
        fragments (Sequence[SourceFragment]): Complete evaluated logical line with exact source spellings.
        has_following_newline (bool): Whether the evaluated or physical line has a following newline separator.

    Returns:
        HardBreak | None: Exact terminal suffix, or None when the line has no supported hard break.
    """
    if not has_following_newline:
        return None
    value = "".join(fragment.value for fragment in fragments)
    if not value.strip():
        return None
    space_start = len(value.rstrip(" "))
    if len(value) - space_start >= 2:
        return HardBreak(kind=HardBreakKind.SPACES, start=space_start, value=value[space_start:], source="".join(fragment.source for fragment in fragments[space_start:]))
    backslash_start = len(value.rstrip("\\"))
    if (len(value) - backslash_start) % 2 == 1:
        return HardBreak(kind=HardBreakKind.BACKSLASH, start=backslash_start, value=value[backslash_start:], source="".join(fragment.source for fragment in fragments[backslash_start:]))
    return None


def terminal_text_hard_break(text: str, *, has_following_newline: bool) -> HardBreak | None:
    """Return a recognized hard-break suffix for source-identical text.

    Args:
        text (str): Complete evaluated/source-identical logical line.
        has_following_newline (bool): Whether the line has a following physical newline.

    Returns:
        HardBreak | None: Exact terminal suffix, or None when no supported boundary is present.
    """
    return terminal_hard_break(tuple(_TextFragment(value=char, source=char) for char in text), has_following_newline=has_following_newline)


def layout_line_for_text(text: str, *, has_following_newline: bool) -> InlineLayoutLine:
    """Return a source-identical layout line with outer whitespace normalized.

    Args:
        text (str): Plain logical-line text to scan.
        has_following_newline (bool): Whether the physical line has a following newline separator.

    Returns:
        InlineLayoutLine: Source-identical fragments and the trimmed semantic-content boundary.
    """
    text = _strip_layout_separators(text, left=True, right=False)
    fragments = tuple(_TextFragment(value=char, source=char) for char in text)
    return InlineLayoutLine(fragments=fragments, content_end=len(_strip_layout_separators(text, left=False, right=True)), has_following_newline=has_following_newline)


def scan_layout_lines(lines: Sequence[InlineLayoutLine]) -> InlineLayoutScanResult:
    """Scan logical lines into token segments separated by semantic hard breaks.

    Args:
        lines (Sequence[InlineLayoutLine]): Ordered logical lines with semantic content boundaries.

    Returns:
        InlineLayoutScanResult: Joined token segments and aggregate rewrite barriers.

    Raises:
        ValueError: If a content boundary is outside its fragment sequence.
    """
    segments: list[InlineLayoutSegment] = []
    tokens: list[InlineToken] = []
    text_parts: list[str] = []
    segment_barriers: list[InlineRewriteBarrier] = []
    all_barriers: list[InlineRewriteBarrier] = []
    for line_index, line in enumerate(lines):
        if not 0 <= line.content_end <= len(line.fragments):
            raise ValueError("Inline-layout content boundary is outside the fragment sequence")
        scan_end = line.content_end
        hard_break = terminal_hard_break(line.fragments, has_following_newline=line.has_following_newline)
        if hard_break is not None:
            if hard_break.start <= line.content_end:
                scan_end = hard_break.start
            else:
                gap = line.fragments[line.content_end : hard_break.start]
                if all(fragment.value.isspace() for fragment in gap):
                    preserved_gap = tuple(fragment for fragment in gap if fragment.value != "\t")
                    hard_break = dataclasses.replace(
                        hard_break,
                        start=line.content_end,
                        value=f"{''.join(fragment.value for fragment in preserved_gap)}{hard_break.value}",
                        source=f"{''.join(fragment.source for fragment in preserved_gap)}{hard_break.source}",
                    )
                else:
                    hard_break = None
        scan = scan_fragments(line.fragments[:scan_end])
        barriers = tuple(dataclasses.replace(barrier, line_index=line_index) for barrier in scan.barriers)
        tokens.extend(scan.tokens)
        segment_barriers.extend(barriers)
        all_barriers.extend(barriers)
        text = _strip_layout_separators("".join(fragment.value for fragment in line.fragments[:scan_end]))
        if text:
            text_parts.append(text)
        if hard_break is not None:
            segments.append(InlineLayoutSegment(text=" ".join(text_parts), scan=InlineScanResult(tokens=tuple(tokens), barriers=tuple(_deduplicate_barriers(segment_barriers))), hard_break=hard_break))
            tokens = []
            text_parts = []
            segment_barriers = []
    if tokens or text_parts or not segments:
        segments.append(InlineLayoutSegment(text=" ".join(text_parts), scan=InlineScanResult(tokens=tuple(tokens), barriers=tuple(_deduplicate_barriers(segment_barriers))), hard_break=None))
    return InlineLayoutScanResult(segments=tuple(segments), barriers=tuple(_deduplicate_barriers(all_barriers)))


@dataclasses.dataclass(frozen=True)
class _TextFragment:
    """Source-identical character used by `scan_text`."""

    value: str
    source: str


def _parse_at(text: str, start: int, *, delimiter_index: _DelimiterIndex) -> _ParseResult:
    """Return the strongest construct or rewrite barrier beginning at an offset."""
    if text[start] not in "[<:`|" and not text.startswith("![", start):
        return _ParseResult()
    if delimiter_index.escaped[start]:
        return _ParseResult()
    if text.startswith("![", start) or text[start] == "[":
        return _parse_markdown_link(text, start, delimiter_index=delimiter_index)
    if text[start] == "<":
        return _parse_autolink(text, start, delimiter_index=delimiter_index)
    if text[start] == ":":
        role = _parse_prefix_role(text, start, delimiter_index=delimiter_index)
        if role.construct is not None or role.barrier is not None:
            return role
    if text[start] == "`":
        return _parse_backticks(text, start, delimiter_index=delimiter_index)
    if text[start] == "|":
        return _parse_substitution(text, start, delimiter_index=delimiter_index)
    return _ParseResult()


def _parse_markdown_link(text: str, start: int, *, delimiter_index: _DelimiterIndex) -> _ParseResult:
    """Parse a supported Markdown link or image at an opening label."""
    label_open = start + 1 if text.startswith("![", start) else start
    label_end = delimiter_index.bracket_closers.get(label_open)
    if label_end is None:
        if text.startswith("![", start):
            return _blocked(start, len(text), InlineRewriteBarrierKind.INCOMPLETE_MARKDOWN_IMAGE_LABEL)
        return _ParseResult()
    suffix_start = label_end + 1
    if suffix_start >= len(text):
        return _ParseResult()
    if text[suffix_start] == "(":
        inline_end, barrier_kind = _markdown_inline_end(text, suffix_start, delimiter_index=delimiter_index)
        if inline_end is None:
            if barrier_kind is None:
                raise RuntimeError("Missing rewrite barrier kind for incomplete Markdown link")
            return _blocked(start, len(text), barrier_kind)
        return _recognized(start, inline_end, InlineMarkupKind.MARKDOWN_LINK, url_like=True)
    if text[suffix_start] == "[":
        reference_end = delimiter_index.bracket_closers.get(suffix_start)
        if reference_end is None:
            return _blocked(start, len(text), InlineRewriteBarrierKind.INCOMPLETE_MARKDOWN_REFERENCE_LABEL)
        return _recognized(start, reference_end + 1, InlineMarkupKind.MARKDOWN_LINK)
    return _ParseResult()


def _markdown_inline_end(text: str, opening: int, *, delimiter_index: _DelimiterIndex) -> tuple[int | None, InlineRewriteBarrierKind | None]:
    """Return the end of a bounded Markdown inline-link destination and title."""
    index = opening + 1
    while index < len(text) and text[index] in ascii_whitespace.SPACE_AND_TAB:
        index += 1
    if index >= len(text):
        return None, InlineRewriteBarrierKind.INCOMPLETE_MARKDOWN_INLINE_DESTINATION
    if text[index] == ")":
        return index + 1, None
    if text[index] == "<":
        index += 1
        while index < len(text) and (text[index] != ">" or delimiter_index.escaped[index]):
            if text[index].isspace() or text[index] in "\r\n<":
                return None, InlineRewriteBarrierKind.MALFORMED_MARKDOWN_ANGLE_DESTINATION
            index += 1
        if index >= len(text):
            return None, InlineRewriteBarrierKind.INCOMPLETE_MARKDOWN_ANGLE_DESTINATION
        index += 1
        if index < len(text) and text[index] == ")":
            return index + 1, None
    else:
        depth = 0
        destination_start = index
        while index < len(text):
            char = text[index]
            if delimiter_index.escaped[index]:
                pass
            elif char == "(":
                depth += 1
                if depth > _MARKDOWN_DESTINATION_MAX_DEPTH:
                    return None, InlineRewriteBarrierKind.MARKDOWN_DESTINATION_NESTING_EXCEEDED
            elif char == ")":
                if depth == 0:
                    return index + 1, None
                depth -= 1
            elif char.isspace():
                break
            index += 1
        if index == destination_start:
            return None, InlineRewriteBarrierKind.MALFORMED_MARKDOWN_INLINE_DESTINATION
    if index >= len(text):
        return None, InlineRewriteBarrierKind.INCOMPLETE_MARKDOWN_INLINE_DESTINATION
    if not text[index].isspace():
        return None, InlineRewriteBarrierKind.MALFORMED_MARKDOWN_INLINE_DESTINATION
    while index < len(text) and text[index] in ascii_whitespace.SPACE_AND_TAB:
        index += 1
    if index >= len(text):
        return None, InlineRewriteBarrierKind.INCOMPLETE_MARKDOWN_INLINE_DESTINATION
    if text[index] == ")":
        return index + 1, None
    opener = text[index]
    if opener not in "\"'(":
        return None, InlineRewriteBarrierKind.UNSUPPORTED_MARKDOWN_LINK_TITLE
    closer = ")" if opener == "(" else opener
    index += 1
    while index < len(text) and (text[index] != closer or delimiter_index.escaped[index]):
        if text[index] in "\r\n" or (opener == "(" and text[index] == "("):
            return None, InlineRewriteBarrierKind.MALFORMED_MARKDOWN_LINK_TITLE
        index += 1
    if index >= len(text):
        return None, InlineRewriteBarrierKind.INCOMPLETE_MARKDOWN_LINK_TITLE
    index += 1
    while index < len(text) and text[index] in ascii_whitespace.SPACE_AND_TAB:
        index += 1
    if index >= len(text) or text[index] != ")":
        return None, InlineRewriteBarrierKind.INCOMPLETE_MARKDOWN_INLINE_LINK
    return index + 1, None


def _parse_autolink(text: str, start: int, *, delimiter_index: _DelimiterIndex) -> _ParseResult:
    """Parse a CommonMark-style URI or email autolink."""
    end = delimiter_index.next_angle_close[start + 1]
    if delimiter_index.next_angle_open[start + 1] < end:
        return _ParseResult()
    if end == len(text):
        candidate = text[start + 1 :]
        if _looks_like_autolink_prefix(candidate):
            return _blocked(start, len(text), InlineRewriteBarrierKind.INCOMPLETE_AUTOLINK)
        return _ParseResult()
    candidate = text[start + 1 : end]
    if _AUTOLINK_URI_RE.fullmatch(candidate) is not None or _AUTOLINK_EMAIL_RE.fullmatch(candidate) is not None:
        return _recognized(start, end + 1, InlineMarkupKind.AUTOLINK, url_like=True)
    return _ParseResult()


def _looks_like_autolink_prefix(candidate: str) -> bool:
    """Return whether an unterminated angle span has strong autolink evidence."""
    scheme = candidate.split(":", 1)[0]
    return (":" in candidate and re.fullmatch(r"[A-Za-z][A-Za-z0-9+.-]{1,31}", scheme) is not None) or ("@" in candidate and not any(char.isspace() for char in candidate))


def _parse_prefix_role(text: str, start: int, *, delimiter_index: _DelimiterIndex) -> _ParseResult:
    """Parse a boundary-valid reStructuredText prefix role."""
    if not _valid_rest_start(text, start):
        return _ParseResult()
    role_match = _ROLE_NAME_RE.match(text, start + 1)
    if role_match is None or role_match.end() >= len(text) or text[role_match.end()] != ":":
        return _ParseResult()
    backtick = role_match.end() + 1
    if backtick >= len(text) or text[backtick] != "`":
        return _ParseResult()
    close = delimiter_index.backtick_closers.get(backtick)
    if close is None:
        return _blocked(start, len(text), InlineRewriteBarrierKind.INCOMPLETE_REST_PREFIX_ROLE)
    end = close + 1
    if close == backtick + 1 or not _valid_rest_end(text, end):
        return _blocked(start, end, InlineRewriteBarrierKind.MALFORMED_REST_PREFIX_ROLE)
    return _recognized(start, end, InlineMarkupKind.REST_ROLE)


def _parse_backticks(text: str, start: int, *, delimiter_index: _DelimiterIndex) -> _ParseResult:
    """Parse Markdown code and reStructuredText backtick constructs."""
    run_length = _delimiter_run_length(text, start, "`")
    close = delimiter_index.backtick_closers.get(start)
    if close is None:
        return _blocked(start, min(len(text), start + run_length), InlineRewriteBarrierKind.UNCLOSED_INLINE_BACKTICK_SPAN)
    content_start = start + run_length
    if close == content_start:
        return _blocked(start, close + run_length, InlineRewriteBarrierKind.EMPTY_INLINE_BACKTICK_SPAN)
    end = close + run_length
    if run_length == 2 and _valid_rest_start(text, start) and _valid_rest_end(text, end):
        return _recognized(start, end, InlineMarkupKind.REST_LITERAL)
    if run_length == 1 and _valid_rest_start(text, start):
        role_end = _suffix_role_end(text, end)
        if role_end is not None and _valid_rest_end(text, role_end):
            return _recognized(start, role_end, InlineMarkupKind.REST_ROLE)
        if end < len(text) and text[end] == ":":
            role_match = _ROLE_NAME_RE.match(text, end + 1)
            if role_match is not None:
                return _blocked(start, role_match.end(), InlineRewriteBarrierKind.INCOMPLETE_REST_SUFFIX_ROLE)
        reference_end = end + 2 if text.startswith("__", end) else end + 1 if text.startswith("_", end) else None
        if reference_end is not None and _valid_rest_end(text, reference_end):
            return _recognized(start, reference_end, InlineMarkupKind.REST_INTERPRETED, url_like=_has_rest_embedded_target(text, content_start, close, delimiter_index=delimiter_index))
        if _valid_rest_end(text, end):
            return _recognized(start, end, InlineMarkupKind.REST_INTERPRETED)
    return _recognized(start, end, InlineMarkupKind.MARKDOWN_CODE)


def _suffix_role_end(text: str, start: int) -> int | None:
    """Return the end of a valid reStructuredText suffix role."""
    if start >= len(text) or text[start] != ":":
        return None
    match = _ROLE_NAME_RE.match(text, start + 1)
    if match is None or match.end() >= len(text) or text[match.end()] != ":":
        return None
    return match.end() + 1


def _has_rest_embedded_target(text: str, start: int, end: int, *, delimiter_index: _DelimiterIndex) -> bool:
    """Return whether interpreted text ends in an unescaped embedded target."""
    if end <= start or text[end - 1] != ">":
        return False
    opening = text.rfind("<", start, end - 1)
    return opening > start and not delimiter_index.escaped[opening] and bool(text[opening + 1 : end - 1].strip())


def _parse_substitution(text: str, start: int, *, delimiter_index: _DelimiterIndex) -> _ParseResult:
    """Parse a boundary-valid reStructuredText substitution reference."""
    if not _valid_rest_start(text, start):
        return _ParseResult()
    end = start + 1
    while end < len(text) and (text[end] != "|" or delimiter_index.escaped[end]):
        end += 1
    if end >= len(text) or end == start + 1 or not _valid_rest_end(text, end + 1):
        return _ParseResult()
    return _recognized(start, end + 1, InlineMarkupKind.REST_SUBSTITUTION)


def _delimiter_index(text: str) -> _DelimiterIndex:
    """Build delimiter matches and angle successors in one pass per direction."""
    escaped = _escaped_indices(text)
    backtick_runs: list[tuple[int, int]] = []
    bracket_stack: list[int] = []
    bracket_closers: dict[int, int] = {}
    index = 0
    while index < len(text):
        if text[index] == "`":
            run_length = _delimiter_run_length(text, index, "`")
            if not escaped[index]:
                backtick_runs.append((index, run_length))
            index += run_length
            continue
        if text[index] == "[" and not escaped[index]:
            bracket_stack.append(index)
        elif text[index] == "]" and bracket_stack and not escaped[index]:
            bracket_closers[bracket_stack.pop()] = index
        index += 1

    backtick_closers: dict[int, int] = {}
    next_backtick_by_length: dict[int, int] = {}
    for start, run_length in reversed(backtick_runs):
        closer = next_backtick_by_length.get(run_length)
        if closer is not None:
            backtick_closers[start] = closer
        next_backtick_by_length[run_length] = start

    next_angle_open = [len(text)] * (len(text) + 1)
    next_angle_close = [len(text)] * (len(text) + 1)
    open_index = len(text)
    close_index = len(text)
    for index in range(len(text) - 1, -1, -1):
        if text[index] == "<":
            open_index = index
        elif text[index] == ">":
            close_index = index
        next_angle_open[index] = open_index
        next_angle_close[index] = close_index
    return _DelimiterIndex(backtick_closers=backtick_closers, bracket_closers=bracket_closers, next_angle_open=tuple(next_angle_open), next_angle_close=tuple(next_angle_close), escaped=escaped)


def _delimiter_run_length(text: str, start: int, delimiter: str) -> int:
    """Return the length of one same-character delimiter run."""
    end = start
    while end < len(text) and text[end] == delimiter:
        end += 1
    return end - start


def _valid_rest_start(text: str, start: int) -> bool:
    """Return whether an inline reStructuredText construct may start here."""
    return start == 0 or text[start - 1].isspace() or text[start - 1] in "'\"([{<-/:"


def _valid_rest_end(text: str, end: int) -> bool:
    """Return whether an inline reStructuredText construct may end here."""
    return end == len(text) or text[end].isspace() or text[end] in "'\".,:;!?-)]}>/\\"


def _escaped_indices(text: str) -> tuple[bool, ...]:
    """Return whether each character follows an odd backslash run."""
    escaped: list[bool] = []
    backslashes = 0
    for char in text:
        escaped.append(backslashes % 2 == 1)
        backslashes = backslashes + 1 if char == "\\" else 0
    return tuple(escaped)


def _recognized(start: int, end: int, kind: InlineMarkupKind, *, url_like: bool = False) -> _ParseResult:
    """Return a successful scanner result."""
    return _ParseResult(construct=_Construct(start=start, end=end, kind=kind, url_like=url_like))


def _blocked(start: int, end: int, kind: InlineRewriteBarrierKind) -> _ParseResult:
    """Return a conservative rewrite-barrier result."""
    return _ParseResult(barrier=InlineRewriteBarrier(start=start, end=max(start + 1, end), kind=kind))


def _plain_tokens(fragments: Sequence[SourceFragment], *, text: str) -> tuple[InlineToken, ...]:
    """Return whitespace-delimited source-aware tokens without markup parsing."""
    tokens: list[InlineToken] = []
    index = 0
    while index < len(text):
        if unicode_safety.is_layout_separator(text[index]):
            index += 1
            continue
        end = index + 1
        while end < len(text) and not unicode_safety.is_layout_separator(text[end]):
            end += 1
        value = text[index:end]
        tokens.append(InlineToken(value=value, source="".join(fragment.source for fragment in fragments[index:end]), url_like=is_bare_url(value)))
        index = end
    return tuple(tokens)


def _tokens_for_constructs(fragments: Sequence[SourceFragment], *, text: str, constructs: list[_Construct]) -> tuple[InlineToken, ...]:
    """Expand constructs to punctuation envelopes and tokenize remaining prose."""
    left_boundaries = [0] * len(text)
    run_start = 0
    for index, char in enumerate(text):
        if unicode_safety.is_layout_separator(char):
            run_start = index + 1
        else:
            left_boundaries[index] = run_start
    right_boundaries = [len(text)] * len(text)
    run_end = len(text)
    for index in range(len(text) - 1, -1, -1):
        if unicode_safety.is_layout_separator(text[index]):
            run_end = index
        else:
            right_boundaries[index] = run_end
    envelopes: list[_Envelope] = []
    for construct in constructs:
        start = left_boundaries[construct.start]
        end = right_boundaries[construct.end - 1]
        if envelopes and start <= envelopes[-1].end:
            envelope = envelopes[-1]
            envelope.end = max(envelope.end, end)
            envelope.kinds.add(construct.kind)
            envelope.url_like = envelope.url_like or construct.url_like
        else:
            envelopes.append(_Envelope(start=start, end=end, kinds={construct.kind}, url_like=construct.url_like))
    tokens: list[InlineToken] = []
    envelope_index = 0
    index = 0
    while index < len(text):
        if unicode_safety.is_layout_separator(text[index]):
            index += 1
            continue
        if envelope_index < len(envelopes) and index == envelopes[envelope_index].start:
            envelope = envelopes[envelope_index]
            tokens.append(
                InlineToken(
                    value=text[envelope.start : envelope.end],
                    source="".join(fragment.source for fragment in fragments[envelope.start : envelope.end]),
                    kind=next(iter(envelope.kinds)) if len(envelope.kinds) == 1 else InlineMarkupKind.MIXED,
                    url_like=envelope.url_like,
                )
            )
            index = envelope.end
            envelope_index += 1
            continue
        next_whitespace = index + 1
        while next_whitespace < len(text) and not unicode_safety.is_layout_separator(text[next_whitespace]):
            next_whitespace += 1
        next_envelope = envelopes[envelope_index].start if envelope_index < len(envelopes) else len(text)
        end = min(next_whitespace, next_envelope)
        value = text[index:end]
        tokens.append(InlineToken(value=value, source="".join(fragment.source for fragment in fragments[index:end]), url_like=is_bare_url(value)))
        index = end
    return tuple(tokens)


def is_bare_url(text: str) -> bool:
    """Return whether a punctuation-trimmed token is a bare URL.

    Args:
        text (str): Evaluated wrapping token to classify.

    Returns:
        bool: Whether the token has a supported bare-URL prefix.
    """
    candidate = text.lstrip(_URL_LEADING_PUNCTUATION).rstrip(_URL_TRAILING_PUNCTUATION)
    return _BARE_URL_RE.fullmatch(candidate) is not None


def _strip_layout_separators(text: str, *, left: bool = True, right: bool = True) -> str:
    """Strip wrapping separators while preserving nonbreaking prose spaces."""
    start = 0
    end = len(text)
    if left:
        while start < end and unicode_safety.is_layout_separator(text[start]):
            start += 1
    if right:
        while end > start and unicode_safety.is_layout_separator(text[end - 1]):
            end -= 1
    return text[start:end]


def _deduplicate_barriers(barriers: list[InlineRewriteBarrier]) -> list[InlineRewriteBarrier]:
    """Return stable unique rewrite barriers."""
    unique: list[InlineRewriteBarrier] = []
    seen: set[tuple[int, int, InlineRewriteBarrierKind, int]] = set()
    for barrier in barriers:
        key = (barrier.start, barrier.end, barrier.kind, barrier.line_index)
        if key not in seen:
            seen.add(key)
            unique.append(barrier)
    return unique
