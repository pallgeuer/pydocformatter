"""PDF502 missing-return-documentation rule."""

from __future__ import annotations

import pydocformatter.rules.definition_helpers.docstring_conventions as docstring_conventions
import pydocformatter.rules.definition_helpers.missing_documentation as missing_documentation
import pydocformatter.rules.definition_helpers.value_documentation as value_documentation
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.violations as rule_violations
from pydocformatter.cli.settings_check import DocstringConvention
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleCheckKind, RuleMetadata, RuleSettingEffect, RuleSettingEffects, RuleSettingEffectValues


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
        setting_effects=(
            RuleSettingEffects(
                setting="docstring_convention",
                effects=(RuleSettingEffectValues(effect=RuleSettingEffect.IGNORED, values=(DocstringConvention.NONE, DocstringConvention.PEP257)),),
            ),
        ),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
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
            if any(target.has_content for target in return_targets) or not missing_documentation.should_check_missing_documentation(
                definition, docstring, context=context, has_relevant_documentation=bool(return_targets)
            ):
                continue
            violations.append(rule_violations.diagnostic(cls.meta, facts.meaningful_returns[0].line_numbers, suppression_line_numbers=(PDF_definition.docstring_physical_line_numbers(docstring),)))
        return tuple(violations)
