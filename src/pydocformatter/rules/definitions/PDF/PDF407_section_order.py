"""PDF407 section-order rule."""

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
from pydocformatter.rules.definition_helpers import docstring_conventions, docstring_sections, rest_fields, section_edits
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleCacheBehavior, RuleCheckKind, RuleMetadata


if TYPE_CHECKING:
    # First-party imports
    import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
    from pydocformatter.rules.definition import RuleContext


@rule_registration.register_rule_to(PDF)
class PDF407SectionOrder(RuleBase):
    """Rule implementation for PDF407.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF407"),
        name="section-order",
        message="Docstring sections should be in the configured order",
        fix_availability=FixAvailability.NEVER,
        stable_since="1.0.0",
        setting_effects=docstring_conventions.convention_setting_effects(disabled=docstring_conventions.UNPARSED_CONVENTIONS),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
        cache_behavior=RuleCacheBehavior.FILE_LOCAL,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for convention sections that appear out of order.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        return _violations(context, rule=cls.meta)


def _violations(context: RuleContext, *, rule: RuleMetadata) -> tuple[rule_violations.RuleViolation, ...]:
    """Return violations for convention sections or reST fields that appear out of order."""
    data = PDF.require_data(context)
    violations: list[rule_violations.RuleViolation] = []
    for docstring in data.docstrings:
        if docstring.structure.convention is DocstringConvention.REST:
            violations.extend(_rest_field_violations(docstring, rule=rule))
        else:
            max_rank = -1
            max_rank_section_name = ""
            for section in docstring.structure.sections:
                rank = docstring_sections.section_order_rank(docstring.structure.convention, section.name)
                if rank is None:
                    continue
                if rank < max_rank:
                    line = docstring.structure.lines[section.header_line]
                    violations.append(
                        rule_violations.diagnostic(
                            rule, section_edits.line_numbers(docstring, line), instance_message=f"Docstring section '{section.name}' should appear before '{max_rank_section_name}'"
                        )
                    )
                else:
                    max_rank = rank
                    max_rank_section_name = section.name
    return tuple(violations)


def _rest_field_violations(docstring: PDF_definition.DocstringInfo, *, rule: RuleMetadata) -> tuple[rule_violations.RuleViolation, ...]:
    """Return violations for out-of-order reStructuredText fields."""
    violations: list[rule_violations.RuleViolation] = []
    max_rank = -1
    max_rank_label = ""
    for entry in docstring.structure.entries:
        if entry.field_name is None:
            continue
        rank = rest_fields.order_rank(entry)
        if rank is None:
            continue
        label = rest_fields.label(entry)
        if rank < max_rank:
            line = docstring.structure.lines[entry.start_line]
            violations.append(rule_violations.diagnostic(rule, section_edits.line_numbers(docstring, line), instance_message=f"Docstring field '{label}' should appear before '{max_rank_label}'"))
        else:
            max_rank = rank
            max_rank_label = label
    return tuple(violations)
