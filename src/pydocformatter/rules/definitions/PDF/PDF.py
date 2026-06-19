from __future__ import annotations

import dataclasses
import enum
import re
import typing
from collections.abc import Iterator

import libcst as cst
import libcst.metadata as cst_metadata

import pydocformatter.cli.settings_check as settings_check
import pydocformatter.rules.definition_helpers.docstring_sections as docstring_sections
import pydocformatter.rules.definition_helpers.source_text as source_text
import pydocformatter.rules.definition_helpers.string_literals as string_literals
import pydocformatter.rules.definition_helpers.text_layout as text_layout
import pydocformatter.rules.edits as rule_edits
import pydocformatter.rules.registration as rule_registration
from pydocformatter.rules.definition import RuleCategoryBase, RuleCategoryContext, RuleContext
from pydocformatter.rules.models import RuleCategoryMetadata


class DefinitionKind(enum.Enum):
    """Kinds of Python definitions that may own docstrings."""

    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"


class DocstringKind(enum.Enum):
    """LibCST string-expression shapes accepted as Python docstrings."""

    SIMPLE = "simple"
    CONCATENATED = "concatenated"


class DocstringBlockKind(enum.Enum):
    """Semantic block kinds recognized inside docstrings."""

    BLANK = "blank"
    SUMMARY = "summary"
    PARAGRAPH = "paragraph"
    SECTION = "section"
    SECTION_HEADER = "section-header"
    SECTION_ENTRY = "section-entry"
    LIST_ITEM = "list-item"
    HEADING = "heading"
    DOCTEST = "doctest"
    CODE_FENCE = "code-fence"
    BLOCK_QUOTE = "block-quote"
    TABLE = "table"
    DIRECTIVE = "directive"
    LITERAL_BLOCK = "literal-block"
    REST_FIELD = "rest-field"
    VERBATIM = "verbatim"


class DocstringEntryKind(enum.Enum):
    """Semantic entry kinds exposed to convention-aware rules."""

    PARAMETER = "parameter"
    RETURN = "return"
    YIELD = "yield"
    EXCEPTION = "exception"
    ATTRIBUTE = "attribute"
    METHOD = "method"
    FIELD = "field"


@dataclasses.dataclass(frozen=True)
class DocstringValueLine:
    """One logical line in an evaluated docstring value."""

    index: int
    start_offset: int
    end_offset: int
    raw_text: str
    text: str
    raw_indent: str
    text_indent: str
    text_raw_start_column: int
    text_virtual_prefix_length: int
    source_line_number: int | None


@dataclasses.dataclass(frozen=True)
class DocstringEntry:
    """One parsed convention section entry or rest field."""

    kind: DocstringEntryKind
    names: tuple[str, ...]
    type_text: str | None
    description: str
    start_line: int
    end_line: int
    field_name: str | None = None
    field_argument: str | None = None


@dataclasses.dataclass(frozen=True)
class ReflowRegionLine:
    """One reflowable text line with its evaluated-value span."""

    text: str
    start_offset: int
    end_offset: int


@dataclasses.dataclass(frozen=True)
class ReflowRegionRun:
    """One contiguous source run of reflowable lines."""

    start_line: int
    end_line: int
    lines: tuple[ReflowRegionLine, ...]


@dataclasses.dataclass(frozen=True)
class ReflowRegion:
    """A contiguous semantic region whose lines may be merged before wrapping."""

    kind: DocstringBlockKind
    start_line: int
    end_line: int
    start_offset: int
    end_offset: int
    lines: tuple[ReflowRegionLine, ...]
    initial_indent: str
    subsequent_indent: str


@dataclasses.dataclass(frozen=True)
class DocstringBlock:
    """One nested semantic block in a docstring."""

    kind: DocstringBlockKind
    start_line: int
    end_line: int
    children: tuple[DocstringBlock, ...] = ()
    entry: DocstringEntry | None = None


@dataclasses.dataclass(frozen=True)
class DocstringSection:
    """One convention-specific docstring section."""

    name: str
    start_line: int
    end_line: int
    header_line: int
    content_start_line: int
    entries: tuple[DocstringEntry, ...]


@dataclasses.dataclass(frozen=True)
class FinalConventionSectionSpacing:
    """Spacing facts for the final recognized convention section."""

    section: DocstringBlock
    final_content_line: int | None
    trailing_blank_line: int | None


@dataclasses.dataclass(frozen=True)
class DocstringOutputLine:
    """One output logical docstring line for whole-literal rendering."""

    original: DocstringValueLine | None = None
    source: str | None = None
    value: str | None = None
    strip_docstring_margin: bool = False


class DocstringOutputSeparatorFallback(enum.Enum):
    """Separator fallback direction for whole-literal rendering."""

    OPENING = "opening"
    CLOSING = "closing"
    BOTH = "both"


@dataclasses.dataclass(frozen=True)
class DocstringStructure:
    """Convention-aware semantic structure prepared for one docstring."""

    convention: settings_check.DocstringConvention
    lines: tuple[DocstringValueLine, ...]
    blocks: tuple[DocstringBlock, ...]
    sections: tuple[DocstringSection, ...]
    entries: tuple[DocstringEntry, ...]
    reflow_regions: tuple[ReflowRegion, ...]


@dataclasses.dataclass(frozen=True)
class DefinitionInfo:
    """Convention-neutral information about one documentable definition."""

    node: cst.Module | cst.ClassDef | cst.FunctionDef
    kind: DefinitionKind
    name: str
    qualified_name: str
    parent: DefinitionInfo | None
    body: cst.Module | cst.BaseSuite
    asynchronous: bool
    decorators: tuple[cst.Decorator, ...]
    parameters: cst.Parameters | None
    returns: cst.Annotation | None


@dataclasses.dataclass(frozen=True)
class DocstringLine:
    """One physical source line occupied by a docstring expression."""

    line_number: int
    start_column: int
    end_column: int
    source: str


@dataclasses.dataclass(frozen=True)
class DocstringInfo:
    """Lossless source and owner information for one existing docstring."""

    node: cst.SimpleString | cst.ConcatenatedString
    expression: cst.Expr
    statement: cst.SimpleStatementLine | cst.SimpleStatementSuite
    owner: DefinitionInfo
    kind: DocstringKind
    range: cst_metadata.CodeRange
    source: str
    value: str
    physical_lines: tuple[DocstringLine, ...]
    value_lines: tuple[str, ...]
    structure: DocstringStructure


@dataclasses.dataclass(frozen=True)
class SummaryLineTarget:
    """One parsed summary line targeted by first-line style rules."""

    docstring: DocstringInfo
    block: DocstringBlock
    line: DocstringValueLine


@dataclasses.dataclass(frozen=True)
class PDFCategoryData:
    """Prepared definitions and docstrings shared by PDF rules."""

    definitions: tuple[DefinitionInfo, ...]
    docstrings: tuple[DocstringInfo, ...]
    summary_line_targets: tuple[SummaryLineTarget, ...]
    summary_terminal_line_targets: tuple[SummaryLineTarget, ...]

    def docstring_for(self, definition: DefinitionInfo) -> DocstringInfo | None:
        """Return the docstring owned by a definition, if one exists."""
        return next((docstring for docstring in self.docstrings if docstring.owner is definition), None)


