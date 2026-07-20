"""PDF526 parameter-documentation-order rule."""

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
from pydocformatter.rules.definition_helpers import docstring_conventions, parameter_documentation
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleCacheBehavior, RuleCheckKind, RuleMetadata


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.definition import RuleContext


@rule_registration.register_rule_to(PDF)
class PDF526ParameterDocumentationOrder(RuleBase):
    """Rule implementation for PDF526.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF526"),
        name="parameter-documentation-order",
        message="Docstring parameters are not in function signature order",
        fix_availability=FixAvailability.NEVER,
        stable_since="1.1.0",
        setting_effects=docstring_conventions.convention_setting_effects(disabled=docstring_conventions.UNPARSED_CONVENTIONS),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
        cache_behavior=RuleCacheBehavior.FILE_LOCAL,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for parameter documentation that does not follow signature order.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        data = PDF.require_data(context)
        violations: list[rule_violations.RuleViolation] = []
        for definition in data.definitions:
            if definition.kind is not PDF_definition.DefinitionKind.FUNCTION or definition.parameters is None:
                continue
            docstring = data.docstring_for(definition)
            if docstring is None:
                continue
            violations.extend(
                (
                    rule_violations.diagnostic(
                        cls.meta,
                        issue.documented_parameter.line_numbers,
                        instance_message=(
                            f"Docstring parameter '{issue.signature_parameter.display_name}' should appear before '{issue.preceding_signature_parameter.display_name}' to match the function signature"
                        ),
                    )
                )
                for issue in parameter_documentation.parameter_order_issues(definition, docstring, context=context)
            )
        return tuple(violations)
