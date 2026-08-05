"""PDF213 placeholder-docstring rule."""

# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# First-party imports
import pydocformatter.rules.violations as rule_violations
import pydocformatter.rules.registration as rule_registration
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.definition_helpers import docstring_source
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleCacheBehavior, RuleCheckKind, RuleMetadata


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.definition import RuleContext


_WORD_MARKER_SUFFIX_CHARACTERS = ".:;!?"


@rule_registration.register_rule_to(PDF)
class PDF213PlaceholderDocstring(RuleBase):
    """Rule implementation for PDF213.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF213"),
        name="placeholder-docstring",
        message="Docstring is a placeholder",
        fix_availability=FixAvailability.NEVER,
        stable_since="1.1.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
        cache_behavior=RuleCacheBehavior.FILE_LOCAL,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for docstrings whose complete value is a configured placeholder.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        data = PDF.require_data(context)
        normalized_markers = frozenset(marker.upper() for marker in context.settings.docstring_placeholder_markers)
        return tuple(
            rule_violations.diagnostic(cls.meta, docstring_source.docstring_physical_line_numbers(docstring)) for docstring in data.docstrings if _is_placeholder(docstring.value, normalized_markers)
        )


def _is_placeholder(value: str, normalized_markers: frozenset[str]) -> bool:
    """Return whether a complete evaluated docstring value matches a configured placeholder."""
    stripped = value.strip()
    if not stripped:
        return False
    if stripped == "...":
        return "..." in normalized_markers
    label = stripped.rstrip(_WORD_MARKER_SUFFIX_CHARACTERS)
    if not label or not label.isascii():
        return False
    return label.upper() in normalized_markers