class _DefinitionCollector(cst.CSTVisitor):
    """Collect documentable definitions and their existing docstrings."""

    def __init__(self, context: RuleCategoryContext) -> None:
        super().__init__()
        self.context = context
        self.source_lines = source_text.source_lines(context.module.code)
        self.definitions: list[DefinitionInfo] = []
        self.docstrings: list[DocstringInfo] = []
        self.stack: list[DefinitionInfo] = []

        module_definition = DefinitionInfo(
            node=context.module,
            kind=DefinitionKind.MODULE,
            name="<module>",
            qualified_name="<module>",
            parent=None,
            body=context.module,
            asynchronous=False,
            decorators=(),
            parameters=None,
            returns=None,
        )
        self.definitions.append(module_definition)
        self.stack.append(module_definition)
        self._collect_docstring(module_definition)

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        """Collect a class and make it the current definition owner."""
        definition = DefinitionInfo(
            node=node,
            kind=DefinitionKind.CLASS,
            name=node.name.value,
            qualified_name=_qualified_name(self.stack[-1], node.name.value),
            parent=self.stack[-1],
            body=node.body,
            asynchronous=False,
            decorators=tuple(node.decorators),
            parameters=None,
            returns=None,
        )
        self.definitions.append(definition)
        self.stack.append(definition)
        self._collect_docstring(definition)

    def leave_ClassDef(self, original_node: cst.ClassDef) -> None:
        """Restore the enclosing definition after visiting a class."""
        del original_node
        self.stack.pop()

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        """Collect a function and make it the current definition owner."""
        definition = DefinitionInfo(
            node=node,
            kind=DefinitionKind.FUNCTION,
            name=node.name.value,
            qualified_name=_qualified_name(self.stack[-1], node.name.value),
            parent=self.stack[-1],
            body=node.body,
            asynchronous=node.asynchronous is not None,
            decorators=tuple(node.decorators),
            parameters=node.params,
            returns=node.returns,
        )
        self.definitions.append(definition)
        self.stack.append(definition)
        self._collect_docstring(definition)

    def leave_FunctionDef(self, original_node: cst.FunctionDef) -> None:
        """Restore the enclosing definition after visiting a function."""
        del original_node
        self.stack.pop()

    def _collect_docstring(self, owner: DefinitionInfo) -> None:
        """Collect an owner's first string expression when it is a docstring."""
        first_expression = _first_expression(owner.body)
        if first_expression is None:
            return
        expression, statement = first_expression
        node = expression.value
        if not isinstance(node, (cst.SimpleString, cst.ConcatenatedString)) or not isinstance(node.evaluated_value, str):
            return
        code_range = self.context.positions[node]
        source = source_text.source_for_range(code_range, source_lines=self.source_lines)
        physical_lines = _physical_lines(code_range, source)
        source_line_number = _simple_docstring_source_line_number(node, source=source, physical_lines=physical_lines, code_range=code_range) if isinstance(node, cst.SimpleString) else None
        self.docstrings.append(
            DocstringInfo(
                node=node,
                expression=expression,
                statement=statement,
                owner=owner,
                kind=DocstringKind.SIMPLE if isinstance(node, cst.SimpleString) else DocstringKind.CONCATENATED,
                range=code_range,
                source=source,
                value=node.evaluated_value,
                physical_lines=physical_lines,
                value_lines=tuple(node.evaluated_value.splitlines()),
                structure=_parse_docstring(
                    node.evaluated_value,
                    settings=self.context.settings,
                    source_line_number=source_line_number,
                    source_indent=(
                        _docstring_source_indent(
                            statement,
                            code_range=code_range,
                            source_lines=self.source_lines,
                            indent_width=self.context.settings.indent_width,
                        )
                        if isinstance(node, cst.SimpleString)
                        else None
                    ),
                ),
            )
        )


@rule_registration.register_rule_category
class PDF(RuleCategoryBase):
    """Docstring formatting rule category."""

    meta = RuleCategoryMetadata(
        prefix="PDF",
        name="pydocformatter docstring formatting",
        url="https://github.com/pallgeuer/pydocformatter",
    )

    @classmethod
    def prepare(cls, context: RuleCategoryContext) -> PDFCategoryData:
        """Collect documentable definitions and existing docstrings."""
        del cls
        collector = _DefinitionCollector(context)
        context.module.visit(collector)
        docstrings = tuple(collector.docstrings)
        return PDFCategoryData(
            definitions=tuple(collector.definitions),
            docstrings=docstrings,
            summary_line_targets=summary_first_line_targets(docstrings),
            summary_terminal_line_targets=summary_terminal_line_targets(docstrings),
        )

    @classmethod
    def require_data(cls, context: RuleContext) -> PDFCategoryData:
        """Return prepared PDF data or raise for an invalid rule context."""
        if not isinstance(context.category_data, PDFCategoryData):
            raise TypeError(f"{cls.meta.prefix} rules require PDFCategoryData")
        return context.category_data


def is_adornment(text: str) -> bool:
    """Return whether text is a heading or section adornment line."""
    return _is_adornment(text)


def final_convention_section(docstring: DocstringInfo) -> DocstringBlock | None:
    """Return the final top-level convention section, if there is one."""
    if not docstring_sections.convention_parses_sections(docstring.structure.convention):
        return None
    non_blank_blocks = tuple(block for block in docstring.structure.blocks if block.kind is not DocstringBlockKind.BLANK)
    if not non_blank_blocks or non_blank_blocks[-1].kind is not DocstringBlockKind.SECTION:
        return None
    return non_blank_blocks[-1]


def final_convention_section_spacing(docstring: DocstringInfo) -> FinalConventionSectionSpacing | None:
    """Return final convention section content and trailing blank facts."""
    section = final_convention_section(docstring)
    if section is None:
        return None
    return FinalConventionSectionSpacing(
        section=section,
        final_content_line=_final_section_content_line(docstring, section),
        trailing_blank_line=_final_section_trailing_blank_line(docstring, section),
    )


def docstring_line_source(
    line: DocstringValueLine,
    *,
    fragments: tuple[string_literals.StringValueFragment, ...],
    strip_docstring_margin: bool,
) -> str:
    """Return source spelling for a logical docstring line."""
    if not strip_docstring_margin:
        return string_literals.source_for_value_slice(fragments, line.start_offset, line.end_offset)
    start_offset = line.start_offset + line.text_raw_start_column
    return f"{' ' * line.text_virtual_prefix_length}{string_literals.source_for_value_slice(fragments, start_offset, line.end_offset)}"


def _final_section_content_line(docstring: DocstringInfo, section: DocstringBlock) -> int | None:
    """Return the final non-header, non-blank line in a convention section."""
    header = next((child for child in section.children if child.kind is DocstringBlockKind.SECTION_HEADER), None)
    header_lines = range(header.start_line, header.end_line) if header is not None else range(0)
    for index in range(section.end_line - 1, section.start_line - 1, -1):
        if index in header_lines:
            continue
        if docstring.structure.lines[index].text.strip():
            return index
    return None


def _final_section_trailing_blank_line(docstring: DocstringInfo, section: DocstringBlock) -> int | None:
    """Return the retained trailing blank line after final section content."""
    trailing_child_blank = section.children[-1] if section.children and section.children[-1].kind is DocstringBlockKind.BLANK else None
    if trailing_child_blank is not None:
        return _first_non_closing_quote_prefix_line(docstring, start=trailing_child_blank.start_line, end=trailing_child_blank.end_line)
    blank_block = next((block for block in docstring.structure.blocks if block.start_line == section.end_line and block.kind is DocstringBlockKind.BLANK), None)
    if blank_block is None:
        return None
    return _first_non_closing_quote_prefix_line(docstring, start=blank_block.start_line, end=blank_block.end_line)


def _first_non_closing_quote_prefix_line(docstring: DocstringInfo, *, start: int, end: int) -> int | None:
    """Return the first blank line that is not only a same-line closing quote prefix."""
    for index in range(start, end):
        if not is_same_line_closing_delimiter_prefix(docstring, docstring.structure.lines[index]):
            return index
    return None


_LIST_RE = re.compile(r"^(?P<indent>[ \t]*)(?P<marker>(?:[-+*]|\d+[.)]))[ \t]+(?P<text>.*)$")
_BLOCK_QUOTE_RE = re.compile(r"^(?P<indent>[ \t]*)(?P<quote>(?:>[ \t]*)+)(?P<text>.*)$")
_FENCE_RE = re.compile(r"^[ \t]*(?P<fence>`{3,}|~{3,})(?P<info>.*)$")
_DIRECTIVE_RE = re.compile(r"^(?P<indent>[ \t]*)\.\.[ \t]+(?P<name>[\w-]+)::(?P<argument>.*)$")
_REST_FIELD_RE = re.compile(r"^(?P<indent>[ \t]*):(?P<field>[\w-]+)(?:[ \t]+(?P<argument>[^:]*?\S))?[ \t]*:[ \t]*(?P<description>.*)$")
_GOOGLE_ENTRY_RE = re.compile(r"^(?P<indent>[ \t]+)(?P<name>\*{0,2}[A-Za-z_][\w.]*)(?:[ \t]*\((?P<type>[^)]+)\))?[ \t]*:[ \t]*(?P<description>.*)$")
_GENERIC_ENTRY_RE = re.compile(r"^(?P<indent>[ \t]+)(?P<name>[^:]+):[ \t]*(?P<description>.*)$")
_NUMPY_ENTRY_RE = re.compile(r"^(?P<indent>[ \t]*)(?P<name>\*{0,2}[A-Za-z_][\w., ]*?)[ \t]*:[ \t]*(?P<type>.+)$")
_ATX_HEADING_RE = re.compile(r"^[ \t]{0,3}#{1,6}[ \t]+\S")
_MARKDOWN_TABLE_DELIMITER_RE = re.compile(r"^[ \t]*\|?[ \t]*:?-{3,}:?[ \t]*(?:\|[ \t]*:?-{3,}:?[ \t]*)+\|?[ \t]*$")
_REST_GRID_BORDER_RE = re.compile(r"^[ \t]*\+(?:[-=]+\+)+[ \t]*$")
_REST_SIMPLE_BORDER_RE = re.compile(r"^[ \t]*={3,}(?:[ \t]+={3,})+[ \t]*$")


