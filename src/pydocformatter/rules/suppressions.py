"""Source directive parsing for pydocformatter finding suppression.

Attributes:
    SuppressionSelectorKey (TypeAlias): Line and selector-index pair used to track whether each parsed suppression
        selector was consumed.
"""

# Future imports
from __future__ import annotations

# Standard library imports
import re
import dataclasses
from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING

# Third-party imports
import libcst as cst
import libcst.metadata as cst_metadata

# First-party imports
import pydocformatter.rules.violations as rule_violations
import pydocformatter.rules.definition_helpers.directives as directive_helpers
from pydocformatter.rules.codes import ALL_RULE_SELECTOR_TAG, RuleCode
from pydocformatter.rules.models import RuleFinding


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.collection import RuleCollection
    from pydocformatter.rules.models import RuleMetadata


SuppressionSelectorKey = tuple[int, int]

_TYPE_DIRECTIVE_RE = re.compile(r"^#\s*type\s*:", re.IGNORECASE)
_TOOL_DIRECTIVE_RE = re.compile(
    r"^#\s*(?:noqa\b|nosec\b|nosemgrep\b|pydocfmt\b|pylint\b|pyright\b|mypy\b|ty\s*:|ruff\b|flake8\b|fmt\s*:|isort\s*:|pragma\b|noinspection\b|language\s*=|@formatter\s*:)", re.IGNORECASE
)
_EMPTY_RULE_CODES: frozenset[RuleCode] = frozenset()


@dataclasses.dataclass(frozen=True)
class SuppressionViolationFilterResult:
    """Unsuppressed violations and selector keys used while filtering them.

    Attributes:
        violations (tuple[rule_violations.RuleViolation, ...]): Violations that no source directive suppressed.
        used_selector_keys (frozenset[SuppressionSelectorKey]): Directive selector entries that suppressed at least one
            finding.
    """

    violations: tuple[rule_violations.RuleViolation, ...]
    used_selector_keys: frozenset[SuppressionSelectorKey]


@dataclasses.dataclass(frozen=True)
class SuppressionIndex:
    """Parsed pydocformatter suppression directives for one source state.

    Attributes:
        directives (tuple[SuppressionDirective, ...]): Suppression directives collected from comments outside strings.
    """

    directives: tuple[SuppressionDirective, ...]

    def used_selector_keys(
        self, finding: RuleFinding, *, active_category_prefix: str, authorized_expression_ranges: frozenset[cst_metadata.CodeRange] = frozenset()
    ) -> frozenset[SuppressionSelectorKey]:
        """Return stable selector keys used by suppressing one finding.

        Args:
            finding (RuleFinding): Finding whose suppression coverage should be checked.
            active_category_prefix (str): Prefix of the category currently filtering findings.
            authorized_expression_ranges (frozenset[cst_metadata.CodeRange]): Exact string-expression ranges eligible
                for expanded coverage in the active category.

        Returns:
            frozenset[SuppressionSelectorKey]: Directive selector keys that suppress the finding.
        """
        used: set[SuppressionSelectorKey] = set()
        for directive_index, directive in enumerate(self.directives):
            used.update(
                directive.used_selector_keys(finding, directive_index=directive_index, active_category_prefix=active_category_prefix, authorized_expression_ranges=authorized_expression_ranges)
            )
        return frozenset(used)

    def unused_findings(self, used_selector_keys: frozenset[SuppressionSelectorKey], *, selected_rule_codes: frozenset[RuleCode], rule: RuleMetadata) -> tuple[RuleFinding, ...]:
        """Return PCF101-style findings for invalid or unused audited selectors.

        Args:
            used_selector_keys (frozenset[SuppressionSelectorKey]): Selector keys consumed while filtering findings.
            selected_rule_codes (frozenset[RuleCode]): Rules active for the current file after selection and ignores.
            rule (RuleMetadata): PCF101 metadata to attach to unused-suppression findings.

        Returns:
            tuple[RuleFinding, ...]: Diagnostics for invalid selectors and selected-but-unused suppressions.
        """
        findings: list[RuleFinding] = []
        for directive_index, directive in enumerate(self.directives):
            findings.extend(directive.unused_findings(directive_index=directive_index, used_selector_keys=used_selector_keys, selected_rule_codes=selected_rule_codes, rule=rule))
        return tuple(findings)

    def filter_violations(
        self, violations: tuple[rule_violations.RuleViolation, ...], *, active_category_prefix: str, authorized_expression_ranges: frozenset[cst_metadata.CodeRange] = frozenset()
    ) -> SuppressionViolationFilterResult:
        """Return unsuppressed violations and selector keys used during filtering.

        Args:
            violations (tuple[rule_violations.RuleViolation, ...]): Rule violations before source suppressions are
                applied.
            active_category_prefix (str): Prefix of the category currently filtering violations.
            authorized_expression_ranges (frozenset[cst_metadata.CodeRange]): Exact string-expression ranges eligible
                for expanded coverage in the active category.

        Returns:
            SuppressionViolationFilterResult: Remaining violations plus selector keys that were consumed.
        """
        unsuppressed_violations: list[rule_violations.RuleViolation] = []
        used_selector_keys: set[SuppressionSelectorKey] = set()
        for violation in violations:
            finding_used_selector_keys = self.used_selector_keys(violation.finding, active_category_prefix=active_category_prefix, authorized_expression_ranges=authorized_expression_ranges)
            if finding_used_selector_keys:
                used_selector_keys.update(finding_used_selector_keys)
            else:
                unsuppressed_violations.append(violation)
        return SuppressionViolationFilterResult(violations=tuple(unsuppressed_violations), used_selector_keys=frozenset(used_selector_keys))


