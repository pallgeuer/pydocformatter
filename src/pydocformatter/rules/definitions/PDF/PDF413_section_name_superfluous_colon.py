"""PDF413 section-name-superfluous-colon rule."""

# Future imports
from __future__ import annotations

# Standard library imports
import re
import dataclasses
from typing import TYPE_CHECKING

# First-party imports
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
from pydocformatter.cli.settings_check import DocstringConvention
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.definition_helpers import ascii_whitespace, docstring_conventions, docstring_sections, section_edits
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleCacheBehavior, RuleCheckKind, RuleMetadata, RuleSettingEffect, RuleSettingEffects, RuleSettingEffectValues


if TYPE_CHECKING:
    # First-party imports
    import pydocformatter.rules.violations as rule_violations
    from pydocformatter.rules.definition import RuleContext


_NUMPY_COLON_SECTION_RE = re.compile(r"^[ \t]*(?P<name>[A-Za-z][A-Za-z ]*?):[ \t]*$")


@dataclasses.dataclass(frozen=True)
class _Target:
    """One NumPy section-name colon target."""

    line: PDF_definition.DocstringValueLine
    name: str


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
        fix_availability=FixAvailability.USUALLY,
        stable_since="1.1.0",
        setting_effects=(
            RuleSettingEffects(
                setting="docstring_convention", effects=(RuleSettingEffectValues(effect=RuleSettingEffect.DISABLED, values=docstring_conventions.conventions_except(DocstringConvention.NUMPY)),)
            ),
        ),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
        cache_behavior=RuleCacheBehavior.FILE_LOCAL,
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
        accumulator = section_edits.ReplacementAccumulator(docstring, context=context, rule=rule)
        for target in _targets(docstring):
            _add_target(accumulator, target)
        results.extend(accumulator.results())
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


def _unparsed_targets(docstring: PDF_definition.DocstringInfo, blocks: tuple[PDF_definition.DocstringBlock, ...], *, handled_indexes: set[int]) -> tuple[_Target, ...]:
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


def _add_target(accumulator: section_edits.ReplacementAccumulator, target: _Target) -> None:
    """Add one NumPy section-name colon replacement when required."""
    if not _is_superfluous_colon_suffix(_section_suffix(target.line.text, target.name)):
        return
    message = f"Docstring section '{target.name}' should not end with a colon"
    replacement = section_edits.replacement_for_section_suffix(target.line, target.name, "")
    accumulator.add_replacement(target.line, replacement, "", instance_message=message)


def _unparsed_numpy_colon_section_name(text: str) -> str | None:
    """Return an unparsed recognized NumPy section name with an immediate colon suffix."""
    match = _NUMPY_COLON_SECTION_RE.match(text)
    if match is None:
        return None
    matched_name = match.group("name")
    if not isinstance(matched_name, str):
        raise TypeError("NumPy section-name capture must be a string")
    name = matched_name.rstrip()
    if docstring_sections.canonical_section_name(DocstringConvention.NUMPY, name) is None:
        return None
    return name


def _section_suffix(text: str, name: str) -> str:
    """Return the text after a section name on its header line."""
    start_column = len(text) - len(text.lstrip(ascii_whitespace.SPACE_AND_TAB))
    return text[start_column + len(name) :]


def _is_superfluous_colon_suffix(suffix: str) -> bool:
    """Return whether a section-name suffix is exactly a colon with optional trailing whitespace."""
    return suffix.startswith(":") and not suffix[1:].strip(ascii_whitespace.SPACE_AND_TAB)