class _DocstringParser:
    """Parse one evaluated docstring value into conservative semantic blocks."""

    def __init__(self, value: str, *, settings: settings_check.CheckSettings, source_line_number: int | None, source_indent: int | None) -> None:
        self.value = value
        self.settings = settings
        self.lines = _value_lines(value, source_line_number=source_line_number, source_indent=source_indent)
        self.blocks: list[DocstringBlock] = []
        self.sections: list[DocstringSection] = []
        self.entries: list[DocstringEntry] = []
        self.reflow_regions: list[ReflowRegion] = []
        self.summary_pending = True

    def parse(self) -> DocstringStructure:
        """Return the complete semantic structure."""
        self.blocks.extend(self._parse_range(0, len(self.lines)))
        return DocstringStructure(
            convention=self.settings.docstring_convention,
            lines=self.lines,
            blocks=tuple(self.blocks),
            sections=tuple(sorted(self.sections, key=lambda section: (section.start_line, section.end_line))),
            entries=tuple(sorted(self.entries, key=lambda entry: (entry.start_line, entry.end_line))),
            reflow_regions=tuple(sorted(self.reflow_regions, key=lambda region: (region.start_line, region.end_line))),
        )

    def _parse_range(self, start: int, end: int) -> list[DocstringBlock]:
        blocks: list[DocstringBlock] = []
        index = start
        while index < end:
            text = self.lines[index].text
            if not text.strip():
                block_end = index + 1
                while block_end < end and not self.lines[block_end].text.strip():
                    block_end += 1
                blocks.append(DocstringBlock(DocstringBlockKind.BLANK, index, block_end))
                index = block_end
                continue
            section = self._section_at(index, end)
            if section is not None:
                section_block, index = self._parse_section(index, end, section)
                blocks.append(section_block)
                self.summary_pending = False
                continue
            if self.settings.docstring_parse_code_fences and (fence := _FENCE_RE.match(text)) is not None:
                block_end = self._fence_end(index, end, fence.group("fence"))
                blocks.append(DocstringBlock(DocstringBlockKind.CODE_FENCE, index, block_end))
                index = block_end
                self.summary_pending = False
                continue
            if self.settings.docstring_parse_doctests and _is_doctest_prompt(text):
                block_end = index + 1
                while block_end < end and self.lines[block_end].text.strip():
                    block_end += 1
                blocks.append(DocstringBlock(DocstringBlockKind.DOCTEST, index, block_end))
                index = block_end
                self.summary_pending = False
                continue
            if self.settings.docstring_parse_directives and (directive := _DIRECTIVE_RE.match(text)) is not None:
                block_end = self._indented_body_end(index, end, text_layout.leading_width(directive.group("indent")))
                blocks.append(DocstringBlock(DocstringBlockKind.DIRECTIVE, index, block_end))
                index = block_end
                self.summary_pending = False
                continue
            if self.settings.docstring_parse_literal_blocks and text.rstrip().endswith("::") and self._has_indented_body(index, end):
                block_end = self._indented_body_end(index, end, text_layout.leading_width(text))
                blocks.append(DocstringBlock(DocstringBlockKind.LITERAL_BLOCK, index, block_end))
                index = block_end
                self.summary_pending = False
                continue
            if self.settings.docstring_parse_tables and (table_end := self._table_end(index, end)) is not None:
                blocks.append(DocstringBlock(DocstringBlockKind.TABLE, index, table_end))
                index = table_end
                self.summary_pending = False
                continue
            if self.settings.docstring_parse_headings and (self._is_heading(index, end)):
                block_end = index + 2 if index + 1 < end and _is_adornment(self.lines[index + 1].text) else index + 1
                blocks.append(DocstringBlock(DocstringBlockKind.HEADING, index, block_end))
                index = block_end
                self.summary_pending = False
                continue
            if self._parses_rest_fields() and (field_match := _REST_FIELD_RE.match(text)) is not None:
                block, index = self._parse_rest_field(index, end, field_match)
                blocks.append(block)
                self.summary_pending = False
                continue
            if self.settings.docstring_parse_list_items and (list_match := _LIST_RE.match(text)) is not None:
                block, index = self._parse_list_item(index, end, list_match)
                blocks.append(block)
                self.summary_pending = False
                continue
            if self.settings.docstring_parse_block_quotes and (quote_match := _BLOCK_QUOTE_RE.match(text)) is not None:
                block, index = self._parse_block_quote(index, end, quote_match)
                blocks.append(block)
                self.summary_pending = False
                continue
            if text[:1].isspace():
                block_end = index + 1
                while block_end < end and (not self.lines[block_end].text.strip() or self.lines[block_end].text[:1].isspace()):
                    block_end += 1
                block_end = self._trim_trailing_blank_lines(index, block_end)
                blocks.append(DocstringBlock(DocstringBlockKind.VERBATIM, index, block_end))
                index = block_end
                self.summary_pending = False
                continue
            block_end = index + 1
            while block_end < end and self.lines[block_end].text.strip() and not self._starts_special(block_end, end) and not self.lines[block_end].text[:1].isspace():
                block_end += 1
            kind = DocstringBlockKind.SUMMARY if self.summary_pending else DocstringBlockKind.PARAGRAPH
            blocks.append(DocstringBlock(kind, index, block_end))
            self._add_reflow(kind, index, block_end, lines=self._stripped_reflow_lines(index, block_end), initial_indent="", subsequent_indent="")
            self.summary_pending = False
            index = block_end
        return blocks

    def _starts_special(self, index: int, end: int) -> bool:
        text = self.lines[index].text
        return (
            self._section_at(index, end) is not None
            or (self.settings.docstring_parse_code_fences and _FENCE_RE.match(text) is not None)
            or (self.settings.docstring_parse_doctests and _is_doctest_prompt(text))
            or (self.settings.docstring_parse_directives and _DIRECTIVE_RE.match(text) is not None)
            or (self.settings.docstring_parse_literal_blocks and text.rstrip().endswith("::") and self._has_indented_body(index, end))
            or (self.settings.docstring_parse_tables and self._table_end(index, end) is not None)
            or (self.settings.docstring_parse_headings and self._is_heading(index, end))
            or (self._parses_rest_fields() and _REST_FIELD_RE.match(text) is not None)
            or (self.settings.docstring_parse_list_items and _LIST_RE.match(text) is not None)
            or (self.settings.docstring_parse_block_quotes and _BLOCK_QUOTE_RE.match(text) is not None)
        )

    def _section_at(self, index: int, end: int, *, max_indent: int | None = None) -> str | None:
        convention = self.settings.docstring_convention
        if not docstring_sections.convention_parses_sections(convention):
            return None
        text = self.lines[index].text
        if max_indent is not None and text_layout.leading_width(text) > max_indent:
            return None
        stripped = text.strip()
        candidate = stripped[:-1].rstrip() if stripped.endswith(":") else stripped
        names = docstring_sections.GOOGLE_SECTIONS if convention == settings_check.DocstringConvention.GOOGLE else docstring_sections.NUMPY_SECTIONS
        if candidate.lower() not in names:
            return None
        if convention == settings_check.DocstringConvention.NUMPY and index + 1 < end and _is_adornment(self.lines[index + 1].text):
            return candidate
        if convention == settings_check.DocstringConvention.GOOGLE:
            return candidate
        return candidate if not stripped.endswith(":") else None

    def _parses_rest_fields(self) -> bool:
        return self.settings.docstring_convention == settings_check.DocstringConvention.REST

    def _parse_section(self, start: int, end: int, name: str) -> tuple[DocstringBlock, int]:
        content_start = start + 1
        if content_start < end and _is_adornment(self.lines[content_start].text):
            content_start += 1
        section_end = self._section_end(content_start, end, text_layout.leading_width(self.lines[start].text))
        entries = self._section_entries(name, content_start, section_end)
        children: list[DocstringBlock] = [DocstringBlock(DocstringBlockKind.SECTION_HEADER, start, content_start)]
        if entries:
            entry_by_start = {entry.start_line: entry for entry in entries}
            index = content_start
            previous_summary = self.summary_pending
            self.summary_pending = False
            while index < section_end:
                entry = entry_by_start.get(index)
                if entry is not None:
                    children.append(DocstringBlock(DocstringBlockKind.SECTION_ENTRY, entry.start_line, entry.end_line, entry=entry))
                    index = entry.end_line
                    continue
                next_entry = min((entry_start for entry_start in entry_by_start if entry_start > index), default=section_end)
                children.extend(self._parse_range(index, next_entry))
                index = next_entry
            self.summary_pending = previous_summary
        else:
            previous_summary = self.summary_pending
            self.summary_pending = False
            children.extend(self._parse_range(content_start, section_end))
            self.summary_pending = previous_summary
        section = DocstringSection(name=name, start_line=start, end_line=section_end, header_line=start, content_start_line=content_start, entries=entries)
        self.sections.append(section)
        self.entries.extend(entries)
        return DocstringBlock(DocstringBlockKind.SECTION, start, section_end, children=tuple(children)), section_end

    def _section_entries(self, name: str, start: int, end: int) -> tuple[DocstringEntry, ...]:
        if self.settings.docstring_convention == settings_check.DocstringConvention.GOOGLE:
            return self._google_entries(name, start, end)
        if self.settings.docstring_convention == settings_check.DocstringConvention.NUMPY:
            return self._numpy_entries(name, start, end)
        return ()

    def _google_entries(self, section_name: str, start: int, end: int) -> tuple[DocstringEntry, ...]:
        entries: list[DocstringEntry] = []
        index = start
        kind = _entry_kind(self.settings.docstring_convention, section_name)
        while index < end:
            protected_end = self._protected_block_end(index, end)
            if protected_end is not None:
                index = protected_end
                continue
            match = _GOOGLE_ENTRY_RE.match(self.lines[index].text)
            if match is None and kind in (DocstringEntryKind.RETURN, DocstringEntryKind.YIELD, DocstringEntryKind.EXCEPTION):
                match = _GENERIC_ENTRY_RE.match(self.lines[index].text)
            if match is None:
                none_entry = _google_none_value_entry(kind, self.lines[index].text, start=index)
                if none_entry is not None:
                    entries.append(none_entry)
                    index = none_entry.end_line
                    continue
                index += 1
                continue
            entry_end = self._entry_end(index, end, text_layout.leading_width(match.group("indent")))
            name = match.group("name").strip()
            type_text = match.groupdict().get("type")
            first_description = match.group("description").strip()
            description_reflow_lines = []
            first_description_line = self._reflow_line_from_text_span(index, match.start("description"), len(self.lines[index].text))
            if first_description_line is not None and first_description_line.text:
                description_reflow_lines.append(first_description_line)
            description_reflow_lines.extend(self._stripped_reflow_lines(index + 1, entry_end, skip_empty=True))
            description_lines = [line.text for line in description_reflow_lines]
            names = tuple(part.strip() for part in name.split(","))
            if kind in (DocstringEntryKind.RETURN, DocstringEntryKind.YIELD) and type_text is None:
                names = ()
                type_text = name
            entry = DocstringEntry(
                kind=kind,
                names=names,
                type_text=type_text.strip() if type_text else None,
                description=" ".join(description_lines).strip(),
                start_line=index,
                end_line=entry_end,
            )
            entries.append(entry)
            unit = text_layout.indent_unit(self.settings)
            prefix = f'{unit}{self.lines[index].text[len(match.group("indent")) : match.start("description")]}'
            if description_lines and not first_description and not prefix.endswith((" ", "\t")):
                prefix = f"{prefix} "
            self._add_reflow(DocstringBlockKind.SECTION_ENTRY, index, entry_end, lines=tuple(description_reflow_lines), initial_indent=prefix, subsequent_indent=unit * 2)
            index = entry_end
        return tuple(entries)

    def _numpy_entries(self, section_name: str, start: int, end: int) -> tuple[DocstringEntry, ...]:
        entries: list[DocstringEntry] = []
        index = start
        kind = _entry_kind(self.settings.docstring_convention, section_name)
        while index < end:
            protected_end = self._protected_block_end(index, end)
            if protected_end is not None:
                index = protected_end
                continue
            text = self.lines[index].text
            match = _NUMPY_ENTRY_RE.match(text)
            if match is not None:
                entry_end = self._entry_end(index, end, text_layout.leading_width(match.group("indent")))
                description_reflow_lines = self._stripped_reflow_lines(index + 1, entry_end, skip_empty=True)
                description_lines = [line.text for line in description_reflow_lines]
                entry = DocstringEntry(
                    kind=kind,
                    names=tuple(part.strip() for part in match.group("name").split(",")),
                    type_text=match.group("type").strip(),
                    description=" ".join(description_lines),
                    start_line=index,
                    end_line=entry_end,
                )
                entries.append(entry)
                if description_lines:
                    self._add_reflow(
                        DocstringBlockKind.SECTION_ENTRY,
                        index + 1,
                        entry_end,
                        lines=tuple(description_reflow_lines),
                        initial_indent=text_layout.indent_unit(self.settings),
                        subsequent_indent=text_layout.indent_unit(self.settings),
                    )
                index = entry_end
                continue
            if kind in (DocstringEntryKind.RETURN, DocstringEntryKind.YIELD, DocstringEntryKind.EXCEPTION) and text.strip():
                entry_end = self._entry_end(index, end, text_layout.leading_width(text))
                description_reflow_lines = self._stripped_reflow_lines(index + 1, entry_end, skip_empty=True)
                description_lines = [line.text for line in description_reflow_lines]
                entries.append(
                    DocstringEntry(
                        kind=kind,
                        names=(text.strip(),) if kind == DocstringEntryKind.EXCEPTION else (),
                        type_text=None if kind == DocstringEntryKind.EXCEPTION else text.strip(),
                        description=" ".join(description_lines),
                        start_line=index,
                        end_line=entry_end,
                    )
                )
                if description_lines:
                    self._add_reflow(
                        DocstringBlockKind.SECTION_ENTRY,
                        index + 1,
                        entry_end,
                        lines=tuple(description_reflow_lines),
                        initial_indent=text_layout.indent_unit(self.settings),
                        subsequent_indent=text_layout.indent_unit(self.settings),
                    )
                index = entry_end
                continue
            index += 1
        return tuple(entries)

    def _parse_rest_field(self, start: int, end: int, match: re.Match[str]) -> tuple[DocstringBlock, int]:
        block_end = self._continuation_end(start, end, text_layout.leading_width(match.group("indent")))
        field = match.group("field").lower()
        argument = (match.group("argument") or "").strip()
        first_description_line = self._reflow_line_from_text_span(start, match.start("description"), len(self.lines[start].text))
        has_first_description = first_description_line is not None and bool(first_description_line.text)
        description_reflow_lines: list[ReflowRegionLine] = []
        reflow_runs: list[ReflowRegionRun] = []
        if has_first_description:
            assert first_description_line is not None
            description_reflow_lines.append(first_description_line)
        continuation_runs = self._rest_field_description_reflow_runs(start + 1, block_end)
        description_reflow_lines.extend(line for run in continuation_runs for line in run.lines)
        if has_first_description:
            assert first_description_line is not None
            if continuation_runs and continuation_runs[0].start_line == start + 1:
                first_run = continuation_runs[0]
                reflow_runs.append(ReflowRegionRun(start_line=start, end_line=first_run.end_line, lines=(first_description_line, *first_run.lines)))
                reflow_runs.extend(continuation_runs[1:])
            else:
                reflow_runs.append(ReflowRegionRun(start_line=start, end_line=start + 1, lines=(first_description_line,)))
                reflow_runs.extend(continuation_runs)
        elif continuation_runs and continuation_runs[0].start_line == start + 1:
            first_run = continuation_runs[0]
            reflow_runs.append(ReflowRegionRun(start_line=start, end_line=first_run.end_line, lines=first_run.lines))
            reflow_runs.extend(continuation_runs[1:])
        else:
            reflow_runs.extend(continuation_runs)
        description_lines = [line.text for line in description_reflow_lines]
        kind, names, type_text = _rest_entry_metadata(field, argument)
        entry = DocstringEntry(
            kind=kind,
            names=names,
            type_text=type_text,
            description=" ".join(description_lines).strip(),
            start_line=start,
            end_line=block_end,
            field_name=field,
            field_argument=argument or None,
        )
        self.entries.append(entry)
        prefix = self.lines[start].text[: match.start("description")]
        subsequent_indent = " " * len(prefix.expandtabs(self.settings.indent_width))
        if reflow_runs and reflow_runs[0].start_line == start and not has_first_description and not prefix.endswith((" ", "\t")):
            prefix = f"{prefix} "
            subsequent_indent = " " * len(prefix.expandtabs(self.settings.indent_width))
        for index, run in enumerate(reflow_runs):
            run_indent = prefix if run.start_line == start else self.lines[run.start_line].text_indent
            run_subsequent_indent = subsequent_indent if run.start_line == start else run_indent
            self._add_reflow(
                DocstringBlockKind.REST_FIELD,
                run.start_line,
                run.end_line,
                lines=run.lines,
                initial_indent=run_indent,
                subsequent_indent=run_subsequent_indent,
            )
        return DocstringBlock(DocstringBlockKind.REST_FIELD, start, block_end, entry=entry), block_end

    def _rest_field_description_reflow_runs(self, start: int, end: int) -> tuple[ReflowRegionRun, ...]:
        runs: list[ReflowRegionRun] = []
        run_start: int | None = None
        run_lines: list[ReflowRegionLine] = []
        index = start
        while index < end:
            protected_end = self._protected_block_end(index, end)
            if protected_end is not None:
                if run_start is not None and run_lines:
                    runs.append(ReflowRegionRun(start_line=run_start, end_line=index, lines=tuple(run_lines)))
                    run_start = None
                    run_lines = []
                index = protected_end
                continue
            line = self._reflow_line_from_text_span(index, 0, len(self.lines[index].text))
            if line is not None and line.text:
                if run_start is None:
                    run_start = index
                run_lines.append(line)
            index += 1
        if run_start is not None and run_lines:
            runs.append(ReflowRegionRun(start_line=run_start, end_line=end, lines=tuple(run_lines)))
        return tuple(runs)

    def _parse_list_item(self, start: int, end: int, match: re.Match[str]) -> tuple[DocstringBlock, int]:
        block_end = self._list_item_end(start, end, match)
        prefix = f'{match.group("indent")}{match.group("marker")} '
        first_line = self._reflow_line_from_text_span(start, match.start("text"), len(self.lines[start].text))
        lines = (() if first_line is None else (first_line,)) + self._stripped_reflow_lines(start + 1, block_end)
        self._add_reflow(DocstringBlockKind.LIST_ITEM, start, block_end, lines=tuple(lines), initial_indent=prefix, subsequent_indent=" " * len(prefix.expandtabs(self.settings.indent_width)))
        return DocstringBlock(DocstringBlockKind.LIST_ITEM, start, block_end), block_end

    def _parse_block_quote(self, start: int, end: int, match: re.Match[str]) -> tuple[DocstringBlock, int]:
        prefix = f'{match.group("indent")}{match.group("quote")}'
        block_end = self._block_quote_end(start, end, prefix)
        texts = tuple(line for line in (self._reflow_line_from_text_span(line, len(prefix), len(self.lines[line].text)) for line in range(start, block_end)) if line is not None)
        self._add_reflow(DocstringBlockKind.BLOCK_QUOTE, start, block_end, lines=tuple(texts), initial_indent=prefix, subsequent_indent=prefix)
        return DocstringBlock(DocstringBlockKind.BLOCK_QUOTE, start, block_end), block_end

    def _add_reflow(self, kind: DocstringBlockKind, start: int, end: int, *, lines: tuple[ReflowRegionLine, ...], initial_indent: str, subsequent_indent: str) -> None:
        if not lines or not any(line.text for line in lines):
            return
        self.reflow_regions.append(
            ReflowRegion(
                kind=kind,
                start_line=start,
                end_line=end,
                start_offset=self.lines[start].start_offset,
                end_offset=self.lines[end - 1].end_offset,
                lines=lines,
                initial_indent=initial_indent,
                subsequent_indent=subsequent_indent,
            )
        )

    def _stripped_reflow_lines(self, start: int, end: int, *, skip_empty: bool = False) -> tuple[ReflowRegionLine, ...]:
        lines: list[ReflowRegionLine] = []
        for index in range(start, end):
            line = self._reflow_line_from_text_span(index, 0, len(self.lines[index].text))
            if line is not None and (line.text or not skip_empty):
                lines.append(line)
        return tuple(lines)

    def _reflow_line_from_text_span(self, line_index: int, start_column: int, end_column: int) -> ReflowRegionLine | None:
        line = self.lines[line_index]
        while start_column < end_column and line.text[start_column].isspace():
            start_column += 1
        while end_column > start_column and line.text[end_column - 1].isspace():
            end_column -= 1
        if start_column > end_column:
            return None
        start_offset = value_offset_for_text_column(line, start_column)
        end_offset = value_offset_for_text_column(line, end_column)
        return ReflowRegionLine(text=line.text[start_column:end_column], start_offset=start_offset, end_offset=end_offset)

    def _fence_end(self, start: int, end: int, opening: str) -> int:
        index = start + 1
        while index < end:
            match = _FENCE_RE.match(self.lines[index].text)
            if match is not None and match.group("fence")[0] == opening[0] and len(match.group("fence")) >= len(opening) and not match.group("info").strip():
                return index + 1
            index += 1
        return end

    def _section_end(self, start: int, end: int, section_indent: int) -> int:
        index = start
        while index < end:
            if self._section_at(index, end, max_indent=section_indent) is not None:
                return index
            protected_end = self._protected_block_end(index, end)
            index = protected_end if protected_end is not None else index + 1
        return end

    def _protected_block_end(self, index: int, end: int) -> int | None:
        text = self.lines[index].text
        if self.settings.docstring_parse_code_fences and (fence := _FENCE_RE.match(text)) is not None:
            return self._fence_end(index, end, fence.group("fence"))
        if self.settings.docstring_parse_doctests and _is_doctest_prompt(text):
            block_end = index + 1
            while block_end < end and self.lines[block_end].text.strip():
                block_end += 1
            return block_end
        if self.settings.docstring_parse_directives and (directive := _DIRECTIVE_RE.match(text)) is not None:
            return self._indented_body_end(index, end, text_layout.leading_width(directive.group("indent")))
        if self.settings.docstring_parse_literal_blocks and text.rstrip().endswith("::") and self._has_indented_body(index, end):
            return self._indented_body_end(index, end, text_layout.leading_width(text))
        if self.settings.docstring_parse_tables and (table_end := self._table_end(index, end)) is not None:
            return table_end
        if self.settings.docstring_parse_headings and self._is_heading(index, end):
            return index + 2 if index + 1 < end and _is_adornment(self.lines[index + 1].text) else index + 1
        if self._parses_rest_fields() and (field_match := _REST_FIELD_RE.match(text)) is not None:
            return self._continuation_end(index, end, text_layout.leading_width(field_match.group("indent")))
        if self.settings.docstring_parse_list_items and (list_match := _LIST_RE.match(text)) is not None:
            return self._list_item_end(index, end, list_match)
        if self.settings.docstring_parse_block_quotes and (quote_match := _BLOCK_QUOTE_RE.match(text)) is not None:
            prefix = f'{quote_match.group("indent")}{quote_match.group("quote")}'
            return self._block_quote_end(index, end, prefix)
        return None

    def _list_item_end(self, start: int, end: int, match: re.Match[str]) -> int:
        base_indent = text_layout.leading_width(match.group("indent"))
        block_end = start + 1
        while block_end < end:
            text = self.lines[block_end].text
            if not text.strip() or _LIST_RE.match(text) is not None or text_layout.leading_width(text) <= base_indent:
                break
            block_end += 1
        return block_end

    def _block_quote_end(self, start: int, end: int, prefix: str) -> int:
        block_end = start + 1
        while block_end < end:
            next_match = _BLOCK_QUOTE_RE.match(self.lines[block_end].text)
            if next_match is None or f'{next_match.group("indent")}{next_match.group("quote")}' != prefix:
                break
            block_end += 1
        return block_end

    def _has_indented_body(self, index: int, end: int) -> bool:
        next_index = index + 1
        while next_index < end and not self.lines[next_index].text.strip():
            next_index += 1
        if next_index >= end:
            return False
        base_indent = text_layout.leading_width(self.lines[index].text)
        next_indent = text_layout.leading_width(self.lines[next_index].text)
        return next_indent > base_indent

    def _indented_body_end(self, start: int, end: int, base_indent: int) -> int:
        index = start + 1
        while index < end:
            text = self.lines[index].text
            indent = text_layout.leading_width(text)
            if text.strip() and indent <= base_indent:
                break
            index += 1
        return self._trim_trailing_blank_lines(start, index)

    def _trim_trailing_blank_lines(self, start: int, end: int) -> int:
        index = end
        while index > start + 1 and not self.lines[index - 1].text.strip():
            index -= 1
        return index

    def _entry_end(self, start: int, end: int, base_indent: int) -> int:
        index = start + 1
        while index < end:
            text = self.lines[index].text
            if not text.strip() or text_layout.leading_width(text) <= base_indent or self._protected_block_end(index, end) is not None:
                break
            index += 1
        return index

    def _continuation_end(self, start: int, end: int, base_indent: int) -> int:
        index = start + 1
        while index < end:
            text = self.lines[index].text
            if not text.strip():
                break
            indent = text_layout.leading_width(text)
            if indent <= base_indent:
                break
            index += 1
        return index

    def _table_end(self, index: int, end: int) -> int | None:
        text = self.lines[index].text
        if "|" in text and index + 1 < end and _MARKDOWN_TABLE_DELIMITER_RE.fullmatch(self.lines[index + 1].text) is not None:
            table_end = index + 2
            while table_end < end and "|" in self.lines[table_end].text:
                table_end += 1
            return table_end
        if _REST_GRID_BORDER_RE.fullmatch(text) is not None:
            table_end = index + 1
            while table_end < end and ("|" in self.lines[table_end].text or _REST_GRID_BORDER_RE.fullmatch(self.lines[table_end].text) is not None):
                table_end += 1
            return table_end
        if _REST_SIMPLE_BORDER_RE.fullmatch(text) is not None:
            table_end = index + 1
            while table_end < end and self.lines[table_end].text.strip():
                table_end += 1
            return table_end
        return None

    def _is_heading(self, index: int, end: int) -> bool:
        return _ATX_HEADING_RE.match(self.lines[index].text) is not None or (index + 1 < end and bool(self.lines[index].text.strip()) and _is_adornment(self.lines[index + 1].text))


