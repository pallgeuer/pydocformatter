"""PDF616 forbidden-function-docstring rule."""

from __future__ import annotations

import pydocformatter.rules.definition_helpers.function_decorators as function_decorators
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.violations as rule_violations
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleCheckKind, RuleMetadata


@rule_registration.register_rule_to(PDF)
class PDF616ForbiddenFunctionDocstring(RuleBase):
    """Rule implementation for PDF616.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF616"),
        name="forbidden-function-docstring",
        message="Function decorated with forbidden decorator should not have a docstring",
        fix_availability=FixAvailability.NEVER,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for forbidden function docstrings.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        data = PDF.require_data(context)
        violations: list[rule_violations.RuleViolation] = []
        for definition in data.definitions:
            decorator_name = function_decorators.forbidden_docstring_decorator(definition, settings=context.settings)
            if decorator_name is None:
                continue
            docstring = data.docstring_for(definition)
            if docstring is None:
                continue
            violations.append(
                rule_violations.diagnostic(
                    cls.meta,
                    PDF_definition.docstring_physical_line_numbers(docstring),
                    instance_message=f"Function decorated with '@{decorator_name}' should not have a docstring",
                )
            )
        return tuple(violations)
