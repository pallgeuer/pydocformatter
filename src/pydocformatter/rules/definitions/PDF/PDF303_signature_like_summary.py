"""PDF303 signature-like-summary rule."""

from __future__ import annotations

import pydocformatter.rules.definition_helpers.summary_style as summary_style
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.violations as rule_violations
from pydocformatter.cli.settings_check import DocstringConvention
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleCheckKind, RuleMetadata, RuleSettingEffect, RuleSettingEffects, RuleSettingEffectValues


@rule_registration.register_rule_to(PDF)
class PDF303SignatureLikeSummary(RuleBase):
    """Rule implementation for PDF303.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF303"),
        name="signature-like-summary",
        message="Docstring summary should not be a signature",
        fix_availability=FixAvailability.NEVER,
        stable_since="1.0.0",
        setting_effects=(
            RuleSettingEffects(
                setting="docstring_convention",
                effects=(RuleSettingEffectValues(effect=RuleSettingEffect.IGNORED, values=(DocstringConvention.NUMPY,)),),
            ),
        ),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for summaries that include the function signature.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        data = PDF.require_data(context)
        violations: list[rule_violations.RuleViolation] = []
        for target in data.summary_line_targets:
            if not summary_style.is_function_docstring(target.docstring):
                continue
            if _contains_signature(target.line.text, target.docstring.owner.name):
                violations.append(
                    rule_violations.diagnostic(
                        cls.meta, summary_style.line_numbers(target), instance_message=f"Docstring summary should not include signature for function '{target.docstring.owner.name}'"
                    )
                )
        return tuple(violations)


def _contains_signature(line: str, function_name: str) -> bool:
    """Return whether a line contains a function name immediately followed by an opening parenthesis."""
    start = 0
    needle = f"{function_name}("
    while (index := line.find(needle, start)) != -1:
        if index == 0 or line[index - 1] in " \t;,":
            return True
        start = index + 1
    return False
