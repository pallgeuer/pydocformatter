"""Span-aware directive comment syntax shared by comment rules and suppression parsing.

Attributes:
    NOQA_RE (re.Pattern[str]): Generic `noqa` parser that keeps selector payloads and trailing rationale comments
        separate.
    PYDOCFMT_NOQA_RE (re.Pattern[str]): Pydocfmt line-suppression parser for optional rule selectors and preserved
        rationale text.
    DirectiveSemanticIdentity (TypeAlias): Canonical local rule or classified token identity used for first-seen
        directive-list deduplication.
"""

# Future imports
from __future__ import annotations

# Standard library imports
import re
import enum
import dataclasses
from collections.abc import Mapping
from typing import TYPE_CHECKING, TypeAlias

# Third-party imports
import libcst.metadata as cst_metadata

# First-party imports
from pydocformatter.rules.codes import RuleCode


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.collection import RuleCollection


NOQA_RE = re.compile(r"^noqa(?:\s*:\s*(?P<selectors>[^#]*?))?(?P<rest>[ \t\f]+#.*|)$", re.IGNORECASE)
PYDOCFMT_NOQA_RE = re.compile(r"^pydocfmt\s*:\s*noqa(?:\s*:\s*(?P<selectors>[^#]*?))?(?P<rest>[ \t\f]+#.*|)$", re.IGNORECASE)
_BRACKET_DIRECTIVE_RE = re.compile(r"^(?P<marker>#\s*)?(?P<tool>pydocfmt|ruff)\s*:\s*(?P<action>ignore|file-ignore|disable|enable)\s*(?P<list>\[(?P<selectors>[^\]]*)\])(?P<rest>.*)$", re.IGNORECASE)
_RUFF_EXACT_CODE_RE = re.compile(r"^[A-Za-z]+[0-9]+$")
_RUFF_BROAD_CODE_RE = re.compile(r"^[A-Z]+$")
_SAFE_FOREIGN_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)*$")
_SAFE_LIST_TOKEN_RE = re.compile(r"^[A-Za-z0-9_.-]+$")

DirectiveSemanticIdentity: TypeAlias = RuleCode | tuple[str, str]


class DirectiveTool(enum.Enum):
    """Tool owning a recognized bracket directive.

    Attributes:
        PYDOCFMT: Pydocformatter directive syntax.
        RUFF: Ruff directive syntax.
    """

    PYDOCFMT = "pydocfmt"
    RUFF = "ruff"


class DirectiveTokenKind(enum.Enum):
    """Semantic classification of one bracket-list token.

    Attributes:
        PYDOCFMT_EXACT_CODE: Registered exact pydocformatter rule code.
        PYDOCFMT_EXACT_NAME: Registered exact pydocformatter rule name.
        PYDOCFMT_BROAD_CODE: Valid broad pydocformatter code selector.
        UNKNOWN: Syntactically valid but unregistered selector.
        INVALID: Invalid pydocformatter selector syntax.
        RUFF_EXACT_CODE: Ruff selector with an alphabetic prefix and numeric suffix.
        RUFF_BROAD_CODE: Ruff uppercase broad selector without a single-name equivalent.
        RUFF_NAME: Ruff selector with a safely recognized name shape.
        FOREIGN: Ruff token without a safely recognized policy shape.
    """

    PYDOCFMT_EXACT_CODE = "pydocfmt-exact-code"
    PYDOCFMT_EXACT_NAME = "pydocfmt-exact-name"
    PYDOCFMT_BROAD_CODE = "pydocfmt-broad-code"
    UNKNOWN = "unknown"
    INVALID = "invalid"
    RUFF_EXACT_CODE = "ruff-exact-code"
    RUFF_BROAD_CODE = "ruff-broad-code"
    RUFF_NAME = "ruff-name"
    FOREIGN = "foreign"


@dataclasses.dataclass(frozen=True)
class BracketDirectiveToken:
    """One span-aware token in a recognized bracket directive.

    Attributes:
        original (str): Trimmed source spelling.
        normalized (str): Canonical spelling used by safe normalization.
        raw_segment (str): Exact source segment between adjacent commas.
        source_order (int): Zero-based nonempty token order.
        segment_index (int): Zero-based raw comma-separated segment position.
        kind (DirectiveTokenKind): Semantic token classification.
        matched_codes (frozenset[RuleCode]): Concrete local rules covered by a pydocfmt selector.
        resolved_code (RuleCode | None): Concrete local rule identity for exact pydocfmt selectors.
        resolved_name (str | None): Canonical name paired with an exact pydocfmt selector.
        semantic_identity (DirectiveSemanticIdentity): First-seen deduplication identity.
        survives_deduplication (bool): Whether this is the first token with its semantic identity.
    """

    original: str
    normalized: str
    raw_segment: str
    source_order: int
    segment_index: int
    kind: DirectiveTokenKind
    matched_codes: frozenset[RuleCode]
    resolved_code: RuleCode | None
    resolved_name: str | None
    semantic_identity: DirectiveSemanticIdentity
    survives_deduplication: bool

    def raw_segment_with(self, spelling: str) -> str:
        """Replace only the trimmed token spelling in this exact segment.

        Args:
            spelling (str): Replacement spelling for the trimmed token.

        Returns:
            str: Original segment whitespace surrounding the replacement spelling.
        """
        start = len(self.raw_segment) - len(self.raw_segment.lstrip())
        end = len(self.raw_segment.rstrip())
        return f"{self.raw_segment[:start]}{spelling}{self.raw_segment[end:]}"