@dataclasses.dataclass(frozen=True)
class SourceDirectiveIndexes:
    """Suppression and bracket-directive indexes for one exact source state.

    Attributes:
        suppression_index (SuppressionIndex): Parsed source suppressions.
        bracket_directive_index (directive_helpers.BracketDirectiveIndex): Bracket directives indexed by comment range.
    """

    suppression_index: SuppressionIndex
    bracket_directive_index: directive_helpers.BracketDirectiveIndex


@dataclasses.dataclass(frozen=True)
class SuppressionDirective:
    """One parsed source suppression directive.

    Attributes:
        line (int): One-based source line where the directive comment appears.
        selectors (tuple[SuppressionSelector, ...]): Parsed selector entries carried by the directive.
    """

    line: int
    selectors: tuple[SuppressionSelector, ...]

    def used_selector_keys(
        self, finding: RuleFinding, *, directive_index: int, active_category_prefix: str, authorized_expression_ranges: frozenset[cst_metadata.CodeRange] = frozenset()
    ) -> set[SuppressionSelectorKey]:
        """Return selector keys used by suppressing this finding.

        Args:
            finding (RuleFinding): Finding whose suppression coverage should be checked.
            directive_index (int): Position of this directive in the source-level directive tuple.
            active_category_prefix (str): Prefix of the category currently filtering findings.
            authorized_expression_ranges (frozenset[cst_metadata.CodeRange]): Exact string-expression ranges eligible
                for expanded coverage in the active category.

        Returns:
            set[SuppressionSelectorKey]: Selector keys from this directive that suppress the finding.
        """
        return {
            (directive_index, selector_index)
            for selector_index, selector in enumerate(self.selectors)
            if selector.suppresses(finding, active_category_prefix=active_category_prefix, authorized_expression_ranges=authorized_expression_ranges)
        }

    def unused_findings(self, *, directive_index: int, used_selector_keys: frozenset[SuppressionSelectorKey], selected_rule_codes: frozenset[RuleCode], rule: RuleMetadata) -> list[RuleFinding]:
        """Return unused or invalid findings for audited selectors.

        Args:
            directive_index (int): Position of this directive in the source-level directive tuple.
            used_selector_keys (frozenset[SuppressionSelectorKey]): Selector keys consumed while filtering findings.
            selected_rule_codes (frozenset[RuleCode]): Rules active for the current file after selection and ignores.
            rule (RuleMetadata): PCF101 metadata to attach to unused-suppression findings.

        Returns:
            list[RuleFinding]: Diagnostics for invalid selectors and selected-but-unused suppressions on this directive.
        """
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
    """One selector entry inside a suppression directive.

    Attributes:
        text (str): Original selector text used for unused-suppression messages.
        matched_codes (frozenset[RuleCode]): Concrete rules covered by the selector.
        coverage_lines (frozenset[int]): One-based source lines that the directive is allowed to suppress.
        audit (bool): Whether PCF101 should report this selector when it is invalid or unused.
        invalid_message (str | None): Precomputed diagnostic text for selectors that failed to parse or match rules.
        candidate_expression_ranges (tuple[cst_metadata.CodeRange, ...]): Prefix-neutral string-expression ranges that
            can expand coverage when authorized by the active rule category.
        directive_line (int | None): Physical line available to rules that opt into directive self-suppression.
    """

    text: str
    matched_codes: frozenset[RuleCode]
    coverage_lines: frozenset[int]
    audit: bool
    invalid_message: str | None = None
    candidate_expression_ranges: tuple[cst_metadata.CodeRange, ...] = ()
    directive_line: int | None = None

    def suppresses(self, finding: RuleFinding, *, active_category_prefix: str, authorized_expression_ranges: frozenset[cst_metadata.CodeRange] = frozenset()) -> bool:
        """Return whether this selector suppresses one finding.

        Args:
            finding (RuleFinding): Finding to compare against matched rule codes and coverage lines.
            active_category_prefix (str): Prefix of the category currently filtering findings.
            authorized_expression_ranges (frozenset[cst_metadata.CodeRange]): Exact string-expression ranges eligible
                for expanded coverage in the active category.

        Returns:
            bool: Whether the selector covers the finding's rule and at least one complete suppression target.
        """
        if self.invalid_message is not None:
            return False
        if finding.rule.code not in self.matched_codes:
            return False
        coverage_options = [self.coverage_lines]
        if self.directive_line is not None and finding.rule.allows_directive_self_suppression:
            coverage_options.append(frozenset((self.directive_line,)))
        if finding.rule.code.prefix == active_category_prefix:
            coverage_options.extend(self.coverage_lines | _range_lines(code_range) for code_range in self.candidate_expression_ranges if code_range in authorized_expression_ranges)
        return any(bool(target) and set(target).issubset(coverage_lines) for target in finding.suppression_targets for coverage_lines in coverage_options)


