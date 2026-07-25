"""PDF004 docstring-suspicious-unicode rule."""

# Future imports
from __future__ import annotations

# Standard library imports
import operator
import dataclasses
from collections import defaultdict
from typing import TYPE_CHECKING

# Third-party imports
import libcst as cst
import libcst.metadata as cst_metadata

# First-party imports
import pydocformatter.rules.edits as rule_edits
import pydocformatter.rules.violations as rule_violations
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.definition_helpers import source_text, string_literals, unicode_safety
from pydocformatter.rules.models import FixAvailability, RuleCacheBehavior, RuleCheckKind, RuleMetadata


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.definition import RuleContext


@dataclasses.dataclass(frozen=True)
class _MappedOccurrence:
    """One suspicious evaluated character mapped to physical source."""

    occurrence: unicode_safety.SuspiciousUnicodeOccurrence
    range: cst_metadata.CodeRange
    line_number: int


@rule_registration.register_rule_to(PDF_definition.PDF)
class PDF004DocstringSuspiciousUnicode(RuleBase):
    """Rule implementation for PDF004.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF004"),
        name="docstring-suspicious-unicode",
        message="Docstring contains suspicious Unicode",
        fix_availability=FixAvailability.SOMETIMES,
        stable_since="1.1.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
        cache_behavior=RuleCacheBehavior.FILE_LOCAL,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return suspicious Unicode violations for evaluated docstring values.

        Args:
            context (RuleContext): Current file context with parsed module and prepared PDF data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Grouped fixable and diagnostic-only findings.
        """
        data = PDF_definition.PDF.require_data(context)
        return tuple(violation for docstring in data.docstrings for violation in _violations_for_docstring(docstring, context=context))


def _violations_for_docstring(docstring: PDF_definition.DocstringInfo, *, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
    """Return grouped mapped findings and conservative fallbacks for one docstring."""
    occurrences = docstring.unicode_occurrences
    if not occurrences:
        return ()
    mapped, unmapped_code_points = _map_occurrences(docstring, occurrences=occurrences, context=context)
    first_occurrences: dict[int, unicode_safety.SuspiciousUnicodeOccurrence] = {}
    for occurrence in occurrences:
        first_occurrences.setdefault(occurrence.code_point, occurrence)
    violations: list[tuple[int, rule_violations.RuleViolation]] = []
    for code_point in unmapped_code_points:
        occurrence = first_occurrences[code_point]
        violations.append((
            occurrence.offset,
            rule_violations.diagnostic(PDF004DocstringSuspiciousUnicode.meta, tuple(line.line_number for line in docstring.physical_lines), instance_message=_message(occurrence)),
        ))
    groups: dict[tuple[int, int], list[_MappedOccurrence]] = defaultdict(list)
    for item in mapped:
        if item.occurrence.code_point not in unmapped_code_points:
            groups[item.occurrence.code_point, item.line_number].append(item)
    for group in groups.values():
        occurrence = group[0].occurrence
        changes = tuple(_change(item) for item in group) if all(item.occurrence.can_fix for item in group) else ()
        violation = (
            rule_violations.violation_for_grouped_planned_source_changes(PDF004DocstringSuspiciousUnicode.meta, changes, instance_message=_message(occurrence))
            if changes
            else rule_violations.diagnostic(PDF004DocstringSuspiciousUnicode.meta, (group[0].line_number,), instance_message=_message(occurrence))
        )
        violations.append((min(item.occurrence.offset for item in group), violation))
    return tuple(violation for _, violation in sorted(violations, key=operator.itemgetter(0)))


def _map_occurrences(
    docstring: PDF_definition.DocstringInfo, *, occurrences: tuple[unicode_safety.SuspiciousUnicodeOccurrence, ...], context: RuleContext
) -> tuple[tuple[_MappedOccurrence, ...], set[int]]:
    """Map occurrences through supported simple-string leaves."""
    parts = docstring.simple_string_parts
    if parts is None:
        return (), {occurrence.code_point for occurrence in occurrences}
    line_bounds = PDF_definition.line_bounds_for_context(context)
    mapped: list[_MappedOccurrence] = []
    unmapped_code_points: set[int] = set()
    occurrence_index = 0
    for part in parts:
        leaf_occurrences: list[unicode_safety.SuspiciousUnicodeOccurrence] = []
        while occurrence_index < len(occurrences) and occurrences[occurrence_index].offset < part.value_end:
            leaf_occurrences.append(occurrences[occurrence_index])
            occurrence_index += 1
        leaf_range = context.positions.get(part.node)
        if part.source_map is None or leaf_range is None:
            unmapped_code_points.update(occurrence.code_point for occurrence in leaf_occurrences)
        else:
            mapped.extend(
                _mapped_leaf_occurrence(occurrence, value_start=part.value_start, leaf=part.node, leaf_range=leaf_range, source_map=part.source_map, line_bounds=line_bounds)
                for occurrence in leaf_occurrences
            )
    if occurrence_index != len(occurrences):
        return (), {occurrence.code_point for occurrence in occurrences}
    return tuple(mapped), unmapped_code_points


def _mapped_leaf_occurrence(
    occurrence: unicode_safety.SuspiciousUnicodeOccurrence,
    *,
    value_start: int,
    leaf: cst.SimpleString,
    leaf_range: cst_metadata.CodeRange,
    source_map: string_literals.SimpleStringSourceMap,
    line_bounds: source_text.LineBounds,
) -> _MappedOccurrence:
    """Return one occurrence mapped to its character-producing source."""
    local_offset = occurrence.offset - value_start
    body_start = source_text.offset_for_position(leaf_range.start, line_bounds=line_bounds) + len(leaf.prefix) + len(leaf.quote)
    source_start = body_start + source_map.producing_source_starts[local_offset]
    source_end = source_start + len(source_map.fragments[local_offset].source)
    code_range = cst_metadata.CodeRange(start=source_text.position_for_offset(source_start, line_bounds=line_bounds), end=source_text.position_for_offset(source_end, line_bounds=line_bounds))
    return _MappedOccurrence(occurrence=occurrence, range=code_range, line_number=code_range.start.line)


def _change(item: _MappedOccurrence) -> rule_edits.PlannedSourceChange:
    """Return the narrow ASCII-space replacement for one mapped occurrence."""
    return rule_edits.PlannedSourceChange(edit=rule_edits.SourceEdit(range=item.range, replacement=" "), line_numbers=(item.line_number,), suppression_line_numbers=())


def _message(occurrence: unicode_safety.SuspiciousUnicodeOccurrence) -> str:
    """Return the instance message for an occurrence."""
    return f"Docstring contains suspicious Unicode character {occurrence.code_point_text}"
