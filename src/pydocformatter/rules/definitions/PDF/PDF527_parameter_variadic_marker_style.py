"""PDF527 parameter-variadic-marker-style rule."""

# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# First-party imports
import pydocformatter.rules.violations as rule_violations
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
from pydocformatter.cli.settings_check import DocstringConvention
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.definition_helpers import docstring_conventions, parameter_documentation
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleCacheBehavior, RuleCheckKind, RuleMetadata


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.definition import RuleContext


@rule_registration.register_rule_to(PDF)
class PDF527ParameterVariadicMarkerStyle(RuleBase):
    """Rule implementation for PDF527.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF527"),
        name="parameter-variadic-marker-style",
        message="Docstring parameter variadic markers do not use the canonical spelling",
        fix_availability=FixAvailability.USUALLY,
        stable_since="1.1.0",
        setting_effects=docstring_conventions.convention_setting_effects(disabled=docstring_conventions.UNPARSED_CONVENTIONS),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
        cache_behavior=RuleCacheBehavior.FILE_LOCAL,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for parameter documentation with noncanonical variadic markers.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        data = PDF.require_data(context)
        violations: list[rule_violations.RuleViolation] = []
        for definition in data.definitions:
            if definition.kind is not PDF_definition.DefinitionKind.FUNCTION or definition.parameters is None:
                continue
            docstring = data.docstring_for(definition)
            if docstring is None:
                continue
            violations.extend(
                rule_violations.violation_for_optional_planned_source_change(
                    cls.meta,
                    parameter_documentation.planned_parameter_name_change(docstring, issue, context=context),
                    line_numbers=issue.documented_parameter.line_numbers,
                    instance_message=_instance_message(issue, context=context),
                )
                for issue in parameter_documentation.parameter_variadic_marker_style_issues(definition, docstring, context=context)
            )
        return tuple(violations)


def _instance_message(issue: parameter_documentation.ParameterVariadicMarkerStyleIssue, *, context: RuleContext) -> str:
    """Return the convention-specific diagnostic for a variadic marker style issue."""
    if context.settings.docstring_convention is DocstringConvention.REST:
        return f"Docstring parameter '{issue.documented_parameter.name}' should be written as '{issue.expected_name}' without variadic markers under the reStructuredText convention"
    return f"Docstring parameter '{issue.documented_parameter.name}' should be written as '{issue.expected_name}' to match the function signature"
