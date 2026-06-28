"""Source directive parsing for pydocformatter finding suppression."""

from __future__ import annotations

import dataclasses
import re
from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING

import libcst as cst
import libcst.metadata as cst_metadata

import pydocformatter.rules.definition_helpers.directives as directive_helpers
from pydocformatter.rules.codes import ALL_RULE_SELECTOR_TAG, RuleCode, RuleSelector
from pydocformatter.rules.collection import RuleCollection
from pydocformatter.rules.models import RuleFinding, RuleMetadata

if TYPE_CHECKING:
    import pydocformatter.rules.violations as rule_violations

SuppressionSelectorKey = tuple[int, int]

_TYPE_DIRECTIVE_RE = re.compile(r"^#\s*type\s*:", re.IGNORECASE)
_TOOL_DIRECTIVE_RE = re.compile(
    r"^#\s*(?:noqa\b|nosec\b|nosemgrep\b|pydocfmt\b|pylint\b|pyright\b|mypy\b|ty\s*:|ruff\b|flake8\b|fmt\s*:|isort\s*:|pragma\b|noinspection\b|language\s*=|@formatter\s*:)",
    re.IGNORECASE,
)


@dataclasses.dataclass(frozen=True)
class SuppressionViolationFilterResult:
    """Unsuppressed violations and selector keys used while filtering them."""

    violations: tuple[rule_violations.RuleViolation, ...]
    used_selector_keys: frozenset[SuppressionSelectorKey]


@dataclasses.dataclass(frozen=True)
class SuppressionIndex:
    """Parsed pydocformatter suppression directives for one source state."""

    directives: tuple[SuppressionDirective, ...]

    def used_selector_keys(self, finding: RuleFinding) -> frozenset[SuppressionSelectorKey]:
        """Return stable selector keys used by suppressing one finding."""
        used: set[SuppressionSelectorKey] = set()
        for directive_index, directive in enumerate(self.directives):
            used.update(directive.used_selector_keys(finding, directive_index=directive_index))
        return frozenset(used)

    def unused_findings(self, used_selector_keys: frozenset[SuppressionSelectorKey], *, selected_rule_codes: frozenset[RuleCode], rule: RuleMetadata) -> tuple[RuleFinding, ...]:
        """Return PCF006-style findings for invalid or unused audited selectors."""
        findings: list[RuleFinding] = []
        for directive_index, directive in enumerate(self.directives):
            findings.extend(directive.unused_findings(directive_index=directive_index, used_selector_keys=used_selector_keys, selected_rule_codes=selected_rule_codes, rule=rule))
        return tuple(findings)

    def filter_violations(self, violations: tuple[rule_violations.RuleViolation, ...]) -> SuppressionViolationFilterResult:
        """Return unsuppressed violations and selector keys used during filtering."""
        unsuppressed_violations: list[rule_violations.RuleViolation] = []
        used_selector_keys: set[SuppressionSelectorKey] = set()
        for violation in violations:
            finding_used_selector_keys = self.used_selector_keys(violation.finding)
            if finding_used_selector_keys:
                used_selector_keys.update(finding_used_selector_keys)
            else:
                unsuppressed_violations.append(violation)
        return SuppressionViolationFilterResult(violations=tuple(unsuppressed_violations), used_selector_keys=frozenset(used_selector_keys))


@dataclasses.dataclass(frozen=True)
class SuppressionDirective:
    """One parsed source suppression directive."""

    line: int
    selectors: tuple[SuppressionSelector, ...]

    def used_selector_keys(self, finding: RuleFinding, *, directive_index: int) -> set[SuppressionSelectorKey]:
        """Return selector keys used by suppressing this finding."""
        return {(directive_index, selector_index) for selector_index, selector in enumerate(self.selectors) if selector.suppresses(finding)}

    def unused_findings(self, *, directive_index: int, used_selector_keys: frozenset[SuppressionSelectorKey], selected_rule_codes: frozenset[RuleCode], rule: RuleMetadata) -> list[RuleFinding]:
        """Return unused or invalid findings for audited selectors."""
        findings: list[RuleFinding] = []
        for selector_index, selector in enumerate(self.selectors):
            if not selector.audit:
                continue
            selector_key = (directive_index, selector_index)
            if selector.invalid_message is not None:
                findings.append(RuleFinding(rule=rule, line_numbers=(self.line,), instance_message=selector.invalid_message, instance_fixable=None))
            elif selector_key not in used_selector_keys and selector.matched_codes & selected_rule_codes:
                findings.append(RuleFinding(rule=rule, line_numbers=(self.line,), instance_message=f"Suppression selector '{selector.text}' did not suppress any findings", instance_fixable=None))
        return findings


