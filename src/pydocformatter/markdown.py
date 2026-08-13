"""Markdown fenced Python block discovery and reconstruction."""

# Future imports
from __future__ import annotations

# Standard library imports
import re
import difflib
import dataclasses

# First-party imports
from pydocformatter.utils import text


_UTF8_BOM = "\ufeff"
_PYTHON_FENCE_LANGUAGES = frozenset(("py", "python", "python3"))
_PYDOCFMT_SKIP_TOKEN = "pydocfmt-skip"  # ruff: ignore[hardcoded-password-string]
_OPENING_FENCE_RE = re.compile(r"^(?P<indent> {0,3})(?P<fence>`{3,}|~{3,})(?P<info>[^\r\n]*)(?P<ending>\r\n|\n|\r)?$")


@dataclasses.dataclass(frozen=True)
class MarkdownFence:
    """One closed raw-line Markdown fence.

    Attributes:
        body_start (int): Character offset where the fenced body begins.
        body_end (int): Character offset where the fenced body ends.
        body_start_line (int): One-based Markdown line containing the first body line.
        opening_line (str): Complete original opening line, including its line ending.
        closing_line (str): Complete original closing line, including its line ending.
        marker (str): Opening backtick or tilde marker.
        indent (str): ASCII-space indentation preceding the opening marker.
        language (str): Case-normalized first info-string token, or an empty string.
        skipped (bool): Whether a Python info string contains the exact `pydocfmt-skip` token.
        raw_body_lines (tuple[str, ...]): Complete original physical body lines.
        logical_body_lines (tuple[str, ...]): Body lines after CommonMark fence indentation removal.
        removed_prefixes (tuple[str, ...]): Prefix removed from each physical line to obtain logical source.
    """

    body_start: int
    body_end: int
    body_start_line: int
    opening_line: str
    closing_line: str
    marker: str
    indent: str
    language: str
    skipped: bool
    raw_body_lines: tuple[str, ...]
    logical_body_lines: tuple[str, ...]
    removed_prefixes: tuple[str, ...]

    @property
    def is_python(self) -> bool:
        """Whether this fence has a supported Python language token.

        Returns:
            bool: Whether the info string selects Python handling.
        """
        return self.language in _PYTHON_FENCE_LANGUAGES

    @property
    def source(self) -> str:
        """Logical Python source after CommonMark indentation removal.

        Returns:
            str: Concatenated logical body lines.
        """
        return "".join(self.logical_body_lines)

    def prefix_for_line(self, line: int) -> str:
        """Return the original removed prefix for a logical body line.

        Args:
            line (int): One-based logical body line number.

        Returns:
            str: Original removed indentation, or the opener indentation for a generated line.
        """
        if 1 <= line <= len(self.removed_prefixes):
            return self.removed_prefixes[line - 1]
        return self.indent

    def render_body(self, source: str) -> str:
        """Render formatted logical source as a safely prefixed Markdown body.

        Args:
            source (str): Formatted logical Python source.

        Returns:
            str: Reconstructed physical body preserving unchanged lines.
        """
        replacement_lines = text.split_physical_lines(source, keepends=True)
        matcher = difflib.SequenceMatcher(a=self.logical_body_lines, b=replacement_lines, autojunk=False)
        rendered: list[str] = []
        for operation, original_start, original_end, replacement_start, replacement_end in matcher.get_opcodes():
            if operation == "equal":
                rendered.extend(self.raw_body_lines[original_start:original_end])
            else:
                rendered.extend(line if line in {"\r", "\n", "\r\n"} else f"{self.indent}{line}" for line in replacement_lines[replacement_start:replacement_end])
        return "".join(rendered)


@dataclasses.dataclass(frozen=True)
class MarkdownRewriteValidation:
    """Candidate fence inventory and any structural rewrite error.

    Attributes:
        fences (tuple[MarkdownFence, ...]): Closed fences parsed from the rewritten candidate.
        error (str | None): Unsafe rewrite description, or None when the candidate is valid.
    """

    fences: tuple[MarkdownFence, ...]
    error: str | None