def _parse_docstring(value: str, *, settings: settings_check.CheckSettings, source_line_number: int | None, source_indent: int | None) -> DocstringStructure:
    """Return semantic structure for an evaluated docstring value."""
    return _DocstringParser(value, settings=settings, source_line_number=source_line_number, source_indent=source_indent).parse()


def _value_lines(value: str, *, source_line_number: int | None, source_indent: int | None) -> tuple[DocstringValueLine, ...]:
    """Split an evaluated value into offset-bearing logical lines."""
    raw_lines: list[tuple[int, int, str]] = []
    start = 0
    while start < len(value):
        newline = re.search(r"\r\n|\r|\n", value[start:])
        end = len(value) if newline is None else start + newline.start()
        raw_lines.append((start, end, value[start:end]))
        if newline is None:
            start = len(value)
        else:
            start += newline.end()
    if not raw_lines:
        raw_lines.append((0, 0, ""))
    margin = source_indent if source_indent is not None else min((text_layout.leading_width(text) for _, _, text in raw_lines[1:] if text.strip()), default=0)
    lines: list[DocstringValueLine] = []
    for index, (line_start, line_end, raw_text) in enumerate(raw_lines):
        if index == 0:
            text_raw_start_column = len(raw_text) - len(raw_text.lstrip(" \t"))
            text_virtual_prefix_length = 0
            text = raw_text[text_raw_start_column:]
        else:
            text, text_raw_start_column, text_virtual_prefix_length = text_layout.strip_indent_with_mapping(raw_text, margin)
        lines.append(
            DocstringValueLine(
                index=index,
                start_offset=line_start,
                end_offset=line_end,
                raw_text=raw_text,
                text=text,
                raw_indent=raw_text[: len(raw_text) - len(raw_text.lstrip(" \t"))],
                text_indent=text[: len(text) - len(text.lstrip(" \t"))],
                text_raw_start_column=text_raw_start_column,
                text_virtual_prefix_length=text_virtual_prefix_length,
                source_line_number=None if source_line_number is None else source_line_number + index,
            )
        )
    return tuple(lines)


