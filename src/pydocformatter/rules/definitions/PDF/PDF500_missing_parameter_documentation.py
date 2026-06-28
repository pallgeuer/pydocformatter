"""PDF500 missing-parameter-documentation rule."""

from __future__ import annotations

import pydocformatter.rules.definition_helpers.docstring_conventions as docstring_conventions
import pydocformatter.rules.definition_helpers.parameter_documentation as parameter_documentation
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.violations as rule_violations
from pydocformatter.cli.settings_check import DocstringConvention
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleCheckKind, RuleMetadata, RuleSettingEffect, RuleSettingEffects, RuleSettingEffectValues


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
        stable_since="1.0.0",
        setting_effects=(
            RuleSettingEffects(
                setting="docstring_convention",
                effects=(RuleSettingEffectValues(effect=RuleSettingEffect.IGNORED, values=docstring_conventions.ignored_conventions_except(DocstringConvention.GOOGLE, DocstringConvention.REST)),),
            ),
        ),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for signature parameters missing docstring documentation."""
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
            documented_names = {parameter.comparison_name for parameter in parameter_documentation.documented_parameters(docstring)}
            docstring_suppression_target = (PDF_definition.docstring_physical_line_numbers(docstring),)
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
