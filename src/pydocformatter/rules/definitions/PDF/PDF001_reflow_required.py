from __future__ import annotations

import dataclasses

import libcst as cst

import pydocformatter.rules.definition_helpers.string_literals as string_literals
import pydocformatter.rules.definition_helpers.text_layout as text_layout
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
import pydocformatter.rules.edits as rule_edits
import pydocformatter.rules.registration as rule_registration
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext, RuleFixResult
from pydocformatter.rules.models import FixAvailability, RuleFinding, RuleMetadata


@rule_registration.register_rule_to(PDF_definition.PDF)
class PDF001ReflowRequired(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PDF001"),
        name="reflow-required",
        message="Docstring chunk needs reflow",
        fix_availability=FixAvailability.SOMETIMES,
        stable_since="0.3.0",
        setting_effects=(),
        incompatible_with=(),
    )

    @classmethod
    def check(cls, context: RuleContext) -> tuple[RuleFinding, ...]:
        """Return findings for docstring reflow changes."""
        return tuple(result.finding for result in _docstring_results(context))

    @classmethod
    def fix(cls, context: RuleContext) -> RuleFixResult:
        """Apply docstring reflow changes."""
        changes = _planned_changes(context)
        if not changes:
            return RuleFixResult(module=context.module)
        module = rule_edits.apply_planned_source_changes(context.module, changes)
        findings = rule_edits.findings_for_planned_source_changes(cls.meta, changes, instance_fixable=True)
        return RuleFixResult(module=module, fixed_findings=findings)


def _planned_changes(context: RuleContext) -> tuple[rule_edits.PlannedSourceChange, ...]:
    """Return all safe docstring reflow changes for the current source."""
    return tuple(result.change for result in _docstring_results(context) if result.change is not None)


@dataclasses.dataclass(frozen=True)
class _DocstringResult:
    """Finding and optional fix for one docstring needing reflow."""

    finding: RuleFinding
    change: rule_edits.PlannedSourceChange | None


@dataclasses.dataclass(frozen=True)
class _RegionReplacement:
    """One evaluated-value replacement with source spelling."""

    start_offset: int
    end_offset: int
    value_text: str
    source_text: str
    line_numbers: tuple[int, ...]


def _docstring_results(context: RuleContext) -> tuple[_DocstringResult, ...]:
    """Return all docstring reflow findings and any available fixes."""
    data = PDF_definition.PDF.require_data(context)
    results: list[_DocstringResult] = []
    for docstring in data.docstrings:
        result = _docstring_result(docstring, context=context)
        if result is not None:
            results.append(result)
    return tuple(results)


def _docstring_result(docstring: PDF_definition.DocstringInfo, *, context: RuleContext) -> _DocstringResult | None:
    """Return one reflow finding and any safe whole-literal replacement."""
    if docstring.kind != PDF_definition.DocstringKind.SIMPLE or not isinstance(docstring.node, cst.SimpleString):
        return None
    if not docstring.structure.reflow_regions or not _has_safe_source_mapping(docstring):
        return None
    fragments = string_literals.value_fragments_for_simple_string(docstring.node, line_ending=context.line_ending)

    fallback_prefix = _fallback_line_prefix(context.module.code, docstring=docstring)
    replacements: list[_RegionReplacement] = []
    for region in docstring.structure.reflow_regions:
        replacement = _replacement_for_region(docstring, region, context=context, fallback_prefix=fallback_prefix, fragments=fragments)
        if replacement is None:
            continue
        current = docstring.value[replacement.start_offset : replacement.end_offset]
        if replacement.value_text != current:
            replacements.append(replacement)
    if not replacements:
        return None

    value = docstring.value
    for replacement in reversed(replacements):
        value = f"{value[: replacement.start_offset]}{replacement.value_text}{value[replacement.end_offset:]}"
    line_numbers = tuple(sorted({line_number for replacement in replacements for line_number in replacement.line_numbers}))
    change = _planned_change_from_replacements(docstring, replacements, fragments=fragments, value=value) if fragments is not None else None
    return _DocstringResult(
        finding=RuleFinding(rule=PDF001ReflowRequired.meta, line_numbers=line_numbers, instance_fixable=change is not None),
        change=change,
    )


def _replacement_for_region(
    docstring: PDF_definition.DocstringInfo,
    region: PDF_definition.ReflowRegion,
    *,
    context: RuleContext,
    fallback_prefix: str,
    fragments: tuple[string_literals.StringValueFragment, ...] | None,
) -> _RegionReplacement | None:
    """Return generated evaluated-value text for one reflow region."""
    source_line_numbers = _source_line_numbers_for_region(docstring, region)
    if source_line_numbers is None:
        return None
    initial_base = _line_base_prefix(docstring, region.start_line, first_generated_line=True, fallback_prefix=fallback_prefix)
    subsequent_base = _line_base_prefix(docstring, region.start_line, first_generated_line=False, fallback_prefix=fallback_prefix)
    width = min(
        context.settings.line_length - text_layout.display_width(initial_base, tab_width=context.settings.indent_width),
        context.settings.line_length - text_layout.display_width(subsequent_base, tab_width=context.settings.indent_width),
    )
    if _should_split_google_entry_prefix(region, width=width, tab_width=context.settings.indent_width):
        wrapped = _wrapped_region_lines(
            docstring,
            region,
            width=width,
            initial_indent=region.subsequent_indent,
            subsequent_indent=region.subsequent_indent,
            tab_width=context.settings.indent_width,
            fragments=fragments,
        )
        if not wrapped:
            return None
        return _render_region_replacement(
            docstring,
            region,
            wrapped=(string_literals.WrappedSourceLine(value=region.initial_indent.rstrip(), source=region.initial_indent.rstrip()), *wrapped),
            source_line_numbers=source_line_numbers,
            fallback_prefix=fallback_prefix,
            line_ending=context.line_ending,
        )
    wrapped = _wrapped_region_lines(
        docstring,
        region,
        width=width,
        initial_indent=region.initial_indent,
        subsequent_indent=region.subsequent_indent,
        tab_width=context.settings.indent_width,
        fragments=fragments,
    )
    if not wrapped:
        return None
    return _render_region_replacement(
        docstring,
        region,
        wrapped=wrapped,
        source_line_numbers=source_line_numbers,
        fallback_prefix=fallback_prefix,
        line_ending=context.line_ending,
    )