def _entry_kind(convention: settings_check.DocstringConvention, section_name: str) -> DocstringEntryKind:
    """Return the semantic entry kind for a convention section."""
    normalized = section_name.lower()
    if normalized in docstring_sections.PARAMETER_SECTION_NAMES:
        return DocstringEntryKind.PARAMETER
    if normalized in {"return", "returns"}:
        return DocstringEntryKind.RETURN
    if normalized in {"yield", "yields"}:
        return DocstringEntryKind.YIELD
    if normalized in {"raises", "warns"} or (convention == settings_check.DocstringConvention.NUMPY and normalized == "warnings"):
        return DocstringEntryKind.EXCEPTION
    if normalized == "attributes":
        return DocstringEntryKind.ATTRIBUTE
    if normalized == "methods":
        return DocstringEntryKind.METHOD
    return DocstringEntryKind.FIELD


def _rest_entry_kind(field: str) -> DocstringEntryKind:
    """Return the semantic entry kind for a rest field name."""
    if field in docstring_sections.REST_PARAMETER_VALUE_FIELDS or field in docstring_sections.REST_PARAMETER_TYPE_FIELDS:
        return DocstringEntryKind.PARAMETER
    if field in docstring_sections.REST_RETURN_VALUE_FIELDS or field in docstring_sections.REST_RETURN_TYPE_FIELDS:
        return DocstringEntryKind.RETURN
    if field in docstring_sections.REST_YIELD_VALUE_FIELDS or field in docstring_sections.REST_YIELD_TYPE_FIELDS:
        return DocstringEntryKind.YIELD
    if field in docstring_sections.REST_EXCEPTION_FIELDS:
        return DocstringEntryKind.EXCEPTION
    return DocstringEntryKind.FIELD


