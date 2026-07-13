"""PDF408 repeated-section rule."""

# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# First-party imports
import pydocformatter.rules.violations as rule_violations
import pydocformatter.rules.registration as rule_registration
from pydocformatter.cli.settings_check import DocstringConvention
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.definition_helpers import docstring_sections, rest_fields, section_edits
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleCheckKind, RuleMetadata, RuleSettingEffect, RuleSettingEffects, RuleSettingEffectValues


if TYPE_CHECKING:
    # First-party imports
    import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
    from pydocformatter.rules.definition import RuleContext


@rule_registration.register_rule_to(PDF)
class PDF408RepeatedSection(RuleBase):
    """Rule implementation for PDF408.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF408"),
        name="repeated-section",
        message="Docstring section should not be repeated",
        fix_availability=FixAvailability.NEVER,
        stable_since="1.0.0",
        setting_effects=(
            RuleSettingEffects(setting="docstring_convention", effects=(RuleSettingEffectValues(effect=RuleSettingEffect.DISABLED, values=(DocstringConvention.NONE, DocstringConvention.PEP257)),)),
        ),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for repeated convention sections.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        return _violations(context, rule=cls.meta)


def _violations(context: RuleContext, *, rule: RuleMetadata) -> tuple[rule_violations.RuleViolation, ...]:
    """Return violations for repeated convention sections or reST fields."""
    data = PDF.require_data(context)
    violations: list[rule_violations.RuleViolation] = []
    for docstring in data.docstrings:
        if docstring.structure.convention is DocstringConvention.REST:
            violations.extend(_rest_field_violations(docstring, rule=rule))
        else:
            seen_keys: dict[str, str] = {}
            for section in docstring.structure.sections:
                key = docstring_sections.repeated_section_key(docstring.structure.convention, section.name)
                if key in seen_keys:
                    line = docstring.structure.lines[section.header_line]
                    violations.append(
                        rule_violations.diagnostic(rule, section_edits.line_numbers(docstring, line), instance_message=f"Docstring section '{section.name}' repeats earlier section '{seen_keys[key]}'")
                    )
                else:
                    seen_keys[key] = section.name
    return tuple(violations)


def _rest_field_violations(docstring: PDF_definition.DocstringInfo, *, rule: RuleMetadata) -> tuple[rule_violations.RuleViolation, ...]:
    """Return violations for repeated reStructuredText fields."""
    violations: list[rule_violations.RuleViolation] = []
    seen_keys: dict[tuple[str, str, str], str] = {}
    for entry in docstring.structure.entries:
        if entry.field_name is None:
            continue
        key = rest_fields.repetition_key(entry)
        if key is None:
            continue
        label = rest_fields.label(entry)
        if key in seen_keys:
            line = docstring.structure.lines[entry.start_line]
            violations.append(rule_violations.diagnostic(rule, section_edits.line_numbers(docstring, line), instance_message=f"Docstring field '{label}' repeats earlier field '{seen_keys[key]}'"))
        else:
            seen_keys[key] = label
    return tuple(violations)