def _should_split_google_entry_prefix(region: PDF_definition.ReflowRegion, *, width: int, tab_width: int) -> bool:
    """Return whether a Google entry prefix should stand alone before wrapped description text."""
    if region.kind is not PDF_definition.DocstringBlockKind.SECTION_ENTRY:
        return False
    if text_layout.display_width(region.initial_indent, tab_width=tab_width) <= text_layout.display_width(region.subsequent_indent, tab_width=tab_width):
        return False
    # Move very long Google entry prefixes onto their own line when the first description line would have too little
    # useful room.
    return width - text_layout.display_width(region.initial_indent, tab_width=tab_width) < max(8, tab_width * 2)


def _source_line_numbers_for_region(docstring: PDF_definition.DocstringInfo, region: PDF_definition.ReflowRegion) -> tuple[int, ...] | None:
    """Return safe concrete source line numbers for a reflow region."""
    line_numbers: list[int] = []
    for index in range(region.start_line, region.end_line):
        line_number = docstring.structure.lines[index].source_line_number
        if line_number is None:
            return None
        line_numbers.append(line_number)
    return tuple(line_numbers)


def _wrapped_region_lines(
    docstring: PDF_definition.DocstringInfo,
    region: PDF_definition.ReflowRegion,
    *,
    width: int,
    initial_indent: str,
    subsequent_indent: str,
    tab_width: int,
    fragments: tuple[string_literals.StringValueFragment, ...] | None,
) -> tuple[string_literals.WrappedSourceLine, ...]:
    """Return normalized wrapped region lines."""
    if fragments is None:
        return string_literals.wrap_source_words(
            tuple(
                word
                for line in region.lines
                for word in string_literals.source_words_for_value_slice(
                    tuple(string_literals.StringValueFragment(value=char, source=char) for char in line.text),
                    0,
                    len(line.text),
                )
            ),
            width=max(1, width),
            initial_indent=initial_indent,
            subsequent_indent=subsequent_indent,
            tab_width=tab_width,
        )
    return string_literals.wrap_source_words(
        _source_words_for_region(region, fragments=fragments),
        width=max(1, width),
        initial_indent=initial_indent,
        subsequent_indent=subsequent_indent,
        tab_width=tab_width,
    )


def _source_words_for_region(region: PDF_definition.ReflowRegion, *, fragments: tuple[string_literals.StringValueFragment, ...]) -> tuple[string_literals.SourceWord, ...]:
    """Return source-aware words for a reflow region."""
    words: list[string_literals.SourceWord] = []
    for region_line in region.lines:
        words.extend(string_literals.source_words_for_value_slice(fragments, region_line.start_offset, region_line.end_offset))
    return tuple(words)


def _render_region_replacement(
    docstring: PDF_definition.DocstringInfo,
    region: PDF_definition.ReflowRegion,
    *,
    wrapped: tuple[string_literals.WrappedSourceLine, ...],
    source_line_numbers: tuple[int, ...],
    fallback_prefix: str,
    line_ending: str,
) -> _RegionReplacement | None:
    """Return replacement text for normalized wrapped region lines."""
    value_lines = [_raw_generated_line(docstring, region.start_line, line.value, first_generated_line=index == 0, fallback_prefix=fallback_prefix) for index, line in enumerate(wrapped)]
    source_lines = [_raw_generated_line(docstring, region.start_line, line.source, first_generated_line=index == 0, fallback_prefix=fallback_prefix) for index, line in enumerate(wrapped)]
    return _RegionReplacement(
        start_offset=region.start_offset,
        end_offset=region.end_offset,
        value_text="\n".join(value_lines),
        source_text=line_ending.join(source_lines),
        line_numbers=source_line_numbers,
    )


def _planned_change_from_replacements(
    docstring: PDF_definition.DocstringInfo,
    replacements: list[_RegionReplacement],
    *,
    fragments: tuple[string_literals.StringValueFragment, ...],
    value: str,
) -> rule_edits.PlannedSourceChange | None:
    """Return a source edit after applying source-preserving replacements."""
    if not isinstance(docstring.node, cst.SimpleString):
        return None
    source_chunks: list[str] = []
    cursor = 0
    for replacement in sorted(replacements, key=lambda item: item.start_offset):
        source_chunks.append(string_literals.source_for_value_slice(fragments, cursor, replacement.start_offset))
        source_chunks.append(replacement.source_text)
        cursor = replacement.end_offset
    source_chunks.append(string_literals.source_for_value_slice(fragments, cursor, len(fragments)))
    rendered = string_literals.render_simple_string_from_body_source(docstring.node.prefix, docstring.node.quote, "".join(source_chunks), expected_value=value)
    if rendered is None or rendered == docstring.source:
        return None
    return rule_edits.PlannedSourceChange(
        edit=rule_edits.SourceEdit(range=docstring.range, replacement=rendered),
        line_numbers=tuple(sorted({line_number for replacement in replacements for line_number in replacement.line_numbers})),
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
