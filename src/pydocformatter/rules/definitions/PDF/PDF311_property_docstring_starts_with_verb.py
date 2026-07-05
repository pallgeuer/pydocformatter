"""PDF311 property-docstring-starts-with-verb rule."""

from __future__ import annotations

import pydocformatter.rules.definition_helpers.decorators as decorator_helpers
import pydocformatter.rules.definition_helpers.summary_style as summary_style
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.violations as rule_violations
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleCheckKind, RuleMetadata


@rule_registration.register_rule_to(PDF)
class PDF311PropertyDocstringStartsWithVerb(RuleBase):
    """Rule implementation for PDF311.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF311"),
        name="property-docstring-starts-with-verb",
        message="Property docstring should not start with a verb",
        fix_availability=FixAvailability.NEVER,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for property docstrings that start with disallowed verbs.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        data = PDF.require_data(context)
        violations: list[rule_violations.RuleViolation] = []
        for target in data.summary_line_targets:
            owner = target.docstring.owner
            if (
                not isinstance(owner, PDF_definition.DefinitionInfo)
                or owner.kind is not PDF_definition.DefinitionKind.FUNCTION
                or summary_style.is_test_function(owner)
                or not decorator_helpers.has_property_decorator(owner.decorators, context=context, settings=context.settings)
            ):
                continue
            word = summary_style.first_word_target(target)
            if word is None:
                continue
            normalized = summary_style.normalize_word(word.word)
            if normalized in _DISALLOWED_VERBS:
                violations.append(rule_violations.diagnostic(cls.meta, summary_style.line_numbers(word), instance_message=f'Property docstring should not start with a verb ("{word.word}")'))
        return tuple(violations)


_DISALLOWED_VERBS = frozenset(("return", "returns", "get", "gets", "yield", "yields", "fetch", "fetches", "retrieve", "retrieves"))