def _rest_entry_metadata(field: str, argument: str) -> tuple[DocstringEntryKind, tuple[str, ...], str | None]:
    kind = _rest_entry_kind(field)
    if not argument:
        return kind, (), None
    if field == "type":
        return kind, (argument,), None
    if kind is not DocstringEntryKind.PARAMETER:
        return kind, (argument,), None
    parts = argument.rsplit(None, 1)
    if len(parts) == 1:
        return kind, (argument,), None
    type_text, name = parts
    return kind, (name,), type_text


def _google_none_value_entry(kind: DocstringEntryKind, text: str, *, start: int) -> DocstringEntry | None:
    """Return a Google return/yield entry for bare None spellings."""
    if kind not in (DocstringEntryKind.RETURN, DocstringEntryKind.YIELD) or not text[:1].isspace() or text.strip() not in {"None", "None."}:
        return None
    return DocstringEntry(kind=kind, names=(), type_text="None", description="", start_line=start, end_line=start + 1)


def _is_adornment(text: str) -> bool:
    """Return whether text is a heading or section adornment line."""
    stripped = text.strip()
    return len(stripped) >= 3 and len(set(stripped)) == 1 and stripped[0] in "-=~`^:#*+"


def _is_doctest_prompt(text: str) -> bool:
    """Return whether text starts with a whitespace-delimited doctest prompt."""
    return text.lstrip().startswith(">>> ")


def is_same_line_closing_delimiter_prefix(docstring: DocstringInfo, line: DocstringValueLine) -> bool:
    """Return whether a value line prefixes same-line closing quotes."""
    return line.index == len(docstring.structure.lines) - 1 and docstring.value != "" and not docstring_value_ends_with_newline(docstring)


def is_safely_mapped_simple_docstring(docstring: DocstringInfo, *, require_multiline: bool = False) -> bool:
    """Return whether a simple docstring can be safely rewritten by evaluated line."""
    return (
        docstring.kind is DocstringKind.SIMPLE
        and isinstance(docstring.node, cst.SimpleString)
        and (not require_multiline or len(docstring.physical_lines) > 1)
        and all(line.source_line_number is not None for line in docstring.structure.lines)
    )


def docstring_value_fragments(docstring: DocstringInfo, *, line_ending: str) -> tuple[string_literals.StringValueFragment, ...] | None:
    """Return source fragments for a safely rewritable simple docstring."""
    if not isinstance(docstring.node, cst.SimpleString):
        return None
    return string_literals.value_fragments_for_simple_string(docstring.node, line_ending=line_ending)


def docstring_canonical_margin(docstring: DocstringInfo, *, context: RuleContext, source_lines: list[str] | None = None) -> str:
    """Return the raw indentation margin for continuation and aligned blank lines."""
    lines = source_lines if source_lines is not None else source_text.source_lines_from_context(context)
    source_line = lines[docstring.range.start.line - 1]
    line_indent = source_line[: len(source_line) - len(source_line.lstrip(" \t"))]
    if isinstance(docstring.statement, cst.SimpleStatementSuite):
        return f"{line_indent}{text_layout.indent_unit(context.settings)}"
    prefix = source_line[: docstring.range.start.column]
    return prefix if prefix.strip() == "" else line_indent


def planned_simple_docstring_line_change(
    docstring: DocstringInfo,
    *,
    context: RuleContext,
    raw_line_targets: tuple[str | None, ...],
) -> rule_edits.PlannedSourceChange | None:
    """Return one whole-literal replacement for changed raw evaluated lines."""
    if len(raw_line_targets) != len(docstring.structure.lines):
        raise ValueError("Raw line targets must match the docstring line count")
    replacements: list[rule_edits.PlannedTextReplacement] = []
    for line, target in zip(docstring.structure.lines, raw_line_targets):
        line_number = line.source_line_number
        if target is not None and line_number is not None and line.raw_text != target:
            replacements.append(
                rule_edits.PlannedTextReplacement(
                    start_offset=line.start_offset,
                    end_offset=line.end_offset,
                    text=target,
                    line_numbers=(line_number,),
                )
            )
    if not replacements:
        return None
    # Safe simple docstrings map evaluated line text back to source body text modulo newline spelling.
    value_lines = [target if target is not None else line.raw_text for line, target in zip(docstring.structure.lines, raw_line_targets)]
    return planned_simple_docstring_source_change(docstring, context=context, replacements=tuple(replacements), value_lines=value_lines)


def planned_simple_docstring_source_change(
    docstring: DocstringInfo,
    *,
    context: RuleContext,
    replacements: tuple[rule_edits.PlannedTextReplacement, ...],
    value_lines: list[str],
) -> rule_edits.PlannedSourceChange | None:
    """Return one whole-literal replacement from evaluated-value replacements."""
    if not replacements:
        return None
    fragments = docstring_value_fragments(docstring, line_ending=context.line_ending)
    if fragments is None or not isinstance(docstring.node, cst.SimpleString):
        return None
    value = join_docstring_value_lines(docstring, value_lines)
    source_chunks: list[str] = []
    cursor = 0
    for replacement in replacements:
        source_chunks.append(string_literals.source_for_value_slice(fragments, cursor, replacement.start_offset))
        source_chunks.append(replacement.text)
        cursor = replacement.end_offset
    source_chunks.append(string_literals.source_for_value_slice(fragments, cursor, len(fragments)))
    rendered = string_literals.render_simple_string_from_body_source(docstring.node.prefix, docstring.node.quote, "".join(source_chunks), expected_value=value)
    if rendered is None or rendered == docstring.source:
        return None
    return rule_edits.PlannedSourceChange(
        edit=rule_edits.SourceEdit(range=docstring.range, replacement=rendered),
        line_numbers=tuple(line_number for replacement in replacements for line_number in replacement.line_numbers),
    )


