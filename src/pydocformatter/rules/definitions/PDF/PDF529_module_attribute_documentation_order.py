"""PDF529 module-attribute-documentation-order rule."""

# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# First-party imports
import pydocformatter.rules.violations as rule_violations
import pydocformatter.rules.registration as rule_registration
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.definition_helpers import attribute_documentation, docstring_conventions
from pydocformatter.rules.definitions.PDF.PDF import PDF, DefinitionKind
from pydocformatter.rules.models import MODULE_SOURCE_CONTEXTS, FixAvailability, RuleCacheBehavior, RuleCheckKind, RuleMetadata


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.definition import RuleContext


@rule_registration.register_rule_to(PDF)
class PDF529ModuleAttributeDocumentationOrder(RuleBase):
    """Rule implementation for PDF529.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF529"),
        name="module-attribute-documentation-order",
        message="Module docstring attributes are not in declaration order",
        fix_availability=FixAvailability.NEVER,
        stable_since="1.2.0",
        setting_effects=docstring_conventions.convention_setting_effects(disabled=docstring_conventions.UNPARSED_CONVENTIONS, ignored=docstring_conventions.PARSED_CONVENTIONS),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
        cache_behavior=RuleCacheBehavior.FILE_LOCAL,
        source_contexts=MODULE_SOURCE_CONTEXTS,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for module attribute documentation outside source order.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        data = PDF.require_data(context)
        definition = next(definition for definition in data.definitions if definition.kind is DefinitionKind.MODULE)
        docstring = data.docstring_for(definition)
        if docstring is None:
            return ()
        return tuple(
            rule_violations.diagnostic(
                cls.meta,
                issue.documented_attribute.line_numbers,
                instance_message=f"Module docstring attribute '{issue.inventory_attribute.name}' should appear before '{issue.preceding_inventory_attribute.name}' to match the source declaration order",
            )
            for issue in attribute_documentation.attribute_order_issues(data, definition, docstring)
        )