@dataclasses.dataclass(frozen=True)
class _CommentInfo:
    """Comment placement information used to attach directives."""

    line: int
    column: int
    indent: str
    text: str
    standalone: bool
    pydocfmt_local: bool
    range: cst_metadata.CodeRange
    bracket_directive: directive_helpers.BracketDirective | None

    @property
    def content(self) -> str:
        """Stripped comment content without the leading hash."""
        return self.text.removeprefix("#").strip()


@dataclasses.dataclass(frozen=True)
class _StringComponent:
    """One simple string token and its complete containing expression.

    Attributes:
        token_range (cst_metadata.CodeRange): Physical range of the simple string token.
        expression_range (cst_metadata.CodeRange): Physical range of the complete containing string expression.
    """

    token_range: cst_metadata.CodeRange
    expression_range: cst_metadata.CodeRange


class _SourceCollector(cst.CSTVisitor):
    """Collect comments and string-component relationships for suppression attachment."""

    def __init__(self, positions: Mapping[cst.CSTNode, cst_metadata.CodeRange], source_lines: tuple[str, ...], collection: RuleCollection) -> None:
        """Initialize empty source object collections."""
        self.positions = positions
        self.source_lines = source_lines
        self.collection = collection
        self.comments: list[_CommentInfo] = []
        self.string_components: list[_StringComponent] = []
        self.bracket_directives_by_range: dict[cst_metadata.CodeRange, directive_helpers.BracketDirective] = {}
        self._expression_ranges: list[cst_metadata.CodeRange] = []

    def visit_Comment(self, node: cst.Comment) -> None:
        """Collect one comment node."""
        code_range = self.positions[node]
        source_line = self.source_lines[code_range.start.line - 1].rstrip("\r\n")
        line_prefix = source_line[: code_range.start.column]
        bracket_directive = directive_helpers.parse_bracket_directive(node.value, collection=self.collection, comment_range=code_range)
        if bracket_directive is not None:
            self.bracket_directives_by_range[code_range] = bracket_directive
        self.comments.append(
            _CommentInfo(
                line=code_range.start.line,
                column=code_range.start.column,
                indent=line_prefix if not line_prefix.strip(" \t\f") else line_prefix[: len(line_prefix) - len(line_prefix.lstrip(" \t\f"))],
                text=node.value,
                standalone=not line_prefix.strip(" \t\f"),
                pydocfmt_local=_is_pydocfmt_local_ignore(bracket_directive),
                range=code_range,
                bracket_directive=bracket_directive,
            )
        )

    def visit_SimpleString(self, node: cst.SimpleString) -> None:
        """Collect one string token and its complete containing expression."""
        token_range = self.positions[node]
        self.string_components.append(_StringComponent(token_range=token_range, expression_range=self._expression_ranges[0] if self._expression_ranges else token_range))

    def visit_ConcatenatedString(self, node: cst.ConcatenatedString) -> None:
        """Enter one nested implicit-concatenation range."""
        code_range = self.positions[node]
        self._expression_ranges.append(code_range)

    def leave_ConcatenatedString(self, original_node: cst.ConcatenatedString) -> None:
        """Leave one nested implicit-concatenation range."""
        del original_node
        self._expression_ranges.pop()


