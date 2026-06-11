from __future__ import annotations

import dataclasses

import libcst as cst

import pydocformatter.cli.settings_check as settings_check
import pydocformatter.rules.definition_helpers.string_literals as string_literals
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
import pydocformatter.rules.edits as rule_edits
import pydocformatter.rules.registration as rule_registration
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext, RuleFixResult
from pydocformatter.rules.models import FixAvailability, RuleFinding, RuleMetadata


@rule_registration.register_rule_to(PDF_definition.PDF)
class PDF002IncorrectIndentation(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PDF002"),
        name="incorrect-indentation",
        message="Docstring line is incorrectly indented",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="0.3.0",
        setting_effects=(),
        incompatible_with=(),
    )

    @classmethod
    def check(cls, context: RuleContext) -> tuple[RuleFinding, ...]:
        """Return findings for safely normalizable docstring indentation."""
        return rule_edits.findings_for_planned_source_changes(cls.meta, _planned_changes(context))

    @classmethod
    def fix(cls, context: RuleContext) -> RuleFixResult:
        """Normalize docstring indentation."""
        changes = _planned_changes(context)
        if not changes:
            return RuleFixResult(module=context.module)
        module = rule_edits.apply_planned_source_changes(context.module, changes)
        findings = rule_edits.findings_for_planned_source_changes(cls.meta, changes)
        return RuleFixResult(module=module, fixed_findings=findings)


def _planned_changes(context: RuleContext) -> tuple[rule_edits.PlannedSourceChange, ...]:
    """Return all safe docstring indentation changes."""
    data = PDF_definition.PDF.require_data(context)
    lines = PDF_definition.source_lines(context.module.code)
    return tuple(change for docstring in data.docstrings if (change := _planned_change_for_docstring(docstring, context=context, source_lines=lines)) is not None)


def _planned_change_for_docstring(docstring: PDF_definition.DocstringInfo, *, context: RuleContext, source_lines: list[str]) -> rule_edits.PlannedSourceChange | None:
    """Return one whole-literal replacement for a docstring."""
    if not _is_candidate(docstring):
        return None
    # Re-check after candidate filtering so mypy narrows the node type.
    if not isinstance(docstring.node, cst.SimpleString):
        return None
    fragments = string_literals.value_fragments_for_simple_string(docstring.node, line_ending=context.line_ending)
    if fragments is None:
        return None
    canonical_margin = _canonical_margin(docstring, context=context, source_lines=source_lines)
    line_targets = _target_raw_lines(docstring, canonical_margin=canonical_margin, context=context)
    replacements = tuple(
        rule_edits.PlannedTextReplacement(
            start_offset=line.start_offset,
            end_offset=line.end_offset,
            text=_source_for_target_line(line, target, fragments=fragments),
            line_numbers=(line.source_line_number,),
        )
        for line, target in zip(docstring.structure.lines, line_targets)
        if line.index > 0 and line.source_line_number is not None and line.raw_text != target.raw_text
    )
    if not replacements:
        return None

    value_lines = [line_targets[line.index].raw_text if line.index > 0 else line.raw_text for line in docstring.structure.lines]
    value = _join_value_lines(docstring, value_lines)
    source_chunks: list[str] = []
    cursor = 0
    for replacement in replacements:
        source_chunks.append(string_literals.source_for_value_slice(fragments, cursor, replacement.start_offset))
        source_chunks.append(replacement.text)
        cursor = replacement.end_offset
    source_chunks.append(string_literals.source_for_value_slice(fragments, cursor, len(fragments)))
    rendered = string_literals.render_simple_string_from_body_source(docstring.node.prefix, docstring.node.quote, "".join(source_chunks), expected_value=value)
    if rendered is None or rendered == docstring.source:
        return None
    return rule_edits.PlannedSourceChange(
        edit=rule_edits.SourceEdit(range=docstring.range, replacement=rendered),
        line_numbers=tuple(line_number for replacement in replacements for line_number in replacement.line_numbers),
    )


