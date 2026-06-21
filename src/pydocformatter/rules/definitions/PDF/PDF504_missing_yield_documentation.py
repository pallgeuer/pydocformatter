from __future__ import annotations

import pydocformatter.rules.definition_helpers.docstring_conventions as docstring_conventions
import pydocformatter.rules.definition_helpers.missing_documentation as missing_documentation
import pydocformatter.rules.definition_helpers.value_documentation as value_documentation
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
import pydocformatter.rules.registration as rule_registration
from pydocformatter.cli.settings_check import DocstringConvention
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleFinding, RuleMetadata, RuleSettingEffect, RuleSettingEffects, RuleSettingEffectValues


@rule_registration.register_rule_to(PDF)
class PDF504MissingYieldDocumentation(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PDF504"),
        name="missing-yield-documentation",
        message="Function yield value is missing docstring documentation",
        fix_availability=FixAvailability.NEVER,
        stable_since="1.0.0",
        setting_effects=(
            RuleSettingEffects(
                setting="docstring_convention",
                effects=(RuleSettingEffectValues(effect=RuleSettingEffect.IGNORED, values=(DocstringConvention.NONE, DocstringConvention.PEP257)),),
            ),
        ),
        incompatible_with=(),
    )

    @classmethod
    def check(cls, context: RuleContext) -> tuple[RuleFinding, ...]:
        """Return findings for undocumented meaningful yielded values."""
        if docstring_conventions.missing_documentation_is_inert(context.settings.docstring_convention):
            return ()
        findings: list[RuleFinding] = []
        for definition, docstring, facts in value_documentation.documented_function_facts(context):
            yield_targets = value_documentation.value_documentation_targets(docstring, PDF_definition.DocstringEntryKind.YIELD)
            if (
                not facts.meaningful_yields
                or any(target.has_content for target in yield_targets)
                or not missing_documentation.should_check_missing_documentation(definition, docstring, context=context, has_relevant_documentation=bool(yield_targets))
            ):
                continue
            findings.append(RuleFinding(rule=cls.meta, line_numbers=facts.meaningful_yields[0].line_numbers))
        return tuple(findings)
