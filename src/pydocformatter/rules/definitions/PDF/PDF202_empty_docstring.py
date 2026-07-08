"""PDF202 empty-docstring rule."""

# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# First-party imports
import pydocformatter.rules.violations as rule_violations
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleCheckKind, RuleMetadata


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.definition import RuleContext


@rule_registration.register_rule_to(PDF)
class PDF202EmptyDocstring(RuleBase):
    """Rule implementation for PDF202.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF202"),
        name="empty-docstring",
        message="Docstring is empty",
        fix_availability=FixAvailability.NEVER,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for docstrings without meaningful content.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        data = PDF.require_data(context)
        return tuple(rule_violations.diagnostic(cls.meta, _line_numbers(docstring)) for docstring in data.docstrings if not docstring.value.strip())


def _line_numbers(docstring: PDF_definition.DocstringInfo) -> tuple[int, ...]:
    """Return mapped logical source lines or physical docstring expression lines."""
    mapped = PDF_definition.docstring_value_line_numbers(docstring.structure.lines)
    if mapped:
        return mapped
    return tuple(line.line_number for line in docstring.physical_lines)