def source_directive_indexes(module: cst.Module, *, positions: Mapping[cst.CSTNode, cst_metadata.CodeRange], source_lines: tuple[str, ...], collection: RuleCollection) -> SourceDirectiveIndexes:
    """Return suppression and bracket-directive indexes for a module source state.

    Args:
        module (cst.Module): Parsed source module to scan for comments and string-expression topology.
        positions (Mapping[cst.CSTNode, cst_metadata.CodeRange]): LibCST position metadata for excluding
            string-contained comments.
        source_lines (tuple[str, ...]): Physical source lines used to recover exact comment text.
        collection (RuleCollection): Rule collection used to resolve suppression selectors to concrete rule codes.

    Returns:
        SourceDirectiveIndexes: Both directive indexes built by one source traversal.
    """
    if not any("#" in line for line in source_lines):
        return SourceDirectiveIndexes(suppression_index=SuppressionIndex(directives=()), bracket_directive_index=directive_helpers.BracketDirectiveIndex(by_range={}))
    collector = _SourceCollector(positions, source_lines, collection)
    module.visit(collector)
    comments = tuple(sorted(collector.comments, key=lambda comment: (comment.line, comment.column)))
    string_components_by_end_line = _string_components_by_end_line(collector.string_components)
    expression_ranges_by_start_line = _expression_ranges_by_start_line(collector.string_components)
    comments_by_line = _comments_by_line(comments)
    directives: list[SuppressionDirective] = []
    directives.extend(_line_directives(comments, string_components_by_end_line=string_components_by_end_line, collection=collection))
    directives.extend(_pydocfmt_file_directives(comments, source_line_count=len(source_lines), collection=collection))
    directives.extend(_pydocfmt_local_directives(comments, expression_ranges_by_start_line=expression_ranges_by_start_line, comments_by_line=comments_by_line, source_lines=source_lines))
    return SourceDirectiveIndexes(
        suppression_index=SuppressionIndex(directives=tuple(directives)), bracket_directive_index=directive_helpers.BracketDirectiveIndex(by_range=collector.bracket_directives_by_range)
    )


def _line_directives(comments: tuple[_CommentInfo, ...], *, string_components_by_end_line: Mapping[int, tuple[_StringComponent, ...]], collection: RuleCollection) -> tuple[SuppressionDirective, ...]:
    """Return inline pydocfmt and noqa suppression directives."""
    directives: list[SuppressionDirective] = []
    for comment in comments:
        bracket_directive = comment.bracket_directive
        if not comment.standalone and bracket_directive is not None and bracket_directive.tool is directive_helpers.DirectiveTool.PYDOCFMT and bracket_directive.action == "ignore":
            coverage_lines = _line_coverage(comment.line)
            candidate_expression_ranges = _inline_candidate_expression_ranges(comment, coverage_lines=coverage_lines, string_components=string_components_by_end_line.get(comment.line, ()))
            selectors = _selectors_from_bracket(bracket_directive, coverage_lines=coverage_lines, candidate_expression_ranges=candidate_expression_ranges, audit=True)
            directives.append(SuppressionDirective(line=comment.line, selectors=selectors))
            continue
        match = directive_helpers.NOQA_RE.match(comment.content)
        if match is None:
            continue
        if not _has_conventional_comment_marker_spacing(comment.text):
            continue
        coverage_lines = _line_coverage(comment.line)
        candidate_expression_ranges = _inline_candidate_expression_ranges(comment, coverage_lines=coverage_lines, string_components=string_components_by_end_line.get(comment.line, ()))
        selectors = _selectors(
            match.group("selectors"),
            default_text=ALL_RULE_SELECTOR_TAG,
            coverage_lines=coverage_lines,
            candidate_expression_ranges=candidate_expression_ranges,
            collection=collection,
            audit=False,
            include_invalid=False,
            audit_known_explicit=True,
        )
        if selectors:
            directives.append(SuppressionDirective(line=comment.line, selectors=selectors))
    return tuple(directives)


