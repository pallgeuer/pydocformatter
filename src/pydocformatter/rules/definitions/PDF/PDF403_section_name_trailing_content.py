"""PDF403 section-name-trailing-content rule."""

# Future imports
from __future__ import annotations

# Standard library imports
import re
from typing import TYPE_CHECKING

# First-party imports
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
from pydocformatter.cli.settings_check import DocstringConvention
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.definition_helpers import ascii_whitespace, docstring_conventions, docstring_sections, section_edits, text_layout, unicode_safety
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleCacheBehavior, RuleCheckKind, RuleMetadata, RuleSettingEffect, RuleSettingEffects, RuleSettingEffectValues


if TYPE_CHECKING:
    # First-party imports
    import pydocformatter.rules.violations as rule_violations
    from pydocformatter.rules.definition import RuleContext


_GOOGLE_TRAILING_CONTENT_RE = re.compile(r"^(?P<indent>[ \t]*)(?P<name>[A-Za-z][A-Za-z ]*?)[ \t]*:[ \t]+(?P<content>\S.*)$")


@rule_registration.register_rule_to(PDF)
class PDF403SectionNameTrailingContent(RuleBase):
    """Rule implementation for PDF403.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF403"),
        name="section-name-trailing-content",
        message="Docstring section name should be followed by a line break",
        fix_availability=FixAvailability.USUALLY,
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
        """Return violations for section names with content on the same line.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        return _results(context, rule=cls.meta)


def _results(context: RuleContext, *, rule: RuleMetadata) -> tuple[rule_violations.RuleViolation, ...]:
    """Return violations for section names followed by trailing content."""
    data = PDF.require_data(context)
    results: list[rule_violations.RuleViolation] = []
    for docstring in data.docstrings:
        if docstring.structure.convention is not DocstringConvention.GOOGLE:
            continue
        output_lines: list[PDF_definition.DocstringOutputLine] = []
        line_numbers: list[int] = []
        messages: list[str] = []
        protected_indexes = _protected_or_parsed_line_indexes(docstring)
        changed = False
        for line in docstring.structure.lines:
            target = None if line.index in protected_indexes else _google_trailing_content_target(line, context=context)
            if target is None:
                output_lines.append(PDF_definition.DocstringOutputLine(original=line, source=None, value=None))
                continue
            header, content, name = target
            line_numbers.extend(section_edits.line_numbers(docstring, line))
            messages.append(f"Docstring section '{name}' should be followed by a line break")
            output_lines.extend((PDF_definition.DocstringOutputLine(source=header, value=header), PDF_definition.DocstringOutputLine(source=content, value=content)))
            changed = True
        if not changed:
            continue
        change = section_edits.planned_output_change(docstring, context=context, output_lines=tuple(output_lines), line_numbers=tuple(line_numbers))
        results.append(section_edits.result(rule, line_numbers, change=change, instance_message=section_edits.combined_instance_message(messages)))
    return tuple(results)


def _google_trailing_content_target(line: PDF_definition.DocstringValueLine, *, context: RuleContext) -> tuple[str, str, str] | None:
    """Return split header/content lines for a Google section with trailing text."""
    if unicode_safety.has_nonstandard_whitespace_or_control(line.text):
        return None
    match = _GOOGLE_TRAILING_CONTENT_RE.match(line.text)
    if match is None:
        return None
    name = match.group("name").rstrip(ascii_whitespace.SPACE_AND_TAB)
    canonical = docstring_sections.canonical_section_name(DocstringConvention.GOOGLE, name)
    if canonical is None:
        return None
    raw_indent = line.raw_text[: line.text_raw_start_column + len(match.group("indent")) - line.text_virtual_prefix_length]
    header = f"{raw_indent}{name}:"
    trailing_content = match.group("content").strip(ascii_whitespace.SPACE_AND_TAB)
    content = f"{raw_indent}{text_layout.indent_unit(context.settings)}{trailing_content}"
    return header, content, name


def _protected_or_parsed_line_indexes(docstring: PDF_definition.DocstringInfo) -> set[int]:
    """Return logical line indexes that are already parsed or protected from splitting."""
    indexes: set[int] = set()
    for section in docstring.structure.sections:
        indexes.update(range(section.start_line, section.end_line))
    _add_protected_or_parsed_block_indexes(docstring.structure.blocks, indexes)
    return indexes


def _add_protected_or_parsed_block_indexes(blocks: tuple[PDF_definition.DocstringBlock, ...], indexes: set[int]) -> None:
    """Add line indexes occupied by non-paragraph blocks to a mutable set."""
    for block in blocks:
        if block.kind is not PDF_definition.DocstringBlockKind.PARAGRAPH:
            indexes.update(range(block.start_line, block.end_line))
            continue
        _add_protected_or_parsed_block_indexes(block.children, indexes)
