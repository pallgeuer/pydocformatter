"""PDF411 type-like-token-spacing-normalization rule."""

from __future__ import annotations

import dataclasses

import pydocformatter.rules.definition_helpers.docstring_conventions as docstring_conventions
import pydocformatter.rules.definition_helpers.docstring_sections as docstring_sections
import pydocformatter.rules.definition_helpers.section_edits as section_edits
import pydocformatter.rules.definition_helpers.type_expressions as type_expressions
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
import pydocformatter.rules.edits as rule_edits
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.violations as rule_violations
from pydocformatter.cli.settings_check import DocstringConvention
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext
from pydocformatter.rules.models import FixAvailability, RuleCheckKind, RuleMetadata, RuleSettingEffect, RuleSettingEffects, RuleSettingEffectValues


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
        fix_availability=FixAvailability.SOMETIMES,
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
        """Return violations for non-canonical type-like token spacing.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        return _results(context, rule=cls.meta)


@dataclasses.dataclass(frozen=True)
class _LineReplacement:
    """Replacement span for one normalized type-like token."""

    line: PDF_definition.DocstringValueLine
    start_column: int
    end_column: int
    text: str


_TYPE_TEXT_ENTRY_KINDS = frozenset(
    {
        PDF_definition.DocstringEntryKind.PARAMETER,
        PDF_definition.DocstringEntryKind.RETURN,
        PDF_definition.DocstringEntryKind.YIELD,
        PDF_definition.DocstringEntryKind.ATTRIBUTE,
        PDF_definition.DocstringEntryKind.METHOD,
    }
)


def _results(context: RuleContext, *, rule: RuleMetadata) -> tuple[rule_violations.RuleViolation, ...]:
    """Return violations for type-like token spacing."""
    data = PDF_definition.PDF.require_data(context)
    normalized_type_cache: dict[str, str | None] = {}
    results: list[rule_violations.RuleViolation] = []
    for docstring in data.docstrings:
        replacements: list[rule_edits.PlannedTextReplacement] = []
        value_lines = [line.raw_text for line in docstring.structure.lines]
        replacement_line_numbers: list[int] = []
        unfixable_line_numbers: list[int] = []
        replacement_messages: list[str] = []
        unfixable_messages: list[str] = []
        for entry in docstring.structure.entries:
            line_replacement = _line_replacement(docstring.structure.convention, docstring.structure.lines[entry.start_line], entry, normalized_type_cache=normalized_type_cache)
            if line_replacement is None:
                continue
            replacement = section_edits.text_replacement(line_replacement.line, line_replacement.start_column, line_replacement.end_column, line_replacement.text)
            if replacement is None:
                unfixable_line_numbers.extend(section_edits.line_numbers(docstring, line_replacement.line))
                unfixable_messages.append(rule.message)
                continue
            replacements.append(replacement)
            replacement_line_numbers.extend(section_edits.line_numbers(docstring, line_replacement.line))
            replacement_messages.append(rule.message)
            section_edits.replace_value_line_span(value_lines, line_replacement.line, replacement, line_replacement.text)
        if not replacements and not unfixable_line_numbers:
            continue
        change = section_edits.planned_replacement_changes(docstring, context=context, replacements=tuple(replacements), value_lines=value_lines)
        results.extend(
            section_edits.replacement_results(
                rule,
                replacement_line_numbers=replacement_line_numbers,
                unfixable_line_numbers=unfixable_line_numbers,
                change=change,
                replacement_messages=replacement_messages,
                unfixable_messages=unfixable_messages,
            )
        )
    return tuple(results)


def _line_replacement(
    convention: DocstringConvention,
    line: PDF_definition.DocstringValueLine,
    entry: PDF_definition.DocstringEntry,
    *,
    normalized_type_cache: dict[str, str | None],
) -> _LineReplacement | None:
    """Return a convention-specific replacement for an entry's type-like token."""
    if convention is DocstringConvention.GOOGLE:
        return _google_replacement(line, entry, normalized_type_cache=normalized_type_cache)
    if convention is DocstringConvention.NUMPY:
        return _numpy_replacement(line, entry, normalized_type_cache=normalized_type_cache)
    if convention is DocstringConvention.REST:
        return _rest_replacement(line, entry, normalized_type_cache=normalized_type_cache)
    return None