def markdown_fences(source: str) -> tuple[MarkdownFence, ...]:
    """Return recognized closed Markdown fences in source order.

    Args:
        source (str): Complete Markdown source.

    Returns:
        tuple[MarkdownFence, ...]: Every recognized closed fence.
    """
    lines = text.split_physical_lines(source, keepends=True)
    offsets: list[int] = []
    offset = 0
    for line in lines:
        offsets.append(offset)
        offset += len(line)

    fences: list[MarkdownFence] = []
    line_index = 0
    while line_index < len(lines):
        match_line = lines[line_index]
        if line_index == 0 and match_line.startswith(_UTF8_BOM):
            match_line = match_line[len(_UTF8_BOM) :]
        opening = _OPENING_FENCE_RE.fullmatch(match_line)
        if opening is None:
            line_index += 1
            continue
        marker = opening.group("fence")
        info = opening.group("info")
        if marker.startswith("`") and "`" in info:
            line_index += 1
            continue
        tokens = info.strip().split()
        language = tokens[0].lower() if tokens else ""
        closing_index = _closing_fence_index(lines, line_index + 1, marker=marker)
        if closing_index is None:
            break
        indent = opening.group("indent")
        raw_body_lines = tuple(lines[line_index + 1 : closing_index])
        removed_prefixes = tuple(_removed_prefix(line, width=len(indent)) for line in raw_body_lines)
        logical_body_lines = tuple(line[len(prefix) :] for line, prefix in zip(raw_body_lines, removed_prefixes, strict=True))
        body_start = offsets[line_index] + len(lines[line_index])
        fences.append(
            MarkdownFence(
                body_start=body_start,
                body_end=offsets[closing_index],
                body_start_line=line_index + 2,
                opening_line=lines[line_index],
                closing_line=lines[closing_index],
                marker=marker,
                indent=indent,
                language=language,
                skipped=language in _PYTHON_FENCE_LANGUAGES and _PYDOCFMT_SKIP_TOKEN in tokens[1:],
                raw_body_lines=raw_body_lines,
                logical_body_lines=logical_body_lines,
                removed_prefixes=removed_prefixes,
            )
        )
        line_index = closing_index + 1
    return tuple(fences)


def replace_fence_bodies(source: str, replacements: tuple[tuple[MarkdownFence, str], ...]) -> str:
    """Return source with logical fence bodies reconstructed from replacements.

    Args:
        source (str): Complete original Markdown source.
        replacements (tuple[tuple[MarkdownFence, str], ...]): Fences paired with formatted logical bodies in source
            order with non-overlapping body ranges.

    Returns:
        str: Reconstructed Markdown candidate.

    Raises:
        ValueError: If a fence body range is invalid, out of order, or overlaps a preceding range.
    """
    parts: list[str] = []
    cursor = 0
    for fence, replacement in replacements:
        if not 0 <= fence.body_start <= fence.body_end <= len(source):
            raise ValueError("Fence replacement range is outside the Markdown source")
        if fence.body_start < cursor:
            raise ValueError("Fence replacement ranges must be in source order and must not overlap")
        parts.extend((source[cursor : fence.body_start], fence.render_body(replacement)))
        cursor = fence.body_end
    parts.append(source[cursor:])
    return "".join(parts)


def validate_rewrite(original_fences: tuple[MarkdownFence, ...], candidate: str, *, expected_sources: dict[int, str]) -> MarkdownRewriteValidation:
    """Return parsed candidate fences and any structural rewrite error.

    Args:
        original_fences (tuple[MarkdownFence, ...]): Complete original fence inventory.
        candidate (str): Reconstructed Markdown candidate to validate.
        expected_sources (dict[int, str]): Expected logical bodies keyed by fence index.

    Returns:
        MarkdownRewriteValidation: Parsed candidate fence inventory and any unsafe rewrite description.
    """
    candidate_fences = markdown_fences(candidate)
    if len(candidate_fences) != len(original_fences):
        return MarkdownRewriteValidation(fences=candidate_fences, error="the number of recognized closed fences changed")
    for index, (original, rewritten) in enumerate(zip(original_fences, candidate_fences, strict=True)):
        if (rewritten.opening_line, rewritten.closing_line, rewritten.marker, rewritten.indent, rewritten.language, rewritten.skipped) != (
            original.opening_line,
            original.closing_line,
            original.marker,
            original.indent,
            original.language,
            original.skipped,
        ):
            return MarkdownRewriteValidation(fences=candidate_fences, error=f"fence {index + 1} changed its delimiters or info string")
        expected_source = expected_sources.get(index, original.source)
        if rewritten.source != expected_source:
            return MarkdownRewriteValidation(fences=candidate_fences, error=f"fence {index + 1} no longer contains the intended source")
    return MarkdownRewriteValidation(fences=candidate_fences, error=None)


def _removed_prefix(line: str, *, width: int) -> str:
    """Return the CommonMark indentation prefix removed from one body line."""
    removed = 0
    while removed < min(width, len(line)) and line[removed] == " ":
        removed += 1
    return line[:removed]


def _closing_fence_index(lines: list[str], start: int, *, marker: str) -> int | None:
    """Return the matching closing-fence line index, if present."""
    marker_character = re.escape(marker[0])
    closing = re.compile(rf"^ {{0,3}}{marker_character}{{{len(marker)},}}[ \t]*(?:\r\n|\n|\r)?$")
    for line_index in range(start, len(lines)):
        if closing.fullmatch(lines[line_index]) is not None:
            return line_index
    return None