def planned_simple_docstring_output_change(
    docstring: DocstringInfo,
    *,
    context: RuleContext,
    output_lines: tuple[DocstringOutputLine, ...],
    line_numbers: tuple[int, ...],
    preserve_trailing_newline: bool | None = None,
    separator_fallback: DocstringOutputSeparatorFallback | None = None,
) -> rule_edits.PlannedSourceChange | None:
    """Return one whole-literal replacement from target output lines."""
    if not isinstance(docstring.node, cst.SimpleString):
        return None
    fragments = docstring_value_fragments(docstring, line_ending=context.line_ending)
    if fragments is None:
        return None
    keep_trailing_newline = docstring_value_ends_with_newline(docstring) if preserve_trailing_newline is None else preserve_trailing_newline
    body_source = _output_body_source(output_lines, fragments=fragments, line_ending=context.line_ending, preserve_trailing_newline=keep_trailing_newline)
    expected_value = _output_expected_value(output_lines, preserve_trailing_newline=keep_trailing_newline)
    rendered = _render_output_with_separator_fallback(docstring, body_source=body_source, expected_value=expected_value, separator_fallback=separator_fallback)
    if rendered is None or rendered == docstring.source:
        return None
    return rule_edits.PlannedSourceChange(
        edit=rule_edits.SourceEdit(range=docstring.range, replacement=rendered),
        line_numbers=line_numbers,
    )


def docstring_content_indexes(docstring: DocstringInfo) -> tuple[int, ...]:
    """Return logical line indexes containing non-space-tab text."""
    return tuple(line.index for line in docstring.structure.lines if line.text.strip(" \t"))


def docstring_value_line_numbers(lines: tuple[DocstringValueLine, ...]) -> tuple[int, ...]:
    """Return deduplicated source line numbers for changed logical lines."""
    return tuple(dict.fromkeys(line.source_line_number for line in lines if line.source_line_number is not None))


def summary_first_line_targets(docstrings: tuple[DocstringInfo, ...]) -> tuple[SummaryLineTarget, ...]:
    """Return first non-adornment summary lines for parsed top-level summaries."""
    targets: list[SummaryLineTarget] = []
    for docstring in docstrings:
        block = first_summary_block(docstring)
        if block is None:
            continue
        line = first_non_adornment_line(docstring, block.start_line, block.end_line)
        if line is not None:
            targets.append(SummaryLineTarget(docstring=docstring, block=block, line=line))
    return tuple(targets)


def summary_terminal_line_targets(docstrings: tuple[DocstringInfo, ...]) -> tuple[SummaryLineTarget, ...]:
    """Return final non-adornment summary lines for parsed top-level summaries."""
    targets: list[SummaryLineTarget] = []
    for docstring in docstrings:
        block = first_summary_block(docstring)
        if block is None:
            continue
        line = final_non_adornment_line(docstring, block.start_line, block.end_line)
        if line is not None:
            targets.append(SummaryLineTarget(docstring=docstring, block=block, line=line))
    return tuple(targets)


def first_summary_block(docstring: DocstringInfo) -> DocstringBlock | None:
    """Return the first non-blank block when it is a parsed top-level summary."""
    first_block = next((block for block in docstring.structure.blocks if block.kind is not DocstringBlockKind.BLANK), None)
    if first_block is None or first_block.kind is not DocstringBlockKind.SUMMARY:
        return None
    return first_block


def first_non_adornment_line(docstring: DocstringInfo, start: int, end: int) -> DocstringValueLine | None:
    """Return the first non-empty, non-adornment logical line in a summary block."""
    for index in range(start, end):
        line = docstring.structure.lines[index]
        if line.text.strip(" \t") and not is_adornment(line.text):
            return line
    return None


def final_non_adornment_line(docstring: DocstringInfo, start: int, end: int) -> DocstringValueLine | None:
    """Return the final non-empty, non-adornment logical line in a summary block."""
    for index in range(end - 1, start - 1, -1):
        line = docstring.structure.lines[index]
        if line.text.strip(" \t") and not is_adornment(line.text):
            return line
    return None


def docstring_line_numbers(docstring: DocstringInfo, line: DocstringValueLine) -> tuple[int, ...]:
    """Return concrete source lines for a docstring value line."""
    if line.source_line_number is not None:
        return docstring_value_line_numbers((line,))
    return tuple(source_line.line_number for source_line in docstring.physical_lines)


def docstring_value_ends_with_newline(docstring: DocstringInfo) -> bool:
    """Return whether an evaluated docstring value ends with a newline."""
    return docstring.value.endswith(("\r\n", "\r", "\n"))


def _render_output_body_source(docstring: DocstringInfo, *, body_source: str, expected_value: str) -> str | None:
    """Render output body source using the docstring's original literal spelling."""
    if not isinstance(docstring.node, cst.SimpleString):
        return None
    return string_literals.render_simple_string_from_body_source(docstring.node.prefix, docstring.node.quote, body_source, expected_value=expected_value)


def _render_output_with_separator_fallback(
    docstring: DocstringInfo,
    *,
    body_source: str,
    expected_value: str,
    separator_fallback: DocstringOutputSeparatorFallback | None,
) -> str | None:
    """Render output source, applying separator fallback strategy when configured."""
    if separator_fallback is DocstringOutputSeparatorFallback.OPENING:
        return _opening_separator_rendered_output(docstring, body_source=body_source, expected_value=expected_value)
    if separator_fallback is DocstringOutputSeparatorFallback.CLOSING:
        return _closing_separator_rendered_output(docstring, body_source=body_source, expected_value=expected_value)
    if separator_fallback is DocstringOutputSeparatorFallback.BOTH:
        rendered = _render_output_body_source(docstring, body_source=body_source, expected_value=expected_value)
        if rendered is not None:
            return rendered
        fallback_body_source, fallback_expected_value = _separator_fallback_output(body_source, expected_value, separator_fallback=separator_fallback)
        return _render_output_body_source(docstring, body_source=fallback_body_source, expected_value=fallback_expected_value)
    return _render_output_body_source(docstring, body_source=body_source, expected_value=expected_value)


def render_simple_docstring_body_with_separator_fallbacks(docstring: DocstringInfo, *, body_source: str, expected_value: str) -> str | None:
    """Render output source after trying value-preserving quote escapes and separator fallbacks."""
    if not isinstance(docstring.node, cst.SimpleString):
        return None
    for candidate_body, candidate_value in simple_docstring_body_source_candidates(docstring.node, body_source, expected_value=expected_value):
        rendered = _render_output_body_source(docstring, body_source=candidate_body, expected_value=candidate_value)
        if rendered is not None:
            return rendered
    return None


def simple_docstring_body_source_candidates(node: cst.SimpleString, body_source: str, *, expected_value: str) -> Iterator[tuple[str, str]]:
    """Yield source-body candidates ordered by value preservation before separator fallback."""
    seen: set[tuple[str, str]] = set()

    def candidate_once(candidate: tuple[str, str]) -> Iterator[tuple[str, str]]:
        if candidate not in seen:
            seen.add(candidate)
            yield candidate

    escaped_opening = escaped_opening_quote_body_source(node, body_source)
    escaped_closing = escaped_closing_quote_body_source(node, body_source)
    if escaped_opening is not None:
        escaped_both = escaped_closing_quote_body_source(node, escaped_opening)
        if escaped_both is not None:
            yield from candidate_once((escaped_both, expected_value))
        yield from candidate_once((escaped_opening, expected_value))
    if escaped_closing is not None:
        escaped_closing_opening = escaped_opening_quote_body_source(node, escaped_closing)
        if escaped_closing_opening is not None:
            yield from candidate_once((escaped_closing_opening, expected_value))
        yield from candidate_once((escaped_closing, expected_value))
    yield from candidate_once((body_source, expected_value))
    yield from candidate_once(_separator_fallback_output(body_source, expected_value, separator_fallback=DocstringOutputSeparatorFallback.OPENING))
    yield from candidate_once(_separator_fallback_output(body_source, expected_value, separator_fallback=DocstringOutputSeparatorFallback.CLOSING))
    yield from candidate_once(_separator_fallback_output(body_source, expected_value, separator_fallback=DocstringOutputSeparatorFallback.BOTH))


def _opening_separator_rendered_output(docstring: DocstringInfo, *, body_source: str, expected_value: str) -> str | None:
    """Render output with opening quote separator precedence."""
    rendered = _render_output_body_source(docstring, body_source=body_source, expected_value=expected_value)
    if rendered is None:
        fallback_body_source, fallback_expected_value = _separator_fallback_output(body_source, expected_value, separator_fallback=DocstringOutputSeparatorFallback.OPENING)
        return _render_output_body_source(docstring, body_source=fallback_body_source, expected_value=fallback_expected_value)
    return _opening_quote_separator_output(docstring, body_source=body_source, expected_value=expected_value) or rendered


