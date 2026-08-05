"""PDF506 missing-exception-documentation rule."""

# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# First-party imports
import pydocformatter.rules.violations as rule_violations
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.definition_helpers import docstring_conventions, missing_documentation, value_documentation
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleCacheBehavior, RuleCheckKind, RuleMetadata


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.definition import RuleContext


@rule_registration.register_rule_to(PDF)
class PDF506MissingExceptionDocumentation(RuleBase):
    """Rule implementation for PDF506.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF506"),
        name="missing-exception-documentation",
        message="Raised exception is missing docstring documentation",
        fix_availability=FixAvailability.NEVER,
        stable_since="1.0.0",
        setting_effects=docstring_conventions.convention_setting_effects(disabled=docstring_conventions.UNPARSED_CONVENTIONS),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
        cache_behavior=RuleCacheBehavior.FILE_LOCAL,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for enabled exception occurrences missing from docs.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        if docstring_conventions.missing_documentation_is_inert(context.settings.docstring_convention):
            return ()
        violations: list[rule_violations.RuleViolation] = []
        for definition, docstring, facts in value_documentation.documented_function_facts(context):
            documented_names = tuple(
                entry.name for entry in value_documentation.documented_entries(docstring, PDF_definition.DocstringEntryKind.EXCEPTION, require_content=False) if entry.name is not None
            )
            if not missing_documentation.should_check_missing_documentation(
                definition, docstring, context=context, has_relevant_documentation=value_documentation.has_exception_documentation(docstring)
            ):
                continue
            seen: list[str] = []
            for occurrence in value_documentation.effective_exception_occurrences(facts, settings=context.settings):
                if any(value_documentation.exception_names_match(occurrence.name, seen_name) for seen_name in seen):
                    continue
                seen.append(occurrence.name)
                if not any(value_documentation.exception_names_match(occurrence.name, documented_name) for documented_name in documented_names):
                    message = (
                        "AssertionError raised by an assert statement is missing docstring documentation"
                        if occurrence.origin is PDF_definition.ExceptionOccurrenceOrigin.ASSERT
                        else f"Raised exception '{occurrence.name}' is missing docstring documentation"
                    )
                    violations.append(
                        rule_violations.diagnostic(cls.meta, occurrence.line_numbers, suppression_line_numbers=(PDF_definition.docstring_physical_line_numbers(docstring),), instance_message=message)
                    )
        return tuple(violations)