def _is_candidate(docstring: PDF_definition.DocstringInfo) -> bool:
    """Return whether a docstring has unambiguous rewritable indentation."""
    return (
        docstring.kind is PDF_definition.DocstringKind.SIMPLE
        and isinstance(docstring.node, cst.SimpleString)
        and len(docstring.structure.lines) > 1
        and all(line.source_line_number is not None for line in docstring.structure.lines)
    )


@dataclasses.dataclass(frozen=True)
class _LineTarget:
    """Target raw line text and the visual margin stripped from its suffix."""

    raw_text: str
    strip_width: int
    prefix: str


def _canonical_margin(docstring: PDF_definition.DocstringInfo, *, context: RuleContext, source_lines: list[str]) -> str:
    """Return the raw indentation margin for continuation lines."""
    source_line = source_lines[docstring.range.start.line - 1]
    line_indent = source_line[: len(source_line) - len(source_line.lstrip(" \t"))]
    if isinstance(docstring.statement, cst.SimpleStatementSuite):
        return f"{line_indent}{PDF_definition.indent_unit(context.settings)}"
    prefix = source_line[: docstring.range.start.column]
    return prefix if prefix.strip() == "" else line_indent


def _target_raw_lines(docstring: PDF_definition.DocstringInfo, *, canonical_margin: str, context: RuleContext) -> tuple[_LineTarget, ...]:
    """Return target evaluated raw text for each docstring line."""
    targets: list[_LineTarget | None] = [None] * len(docstring.structure.lines)
    targets[0] = _LineTarget(docstring.structure.lines[0].raw_text, 0, "")
    for line in docstring.structure.lines[1:]:
        if not line.raw_text.strip():
            target = canonical_margin if _is_same_line_closing_delimiter_prefix(docstring, line) else _target_blank_line(line.raw_text, canonical_margin=canonical_margin)
            targets[line.index] = _LineTarget(target, 0, "")

    convention_lines = _apply_convention_targets(targets, docstring, canonical_margin=canonical_margin, context=context)
    plain_indexes = tuple(line.index for line in docstring.structure.lines[1:] if targets[line.index] is None and line.index not in convention_lines and line.raw_text.strip())
    _apply_common_margin_targets(targets, docstring, plain_indexes, canonical_margin)

    for line in docstring.structure.lines[1:]:
        if targets[line.index] is None:
            targets[line.index] = _LineTarget(line.raw_text, 0, "")
    return tuple(target if target is not None else _LineTarget("", 0, "") for target in targets)


def _target_blank_line(raw_text: str, *, canonical_margin: str) -> str:
    """Return the accepted blank-line indentation state."""
    if raw_text in {"", canonical_margin}:
        return raw_text
    if raw_text.startswith(canonical_margin):
        return canonical_margin
    return ""


def _is_same_line_closing_delimiter_prefix(docstring: PDF_definition.DocstringInfo, line: PDF_definition.DocstringValueLine) -> bool:
    """Return whether a whitespace-only value line prefixes the closing quotes."""
    return line.index == len(docstring.structure.lines) - 1 and not docstring.value.endswith(("\r\n", "\r", "\n"))