def _closing_separator_rendered_output(docstring: DocstringInfo, *, body_source: str, expected_value: str) -> str | None:
    """Render output with closing quote separator precedence."""
    rendered = _render_output_body_source(docstring, body_source=body_source, expected_value=expected_value)
    if rendered is not None:
        return rendered
    rendered = _closing_quote_separator_output(docstring, body_source=body_source, expected_value=expected_value)
    if rendered is not None:
        return rendered
    fallback_body_source, fallback_expected_value = _separator_fallback_output(body_source, expected_value, separator_fallback=DocstringOutputSeparatorFallback.CLOSING)
    return _render_output_body_source(docstring, body_source=fallback_body_source, expected_value=fallback_expected_value)


def _opening_quote_separator_output(docstring: DocstringInfo, *, body_source: str, expected_value: str) -> str | None:
    """Render an escaped leading quote to keep opening delimiter and content distinct."""
    if not isinstance(docstring.node, cst.SimpleString):
        return None
    escaped_body_source = escaped_opening_quote_body_source(docstring.node, body_source)
    if escaped_body_source is None:
        return None
    return _render_output_body_source(docstring, body_source=escaped_body_source, expected_value=expected_value)


def escaped_opening_quote_body_source(node: cst.SimpleString, body_source: str) -> str | None:
    """Return body source with a leading delimiter quote escaped where possible."""
    if "r" in node.prefix.lower():
        return None
    quote_char = "'" if "'" in node.quote else '"'
    if not body_source.startswith(quote_char):
        return None
    return f"\\{body_source}"


def escaped_closing_quote_body_source(node: cst.SimpleString, body_source: str) -> str | None:
    """Return body source with trailing delimiter quotes escaped where possible."""
    if "r" in node.prefix.lower():
        return None
    quote_char = "'" if "'" in node.quote else '"'
    trailing_quotes = len(body_source) - len(body_source.rstrip(quote_char))
    if trailing_quotes <= 0:
        return None
    escape_count = min(trailing_quotes, len(node.quote) - 1)
    if escape_count <= 0:
        return None
    escaped_quotes = ("\\" + quote_char) * escape_count
    return f"{body_source[:-escape_count]}{escaped_quotes}"


def _closing_quote_separator_output(docstring: DocstringInfo, *, body_source: str, expected_value: str) -> str | None:
    """Render escaped trailing quotes to keep closing delimiter and content distinct."""
    if not isinstance(docstring.node, cst.SimpleString):
        return None
    escaped_body_source = escaped_closing_quote_body_source(docstring.node, body_source)
    if escaped_body_source is None:
        return None
    return _render_output_body_source(docstring, body_source=escaped_body_source, expected_value=expected_value)


def _separator_fallback_output(body_source: str, expected_value: str, *, separator_fallback: DocstringOutputSeparatorFallback) -> tuple[str, str]:
    """Return a one-space separator fallback body and value."""
    if separator_fallback is DocstringOutputSeparatorFallback.OPENING:
        return f" {body_source}", f" {expected_value}"
    if separator_fallback is DocstringOutputSeparatorFallback.CLOSING:
        return f"{body_source} ", f"{expected_value} "
    if separator_fallback is DocstringOutputSeparatorFallback.BOTH:
        return f" {body_source} ", f" {expected_value} "
    raise ValueError(f"Unsupported separator fallback: {separator_fallback!r}")


def _output_body_source(
    output_lines: tuple[DocstringOutputLine, ...],
    *,
    fragments: tuple[string_literals.StringValueFragment, ...],
    line_ending: str,
    preserve_trailing_newline: bool,
) -> str:
    """Return replacement literal body source from output lines."""
    chunks: list[str] = []
    for index, output_line in enumerate(output_lines):
        if index:
            chunks.append(line_ending)
        if output_line.original is None:
            if output_line.source is None:
                raise ValueError("Synthesized output lines require source text")
            chunks.append(output_line.source)
        else:
            chunks.append(docstring_line_source(output_line.original, fragments=fragments, strip_docstring_margin=output_line.strip_docstring_margin))
    if preserve_trailing_newline:
        chunks.append(line_ending)
    return "".join(chunks)


def _output_expected_value(output_lines: tuple[DocstringOutputLine, ...], *, preserve_trailing_newline: bool) -> str:
    """Return replacement evaluated value from output lines."""
    chunks: list[str] = []
    for index, output_line in enumerate(output_lines):
        if index:
            chunks.append("\n")
        if output_line.original is None:
            if output_line.value is None:
                raise ValueError("Synthesized output lines require evaluated text")
            chunks.append(output_line.value)
        elif output_line.strip_docstring_margin:
            chunks.append(output_line.original.text)
        else:
            chunks.append(output_line.original.raw_text)
    if preserve_trailing_newline:
        chunks.append("\n")
    return "".join(chunks)


def join_docstring_value_lines(docstring: DocstringInfo, lines: list[str]) -> str:
    """Join replacement logical lines with the original evaluated newline spellings."""
    chunks: list[str] = []
    for index, (line_info, line) in enumerate(zip(docstring.structure.lines, lines)):
        chunks.append(line)
        if index + 1 < len(lines):
            chunks.append(docstring.value[line_info.end_offset : docstring.structure.lines[index + 1].start_offset])
        else:
            chunks.append(docstring.value[line_info.end_offset :])
    return "".join(chunks)


def _docstring_source_indent(statement: cst.SimpleStatementLine | cst.SimpleStatementSuite, *, code_range: cst_metadata.CodeRange, source_lines: list[str], indent_width: int) -> int:
    """Return the visual indentation margin for a simple docstring."""
    source_indent = text_layout.leading_width(source_lines[code_range.start.line - 1])
    return source_indent + indent_width if isinstance(statement, cst.SimpleStatementSuite) else source_indent


@typing.overload
def value_offset_for_text_column(line: DocstringValueLine, column: int, *, require_source_text: typing.Literal[False] = False) -> int: ...


@typing.overload
def value_offset_for_text_column(line: DocstringValueLine, column: int, *, require_source_text: typing.Literal[True]) -> int | None: ...


def value_offset_for_text_column(line: DocstringValueLine, column: int, *, require_source_text: bool = False) -> int | None:
    """Return the evaluated-value offset for a line.text column."""
    unclamped_raw_column = line.text_raw_start_column + column - line.text_virtual_prefix_length
    if require_source_text and (unclamped_raw_column < line.text_raw_start_column or unclamped_raw_column > len(line.raw_text)):
        return None
    raw_column = line.text_raw_start_column + max(column - line.text_virtual_prefix_length, 0)
    return line.start_offset + raw_column


def _qualified_name(parent: DefinitionInfo, name: str) -> str:
    """Return the qualified name for a child definition."""
    if parent.kind == DefinitionKind.MODULE:
        return name
    return f"{parent.qualified_name}.{name}"


def _first_expression(body: cst.Module | cst.BaseSuite) -> tuple[cst.Expr, cst.SimpleStatementLine | cst.SimpleStatementSuite] | None:
    """Return the first expression statement in a definition body."""
    if isinstance(body, cst.SimpleStatementSuite):
        if body.body and isinstance(body.body[0], cst.Expr):
            return body.body[0], body
        return None

    statements = body.body
    if not statements or not isinstance(statements[0], cst.SimpleStatementLine):
        return None
    statement = statements[0]
    if statement.body and isinstance(statement.body[0], cst.Expr):
        return statement.body[0], statement
    return None


def _simple_docstring_source_line_number(node: cst.SimpleString, *, source: str, physical_lines: tuple[DocstringLine, ...], code_range: cst_metadata.CodeRange) -> int | None:
    """Return the first source line when evaluated lines map unambiguously."""
    value = node.evaluated_value
    if not isinstance(value, str):
        return None
    logical_line_count = len(_value_lines(value, source_line_number=None, source_indent=None))
    has_separate_trailing_closing_delimiter = value.endswith(("\r\n", "\r", "\n")) and len(physical_lines) == logical_line_count + 1 and physical_lines[-1].source.strip() == node.quote
    if len(physical_lines) != logical_line_count and not has_separate_trailing_closing_delimiter:
        return None
    if logical_line_count == 1:
        return code_range.start.line
    body_start = len(node.prefix) + len(node.quote)
    body = source[body_start : -len(node.quote)]
    if "r" not in node.prefix.lower() and "\\" in body:
        return None
    return code_range.start.line


def _physical_lines(code_range: cst_metadata.CodeRange, source: str) -> tuple[DocstringLine, ...]:
    """Split exact docstring source into physical source-line records."""
    lines = re.split(r"\r\n|\r|\n", source)
    return tuple(
        DocstringLine(
            line_number=code_range.start.line + index,
            start_column=code_range.start.column if index == 0 else 0,
            end_column=code_range.end.column if index == len(lines) - 1 else (code_range.start.column + len(line) if index == 0 else len(line)),
            source=line,
        )
        for index, line in enumerate(lines)
    )
