"""PDF500 missing-parameter-documentation rule."""

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
from pydocformatter.rules.definition_helpers import docstring_conventions, docstring_source, parameter_documentation
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleCacheBehavior, RuleCheckKind, RuleMetadata


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.definition import RuleContext


@rule_registration.register_rule_to(PDF)
class PDF500MissingParameterDocumentation(RuleBase):
    """Rule implementation for PDF500.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF500"),
        name="missing-parameter-documentation",
        message="Function parameter is missing docstring documentation",
        fix_availability=FixAvailability.NEVER,
        stable_since="1.1.0",
        setting_effects=docstring_conventions.convention_setting_effects(disabled=docstring_conventions.UNPARSED_CONVENTIONS),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
        cache_behavior=RuleCacheBehavior.FILE_LOCAL,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for signature parameters missing docstring documentation.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        if docstring_conventions.missing_documentation_is_inert(context.settings.docstring_convention):
            return ()
        data = PDF.require_data(context)
        violations: list[rule_violations.RuleViolation] = []
        for definition in data.definitions:
            if definition.kind is not PDF_definition.DefinitionKind.FUNCTION or definition.parameters is None:
                continue
            docstring = data.docstring_for(definition)
            if docstring is None or not parameter_documentation.should_check_missing_parameters(definition, docstring, context=context):
                continue
            documented_names = {parameter.comparison_name for parameter in parameter_documentation.value_documented_parameters(docstring)}
            docstring_suppression_target = (docstring_source.docstring_physical_line_numbers(docstring),)
            for parameter in parameter_documentation.signature_parameters(definition, context=context):
                if parameter.implicit_receiver or parameter.unpacked or parameter.comparison_name in documented_names:
                    continue
                violations.append(
                    rule_violations.diagnostic(
                        cls.meta,
                        parameter.line_numbers,
                        suppression_line_numbers=docstring_suppression_target,
                        instance_message=f"Function parameter '{parameter.display_name}' is missing docstring documentation",
                    )
                )
        return tuple(violations)
