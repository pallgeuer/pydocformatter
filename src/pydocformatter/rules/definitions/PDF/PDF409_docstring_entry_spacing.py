"""PDF409 docstring-entry-spacing rule."""

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
from pydocformatter.rules.definition_helpers import docstring_conventions, section_edits
from pydocformatter.rules.models import FixAvailability, RuleCheckKind, RuleMetadata


if TYPE_CHECKING:
    # First-party imports
    import pydocformatter.rules.edits as rule_edits
    import pydocformatter.rules.violations as rule_violations
    from pydocformatter.rules.definition import RuleContext


@rule_registration.register_rule_to(PDF_definition.PDF)
class PDF409DocstringEntrySpacing(RuleBase):
    """Rule implementation for PDF409.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF409"),
        name="docstring-entry-spacing",
        message="Docstring convention entry spacing should be normalized",
        fix_availability=FixAvailability.SOMETIMES,
        stable_since="1.0.0",
        setting_effects=docstring_conventions.convention_setting_effects(disabled=docstring_conventions.UNPARSED_CONVENTIONS),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for non-canonical convention entry spacing.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        return _results(context, rule=cls.meta)


def _results(context: RuleContext, *, rule: RuleMetadata) -> tuple[rule_violations.RuleViolation, ...]:
    """Return violations for convention entry spacing."""
    data = PDF_definition.PDF.require_data(context)
    results: list[rule_violations.RuleViolation] = []
    for docstring in data.docstrings:
        replacements: list[rule_edits.PlannedTextReplacement] = []
        value_lines = [line.raw_text for line in docstring.structure.lines]
        replacement_line_numbers: list[int] = []
        unfixable_line_numbers: list[int] = []
        replacement_messages: list[str] = []
        unfixable_messages: list[str] = []
        for entry in docstring.structure.entries:
            line = docstring.structure.lines[entry.start_line]
            canonical = _canonical_entry_line(docstring.structure.convention, line.text, entry)
            if canonical is None or canonical == line.text:
                continue
            message = rule.message
            replacement = section_edits.text_replacement(line, 0, len(line.text), canonical)
            if replacement is None:
                unfixable_line_numbers.extend(section_edits.line_numbers(docstring, line))
                unfixable_messages.append(message)
                continue
            replacements.append(replacement)
            replacement_line_numbers.extend(section_edits.line_numbers(docstring, line))
            replacement_messages.append(message)
            section_edits.replace_value_line_span(value_lines, line, replacement, canonical)
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


def _canonical_entry_line(convention: DocstringConvention, text: str, entry: PDF_definition.DocstringEntry) -> str | None:
    """Return the canonical spelling for one convention entry line."""
    if convention is DocstringConvention.GOOGLE:
        return _canonical_google_entry_line(text, entry)
    if convention is DocstringConvention.NUMPY:
        return _canonical_numpy_entry_line(text, entry)
    if convention is DocstringConvention.REST:
        return _canonical_rest_entry_line(text, entry)
    return None


def _canonical_google_entry_line(text: str, entry: PDF_definition.DocstringEntry) -> str | None:
    """Return the canonical Google entry line for spacing normalization."""
    match = PDF_definition._GOOGLE_ENTRY_RE.match(text)
    if match is None and entry.kind in {PDF_definition.DocstringEntryKind.RETURN, PDF_definition.DocstringEntryKind.YIELD, PDF_definition.DocstringEntryKind.EXCEPTION}:
        match = PDF_definition._GENERIC_ENTRY_RE.match(text)
    if match is None:
        return None
    head = _google_entry_head(entry, original_name=match.group("name").strip(), original_type=match.groupdict().get("type"))
    if head is None:
        return None
    description = match.group("description").strip()
    if description == ":" and text.rstrip().endswith("::"):
        return None
    return f"{match.group('indent')}{head}:{f' {description}' if description else ''}"


def _google_entry_head(entry: PDF_definition.DocstringEntry, *, original_name: str, original_type: str | None) -> str | None:
    """Return the canonical Google entry head before the description colon."""
    if entry.kind in {PDF_definition.DocstringEntryKind.RETURN, PDF_definition.DocstringEntryKind.YIELD} and not entry.names:
        return entry.type_text.strip() if entry.type_text else None
    if entry.kind is PDF_definition.DocstringEntryKind.EXCEPTION:
        if original_type:
            return f"{original_name} ({original_type.strip()})"
        return original_name
    if not entry.names:
        return None
    head = ", ".join(entry.names)
    if entry.type_text:
        head = f"{head} ({entry.type_text.strip()})"
    return head


def _canonical_numpy_entry_line(text: str, entry: PDF_definition.DocstringEntry) -> str | None:
    """Return the canonical NumPy entry line for spacing normalization."""
    if entry.kind is PDF_definition.DocstringEntryKind.EXCEPTION and (exception_match := PDF_definition._NUMPY_EXCEPTION_ENTRY_RE.match(text)) is not None:
        description = exception_match.group("description").strip()
        return f"{exception_match.group('indent')}{exception_match.group('name').strip()}:{f' {description}' if description else ''}"
    match = PDF_definition._NUMPY_ENTRY_RE.match(text)
    if match is None:
        return None
    return f"{match.group('indent')}{', '.join(entry.names)} : {entry.type_text.strip() if entry.type_text else match.group('type').strip()}"


def _canonical_rest_entry_line(text: str, entry: PDF_definition.DocstringEntry) -> str | None:
    """Return the canonical reStructuredText field line for spacing normalization."""
    match = PDF_definition._REST_FIELD_RE.match(text)
    if match is None or entry.field_name is None:
        return None
    argument = _canonical_rest_argument(entry)
    description = match.group("description").strip()
    return f"{match.group('indent')}:{match.group('field')}{f' {argument}' if argument else ''}:{f' {description}' if description else ''}"


def _canonical_rest_argument(entry: PDF_definition.DocstringEntry) -> str | None:
    """Return the canonical reStructuredText field argument."""
    if entry.field_argument is None:
        return None
    if entry.kind is PDF_definition.DocstringEntryKind.PARAMETER and entry.names:
        if entry.type_text:
            return f"{entry.type_text.strip()} {entry.names[0]}"
        return entry.names[0]
    return entry.field_argument.strip()