@dataclasses.dataclass(frozen=True)
class SuppressionSelector:
    """One selector entry inside a suppression directive."""

    text: str
    matched_codes: frozenset[RuleCode]
    coverage_lines: frozenset[int]
    audit: bool
    invalid_message: str | None = None

    def suppresses(self, finding: RuleFinding) -> bool:
        """Return whether this selector suppresses one finding."""
        if self.invalid_message is not None:
            return False
        if finding.rule.code not in self.matched_codes:
            return False
        return any(bool(target) and set(target).issubset(self.coverage_lines) for target in finding.suppression_targets)


@dataclasses.dataclass(frozen=True)
class _CommentInfo:
    """Comment placement information used to attach directives."""

    line: int
    column: int
    indent: str
    text: str
    standalone: bool
    pydocfmt_local: bool

    @property
    def content(self) -> str:
        """Return stripped comment content without the leading hash."""
        return self.text.removeprefix("#").strip()


@dataclasses.dataclass(frozen=True)
class _StringRange:
    """Physical source lines occupied by one string expression."""

    start_line: int
    end_line: int

    @property
    def lines(self) -> frozenset[int]:
        """Return all covered physical lines."""
        return frozenset(range(self.start_line, self.end_line + 1))


class _SourceCollector(cst.CSTVisitor):
    """Collect comments and string ranges for suppression attachment."""

    def __init__(self, positions: Mapping[cst.CSTNode, cst_metadata.CodeRange], source_lines: tuple[str, ...]) -> None:
        """Initialize empty source object collections."""
        self.positions = positions
        self.source_lines = source_lines
        self.comments: list[_CommentInfo] = []
        self.strings: list[_StringRange] = []

    def visit_Comment(self, node: cst.Comment) -> None:
        """Collect one comment node."""
        code_range = self.positions[node]
        source_line = self.source_lines[code_range.start.line - 1].rstrip("\r\n")
        line_prefix = source_line[: code_range.start.column]
        content = node.value.removeprefix("#").strip()
        self.comments.append(
            _CommentInfo(
                line=code_range.start.line,
                column=code_range.start.column,
                indent=line_prefix if not line_prefix.strip(" \t\f") else line_prefix[: len(line_prefix) - len(line_prefix.lstrip(" \t\f"))],
                text=node.value,
                standalone=not line_prefix.strip(" \t\f"),
                pydocfmt_local=_is_pydocfmt_local_ignore(content),
            )
        )

    def visit_SimpleString(self, node: cst.SimpleString) -> None:
        """Collect one simple string expression range."""
        self._collect_string(node)

    def visit_ConcatenatedString(self, node: cst.ConcatenatedString) -> None:
        """Collect one concatenated string expression range."""
        self._collect_string(node)

    def _collect_string(self, node: cst.CSTNode) -> None:
        code_range = self.positions[node]
        self.strings.append(_StringRange(start_line=code_range.start.line, end_line=code_range.end.line))


def suppression_index(module: cst.Module, *, positions: Mapping[cst.CSTNode, cst_metadata.CodeRange], source_lines: tuple[str, ...], collection: RuleCollection) -> SuppressionIndex:
    """Return parsed suppression directives for a module source state."""
    if not any("#" in line for line in source_lines):
        return SuppressionIndex(directives=())
    collector = _SourceCollector(positions, source_lines)
    module.visit(collector)
    comments = tuple(sorted(collector.comments, key=lambda comment: (comment.line, comment.column)))
    strings = tuple(collector.strings)
    comments_by_line = _comments_by_line(comments)
    directives: list[SuppressionDirective] = []
    directives.extend(_line_directives(comments, strings=strings, collection=collection))
    directives.extend(_pydocfmt_file_directives(comments, source_line_count=len(source_lines), collection=collection))
    directives.extend(_pydocfmt_local_directives(comments, strings=strings, comments_by_line=comments_by_line, source_lines=source_lines, collection=collection))
    return SuppressionIndex(directives=tuple(directives))


