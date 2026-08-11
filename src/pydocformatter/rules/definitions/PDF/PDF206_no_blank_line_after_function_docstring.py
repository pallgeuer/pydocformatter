"""PDF206 no-blank-line-after-function-docstring rule."""

# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# Third-party imports
import libcst as cst

# First-party imports
import pydocformatter.rules.violations as rule_violations
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
from pydocformatter.cli import settings_check
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.definition_helpers import docstring_statement_spacing
from pydocformatter.rules.models import FixAvailability, RuleCacheBehavior, RuleCheckKind, RuleMetadata, RuleSettingEffect, RuleSettingEffects, RuleSettingEffectValues


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.definition import RuleContext


@rule_registration.register_rule_to(PDF_definition.PDF)
class PDF206NoBlankLineAfterFunctionDocstring(RuleBase):
    """Rule implementation for PDF206.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF206"),
        # Keep the stable name as the intentional policy opposite of PDF207 despite the nested-definition exception.
        name="no-blank-line-after-function-docstring",
        message="Function docstring has incorrect blank line spacing after it",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="1.1.0",
        setting_effects=(RuleSettingEffects(setting="docstring_convention", effects=(RuleSettingEffectValues(effect=RuleSettingEffect.IGNORED, values=tuple(settings_check.DocstringConvention)),)),),
        incompatible_with=(RuleCode("PDF207"),),
        check_kind=RuleCheckKind.STANDARD,
        cache_behavior=RuleCacheBehavior.FILE_LOCAL,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for blank lines after function docstrings.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        data = PDF_definition.PDF.require_data(context)
        return tuple(violation for docstring in data.docstrings if (violation := _violation_for_docstring(docstring, context=context, rule=cls.meta)) is not None)


def _violation_for_docstring(docstring: PDF_definition.DocstringInfo, *, context: RuleContext, rule: RuleMetadata) -> rule_violations.RuleViolation | None:
    """Return the conditional after-docstring spacing violation for one function."""
    if not isinstance(docstring.owner, PDF_definition.DefinitionInfo) or docstring.owner.kind is not PDF_definition.DefinitionKind.FUNCTION:
        return None
    following_statement = docstring_statement_spacing.following_body_statement(docstring)
    nested_definition = isinstance(following_statement, (cst.FunctionDef, cst.ClassDef))
    change = docstring_statement_spacing.planned_change_for_docstring(
        docstring,
        context=context,
        owner_kind=PDF_definition.DefinitionKind.FUNCTION,
        position=docstring_statement_spacing.DocstringStatementSpacingPosition.AFTER,
        desired_blank_lines=1 if nested_definition else 0,
    )
    if change is None:
        return None
    message = "Function docstring should have one blank line after it before a nested definition" if nested_definition else "Function docstring should have no blank lines after it"
    return rule_violations.violation_for_planned_source_change(rule, change, instance_message=message)
