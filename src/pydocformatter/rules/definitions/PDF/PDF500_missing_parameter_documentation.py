from __future__ import annotations

import pydocformatter.rules.definition_helpers.docstring_conventions as docstring_conventions
import pydocformatter.rules.definition_helpers.parameter_documentation as parameter_documentation
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
import pydocformatter.rules.registration as rule_registration
from pydocformatter.cli.settings_check import DocstringConvention
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleFinding, RuleMetadata, RuleSettingEffect, RuleSettingEffects, RuleSettingEffectValues


@rule_registration.register_rule_to(PDF)
class PDF500MissingParameterDocumentation(RuleBase):
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
    )

    @classmethod
    def check(cls, context: RuleContext) -> tuple[RuleFinding, ...]:
        """Return findings for signature parameters missing docstring documentation."""
        if docstring_conventions.missing_documentation_is_inert(context.settings.docstring_convention):
            return ()
        data = PDF.require_data(context)
        findings: list[RuleFinding] = []
        for definition in data.definitions:
            if definition.kind is not PDF_definition.DefinitionKind.FUNCTION or definition.parameters is None:
                continue
            docstring = data.docstring_for(definition)
            if docstring is None or not parameter_documentation.should_check_missing_parameters(definition, docstring, context=context):
                continue
            documented_names = {parameter.comparison_name for parameter in parameter_documentation.documented_parameters(docstring)}
            for parameter in parameter_documentation.signature_parameters(definition, context=context):
                if parameter.implicit_receiver or parameter.unpacked or parameter.comparison_name in documented_names:
                    continue
                findings.append(
                    RuleFinding(
                        rule=cls.meta,
                        line_numbers=parameter.line_numbers,
                        instance_message=f"Function parameter '{parameter.display_name}' is missing docstring documentation",
                    )
                )
        return tuple(findings)
