"""Source spacing helpers for docstring statement blank-line rules."""

from __future__ import annotations

import enum

import libcst as cst
import libcst.metadata as cst_metadata

import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
import pydocformatter.rules.edits as rule_edits
from pydocformatter.rules.definition import RuleContext


class DocstringStatementSpacingPosition(enum.Enum):
    """Adjacent side of a docstring statement whose blank-line run is checked.

    Attributes:
        BEFORE: Blank lines immediately before the docstring statement.
        AFTER: Blank lines immediately after the docstring statement.
    """

    BEFORE = "before"
    AFTER = "after"


def planned_changes(
    context: RuleContext, *, owner_kind: PDF_definition.DefinitionKind, position: DocstringStatementSpacingPosition, desired_blank_lines: int
) -> tuple[rule_edits.PlannedSourceChange, ...]:
    """Return source changes for docstring statement blank-line spacing.

    Args:
        context: Current file context with parsed module, settings, and prepared category data.
        owner_kind: Definition kind whose docstrings should be checked.
        position: Adjacent side of the docstring statement to inspect.
        desired_blank_lines: Required number of blank physical lines.

    Returns:
        Planned source replacements for docstring statement spacing findings.

    Raises:
        ValueError: Raised when the desired blank-line count is negative.
    """
    if desired_blank_lines < 0:
        raise ValueError("Desired blank-line count must not be negative")
    data = PDF_definition.PDF.require_data(context)
    return tuple(
        change
        for docstring in data.docstrings
        if (change := planned_change_for_docstring(docstring, context=context, owner_kind=owner_kind, position=position, desired_blank_lines=desired_blank_lines)) is not None
    )


def planned_change_for_docstring(
    docstring: PDF_definition.DocstringInfo,
    *,
    context: RuleContext,
    owner_kind: PDF_definition.DefinitionKind,
    position: DocstringStatementSpacingPosition,
    desired_blank_lines: int,
) -> rule_edits.PlannedSourceChange | None:
    """Return a blank-run source replacement for one docstring statement.

    Args:
        docstring: Prepared docstring whose owner and statement spacing should be checked.
        context: Current file context with parsed module, settings, and prepared category data.
        owner_kind: Definition kind whose docstrings should be checked.
        position: Adjacent side of the docstring statement to inspect.
        desired_blank_lines: Required number of blank physical lines.

    Returns:
        Planned source replacement for the docstring statement, or None when it already has the requested spacing or is outside this rule's scope.
    """
    if not isinstance(docstring.owner, PDF_definition.DefinitionInfo) or docstring.owner.kind is not owner_kind:
        return None
    if isinstance(docstring.statement, cst.SimpleStatementSuite):
        return None
    if position is DocstringStatementSpacingPosition.AFTER and not _has_following_body_statement(docstring):
        return None
    statement_range = context.positions[docstring.statement]
    if position is DocstringStatementSpacingPosition.BEFORE:
        actual_blank_lines, edit_range = _blank_run_before(statement_range, source_lines=context.source_lines)
    else:
        actual_blank_lines, edit_range = _blank_run_after(statement_range, source_lines=context.source_lines)
    if actual_blank_lines == desired_blank_lines:
        return None
    return rule_edits.PlannedSourceChange(
        edit=rule_edits.SourceEdit(range=edit_range, replacement=context.line_ending * desired_blank_lines),
        line_numbers=(docstring.range.start.line,),
        suppression_line_numbers=(),
    )


def _has_following_body_statement(docstring: PDF_definition.DocstringInfo) -> bool:
    """Return whether the docstring statement has a following sibling statement."""
    if not isinstance(docstring.owner, PDF_definition.DefinitionInfo) or not isinstance(docstring.owner.body, cst.IndentedBlock):
        return False
    body = docstring.owner.body.body
    for index, statement in enumerate(body):
        if statement is docstring.statement:
            return index < len(body) - 1
    return False


def _blank_run_before(statement_range: cst_metadata.CodeRange, *, source_lines: tuple[str, ...]) -> tuple[int, cst_metadata.CodeRange]:
    """Return the immediately preceding blank-run length and replacement range."""
    statement_line = statement_range.start.line
    index = statement_line - 2
    while index >= 0 and _is_blank_source_line(source_lines[index]):
        index -= 1
    first_blank_line = index + 2
    blank_count = statement_line - first_blank_line
    return blank_count, cst_metadata.CodeRange(start=cst_metadata.CodePosition(first_blank_line, 0), end=cst_metadata.CodePosition(statement_line, 0))


def _blank_run_after(statement_range: cst_metadata.CodeRange, *, source_lines: tuple[str, ...]) -> tuple[int, cst_metadata.CodeRange]:
    """Return the immediately following blank-run length and replacement range."""
    first_blank_line = statement_range.end.line + 1
    index = first_blank_line - 1
    while index < len(source_lines) and _is_blank_source_line(source_lines[index]):
        index += 1
    blank_count = index - first_blank_line + 1
    return blank_count, cst_metadata.CodeRange(start=cst_metadata.CodePosition(first_blank_line, 0), end=cst_metadata.CodePosition(first_blank_line + blank_count, 0))


def _is_blank_source_line(line: str) -> bool:
    """Return whether a physical source line contains only whitespace."""
    return not line.strip()