def _line_directives(comments: tuple[_CommentInfo, ...], *, strings: tuple[_StringRange, ...], collection: RuleCollection) -> tuple[SuppressionDirective, ...]:
    directives: list[SuppressionDirective] = []
    for comment in comments:
        if not comment.standalone and (pydocfmt_match := directive_helpers.PYDOCFMT_BRACKET_RE.match(comment.content)) is not None and pydocfmt_match.group("action").lower() == "ignore":
            coverage_lines = _line_coverage(comment.line, strings=strings)
            selectors = _selectors(pydocfmt_match.group("selectors"), default_text=ALL_RULE_SELECTOR_TAG, coverage_lines=coverage_lines, collection=collection, audit=True, include_invalid=True)
            directives.append(SuppressionDirective(line=comment.line, selectors=selectors))
            continue
        match = directive_helpers.NOQA_RE.match(comment.content)
        if match is None:
            continue
        if not _has_conventional_comment_marker_spacing(comment.text):
            continue
        coverage_lines = _line_coverage(comment.line, strings=strings)
        selectors = _selectors(
            match.group("selectors"), default_text=ALL_RULE_SELECTOR_TAG, coverage_lines=coverage_lines, collection=collection, audit=False, include_invalid=False, audit_known_explicit=True
        )
        if selectors:
            directives.append(SuppressionDirective(line=comment.line, selectors=selectors))
    return tuple(directives)


def _pydocfmt_file_directives(comments: tuple[_CommentInfo, ...], *, source_line_count: int, collection: RuleCollection) -> tuple[SuppressionDirective, ...]:
    directives: list[SuppressionDirective] = []
    coverage_lines = frozenset(range(1, source_line_count + 1))
    for comment in comments:
        if not comment.standalone:
            continue
        content = comment.content
        selectors_text: str | None
        match = directive_helpers.PYDOCFMT_NOQA_RE.match(content)
        if match is not None:
            selectors_text = match.group("selectors")
        elif (bracket_match := directive_helpers.PYDOCFMT_BRACKET_RE.match(content)) is not None and bracket_match.group("action").lower() == "file-ignore":
            selectors_text = bracket_match.group("selectors")
        else:
            continue
        selectors = _selectors(selectors_text, default_text=ALL_RULE_SELECTOR_TAG, coverage_lines=coverage_lines, collection=collection, audit=True, include_invalid=True)
        directives.append(SuppressionDirective(line=comment.line, selectors=selectors))
    return tuple(directives)


def _pydocfmt_local_directives(
    comments: tuple[_CommentInfo, ...],
    *,
    strings: tuple[_StringRange, ...],
    comments_by_line: dict[int, tuple[_CommentInfo, ...]],
    source_lines: tuple[str, ...],
    collection: RuleCollection,
) -> tuple[SuppressionDirective, ...]:
    local_lines = {comment.line for comment in comments if comment.standalone and comment.pydocfmt_local}
    directives: list[SuppressionDirective] = []
    for block in _local_blocks(local_lines):
        target_line = block[-1] + 1
        for line in block:
            comment = next(comment for comment in comments_by_line[line] if comment.standalone and comment.pydocfmt_local)
            match = directive_helpers.PYDOCFMT_BRACKET_RE.match(comment.content)
            if match is None:
                continue
            selectors = tuple(
                _local_selector(selector, target_line=target_line, strings=strings, comments_by_line=comments_by_line, source_lines=source_lines, collection=collection)
                for selector in _selector_texts(match.group("selectors"), include_empty=True)
            )
            directives.append(SuppressionDirective(line=line, selectors=selectors))
    return tuple(directives)


def _local_selector(
    text: str, *, target_line: int, strings: tuple[_StringRange, ...], comments_by_line: dict[int, tuple[_CommentInfo, ...]], source_lines: tuple[str, ...], collection: RuleCollection
) -> SuppressionSelector:
    matched_codes, invalid_message = _matched_codes(text, include_invalid=True, collection=collection)
    if invalid_message is not None:
        return SuppressionSelector(text=text, matched_codes=frozenset(), coverage_lines=frozenset(), audit=True, invalid_message=invalid_message)
    prefixes = {code.prefix for code in matched_codes}
    coverage_lines: set[int] = set()
    if "PDF" in prefixes or text == ALL_RULE_SELECTOR_TAG:
        coverage_lines.update(_opening_string_coverage(target_line, strings=strings))
    if "PCF" in prefixes or text == ALL_RULE_SELECTOR_TAG:
        coverage_lines.update(_comment_target_coverage(target_line, comments_by_line=comments_by_line, source_lines=source_lines))
    return SuppressionSelector(text=text, matched_codes=matched_codes, coverage_lines=frozenset(coverage_lines), audit=True)


