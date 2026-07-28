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
from pydocformatter.rules.definition_helpers import ascii_whitespace, docstring_conventions, section_edits
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleCacheBehavior, RuleCheckKind, RuleMetadata, RuleSettingEffect, RuleSettingEffects, RuleSettingEffectValues


if TYPE_CHECKING:
    # First-party imports
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
                setting="docstring_convention", effects=(RuleSettingEffectValues(effect=RuleSettingEffect.DISABLED, values=docstring_conventions.conventions_except(DocstringConvention.GOOGLE)),)
            ),
        ),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
        cache_behavior=RuleCacheBehavior.FILE_LOCAL,
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
        accumulator = section_edits.ReplacementAccumulator(docstring, context=context, rule=rule)
        for section in docstring.structure.sections:
            line = docstring.structure.lines[section.header_line]
            suffix_start = section_edits.section_name_start_column(line) + len(section.name)
            suffix = line.text[suffix_start:]
            if ":" in suffix:
                continue
            message = f"Docstring section '{section.name}' should end with a colon"
            trimmed_suffix = suffix.strip(ascii_whitespace.SPACE_AND_TAB)
            if not trimmed_suffix:
                accumulator.add(line, suffix_start, len(line.text), ":", instance_message=message)
                continue
            leading_end = suffix_start + len(suffix) - len(suffix.lstrip(ascii_whitespace.SPACE_AND_TAB))
            accumulator.add(line, suffix_start, leading_end, ":", instance_message=message)
            trailing_start = suffix_start + len(suffix.rstrip(ascii_whitespace.SPACE_AND_TAB))
            if trailing_start < len(line.text):
                accumulator.add(line, trailing_start, len(line.text), "", instance_message=message)
        results.extend(accumulator.results())
    return tuple(results)
