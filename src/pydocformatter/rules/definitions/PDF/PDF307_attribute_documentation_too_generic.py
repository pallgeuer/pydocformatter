"""PDF307 attribute-documentation-too-generic rule."""

# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# First-party imports
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
from pydocformatter.cli.settings_check import DocstringConvention
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.definition_helpers import docstring_conventions, docstring_sections, documentation_style
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleCheckKind, RuleMetadata, RuleSettingEffect, RuleSettingEffects, RuleSettingEffectValues


if TYPE_CHECKING:
    # First-party imports
    import pydocformatter.rules.violations as rule_violations
    from pydocformatter.rules.definition import RuleContext


_POLICY = documentation_style.DocumentedValueStylePolicy(nouns=frozenset(("attribute", "field", "value")), message_subject="attribute")


@rule_registration.register_rule_to(PDF)
class PDF307AttributeDocumentationTooGeneric(RuleBase):
    """Rule implementation for PDF307.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF307"),
        name="attribute-documentation-too-generic",
        message="Attribute documentation is too generic",
        fix_availability=FixAvailability.NEVER,
        stable_since="1.0.0",
        setting_effects=(
            RuleSettingEffects(
                setting="docstring_convention",
                effects=(
                    RuleSettingEffectValues(
                        effect=RuleSettingEffect.IGNORED, values=docstring_conventions.ignored_conventions_except(DocstringConvention.GOOGLE, DocstringConvention.NUMPY, DocstringConvention.REST)
                    ),
                ),
            ),
        ),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for attribute documentation that only restates the attribute name.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        data = PDF.require_data(context)
        targets: list[documentation_style.DocumentedValueTarget] = []
        for docstring in data.docstrings:
            targets.extend(_entry_targets(docstring))
            target = _attached_docstring_target(docstring)
            if target is not None:
                targets.append(target)
        return documentation_style.too_generic_violations(tuple(targets), rule=cls.meta, policy=_POLICY)


def _entry_targets(docstring: PDF_definition.DocstringInfo) -> tuple[documentation_style.DocumentedValueTarget, ...]:
    """Return parsed owner-docstring attribute-entry style targets."""
    if not isinstance(docstring.owner, PDF_definition.DefinitionInfo) or docstring.owner.kind not in {PDF_definition.DefinitionKind.MODULE, PDF_definition.DefinitionKind.CLASS}:
        return ()
    targets: list[documentation_style.DocumentedValueTarget] = []
    for entry in docstring.structure.entries:
        if entry.kind is not PDF_definition.DocstringEntryKind.ATTRIBUTE or len(entry.names) != 1 or not entry.description or _is_rest_type_entry(entry):
            continue
        line = docstring.structure.lines[entry.start_line]
        targets.append(documentation_style.DocumentedValueTarget(name=entry.names[0], description=entry.description, line_numbers=PDF_definition.docstring_line_numbers(docstring, line)))
    return tuple(targets)


def _is_rest_type_entry(entry: PDF_definition.DocstringEntry) -> bool:
    """Return whether a parsed entry came from a reST attribute type field."""
    return entry.field_name in docstring_sections.REST_ATTRIBUTE_TYPE_FIELDS


def _attached_docstring_target(docstring: PDF_definition.DocstringInfo) -> documentation_style.DocumentedValueTarget | None:
    """Return an attached attribute docstring style target when it is unambiguous."""
    if not isinstance(docstring.owner, PDF_definition.AttributeInfo) or len(docstring.owner.targets) != 1:
        return None
    block = PDF_definition.first_summary_block(docstring)
    if block is None or block.end_line - block.start_line != 1:
        return None
    line = PDF_definition.first_non_adornment_line(docstring, block.start_line, block.end_line)
    if line is None:
        return None
    return documentation_style.DocumentedValueTarget(name=docstring.owner.targets[0], description=line.text, line_numbers=PDF_definition.docstring_line_numbers(docstring, line))