@dataclasses.dataclass(frozen=True)
class BracketDirective:
    """Shared representation of one bracketed pydocfmt or Ruff directive.

    Attributes:
        tool (DirectiveTool): Tool owning the directive.
        action (str): Canonical lowercase directive action.
        comment_range (cst_metadata.CodeRange | None): Complete comment source bounds.
        selectors_range (cst_metadata.CodeRange | None): Source bounds inside the list brackets.
        suffix (str): Exact text after the selector-list contents, including the closing bracket and rationale tail.
        raw_selectors (str): Exact source text inside the list brackets.
        raw_segments (tuple[str, ...]): Exact comma-separated source segments, including empty segments.
        tokens (tuple[BracketDirectiveToken, ...]): Nonempty logical entries in source order.
        safe_list (bool): Whether the selector payload can be safely rendered as a comma-separated token list.
    """

    tool: DirectiveTool
    action: str
    comment_range: cst_metadata.CodeRange | None
    selectors_range: cst_metadata.CodeRange | None
    suffix: str
    raw_selectors: str
    raw_segments: tuple[str, ...]
    tokens: tuple[BracketDirectiveToken, ...]
    safe_list: bool

    @property
    def retained_tokens(self) -> tuple[BracketDirectiveToken, ...]:
        """First-seen semantic entries in source order.

        Returns:
            tuple[BracketDirectiveToken, ...]: Tokens retained by semantic deduplication.
        """
        return tuple(token for token in self.tokens if token.survives_deduplication)

    def normalized_selectors(self) -> str:
        """Render canonical selector-list contents for safe PCF100 normalization.

        Returns:
            str: Canonically spelled, spaced, and deduplicated selector list.
        """
        return ", ".join(token.normalized for token in self.retained_tokens)

    def targeted_selectors(self, replacements: dict[int, str]) -> str:
        """Render targeted spellings while removing aliases of converted identities.

        Args:
            replacements (dict[int, str]): Replacement spellings keyed by nonempty token source order.

        Returns:
            str: Minimally changed selector contents with unrelated tokens preserved exactly.
        """
        token_by_segment = {token.segment_index: token for token in self.tokens}
        targeted_identities = {token.semantic_identity for token in self.tokens if token.source_order in replacements}
        emitted_targeted_identities: set[DirectiveSemanticIdentity] = set()
        rendered_segments: list[str] = []
        for segment_index, raw_segment in enumerate(self.raw_segments):
            token = token_by_segment.get(segment_index)
            if token is None:
                rendered_segments.append(raw_segment)
                continue
            if token.semantic_identity in targeted_identities:
                if token.semantic_identity in emitted_targeted_identities:
                    continue
                emitted_targeted_identities.add(token.semantic_identity)
            rendered_segments.append(token.raw_segment_with(replacements.get(token.source_order, token.original)))
        return ",".join(rendered_segments)


@dataclasses.dataclass(frozen=True)
class BracketDirectiveIndex:
    """Bracket directives parsed once for one exact module source state.

    Attributes:
        by_range (Mapping[cst_metadata.CodeRange, BracketDirective]): Directives indexed by complete comment bounds.
    """

    by_range: Mapping[cst_metadata.CodeRange, BracketDirective]

    def get(self, code_range: cst_metadata.CodeRange) -> BracketDirective | None:
        """Return the directive parsed for a comment range.

        Args:
            code_range (cst_metadata.CodeRange): Complete comment bounds.

        Returns:
            BracketDirective | None: Indexed directive, or none for an unrecognized comment.
        """
        return self.by_range.get(code_range)


