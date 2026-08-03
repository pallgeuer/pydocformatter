"""PDF528 attribute-documentation-order rule."""

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
from pydocformatter.rules.definition_helpers import attribute_documentation, docstring_conventions
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleCacheBehavior, RuleCheckKind, RuleMetadata


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.definition import RuleContext


@rule_registration.register_rule_to(PDF)
class PDF528AttributeDocumentationOrder(RuleBase):
    """Rule implementation for PDF528.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF528"),
        name="attribute-documentation-order",
        message="Docstring attributes are not in declaration order",
        fix_availability=FixAvailability.NEVER,
        stable_since="1.1.0",
        setting_effects=docstring_conventions.convention_setting_effects(disabled=docstring_conventions.UNPARSED_CONVENTIONS, ignored=docstring_conventions.PARSED_CONVENTIONS),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
        cache_behavior=RuleCacheBehavior.FILE_LOCAL,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for attribute documentation outside source order.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        data = PDF.require_data(context)
        violations: list[rule_violations.RuleViolation] = []
        for definition in data.definitions:
            if definition.kind not in {PDF_definition.DefinitionKind.MODULE, PDF_definition.DefinitionKind.CLASS}:
                continue
            docstring = data.docstring_for(definition)
            if docstring is None:
                continue
            violations.extend(
                rule_violations.diagnostic(
                    cls.meta,
                    issue.documented_attribute.line_numbers,
                    instance_message=f"Docstring attribute '{issue.inventory_attribute.name}' should appear before '{issue.preceding_inventory_attribute.name}' to match the source declaration order",
                )
                for issue in attribute_documentation.attribute_order_issues(data, definition, docstring)
            )
        return tuple(violations)
