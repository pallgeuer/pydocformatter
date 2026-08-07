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
from pydocformatter.rules.definition_helpers import ascii_whitespace, docstring_conventions, docstring_sections, section_edits, unicode_safety
from pydocformatter.rules.models import FixAvailability, RuleCacheBehavior, RuleCheckKind, RuleMetadata


if TYPE_CHECKING:
    # First-party imports
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
        fix_availability=FixAvailability.USUALLY,
        stable_since="1.1.0",
        setting_effects=docstring_conventions.convention_setting_effects(disabled=docstring_conventions.UNPARSED_CONVENTIONS),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
        cache_behavior=RuleCacheBehavior.FILE_LOCAL,
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
        accumulator = section_edits.ReplacementAccumulator(docstring, context=context, rule=rule)
        for entry in docstring.structure.entries:
            line = docstring.structure.lines[entry.start_line]
            canonical = _canonical_entry_line(docstring.structure.convention, line.text, entry)
            if canonical is None or canonical == line.text:
                continue
            accumulator.add(line, 0, len(line.text), canonical)
        results.extend(accumulator.results())
    return tuple(results)


def _canonical_entry_line(convention: DocstringConvention, text: str, entry: PDF_definition.DocstringEntry) -> str | None:
    """Return the canonical spelling for one convention entry line."""
    if unicode_safety.has_nonstandard_whitespace_or_control(text):
        return None
    if convention is DocstringConvention.GOOGLE:
        return _canonical_google_entry_line(text, entry)
    if convention is DocstringConvention.NUMPY:
        return _canonical_numpy_entry_line(text, entry)
    if convention is DocstringConvention.REST:
        return _canonical_rest_entry_line(text, entry)
    return None


def _canonical_google_entry_line(text: str, entry: PDF_definition.DocstringEntry) -> str | None:
    """Return the canonical Google entry line for spacing normalization."""
    match = PDF_definition._match_google_entry_for_kind(text, entry.kind)
    if match is None and (entry.kind in {PDF_definition.DocstringEntryKind.RETURN, PDF_definition.DocstringEntryKind.YIELD} or PDF_definition.is_exception_name_entry_kind(entry.kind)):
        match = PDF_definition._match_generic_entry(text)
    if match is None:
        return None
    head = _google_entry_head(entry, original_name=match.name.strip(ascii_whitespace.SPACE_AND_TAB), original_type=match.type_text, original_signature=match.signature_text)
    if head is None:
        return None
    description = match.description.strip(ascii_whitespace.SPACE_AND_TAB)
    if description == ":" and text.rstrip(ascii_whitespace.SPACE_AND_TAB).endswith("::"):
        return None
    return f"{match.indent}{head}:{f' {description}' if description else ''}"


def _google_entry_head(entry: PDF_definition.DocstringEntry, *, original_name: str, original_type: str | None, original_signature: str | None) -> str | None:
    """Return the canonical Google entry head before the description colon."""
    if entry.kind is PDF_definition.DocstringEntryKind.METHOD and original_signature is not None:
        return f"{original_name}{original_signature}"
    if entry.kind in {PDF_definition.DocstringEntryKind.RETURN, PDF_definition.DocstringEntryKind.YIELD} and not entry.names:
        return entry.type_info.text.strip(ascii_whitespace.SPACE_AND_TAB) if entry.type_info is not None else None
    if PDF_definition.is_exception_name_entry_kind(entry.kind):
        if original_type:
            return f"{original_name} ({original_type.strip(ascii_whitespace.SPACE_AND_TAB)})"
        return original_name
    if not entry.names:
        return None
    head = ", ".join(entry.names)
    if entry.type_info is not None:
        head = f"{head} ({entry.type_info.text.strip(ascii_whitespace.SPACE_AND_TAB)})"
    return head


def _canonical_numpy_entry_line(text: str, entry: PDF_definition.DocstringEntry) -> str | None:
    """Return the canonical NumPy entry line for spacing normalization."""
    if PDF_definition.is_exception_name_entry_kind(entry.kind) and (exception_match := PDF_definition._NUMPY_EXCEPTION_ENTRY_RE.match(text)) is not None:
        description = exception_match.group("description").strip(ascii_whitespace.SPACE_AND_TAB)
        return f"{exception_match.group('indent')}{exception_match.group('name').strip(ascii_whitespace.SPACE_AND_TAB)}:{f' {description}' if description else ''}"
    match = PDF_definition._NUMPY_ENTRY_RE.match(text)
    if match is None:
        return None
    return f"{match.group('indent')}{', '.join(entry.names)} : {entry.type_info.text.strip(ascii_whitespace.SPACE_AND_TAB) if entry.type_info is not None else match.group('type').strip(ascii_whitespace.SPACE_AND_TAB)}"


def _canonical_rest_entry_line(text: str, entry: PDF_definition.DocstringEntry) -> str | None:
    """Return the canonical reStructuredText field line for spacing normalization."""
    match = PDF_definition._REST_FIELD_RE.match(text)
    if match is None or entry.field_name is None:
        return None
    argument = _canonical_rest_argument(entry)
    description = match.group("description").strip(ascii_whitespace.SPACE_AND_TAB)
    return f"{match.group('indent')}:{match.group('field')}{f' {argument}' if argument else ''}:{f' {description}' if description else ''}"


def _canonical_rest_argument(entry: PDF_definition.DocstringEntry) -> str | None:
    """Return the canonical reStructuredText field argument."""
    if entry.field_argument is None:
        return None
    if docstring_sections.is_rest_type_field(entry.field_name):
        return entry.field_argument.strip(ascii_whitespace.SPACE_AND_TAB)
    if entry.kind is PDF_definition.DocstringEntryKind.PARAMETER and entry.names:
        if entry.type_info is not None:
            return f"{entry.type_info.text.strip(ascii_whitespace.SPACE_AND_TAB)} {entry.names[0]}"
        return entry.names[0]
    return entry.field_argument.strip(ascii_whitespace.SPACE_AND_TAB)