def _pydocfmt_file_directives(comments: tuple[_CommentInfo, ...], *, source_line_count: int, collection: RuleCollection) -> tuple[SuppressionDirective, ...]:
    """Return file-wide pydocfmt suppression directives."""
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
        elif (bracket_directive := comment.bracket_directive) is not None and bracket_directive.tool is directive_helpers.DirectiveTool.PYDOCFMT and bracket_directive.action == "file-ignore":
            selectors = _selectors_from_bracket(bracket_directive, coverage_lines=coverage_lines, audit=True)
            directives.append(SuppressionDirective(line=comment.line, selectors=selectors))
            continue
        else:
            continue
        selectors = _selectors(selectors_text, default_text=ALL_RULE_SELECTOR_TAG, coverage_lines=coverage_lines, collection=collection, audit=True, include_invalid=True)
        directives.append(SuppressionDirective(line=comment.line, selectors=selectors))
    return tuple(directives)


def _pydocfmt_local_directives(
    comments: tuple[_CommentInfo, ...],
    *,
    expression_ranges_by_start_line: Mapping[int, tuple[cst_metadata.CodeRange, ...]],
    comments_by_line: dict[int, tuple[_CommentInfo, ...]],
    source_lines: tuple[str, ...],
) -> tuple[SuppressionDirective, ...]:
    """Return local pydocfmt suppression directives attached to following source."""
    local_lines = {comment.line for comment in comments if comment.standalone and comment.pydocfmt_local}
    directives: list[SuppressionDirective] = []
    for block in _local_blocks(local_lines):
        target_line = block[-1] + 1
        candidate_expression_ranges = expression_ranges_by_start_line.get(target_line, ())
        for line in block:
            comment = next(comment for comment in comments_by_line[line] if comment.standalone and comment.pydocfmt_local)
            bracket_directive = comment.bracket_directive
            if bracket_directive is None or bracket_directive.tool is not directive_helpers.DirectiveTool.PYDOCFMT or bracket_directive.action != "ignore":
                continue
            selectors = tuple(
                _local_bracket_selector(
                    token, directive_line=line, target_line=target_line, candidate_expression_ranges=candidate_expression_ranges, comments_by_line=comments_by_line, source_lines=source_lines
                )
                for token in bracket_directive.retained_tokens
            )
            if not selectors:
                selectors = (SuppressionSelector(text="", matched_codes=frozenset(), coverage_lines=frozenset(), audit=True, invalid_message="Invalid pydocfmt suppression selector ''"),)
            directives.append(SuppressionDirective(line=line, selectors=selectors))
    return tuple(directives)


def _local_bracket_selector(
    token: directive_helpers.BracketDirectiveToken,
    *,
    directive_line: int,
    target_line: int,
    candidate_expression_ranges: tuple[cst_metadata.CodeRange, ...],
    comments_by_line: dict[int, tuple[_CommentInfo, ...]],
    source_lines: tuple[str, ...],
) -> SuppressionSelector:
    """Return one selector for a local suppression directive."""
    matched_codes, invalid_message = _matched_codes_for_bracket_token(token)
    if invalid_message is not None:
        return SuppressionSelector(text=token.normalized, matched_codes=frozenset(), coverage_lines=frozenset(), audit=True, invalid_message=invalid_message)
    prefixes = {code.prefix for code in matched_codes}
    coverage_lines: set[int] = set()
    if "PCF" in prefixes or token.normalized == ALL_RULE_SELECTOR_TAG:
        coverage_lines.update(_comment_target_coverage(target_line, comments_by_line=comments_by_line, source_lines=source_lines))
    return SuppressionSelector(
        text=token.normalized, matched_codes=matched_codes, coverage_lines=frozenset(coverage_lines), audit=True, candidate_expression_ranges=candidate_expression_ranges, directive_line=directive_line
    )


