"""PDF202 empty-docstring rule."""

from __future__ import annotations

import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
import pydocformatter.rules.registration as rule_registration
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleCheckKind, RuleFinding, RuleMetadata


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
    def check(cls, context: RuleContext) -> tuple[RuleFinding, ...]:
        """Return findings for docstrings without meaningful content."""
        data = PDF.require_data(context)
        return tuple(RuleFinding(rule=cls.meta, line_numbers=_line_numbers(docstring), instance_fixable=None) for docstring in data.docstrings if not docstring.value.strip())


def _line_numbers(docstring: PDF_definition.DocstringInfo) -> tuple[int, ...]:
    """Return mapped logical source lines or physical docstring expression lines."""
    mapped = PDF_definition.docstring_value_line_numbers(docstring.structure.lines)
    if mapped:
        return mapped
    return tuple(line.line_number for line in docstring.physical_lines)