def _selectors(
    selectors_text: str | None,
    *,
    default_text: str,
    coverage_lines: frozenset[int],
    collection: RuleCollection,
    audit: bool,
    include_invalid: bool,
    audit_known_explicit: bool = False,
) -> tuple[SuppressionSelector, ...]:
    explicit = selectors_text is not None
    texts = (default_text,) if selectors_text is None else _selector_texts(selectors_text, include_empty=include_invalid)
    selectors: list[SuppressionSelector] = []
    for text in texts:
        matched_codes, invalid_message = _matched_codes(text, include_invalid=include_invalid, collection=collection)
        if invalid_message is not None:
            selectors.append(SuppressionSelector(text=text, matched_codes=frozenset(), coverage_lines=coverage_lines, audit=True, invalid_message=invalid_message))
        elif matched_codes:
            selectors.append(SuppressionSelector(text=text, matched_codes=matched_codes, coverage_lines=coverage_lines, audit=audit or (audit_known_explicit and explicit)))
    return tuple(selectors)


def _selector_texts(selectors_text: str, *, include_empty: bool) -> tuple[str, ...]:
    texts = tuple(text.strip().upper() for text in selectors_text.split(",") if text.strip())
    if texts:
        return texts
    return ("",) if include_empty else ()


def _matched_codes(text: str, *, include_invalid: bool, collection: RuleCollection) -> tuple[frozenset[RuleCode], str | None]:
    if not RuleSelector.is_valid_tag(text):
        return frozenset(), f"Invalid pydocfmt suppression selector '{text}'" if include_invalid else None
    selector = RuleSelector(text)
    matched_codes = frozenset(rule.meta.code for rule in collection.rules if selector.selects_code(rule.meta.code))
    if not matched_codes:
        return frozenset(), f"Unknown pydocfmt suppression selector '{text}'" if include_invalid else None
    return matched_codes, None


def _comments_by_line(comments: Iterable[_CommentInfo]) -> dict[int, tuple[_CommentInfo, ...]]:
    grouped: dict[int, list[_CommentInfo]] = {}
    for comment in comments:
        grouped.setdefault(comment.line, []).append(comment)
    return {line: tuple(sorted(line_comments, key=lambda comment: comment.column)) for line, line_comments in grouped.items()}


def _line_coverage(line: int, *, strings: tuple[_StringRange, ...]) -> frozenset[int]:
    lines = {line}
    for string in strings:
        if string.end_line == line:
            lines.update(string.lines)
    return frozenset(lines)


def _opening_string_coverage(line: int, *, strings: tuple[_StringRange, ...]) -> frozenset[int]:
    lines: set[int] = set()
    for string in strings:
        if string.start_line == line:
            lines.update(string.lines)
    return frozenset(lines)


def _comment_target_coverage(line: int, *, comments_by_line: dict[int, tuple[_CommentInfo, ...]], source_lines: tuple[str, ...]) -> frozenset[int]:
    line_comments = comments_by_line.get(line, ())
    target = next(iter(line_comments), None)
    if target is None:
        return frozenset()
    if not target.standalone:
        return frozenset((line,))
    lines = {line}
    if not _extends_standalone_comment_run(target):
        return frozenset(lines)
    next_line = line + 1
    while next_line <= len(source_lines):
        comments = comments_by_line.get(next_line, ())
        comment = next((candidate for candidate in comments if candidate.standalone), None)
        if comment is None or not _continues_standalone_comment_run(target, comment):
            break
        lines.add(next_line)
        next_line += 1
    return frozenset(lines)


def _continues_standalone_comment_run(first: _CommentInfo, candidate: _CommentInfo) -> bool:
    return candidate.indent == first.indent and _extends_standalone_comment_run(candidate)


def _extends_standalone_comment_run(comment: _CommentInfo) -> bool:
    return comment.standalone and not _is_protected_comment(comment.text) and not _is_empty_or_hash_only(comment.text)


def _is_empty_or_hash_only(text: str) -> bool:
    return not text.strip("# \t\f")


def _is_protected_comment(text: str) -> bool:
    return _TYPE_DIRECTIVE_RE.match(text) is not None or _TOOL_DIRECTIVE_RE.match(text) is not None


def _has_conventional_comment_marker_spacing(text: str) -> bool:
    return text == "#" or text.startswith(("# ", "#\t", "#\f"))


def _local_blocks(local_lines: set[int]) -> tuple[tuple[int, ...], ...]:
    blocks: list[tuple[int, ...]] = []
    for line in sorted(local_lines):
        if blocks and line == blocks[-1][-1] + 1:
            blocks[-1] = (*blocks[-1], line)
        else:
            blocks.append((line,))
    return tuple(blocks)


def _is_pydocfmt_local_ignore(content: str) -> bool:
    match = directive_helpers.PYDOCFMT_BRACKET_RE.match(content)
    return match is not None and match.group("action").lower() == "ignore"
