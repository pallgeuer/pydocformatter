"""PDF414 malformed-convention-entry rule."""

# Future imports
from __future__ import annotations

# First-party imports
import pydocformatter.rules.violations as rule_violations
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext
from pydocformatter.rules.definition_helpers import docstring_conventions, docstring_source, section_edits
from pydocformatter.rules.models import FixAvailability, RuleCacheBehavior, RuleCheckKind, RuleMetadata


_ISSUE_KINDS = {
    PDF_definition.ConventionEntryIssueKind.GOOGLE_UNBALANCED_METHOD_SIGNATURE,
    PDF_definition.ConventionEntryIssueKind.GOOGLE_UNBALANCED_TYPE,
    PDF_definition.ConventionEntryIssueKind.GOOGLE_MISSING_TYPE,
    PDF_definition.ConventionEntryIssueKind.GOOGLE_MISSING_SEPARATOR,
    PDF_definition.ConventionEntryIssueKind.NUMPY_UNBALANCED_METHOD_SIGNATURE,
    PDF_definition.ConventionEntryIssueKind.NUMPY_MISSING_TYPE,
    PDF_definition.ConventionEntryIssueKind.NUMPY_MISSING_SEPARATOR,
    PDF_definition.ConventionEntryIssueKind.REST_MISSING_CLOSING_DELIMITER,
    PDF_definition.ConventionEntryIssueKind.REST_MISSING_ARGUMENT,
    PDF_definition.ConventionEntryIssueKind.REST_UNEXPECTED_ARGUMENT,
}


@rule_registration.register_rule_to(PDF_definition.PDF)
class PDF414MalformedConventionEntry(RuleBase):
    """Rule implementation for PDF414.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF414"),
        name="malformed-convention-entry",
        message="Docstring convention entry should use valid syntax",
        fix_availability=FixAvailability.SOMETIMES,
        stable_since="1.1.0",
        setting_effects=docstring_conventions.convention_setting_effects(disabled=docstring_conventions.UNPARSED_CONVENTIONS),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
        cache_behavior=RuleCacheBehavior.FILE_LOCAL,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for malformed convention entry syntax.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        data = PDF_definition.PDF.require_data(context)
        return tuple(
            rule_violations.violation_for_optional_planned_source_change(
                cls.meta,
                section_edits.planned_convention_entry_change(docstring, issue, context=context),
                line_numbers=docstring_source.docstring_line_numbers(docstring, docstring.structure.lines[issue.start_line]),
                instance_message=_instance_message(issue),
            )
            for docstring in data.docstrings
            for issue in docstring.structure.convention_entry_issues
            if issue.kind in _ISSUE_KINDS
        )


def _instance_message(issue: PDF_definition.ConventionEntryIssue) -> str:
    """Return the syntax diagnostic for one malformed entry."""
    names = ", ".join(f"'{name}'" for name in issue.names)
    if issue.kind is PDF_definition.ConventionEntryIssueKind.GOOGLE_UNBALANCED_METHOD_SIGNATURE:
        return f"Google docstring method entry {names} has an unbalanced signature"
    if issue.kind is PDF_definition.ConventionEntryIssueKind.GOOGLE_UNBALANCED_TYPE:
        return f"Google docstring entry {names} has an unbalanced parenthesized type"
    if issue.kind is PDF_definition.ConventionEntryIssueKind.GOOGLE_MISSING_TYPE:
        return f"Google docstring entry {names} is missing its type inside parentheses"
    if issue.kind is PDF_definition.ConventionEntryIssueKind.GOOGLE_MISSING_SEPARATOR:
        return f"Google docstring entry {names} is missing the colon before its description"
    if issue.kind is PDF_definition.ConventionEntryIssueKind.NUMPY_UNBALANCED_METHOD_SIGNATURE:
        return f"NumPy docstring method entry {names} has an unbalanced signature"
    if issue.kind is PDF_definition.ConventionEntryIssueKind.NUMPY_MISSING_TYPE:
        return f"NumPy docstring entry {names} is missing its type after the colon"
    if issue.kind is PDF_definition.ConventionEntryIssueKind.NUMPY_MISSING_SEPARATOR:
        return f"NumPy docstring entry {names} is missing the colon before its type"
    field = f":{issue.field_name or ''}:"
    if issue.kind is PDF_definition.ConventionEntryIssueKind.REST_MISSING_CLOSING_DELIMITER:
        return f"reST field '{field}' is missing its closing colon"
    if issue.kind is PDF_definition.ConventionEntryIssueKind.REST_MISSING_ARGUMENT:
        return f"reST field '{field}' is missing its required argument"
    if issue.kind is PDF_definition.ConventionEntryIssueKind.REST_UNEXPECTED_ARGUMENT:
        return f"reST field '{field}' has an unexpected argument"
    raise AssertionError(f"Unsupported PDF414 convention entry issue kind: {issue.kind.value}")
