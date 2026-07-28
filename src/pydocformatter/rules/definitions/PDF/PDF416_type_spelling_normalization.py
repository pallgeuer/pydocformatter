"""PDF416 type-spelling-normalization rule."""

# Future imports
from __future__ import annotations

# Standard library imports
import functools
from typing import TYPE_CHECKING

# First-party imports
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.definition_helpers import docstring_conventions, section_edits, type_expressions
from pydocformatter.rules.models import FixAvailability, RuleCacheBehavior, RuleCheckKind, RuleMetadata


if TYPE_CHECKING:
    # First-party imports
    import pydocformatter.rules.violations as rule_violations
    from pydocformatter.rules.definition import RuleContext


@rule_registration.register_rule_to(PDF_definition.PDF)
class PDF416TypeSpellingNormalization(RuleBase):
    """Rule implementation for PDF416.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF416"),
        name="type-spelling-normalization",
        message="Docstring type spelling should be normalized",
        fix_availability=FixAvailability.SOMETIMES,
        stable_since="1.1.0",
        setting_effects=docstring_conventions.convention_setting_effects(disabled=docstring_conventions.UNPARSED_CONVENTIONS),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
        cache_behavior=RuleCacheBehavior.FILE_LOCAL,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for conservatively normalizable type spelling.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        data = PDF_definition.PDF.require_data(context)
        normalize = functools.lru_cache(maxsize=None)(type_expressions.normalized_type_spelling_text)
        results: list[rule_violations.RuleViolation] = []
        for docstring in data.docstrings:
            accumulator = section_edits.ReplacementAccumulator(docstring, context=context, rule=cls.meta)
            for entry in docstring.structure.entries:
                if entry.type_info is None or entry.type_info.slot is None:
                    continue
                slot = entry.type_info.slot
                normalized = normalize(entry.type_info.text)
                if normalized is None:
                    continue
                line = docstring.structure.lines[slot.line_index]
                accumulator.add(line, slot.semantic_start_column, slot.semantic_end_column, normalized)
            results.extend(accumulator.results())
        return tuple(results)
