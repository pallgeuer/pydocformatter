from __future__ import annotations

import libcst as cst

import pydocformatter.rules.collection as rule_collection
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
import pydocformatter.rules.edits as rule_edits
import pydocformatter.rules.text_helpers as text_helpers
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext, RuleFixResult
from pydocformatter.rules.models import FixAvailability, RuleFinding, RuleMetadata


@rule_collection.register_rule_to(PDF_definition.PDF)
class PDF001ReflowRequired(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PDF001"),
        name="reflow-required",
        message="Docstring chunk needs reflow",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="0.3.0",
        setting_effects=(),
        incompatible_with=(),
    )

    @classmethod
    def check(cls, context: RuleContext) -> tuple[RuleFinding, ...]:
        """Return findings for docstring reflow changes."""
        return rule_edits.findings_for_planned_source_changes(cls.meta, _planned_changes(context))

    @classmethod
    def fix(cls, context: RuleContext) -> RuleFixResult:
        """Apply docstring reflow changes."""
        changes = _planned_changes(context)
        if not changes:
            return RuleFixResult(module=context.module)
        module = rule_edits.apply_planned_source_changes(context.module, changes)
        findings = rule_edits.findings_for_planned_source_changes(cls.meta, changes)
        return RuleFixResult(module=module, fixed_findings=findings)


def _planned_changes(context: RuleContext) -> tuple[rule_edits.PlannedSourceChange, ...]:
    """Return all safe docstring reflow changes for the current source."""
    data = PDF_definition.PDF.require_data(context)
    changes: list[rule_edits.PlannedSourceChange] = []
    for docstring in data.docstrings:
        change = _planned_docstring_change(docstring, context=context)
        if change is not None:
            changes.append(change)
    return tuple(changes)


def _planned_docstring_change(docstring: PDF_definition.DocstringInfo, *, context: RuleContext) -> rule_edits.PlannedSourceChange | None:
    """Return one whole-literal replacement for a safely mapped docstring."""
    if docstring.kind != PDF_definition.DocstringKind.SIMPLE or not isinstance(docstring.node, cst.SimpleString):
        return None
    if not docstring.structure.reflow_regions or not _has_safe_source_mapping(docstring):
        return None

    fallback_prefix = _fallback_line_prefix(context.module.code, docstring=docstring)
    replacements: list[rule_edits.PlannedTextReplacement] = []
    for region in docstring.structure.reflow_regions:
        replacement = _replacement_for_region(docstring, region, context=context, fallback_prefix=fallback_prefix)
        if replacement is None:
            continue
        current = docstring.value[replacement.start_offset : replacement.end_offset]
        if replacement.text != current:
            replacements.append(replacement)
    if not replacements:
        return None

    value = docstring.value
    for replacement in reversed(replacements):
        value = f"{value[: replacement.start_offset]}{replacement.text}{value[replacement.end_offset:]}"
    rendered = _render_simple_string(docstring.node, value, line_ending=context.line_ending, ascii_only=docstring.source.isascii())
    if rendered is None or rendered == docstring.source:
        return None
    return rule_edits.PlannedSourceChange(
        edit=rule_edits.SourceEdit(range=docstring.range, replacement=rendered),
        line_numbers=tuple(sorted({line_number for replacement in replacements for line_number in replacement.line_numbers})),
    )


def _replacement_for_region(docstring: PDF_definition.DocstringInfo, region: PDF_definition.ReflowRegion, *, context: RuleContext, fallback_prefix: str) -> rule_edits.PlannedTextReplacement | None:
    """Return generated evaluated-value text for one reflow region."""
    source_line_numbers = _source_line_numbers_for_region(docstring, region)
    if source_line_numbers is None:
        return None
    initial_base = _line_base_prefix(docstring, region.start_line, first_generated_line=True, fallback_prefix=fallback_prefix)
    subsequent_base = _line_base_prefix(docstring, region.start_line, first_generated_line=False, fallback_prefix=fallback_prefix)
    width = min(
        context.settings.line_length - text_helpers.display_width(initial_base, tab_width=context.settings.indent_width),
        context.settings.line_length - text_helpers.display_width(subsequent_base, tab_width=context.settings.indent_width),
    )
    if _should_split_google_entry_prefix(region, width=width, tab_width=context.settings.indent_width):
        wrapped = _wrapped_region_lines(
            region,
            width=width,
            initial_indent=region.subsequent_indent,
            subsequent_indent=region.subsequent_indent,
        )
        if not wrapped:
            return None
        return _render_region_replacement(
            docstring,
            region,
            wrapped=(region.initial_indent.rstrip(), *wrapped),
            source_line_numbers=source_line_numbers,
            fallback_prefix=fallback_prefix,
        )
    wrapped = _wrapped_region_lines(
        region,
        width=width,
        initial_indent=region.initial_indent,
        subsequent_indent=region.subsequent_indent,
    )
    if not wrapped:
        return None
    return _render_region_replacement(
        docstring,
        region,
        wrapped=wrapped,
        source_line_numbers=source_line_numbers,
        fallback_prefix=fallback_prefix,
    )