def _selectors_from_bracket(
    directive: directive_helpers.BracketDirective, *, coverage_lines: frozenset[int], audit: bool, candidate_expression_ranges: tuple[cst_metadata.CodeRange, ...] = ()
) -> tuple[SuppressionSelector, ...]:
    """Return suppression entries from one shared pydocfmt bracket model."""
    selectors: list[SuppressionSelector] = []
    for token in directive.retained_tokens:
        matched_codes, invalid_message = _matched_codes_for_bracket_token(token)
        selectors.append(
            SuppressionSelector(
                text=token.normalized, matched_codes=matched_codes, coverage_lines=coverage_lines, audit=audit, invalid_message=invalid_message, candidate_expression_ranges=candidate_expression_ranges
            )
        )
    if not selectors:
        selectors.append(
            SuppressionSelector(
                text="",
                matched_codes=frozenset(),
                coverage_lines=coverage_lines,
                audit=audit,
                invalid_message="Invalid pydocfmt suppression selector ''",
                candidate_expression_ranges=candidate_expression_ranges,
            )
        )
    return tuple(selectors)


def _matched_codes_for_bracket_token(token: directive_helpers.BracketDirectiveToken) -> tuple[frozenset[RuleCode], str | None]:
    """Return concrete codes and audit diagnostics for one shared pydocfmt token."""
    if token.kind in {directive_helpers.DirectiveTokenKind.PYDOCFMT_EXACT_CODE, directive_helpers.DirectiveTokenKind.PYDOCFMT_EXACT_NAME, directive_helpers.DirectiveTokenKind.PYDOCFMT_BROAD_CODE}:
        if not token.matched_codes:
            raise AssertionError("Known pydocfmt directive token must match at least one rule code")
        return token.matched_codes, None
    if token.kind is directive_helpers.DirectiveTokenKind.UNKNOWN:
        return _EMPTY_RULE_CODES, f"Unknown pydocfmt suppression selector '{token.normalized}'"
    return _EMPTY_RULE_CODES, f"Invalid pydocfmt suppression selector '{token.normalized}'"


def _selectors(
    selectors_text: str | None,
    *,
    default_text: str,
    coverage_lines: frozenset[int],
    collection: RuleCollection,
    audit: bool,
    include_invalid: bool,
    audit_known_explicit: bool = False,
    candidate_expression_ranges: tuple[cst_metadata.CodeRange, ...] = (),
) -> tuple[SuppressionSelector, ...]:
    """Return parsed selector entries for one suppression directive."""
    explicit = selectors_text is not None
    texts = (default_text,) if selectors_text is None else _selector_texts(selectors_text, include_empty=include_invalid)
    selectors: list[SuppressionSelector] = []
    for text in texts:
        matched_codes, invalid_message = _matched_codes(text, include_invalid=include_invalid, collection=collection)
        if invalid_message is not None:
            selectors.append(
                SuppressionSelector(
                    text=text, matched_codes=frozenset(), coverage_lines=coverage_lines, audit=True, invalid_message=invalid_message, candidate_expression_ranges=candidate_expression_ranges
                )
            )
        elif matched_codes:
            selectors.append(
                SuppressionSelector(
                    text=text, matched_codes=matched_codes, coverage_lines=coverage_lines, audit=audit or (audit_known_explicit and explicit), candidate_expression_ranges=candidate_expression_ranges
                )
            )
    return tuple(selectors)


def _selector_texts(selectors_text: str, *, include_empty: bool) -> tuple[str, ...]:
    """Return normalized selector text entries from a comma-separated list."""
    texts = tuple(dict.fromkeys(text.strip().upper() for text in selectors_text.split(",") if text.strip()))
    if texts:
        return texts
    return ("",) if include_empty else ()


def _matched_codes(text: str, *, include_invalid: bool, collection: RuleCollection) -> tuple[frozenset[RuleCode], str | None]:
    """Return rule codes matched by a suppression selector."""
    resolution = collection.resolve_selector(text)
    if resolution.selector is None:
        return _EMPTY_RULE_CODES, f"Invalid pydocfmt suppression selector '{text}'" if include_invalid else None
    matched_codes = frozenset(rule.meta.code for rule in resolution.matching_rules)
    if not matched_codes:
        return _EMPTY_RULE_CODES, f"Unknown pydocfmt suppression selector '{text}'" if include_invalid else None
    return matched_codes, None


