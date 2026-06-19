from __future__ import annotations

import pydocformatter.rules.definition_helpers.docstring_conventions as docstring_conventions
import pydocformatter.rules.definition_helpers.section_edits as section_edits
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
import pydocformatter.rules.edits as rule_edits
import pydocformatter.rules.registration as rule_registration
from pydocformatter.cli.settings_check import DocstringConvention
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext, RuleFixResult
from pydocformatter.rules.models import FixAvailability, RuleFinding, RuleMetadata, RuleSettingEffect, RuleSettingEffects, RuleSettingEffectValues


@rule_registration.register_rule_to(PDF_definition.PDF)
class PDF407ConventionEntrySpacing(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PDF407"),
        name="convention-entry-spacing",
        message="Docstring convention entry spacing should be normalized",
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
    )

    @classmethod
    def check(cls, context: RuleContext) -> tuple[RuleFinding, ...]:
        """Return findings for non-canonical convention entry spacing."""
        return section_edits.findings_for_results(_results(context, rule=cls.meta))

    @classmethod
    def fix(cls, context: RuleContext) -> RuleFixResult:
        """Normalize safely mapped convention entry spacing."""
        return section_edits.fix_result_for_results(context, cls.meta, _results(context, rule=cls.meta))


def _results(context: RuleContext, *, rule: RuleMetadata) -> tuple[section_edits.SectionEditResult, ...]:
    """Return findings and fixes for convention entry spacing."""
    data = PDF_definition.PDF.require_data(context)
    results: list[section_edits.SectionEditResult] = []
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
        change = section_edits.planned_replacement_change(docstring, context=context, replacements=tuple(replacements), value_lines=value_lines)
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
    if convention is DocstringConvention.GOOGLE:
        return _canonical_google_entry_line(text, entry)
    if convention is DocstringConvention.NUMPY:
        return _canonical_numpy_entry_line(text, entry)
    if convention is DocstringConvention.REST:
        return _canonical_rest_entry_line(text, entry)
    return None


def _canonical_google_entry_line(text: str, entry: PDF_definition.DocstringEntry) -> str | None:
    match = PDF_definition._GOOGLE_ENTRY_RE.match(text)
    if match is None and entry.kind in (PDF_definition.DocstringEntryKind.RETURN, PDF_definition.DocstringEntryKind.YIELD, PDF_definition.DocstringEntryKind.EXCEPTION):
        match = PDF_definition._GENERIC_ENTRY_RE.match(text)
    if match is None:
        return None
    head = _google_entry_head(entry)
    if head is None:
        return None
    description = match.group("description").strip()
    if description == ":" and text.rstrip().endswith("::"):
        return None
    return f'{match.group("indent")}{head}:{f" {description}" if description else ""}'


def _google_entry_head(entry: PDF_definition.DocstringEntry) -> str | None:
    if entry.kind in (PDF_definition.DocstringEntryKind.RETURN, PDF_definition.DocstringEntryKind.YIELD) and not entry.names:
        return entry.type_text.strip() if entry.type_text else None
    if not entry.names:
        return None
    head = ", ".join(entry.names)
    if entry.type_text:
        head = f"{head} ({entry.type_text.strip()})"
    return head


def _canonical_numpy_entry_line(text: str, entry: PDF_definition.DocstringEntry) -> str | None:
    match = PDF_definition._NUMPY_ENTRY_RE.match(text)
    if match is None:
        return None
    return f'{match.group("indent")}{", ".join(entry.names)} : {entry.type_text.strip() if entry.type_text else match.group("type").strip()}'


def _canonical_rest_entry_line(text: str, entry: PDF_definition.DocstringEntry) -> str | None:
    match = PDF_definition._REST_FIELD_RE.match(text)
    if match is None or entry.field_name is None:
        return None
    argument = _canonical_rest_argument(entry)
    description = match.group("description").strip()
    return f'{match.group("indent")}:{match.group("field")}{f" {argument}" if argument else ""}:{f" {description}" if description else ""}'


def _canonical_rest_argument(entry: PDF_definition.DocstringEntry) -> str | None:
    if entry.field_argument is None:
        return None
    if entry.kind is PDF_definition.DocstringEntryKind.PARAMETER and entry.names:
        if entry.type_text:
            return f"{entry.type_text.strip()} {entry.names[0]}"
        return entry.names[0]
    return entry.field_argument.strip()