def _google_replacement(line: PDF_definition.DocstringValueLine, entry: PDF_definition.DocstringEntry, *, normalized_type_cache: dict[str, str | None]) -> _LineReplacement | None:
    """Return a replacement for a Google entry type token."""
    if entry.kind not in _TYPE_TEXT_ENTRY_KINDS:
        return None
    match = PDF_definition._GOOGLE_ENTRY_RE.match(line.text)
    if match is not None and match.group("type") is not None and entry.type_text is not None:
        return _normalized_replacement(line, match.start("type"), match.end("type"), entry.type_text, normalized_type_cache=normalized_type_cache)
    if entry.kind in (PDF_definition.DocstringEntryKind.RETURN, PDF_definition.DocstringEntryKind.YIELD):
        generic_match = PDF_definition._GENERIC_ENTRY_RE.match(line.text)
        if generic_match is not None and entry.type_text is not None:
            return _normalized_replacement(line, generic_match.start("name"), generic_match.end("name"), entry.type_text, normalized_type_cache=normalized_type_cache)
    return None


def _numpy_replacement(line: PDF_definition.DocstringValueLine, entry: PDF_definition.DocstringEntry, *, normalized_type_cache: dict[str, str | None]) -> _LineReplacement | None:
    """Return a replacement for a NumPy entry type token."""
    if entry.kind not in _TYPE_TEXT_ENTRY_KINDS:
        return None
    match = PDF_definition._NUMPY_ENTRY_RE.match(line.text)
    if match is not None and entry.type_text is not None:
        return _normalized_replacement(line, match.start("type"), match.end("type"), entry.type_text, normalized_type_cache=normalized_type_cache)
    if entry.kind in (PDF_definition.DocstringEntryKind.RETURN, PDF_definition.DocstringEntryKind.YIELD) and entry.type_text is not None:
        start_column = len(line.text) - len(line.text.lstrip(" \t"))
        end_column = len(line.text.rstrip(" \t"))
        return _normalized_replacement(line, start_column, end_column, entry.type_text, normalized_type_cache=normalized_type_cache)
    return None


def _rest_replacement(line: PDF_definition.DocstringValueLine, entry: PDF_definition.DocstringEntry, *, normalized_type_cache: dict[str, str | None]) -> _LineReplacement | None:
    """Return a replacement for a reStructuredText field type token."""
    match = PDF_definition._REST_FIELD_RE.match(line.text)
    if match is None or entry.field_name is None:
        return None
    field = entry.field_name
    if field in docstring_sections.REST_TYPE_DESCRIPTION_FIELDS:
        return _normalized_replacement(line, match.start("description"), match.end("description"), match.group("description").strip(), normalized_type_cache=normalized_type_cache)
    if entry.type_text is None or entry.field_argument is None:
        return None
    argument = match.group("argument")
    if argument is None:
        return None
    # _rest_entry_metadata derives type_text as the leading part of the stripped field argument before the final
    # parameter name.
    if not argument.startswith(entry.type_text):
        return None
    start_column = match.start("argument")
    end_column = start_column + len(entry.type_text)
    return _normalized_replacement(line, start_column, end_column, entry.type_text, normalized_type_cache=normalized_type_cache)


def _normalized_replacement(
    line: PDF_definition.DocstringValueLine,
    start_column: int,
    end_column: int,
    text: str,
    *,
    normalized_type_cache: dict[str, str | None],
) -> _LineReplacement | None:
    """Return a replacement object when normalized text differs from source text."""
    normalized = _cached_normalized_type_like_text(text, normalized_type_cache=normalized_type_cache)
    if normalized is None or normalized == text:
        return None
    return _LineReplacement(line=line, start_column=start_column, end_column=end_column, text=normalized)


def _cached_normalized_type_like_text(text: str, *, normalized_type_cache: dict[str, str | None]) -> str | None:
    """Return cached normalized type-like text for an entry fragment."""
    if text not in normalized_type_cache:
        normalized_type_cache[text] = _normalized_type_like_text(text)
    return normalized_type_cache[text]


def _normalized_type_like_text(text: str) -> str | None:
    """Return AST-stable normalized spacing for a type-like expression."""
    return type_expressions.normalized_type_like_text(text)