def parse_bracket_directive(text: str, *, collection: RuleCollection, comment_range: cst_metadata.CodeRange | None = None) -> BracketDirective | None:
    """Parse one bracket directive into the shared span-aware representation.

    Args:
        text (str): Exact comment text including `#`, or stripped directive content when no coordinates are requested.
        collection (RuleCollection): Local rule catalog used to resolve pydocfmt selectors.
        comment_range (cst_metadata.CodeRange | None): Exact source bounds for marker-inclusive comment text.

    Returns:
        BracketDirective | None: Parsed directive, or none when the text is not a recognized bracket form.

    Raises:
        ValueError: If source coordinates are requested for text without a comment marker.
    """
    match = _BRACKET_DIRECTIVE_RE.fullmatch(text)
    if match is None:
        return None
    if comment_range is not None and match.group("marker") is None:
        raise ValueError("Bracket directive coordinates require complete comment text including '#'")
    tool = DirectiveTool(match.group("tool").lower())
    action = match.group("action").lower()
    selectors_start, selectors_end = match.span("selectors")
    source_line = None if comment_range is None else comment_range.start.line
    source_column = 0 if comment_range is None else comment_range.start.column
    selectors_range = None if source_line is None else _range(source_line, source_column + selectors_start, source_column + selectors_end)
    raw_selectors = match.group("selectors")
    segments = raw_selectors.split(",")
    trailing_comma = len(segments) > 1 and not segments[-1].strip()
    empty_nontrailing = any(not segment.strip() for segment in segments[:-1] if len(segments) > 1)
    safe_list = not empty_nontrailing and all(_SAFE_LIST_TOKEN_RE.fullmatch(segment.strip()) is not None for segment in segments if segment.strip())
    identities: set[DirectiveSemanticIdentity] = set()
    tokens: list[BracketDirectiveToken] = []
    for segment_index, segment in enumerate(segments):
        original = segment.strip()
        if original:
            kind, normalized, matched_codes, resolved_code, resolved_name, identity = _classify_token(original, tool=tool, collection=collection)
            survives = identity not in identities or (tool is DirectiveTool.RUFF and action in {"disable", "enable"})
            identities.add(identity)
            tokens.append(
                BracketDirectiveToken(
                    original=original,
                    normalized=normalized,
                    raw_segment=segment,
                    source_order=len(tokens),
                    segment_index=segment_index,
                    kind=kind,
                    matched_codes=matched_codes,
                    resolved_code=resolved_code,
                    resolved_name=resolved_name,
                    semantic_identity=identity,
                    survives_deduplication=survives,
                )
            )
    if trailing_comma:
        safe_list = safe_list and bool(tokens)
    return BracketDirective(
        tool=tool,
        action=action,
        comment_range=comment_range,
        selectors_range=selectors_range,
        suffix=text[selectors_end:],
        raw_selectors=raw_selectors,
        raw_segments=tuple(segments),
        tokens=tuple(tokens),
        safe_list=safe_list,
    )


def _classify_token(original: str, *, tool: DirectiveTool, collection: RuleCollection) -> tuple[DirectiveTokenKind, str, frozenset[RuleCode], RuleCode | None, str | None, DirectiveSemanticIdentity]:
    """Classify one nonempty directive token."""
    if tool is DirectiveTool.RUFF:
        if _RUFF_EXACT_CODE_RE.fullmatch(original) is not None:
            return DirectiveTokenKind.RUFF_EXACT_CODE, original, frozenset(), None, None, ("ruff", original)
        if _RUFF_BROAD_CODE_RE.fullmatch(original) is not None:
            return DirectiveTokenKind.RUFF_BROAD_CODE, original, frozenset(), None, None, ("ruff", original)
        if _SAFE_FOREIGN_TOKEN_RE.fullmatch(original) is not None:
            return DirectiveTokenKind.RUFF_NAME, original, frozenset(), None, None, ("ruff", original)
        return DirectiveTokenKind.FOREIGN, original, frozenset(), None, None, ("ruff", original)

    if not original.isascii():
        return DirectiveTokenKind.INVALID, original, frozenset(), None, None, ("invalid", original)

    lowered = original.lower()
    name_resolution = collection.resolve_selector(lowered)
    if name_resolution.exact_rule is not None:
        rule = name_resolution.exact_rule.meta
        return DirectiveTokenKind.PYDOCFMT_EXACT_NAME, lowered, frozenset((rule.code,)), rule.code, rule.name, rule.code
    uppered = original.upper()
    code_resolution = collection.resolve_selector(uppered)
    if code_resolution.selector is not None:
        matched_codes = frozenset(rule.meta.code for rule in code_resolution.matching_rules)
        if code_resolution.exact_rule is not None:
            rule = code_resolution.exact_rule.meta
            return DirectiveTokenKind.PYDOCFMT_EXACT_CODE, uppered, matched_codes, rule.code, rule.name, rule.code
        if matched_codes:
            return DirectiveTokenKind.PYDOCFMT_BROAD_CODE, uppered, matched_codes, None, None, ("selector", uppered)
        return DirectiveTokenKind.UNKNOWN, uppered, frozenset(), None, None, ("unknown", uppered)
    if name_resolution.kind.value == "unknown-name":
        return DirectiveTokenKind.UNKNOWN, lowered, frozenset(), None, None, ("unknown", lowered)
    return DirectiveTokenKind.INVALID, original, frozenset(), None, None, ("invalid", original)


def _range(line: int, start: int, end: int) -> cst_metadata.CodeRange:
    """Return a same-line half-open source range."""
    return cst_metadata.CodeRange(start=cst_metadata.CodePosition(line, start), end=cst_metadata.CodePosition(line, end))
