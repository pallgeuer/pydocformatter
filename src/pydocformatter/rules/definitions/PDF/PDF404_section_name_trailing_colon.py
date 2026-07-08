"""PDF404 section-name-trailing-colon rule."""

# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# First-party imports
import pydocformatter.rules.registration as rule_registration
from pydocformatter.cli.settings_check import DocstringConvention
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.definition_helpers import docstring_conventions, section_edits
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleCheckKind, RuleMetadata, RuleSettingEffect, RuleSettingEffects, RuleSettingEffectValues


if TYPE_CHECKING:
    # First-party imports
    import pydocformatter.rules.edits as rule_edits
    import pydocformatter.rules.violations as rule_violations
    from pydocformatter.rules.definition import RuleContext


@rule_registration.register_rule_to(PDF)
class PDF404SectionNameTrailingColon(RuleBase):
    """Rule implementation for PDF404.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF404"),
        name="section-name-trailing-colon",
        message="Docstring section name should end with a colon",
        fix_availability=FixAvailability.SOMETIMES,
        stable_since="1.0.0",
        setting_effects=(
            RuleSettingEffects(
                setting="docstring_convention",
                effects=(RuleSettingEffectValues(effect=RuleSettingEffect.IGNORED, values=docstring_conventions.ignored_conventions_except(DocstringConvention.GOOGLE)),),
            ),
        ),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for Google section names missing a trailing colon.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        return _results(context, rule=cls.meta)


def _results(context: RuleContext, *, rule: RuleMetadata) -> tuple[rule_violations.RuleViolation, ...]:
    """Return violations for Google section names missing a colon."""
    data = PDF.require_data(context)
    results: list[rule_violations.RuleViolation] = []
    for docstring in data.docstrings:
        if docstring.structure.convention is not DocstringConvention.GOOGLE:
            continue
        replacements: list[rule_edits.PlannedTextReplacement] = []
        value_lines = [line.raw_text for line in docstring.structure.lines]
        replacement_line_numbers: list[int] = []
        unfixable_line_numbers: list[int] = []
        replacement_messages: list[str] = []
        unfixable_messages: list[str] = []
        for section in docstring.structure.sections:
            line = docstring.structure.lines[section.header_line]
            if line.text.strip().endswith(":"):
                continue
            message = f"Docstring section '{section.name}' should end with a colon"
            replacement = section_edits.replacement_for_section_suffix(line, section.name, ":")
            if replacement is None:
                unfixable_line_numbers.extend(section_edits.line_numbers(docstring, line))
                unfixable_messages.append(message)
                continue
            replacements.append(replacement)
            replacement_line_numbers.extend(section_edits.line_numbers(docstring, line))
            replacement_messages.append(message)
            section_edits.replace_value_line_span(value_lines, line, replacement, ":")
        if not replacements and not unfixable_line_numbers:
            continue
        change = section_edits.planned_replacement_change(docstring, context=context, replacements=tuple(replacements), value_lines=value_lines)
        results.extend(
            section_edits.replacement_results(
                rule,
                replacement_line_numbers=replacement_line_numbers,
                unfixable_line_numbers=unfixable_line_numbers,
                change=change,
                replacement_messages=replacement_messages,
                unfixable_messages=unfixable_messages,
            )
        )
    return tuple(results)
