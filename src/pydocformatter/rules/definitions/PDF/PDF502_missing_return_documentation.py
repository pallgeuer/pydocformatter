"""PDF502 missing-return-documentation rule."""

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
from pydocformatter.rules.definition_helpers import docstring_conventions, docstring_source, missing_documentation, value_documentation
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleCacheBehavior, RuleCheckKind, RuleMetadata


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.definition import RuleContext


@rule_registration.register_rule_to(PDF)
class PDF502MissingReturnDocumentation(RuleBase):
    """Rule implementation for PDF502.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF502"),
        name="missing-return-documentation",
        message="Function return value is missing docstring documentation",
        fix_availability=FixAvailability.NEVER,
        stable_since="1.0.0",
        setting_effects=docstring_conventions.convention_setting_effects(disabled=docstring_conventions.UNPARSED_CONVENTIONS),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
        cache_behavior=RuleCacheBehavior.FILE_LOCAL,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for undocumented meaningful return values.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        if docstring_conventions.missing_documentation_is_inert(context.settings.docstring_convention):
            return ()
        violations: list[rule_violations.RuleViolation] = []
        for definition, docstring, facts in value_documentation.documented_function_facts(context):
            if not facts.meaningful_returns or facts.any_yields:
                continue
            return_targets = value_documentation.value_documentation_targets(docstring, PDF_definition.DocstringEntryKind.RETURN)
            if any(target.has_value_entry and target.has_content for target in return_targets) or not missing_documentation.should_check_missing_documentation(
                definition, docstring, context=context, has_relevant_documentation=bool(return_targets)
            ):
                continue
            violations.append(rule_violations.diagnostic(cls.meta, facts.meaningful_returns[0].line_numbers, suppression_line_numbers=(docstring_source.docstring_physical_line_numbers(docstring),)))
        return tuple(violations)