def _comments_by_line(comments: Iterable[_CommentInfo]) -> dict[int, tuple[_CommentInfo, ...]]:
    """Return comments grouped by their physical source line."""
    grouped: dict[int, list[_CommentInfo]] = {}
    for comment in comments:
        grouped.setdefault(comment.line, []).append(comment)
    return {line: tuple(sorted(line_comments, key=lambda comment: comment.column)) for line, line_comments in grouped.items()}


def _string_components_by_end_line(components: Iterable[_StringComponent]) -> dict[int, tuple[_StringComponent, ...]]:
    """Return string components indexed by their token-ending line."""
    grouped: dict[int, list[_StringComponent]] = {}
    for component in components:
        grouped.setdefault(component.token_range.end.line, []).append(component)
    return {line: tuple(line_components) for line, line_components in grouped.items()}


def _expression_ranges_by_start_line(components: Iterable[_StringComponent]) -> dict[int, tuple[cst_metadata.CodeRange, ...]]:
    """Return unique complete string-expression ranges indexed by their starting line."""
    grouped: dict[int, dict[cst_metadata.CodeRange, None]] = {}
    for component in components:
        expression_range = component.expression_range
        grouped.setdefault(expression_range.start.line, {})[expression_range] = None
    return {line: tuple(line_ranges) for line, line_ranges in grouped.items()}


def _line_coverage(line: int) -> frozenset[int]:
    """Return source lines covered by a line-level suppression."""
    return frozenset((line,))


def _inline_candidate_expression_ranges(comment: _CommentInfo, *, coverage_lines: frozenset[int], string_components: tuple[_StringComponent, ...]) -> tuple[cst_metadata.CodeRange, ...]:
    """Return prefix-neutral expression candidates for an inline string-token directive."""
    if comment.standalone:
        return ()
    expression_ranges: list[cst_metadata.CodeRange] = []
    for component in string_components:
        token_range = component.token_range
        expression_range = component.expression_range
        if token_range.end.line == comment.line and token_range.end.column <= comment.column and _range_lines(expression_range) != coverage_lines and expression_range not in expression_ranges:
            expression_ranges.append(expression_range)
    return tuple(expression_ranges)


def _range_lines(code_range: cst_metadata.CodeRange) -> frozenset[int]:
    """Return all physical lines occupied by a source range."""
    return frozenset(range(code_range.start.line, code_range.end.line + 1))


def _comment_target_coverage(line: int, *, comments_by_line: dict[int, tuple[_CommentInfo, ...]], source_lines: tuple[str, ...]) -> frozenset[int]:
    """Return comment lines covered by a local suppression target."""
    line_comments = comments_by_line.get(line, ())
    target = next(iter(line_comments), None)
    if target is None:
        return frozenset[int]()
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
    """Return whether a comment continues a standalone comment block."""
    return candidate.indent == first.indent and _extends_standalone_comment_run(candidate)


def _extends_standalone_comment_run(comment: _CommentInfo) -> bool:
    """Return whether a comment can participate in a standalone comment block."""
    return comment.standalone and not _is_protected_comment(comment.text) and not _is_empty_or_hash_only(comment.text)


def _is_empty_or_hash_only(text: str) -> bool:
    """Return whether comment text has no content beyond marker characters."""
    return not text.strip("# \t\f")


def _is_protected_comment(text: str) -> bool:
    """Return whether comment text is reserved for another tool or directive."""
    return _TYPE_DIRECTIVE_RE.match(text) is not None or _TOOL_DIRECTIVE_RE.match(text) is not None


def _has_conventional_comment_marker_spacing(text: str) -> bool:
    """Return whether a comment marker uses conventional spacing."""
    return text == "#" or text.startswith(("# ", "#\t", "#\f"))


def _local_blocks(local_lines: set[int]) -> tuple[tuple[int, ...], ...]:
    """Return contiguous blocks of local pydocfmt suppression comment lines."""
    blocks: list[tuple[int, ...]] = []
    for line in sorted(local_lines):
        if blocks and line == blocks[-1][-1] + 1:
            blocks[-1] = (*blocks[-1], line)
        else:
            blocks.append((line,))
    return tuple(blocks)


def _is_pydocfmt_local_ignore(directive: directive_helpers.BracketDirective | None) -> bool:
    """Return whether a parsed comment is a local pydocfmt ignore directive."""
    return directive is not None and directive.tool is directive_helpers.DirectiveTool.PYDOCFMT and directive.action == "ignore"