def _apply_convention_targets(
    targets: list[_LineTarget | None],
    docstring: PDF_definition.DocstringInfo,
    *,
    canonical_margin: str,
    context: RuleContext,
) -> set[int]:
    """Apply convention-aware indentation targets and return covered lines."""
    if docstring.structure.convention not in {settings_check.DocstringConvention.GOOGLE, settings_check.DocstringConvention.NUMPY}:
        return set()
    covered: set[int] = set()
    unit = PDF_definition.indent_unit(context.settings)
    for section in docstring.structure.sections:
        if section.start_line == 0:
            section_indexes = range(section.start_line, section.end_line)
            _preserve_targets(targets, docstring, section_indexes)
            covered.update(section_indexes)
            continue
        header_end = section.content_start_line
        header_indexes = range(section.start_line, header_end)
        _apply_fixed_prefix_targets(targets, docstring, header_indexes, canonical_margin)
        covered.update(header_indexes)
        entry_indexes: set[int] = set()
        for entry in section.entries:
            prefix = f"{canonical_margin}{unit}" if docstring.structure.convention == settings_check.DocstringConvention.GOOGLE else canonical_margin
            _apply_fixed_prefix_targets(targets, docstring, (entry.start_line,), prefix)
            continuation_prefix = f"{canonical_margin}{unit}{unit}" if docstring.structure.convention == settings_check.DocstringConvention.GOOGLE else f"{canonical_margin}{unit}"
            _apply_fixed_prefix_targets(targets, docstring, range(entry.start_line + 1, entry.end_line), continuation_prefix)
            entry_indexes.update(range(entry.start_line, entry.end_line))
        covered.update(entry_indexes)
        other_indexes = tuple(index for index in range(header_end, section.end_line) if index not in entry_indexes and docstring.structure.lines[index].raw_text.strip())
        other_prefix = f"{canonical_margin}{unit}" if docstring.structure.convention == settings_check.DocstringConvention.GOOGLE else canonical_margin
        _apply_common_margin_targets(targets, docstring, other_indexes, other_prefix)
        covered.update(other_indexes)
    return covered


def _preserve_targets(targets: list[_LineTarget | None], docstring: PDF_definition.DocstringInfo, indexes: range) -> None:
    """Assign unchanged targets for structurally non-rewritable lines."""
    for index in indexes:
        line = docstring.structure.lines[index]
        targets[index] = _LineTarget(line.raw_text, 0, "")


def _apply_fixed_prefix_targets(targets: list[_LineTarget | None], docstring: PDF_definition.DocstringInfo, indexes: range | tuple[int, ...], prefix: str) -> None:
    """Assign targets by replacing each line's full leading whitespace."""
    for index in indexes:
        line = docstring.structure.lines[index]
        if index == 0 or not line.raw_text.strip():
            continue
        targets[index] = _LineTarget(f"{prefix}{line.raw_text[len(line.raw_indent):]}", PDF_definition.leading_width(line.raw_indent), prefix)


def _apply_common_margin_targets(targets: list[_LineTarget | None], docstring: PDF_definition.DocstringInfo, indexes: tuple[int, ...], prefix: str) -> None:
    """Assign targets by stripping a shared visual margin before prefixing."""
    if not indexes:
        return
    common_width = min(PDF_definition.leading_width(docstring.structure.lines[index].raw_text) for index in indexes)
    for index in indexes:
        line = docstring.structure.lines[index]
        targets[index] = _LineTarget(f"{prefix}{PDF_definition.strip_indent(line.raw_text, common_width)}", common_width, prefix)


def _source_for_target_line(
    line: PDF_definition.DocstringValueLine,
    target: _LineTarget,
    *,
    fragments: tuple[string_literals.StringValueFragment, ...],
) -> str:
    """Return source spelling for a target line while preserving suffix spelling."""
    if not line.raw_text.strip():
        return target.raw_text
    _, raw_index, virtual_prefix = PDF_definition.strip_indent_with_mapping(line.raw_text, max(target.strip_width, 0))
    return f"{target.prefix}{' ' * virtual_prefix}{string_literals.source_for_value_slice(fragments, line.start_offset + raw_index, line.end_offset)}"


def _join_value_lines(docstring: PDF_definition.DocstringInfo, lines: list[str]) -> str:
    """Join replacement logical lines with the original evaluated newline spellings."""
    chunks: list[str] = []
    for index, (line_info, line) in enumerate(zip(docstring.structure.lines, lines)):
        chunks.append(line)
        if index + 1 < len(lines):
            chunks.append(docstring.value[line_info.end_offset : docstring.structure.lines[index + 1].start_offset])
        else:
            chunks.append(docstring.value[line_info.end_offset :])
    return "".join(chunks)
