"""PDF415 convention-entry-indentation rule."""

# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# First-party imports
import pydocformatter.rules.violations as rule_violations
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
from pydocformatter.cli.settings_check import DocstringConvention
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.definition_helpers import docstring_conventions
from pydocformatter.rules.models import FixAvailability, RuleCacheBehavior, RuleCheckKind, RuleMetadata


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.definition import RuleContext


_ISSUE_KINDS = {
    PDF_definition.ConventionEntryIssueKind.GOOGLE_ENTRY_INDENTATION,
    PDF_definition.ConventionEntryIssueKind.GOOGLE_CONTINUATION_INDENTATION,
    PDF_definition.ConventionEntryIssueKind.NUMPY_CONTINUATION_INDENTATION,
}


@rule_registration.register_rule_to(PDF_definition.PDF)
class PDF415ConventionEntryIndentation(RuleBase):
    """Rule implementation for PDF415.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF415"),
        name="convention-entry-indentation",
        message="Docstring convention entry should use valid indentation",
        fix_availability=FixAvailability.NEVER,
        stable_since="1.1.0",
        setting_effects=docstring_conventions.convention_setting_effects(disabled=docstring_conventions.conventions_except(DocstringConvention.GOOGLE, DocstringConvention.NUMPY)),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
        cache_behavior=RuleCacheBehavior.FILE_LOCAL,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for malformed convention entry indentation.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        data = PDF_definition.PDF.require_data(context)
        return tuple(
            rule_violations.diagnostic(cls.meta, PDF_definition.docstring_line_numbers(docstring, docstring.structure.lines[issue.start_line]), instance_message=_instance_message(issue))
            for docstring in data.docstrings
            for issue in docstring.structure.convention_entry_issues
            if issue.kind in _ISSUE_KINDS
        )


def _instance_message(issue: PDF_definition.ConventionEntryIssue) -> str:
    """Return the indentation diagnostic for one malformed entry."""
    names = ", ".join(f"'{name}'" for name in issue.names)
    entry = f"entry {names}" if names else "entry"
    if issue.kind is PDF_definition.ConventionEntryIssueKind.GOOGLE_ENTRY_INDENTATION:
        return f"Google docstring {entry} should be indented beyond its section header"
    if issue.kind is PDF_definition.ConventionEntryIssueKind.GOOGLE_CONTINUATION_INDENTATION:
        return f"Google docstring {entry} description should be indented beyond the entry"
    if issue.kind is PDF_definition.ConventionEntryIssueKind.NUMPY_CONTINUATION_INDENTATION:
        return f"NumPy docstring {entry} description should be indented beyond the entry"
    raise AssertionError(f"Unsupported PDF415 convention entry issue kind: {issue.kind.value}")
