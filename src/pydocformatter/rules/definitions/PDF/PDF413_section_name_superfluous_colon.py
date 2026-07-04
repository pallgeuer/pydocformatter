"""PDF413 section-name-superfluous-colon rule."""

from __future__ import annotations

import dataclasses
import re

import pydocformatter.rules.definition_helpers.docstring_conventions as docstring_conventions
import pydocformatter.rules.definition_helpers.docstring_sections as docstring_sections
import pydocformatter.rules.definition_helpers.section_edits as section_edits
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
import pydocformatter.rules.edits as rule_edits
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.violations as rule_violations
from pydocformatter.cli.settings_check import DocstringConvention
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleCheckKind, RuleMetadata, RuleSettingEffect, RuleSettingEffects, RuleSettingEffectValues

_NUMPY_COLON_SECTION_RE = re.compile(r"^[ \t]*(?P<name>[A-Za-z][A-Za-z ]*?):[ \t]*$")


@dataclasses.dataclass(frozen=True)
class _Target:
    """One NumPy section-name colon target."""

    line: PDF_definition.DocstringValueLine
    name: str


@dataclasses.dataclass(frozen=True)
class _FixableTarget:
    """Mapped source replacement for one target."""

    replacement: rule_edits.PlannedTextReplacement
    line_numbers: tuple[int, ...]
    message: str


@dataclasses.dataclass(frozen=True)
class _UnfixableTarget:
    """Diagnostic-only section-name colon target."""

    line_numbers: tuple[int, ...]
    message: str


@rule_registration.register_rule_to(PDF)
class PDF413SectionNameSuperfluousColon(RuleBase):
    """Rule implementation for PDF413.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF413"),
        name="section-name-superfluous-colon",
        message="Docstring section name should not end with a colon",
        fix_availability=FixAvailability.SOMETIMES,
        stable_since="1.0.0",
        setting_effects=(
            RuleSettingEffects(
                setting="docstring_convention",
                effects=(RuleSettingEffectValues(effect=RuleSettingEffect.IGNORED, values=docstring_conventions.ignored_conventions_except(DocstringConvention.NUMPY)),),
            ),
        ),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for NumPy section names with superfluous trailing colons.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        return _results(context, rule=cls.meta)


def _results(context: RuleContext, *, rule: RuleMetadata) -> tuple[rule_violations.RuleViolation, ...]:
    """Return violations for NumPy section names that end with a colon."""
    data = PDF.require_data(context)
    results: list[rule_violations.RuleViolation] = []
    for docstring in data.docstrings:
        if docstring.structure.convention is not DocstringConvention.NUMPY:
            continue
        fixable_targets: list[_FixableTarget] = []
        value_lines = [line.raw_text for line in docstring.structure.lines]
        unfixable_targets: list[_UnfixableTarget] = []
        for target in _targets(docstring):
            fixable_target, unfixable_target = _planned_target(docstring, target, value_lines=value_lines)
            if fixable_target is not None:
                fixable_targets.append(fixable_target)
            if unfixable_target is not None:
                unfixable_targets.append(unfixable_target)
        if not fixable_targets and not unfixable_targets:
            continue
        fixable_targets.sort(key=lambda target: target.replacement.start_offset)
        unfixable_targets.sort(key=lambda target: target.line_numbers)
        replacements = tuple(target.replacement for target in fixable_targets)
        change = section_edits.planned_replacement_change(docstring, context=context, replacements=replacements, value_lines=value_lines)
        results.extend(
            section_edits.replacement_results(
                rule,
                replacement_line_numbers=[line_number for target in fixable_targets for line_number in target.line_numbers],
                unfixable_line_numbers=[line_number for target in unfixable_targets for line_number in target.line_numbers],
                change=change,
                replacement_messages=[target.message for target in fixable_targets],
                unfixable_messages=[target.message for target in unfixable_targets],
            )
        )
    return tuple(results)


def _targets(docstring: PDF_definition.DocstringInfo) -> tuple[_Target, ...]:
    """Return parsed and unparsed NumPy section-name colon targets in line order."""
    targets: list[_Target] = []
    handled_indexes: set[int] = set()
    for section in docstring.structure.sections:
        handled_indexes.add(section.header_line)
        targets.append(_Target(line=docstring.structure.lines[section.header_line], name=section.name))
    targets.extend(_unparsed_targets(docstring, docstring.structure.blocks, handled_indexes=handled_indexes))
    return tuple(sorted(targets, key=lambda target: target.line.index))


def _unparsed_targets(
    docstring: PDF_definition.DocstringInfo,
    blocks: tuple[PDF_definition.DocstringBlock, ...],
    *,
    handled_indexes: set[int],
) -> tuple[_Target, ...]:
    """Return unparsed NumPy section-name colon targets inside explicit colon-header blocks."""
    targets: list[_Target] = []
    for block in blocks:
        if block.kind is PDF_definition.DocstringBlockKind.COLON_HEADER and block.start_line not in handled_indexes:
            line = docstring.structure.lines[block.start_line]
            name = _unparsed_numpy_colon_section_name(line.text)
            if name is not None and _is_unparsed_section_boundary(docstring, line):
                targets.append(_Target(line=line, name=name))
        targets.extend(_unparsed_targets(docstring, block.children, handled_indexes=handled_indexes))
    return tuple(targets)


def _is_unparsed_section_boundary(docstring: PDF_definition.DocstringInfo, line: PDF_definition.DocstringValueLine) -> bool:
    """Return whether a colon header is positioned like a standalone section boundary."""
    if line.index == 0:
        return True
    return not docstring.structure.lines[line.index - 1].text.strip()


def _planned_target(
    docstring: PDF_definition.DocstringInfo,
    target: _Target,
    *,
    value_lines: list[str],
) -> tuple[_FixableTarget | None, _UnfixableTarget | None]:
    """Return a planned replacement or diagnostic for one NumPy section-name colon."""
    if not _is_superfluous_colon_suffix(_section_suffix(target.line.text, target.name)):
        return None, None
    message = f"Docstring section '{target.name}' should not end with a colon"
    line_numbers = section_edits.line_numbers(docstring, target.line)
    replacement = section_edits.replacement_for_section_suffix(target.line, target.name, "")
    if replacement is None:
        return None, _UnfixableTarget(line_numbers=line_numbers, message=message)
    section_edits.replace_value_line_span(value_lines, target.line, replacement, "")
    return _FixableTarget(replacement=replacement, line_numbers=line_numbers, message=message), None


def _unparsed_numpy_colon_section_name(text: str) -> str | None:
    """Return an unparsed recognized NumPy section name with an immediate colon suffix."""
    match = _NUMPY_COLON_SECTION_RE.match(text)
    if match is None:
        return None
    name = match.group("name").rstrip()
    if docstring_sections.canonical_section_name(DocstringConvention.NUMPY, name) is None:
        return None
    return name


def _section_suffix(text: str, name: str) -> str:
    """Return the text after a section name on its header line."""
    start_column = len(text) - len(text.lstrip(" \t"))
    return text[start_column + len(name) :]


def _is_superfluous_colon_suffix(suffix: str) -> bool:
    """Return whether a section-name suffix is exactly a colon with optional trailing whitespace."""
    return suffix.startswith(":") and not suffix[1:].strip(" \t")