def _should_split_google_entry_prefix(region: PDF_definition.ReflowRegion, *, width: int, tab_width: int) -> bool:
    """Return whether a Google entry prefix should stand alone before wrapped description text."""
    if region.kind is not PDF_definition.DocstringBlockKind.SECTION_ENTRY:
        return False
    if text_helpers.display_width(region.initial_indent, tab_width=tab_width) <= text_helpers.display_width(region.subsequent_indent, tab_width=tab_width):
        return False
    # Move very long Google entry prefixes onto their own line when the first description line would have too little
    # useful room.
    return width - text_helpers.display_width(region.initial_indent, tab_width=tab_width) < max(8, tab_width * 2)


def _source_line_numbers_for_region(docstring: PDF_definition.DocstringInfo, region: PDF_definition.ReflowRegion) -> tuple[int, ...] | None:
    """Return safe concrete source line numbers for a reflow region."""
    line_numbers: list[int] = []
    for index in range(region.start_line, region.end_line):
        line_number = docstring.structure.lines[index].source_line_number
        if line_number is None:
            return None
        line_numbers.append(line_number)
    return tuple(line_numbers)


def _wrapped_region_lines(region: PDF_definition.ReflowRegion, *, width: int, initial_indent: str, subsequent_indent: str) -> tuple[str, ...]:
    """Return normalized wrapped region lines."""
    return text_helpers.wrap_text(
        " ".join(line.strip() for line in region.lines),
        width=max(1, width),
        initial_indent=initial_indent,
        subsequent_indent=subsequent_indent,
    )


def _render_region_replacement(
    docstring: PDF_definition.DocstringInfo,
    region: PDF_definition.ReflowRegion,
    *,
    wrapped: tuple[str, ...],
    source_line_numbers: tuple[int, ...],
    fallback_prefix: str,
) -> rule_edits.PlannedTextReplacement | None:
    """Return replacement text for normalized wrapped region lines."""
    raw_lines = [_raw_generated_line(docstring, region.start_line, line, first_generated_line=index == 0, fallback_prefix=fallback_prefix) for index, line in enumerate(wrapped)]
    return rule_edits.PlannedTextReplacement(
        start_offset=region.start_offset,
        end_offset=region.end_offset,
        text="\n".join(raw_lines),
        line_numbers=source_line_numbers,
    )


def _has_safe_source_mapping(docstring: PDF_definition.DocstringInfo) -> bool:
    """Return whether evaluated lines can be rewritten as literal body text."""
    return all(line.source_line_number is not None for line in docstring.structure.lines)


def _line_base_prefix(docstring: PDF_definition.DocstringInfo, line_index: int, *, first_generated_line: bool, fallback_prefix: str) -> str:
    """Return the raw evaluated-value prefix before generated semantic text."""
    if line_index == 0 and first_generated_line:
        return docstring.structure.lines[0].raw_indent
    # Continuation output uses the existing body margin when available, while the first generated line above uses the
    # literal line itself.
    margin_line = docstring.structure.lines[line_index if line_index > 0 else min(1, len(docstring.structure.lines) - 1)]
    if margin_line.text_indent and margin_line.raw_indent.endswith(margin_line.text_indent):
        return margin_line.raw_indent[: -len(margin_line.text_indent)]
    if not margin_line.text_indent and margin_line.raw_indent:
        return margin_line.raw_indent
    return fallback_prefix


def _raw_generated_line(docstring: PDF_definition.DocstringInfo, line_index: int, generated_text: str, *, first_generated_line: bool, fallback_prefix: str) -> str:
    """Return generated evaluated-value text using the original raw leading whitespace when it can be mapped."""
    if line_index == 0 and first_generated_line:
        margin_line = docstring.structure.lines[0]
    else:
        margin_line = docstring.structure.lines[line_index if line_index > 0 else min(1, len(docstring.structure.lines) - 1)]
        if not margin_line.raw_indent and not margin_line.text_indent and fallback_prefix:
            return f"{fallback_prefix}{generated_text}"
    if not generated_text.startswith(margin_line.text_indent):
        return f"{fallback_prefix}{generated_text}"
    return f"{margin_line.raw_indent}{generated_text[len(margin_line.text_indent):]}"


def _fallback_line_prefix(source: str, *, docstring: PDF_definition.DocstringInfo) -> str:
    """Return the generated body-line prefix when no prior body line exists."""
    source_line = PDF_definition._source_lines(source)[docstring.range.start.line - 1]
    prefix = source_line[: docstring.range.start.column]
    return prefix if prefix.strip() == "" else " " * docstring.range.start.column


def _render_simple_string(node: cst.SimpleString, value: str, *, line_ending: str, ascii_only: bool) -> str | None:
    """Render a simple string with its existing prefix and quote delimiter."""
    rendered = f"{node.prefix}{node.quote}{value.replace(chr(10), line_ending)}{node.quote}"
    if ascii_only and not rendered.isascii():
        rendered = f"{node.prefix}{node.quote}{PDF_definition.serialize_simple_string_body(value, quote=node.quote, line_ending=line_ending)}{node.quote}"
        if not rendered.isascii():
            return None
    try:
        expression = cst.parse_expression(rendered)
    except Exception:
        return None
    if not isinstance(expression, cst.SimpleString) or expression.evaluated_value != value:
        return None
    return rendered
