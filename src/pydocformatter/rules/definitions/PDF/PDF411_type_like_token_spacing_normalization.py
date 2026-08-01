"""PDF411 type-like-token-spacing-normalization rule."""

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
class PDF411TypeLikeTokenSpacingNormalization(RuleBase):
    """Rule implementation for PDF411.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF411"),
        name="type-like-token-spacing-normalization",
        message="Docstring type-like token spacing should be normalized",
        fix_availability=FixAvailability.USUALLY,
        stable_since="1.0.0",
        setting_effects=docstring_conventions.convention_setting_effects(disabled=docstring_conventions.UNPARSED_CONVENTIONS),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
        cache_behavior=RuleCacheBehavior.FILE_LOCAL,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for non-canonical type-like token spacing.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        return _results(context, rule=cls.meta)


def _results(context: RuleContext, *, rule: RuleMetadata) -> tuple[rule_violations.RuleViolation, ...]:
    """Return violations for type-like token spacing."""
    data = PDF_definition.PDF.require_data(context)
    normalize = functools.lru_cache(maxsize=None)(type_expressions.normalized_type_like_text)
    results: list[rule_violations.RuleViolation] = []
    for docstring in data.docstrings:
        accumulator = section_edits.ReplacementAccumulator(docstring, context=context, rule=rule)
        for entry in docstring.structure.entries:
            if entry.type_info is None or entry.type_info.slot is None:
                continue
            slot = entry.type_info.slot
            normalized = normalize(entry.type_info.text)
            if normalized is None:
                continue
            line = docstring.structure.lines[slot.line_index]
            accumulator.add(line, slot.full_start_column, slot.full_end_column, normalized)
        results.extend(accumulator.results())
    return tuple(results)
