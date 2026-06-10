from __future__ import annotations

import dataclasses
import enum
import re

import libcst as cst
import libcst.metadata as cst_metadata

import pydocformatter.cli.settings_check as settings_check
import pydocformatter.rules.collection as rule_collection
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
    SPHINX_FIELD = "sphinx-field"
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
    source_line_number: int | None


@dataclasses.dataclass(frozen=True)
class DocstringEntry:
    """One parsed convention section entry or Sphinx field."""

    kind: DocstringEntryKind
    names: tuple[str, ...]
    type_text: str | None
    description: str
    start_line: int
    end_line: int


@dataclasses.dataclass(frozen=True)
class ReflowRegion:
    """A contiguous semantic region whose lines may be merged before wrapping."""

    kind: DocstringBlockKind
    start_line: int
    end_line: int
    start_offset: int
    end_offset: int
    lines: tuple[str, ...]
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
    entries: tuple[DocstringEntry, ...]


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
class PDFCategoryData:
    """Prepared definitions and docstrings shared by PDF rules."""

    definitions: tuple[DefinitionInfo, ...]
    docstrings: tuple[DocstringInfo, ...]

    def docstring_for(self, definition: DefinitionInfo) -> DocstringInfo | None:
        """Return the docstring owned by a definition, if one exists."""
        return next((docstring for docstring in self.docstrings if docstring.owner is definition), None)


class _DefinitionCollector(cst.CSTVisitor):
    """Collect documentable definitions and their existing docstrings."""

    def __init__(self, context: RuleCategoryContext) -> None:
        super().__init__()
        self.context = context
        self.source_lines = _source_lines(context.module.code)
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
        source = _source_for_range(code_range, source_lines=self.source_lines)
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


@rule_collection.register_rule_category
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
        return PDFCategoryData(definitions=tuple(collector.definitions), docstrings=tuple(collector.docstrings))

    @classmethod
    def require_data(cls, context: RuleContext) -> PDFCategoryData:
        """Return prepared PDF data or raise for an invalid rule context."""
        if not isinstance(context.category_data, PDFCategoryData):
            raise TypeError(f"{cls.meta.prefix} rules require PDFCategoryData")
        return context.category_data


_GOOGLE_SECTIONS = {
    "args",
    "arguments",
    "attention",
    "attributes",
    "caution",
    "danger",
    "error",
    "example",
    "examples",
    "hint",
    "important",
    "keyword args",
    "keyword arguments",
    "methods",
    "note",
    "notes",
    "other args",
    "other arguments",
    "raises",
    "references",
    "return",
    "returns",
    "see also",
    "tip",
    "todo",
    "warning",
    "warnings",
    "warns",
    "yield",
    "yields",
}
_NUMPY_SECTIONS = {
    "attributes",
    "examples",
    "extended summary",
    "methods",
    "notes",
    "other parameters",
    "other params",
    "parameters",
    "raises",
    "receives",
    "references",
    "returns",
    "see also",
    "short summary",
    "warnings",
    "warns",
    "yields",
}
_LIST_RE = re.compile(r"^(?P<indent>[ \t]*)(?P<marker>(?:[-+*]|\d+[.)]))[ \t]+(?P<text>.*)$")
_BLOCK_QUOTE_RE = re.compile(r"^(?P<indent>[ \t]*)(?P<quote>(?:>[ \t]*)+)(?P<text>.*)$")
_FENCE_RE = re.compile(r"^[ \t]*(?P<fence>`{3,}|~{3,})(?P<info>.*)$")
_DIRECTIVE_RE = re.compile(r"^(?P<indent>[ \t]*)\.\.[ \t]+(?P<name>[\w-]+)::(?P<argument>.*)$")
_SPHINX_FIELD_RE = re.compile(r"^(?P<indent>[ \t]*):(?P<field>[\w-]+)(?:[ \t]+(?P<argument>[^:]+))?:[ \t]*(?P<description>.*)$")
_GOOGLE_ENTRY_RE = re.compile(r"^(?P<indent>[ \t]+)(?P<name>\*{0,2}[A-Za-z_][\w.]*)(?:[ \t]*\((?P<type>[^)]+)\))?:[ \t]*(?P<description>.*)$")
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
                block_end = self._indented_body_end(index, end, _indent_width(directive.group("indent")))
                blocks.append(DocstringBlock(DocstringBlockKind.DIRECTIVE, index, block_end))
                index = block_end
                self.summary_pending = False
                continue
            if self.settings.docstring_parse_literal_blocks and text.rstrip().endswith("::") and self._has_indented_body(index, end):
                block_end = self._indented_body_end(index, end, _leading_width(text))
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
            if self.settings.docstring_parse_sphinx_fields and (field_match := _SPHINX_FIELD_RE.match(text)) is not None:
                block, index = self._parse_sphinx_field(index, end, field_match)
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
                blocks.append(DocstringBlock(DocstringBlockKind.VERBATIM, index, block_end))
                index = block_end
                self.summary_pending = False
                continue
            block_end = index + 1
            while block_end < end and self.lines[block_end].text.strip() and not self._starts_special(block_end, end) and not self.lines[block_end].text[:1].isspace():
                block_end += 1
            kind = DocstringBlockKind.SUMMARY if self.summary_pending else DocstringBlockKind.PARAGRAPH
            blocks.append(DocstringBlock(kind, index, block_end))
            self._add_reflow(kind, index, block_end, lines=tuple(self.lines[line].text.strip() for line in range(index, block_end)), initial_indent="", subsequent_indent="")
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
            or (self.settings.docstring_parse_sphinx_fields and _SPHINX_FIELD_RE.match(text) is not None)
            or (self.settings.docstring_parse_list_items and _LIST_RE.match(text) is not None)
            or (self.settings.docstring_parse_block_quotes and _BLOCK_QUOTE_RE.match(text) is not None)
        )

    def _section_at(self, index: int, end: int) -> str | None:
        convention = self.settings.docstring_convention
        if convention not in (settings_check.DocstringConvention.GOOGLE, settings_check.DocstringConvention.NUMPY):
            return None
        text = self.lines[index].text
        if text[:1].isspace():
            return None
        stripped = text.strip()
        candidate = stripped[:-1].rstrip() if stripped.endswith(":") else stripped
        names = _GOOGLE_SECTIONS if convention == settings_check.DocstringConvention.GOOGLE else _NUMPY_SECTIONS
        if candidate.lower() not in names:
            return None
        if convention == settings_check.DocstringConvention.NUMPY and index + 1 < end and _is_adornment(self.lines[index + 1].text):
            return candidate
        if convention == settings_check.DocstringConvention.GOOGLE:
            return candidate
        return candidate if not stripped.endswith(":") else None

    def _parse_section(self, start: int, end: int, name: str) -> tuple[DocstringBlock, int]:
        content_start = start + 1
        if content_start < end and _is_adornment(self.lines[content_start].text):
            content_start += 1
        section_end = self._section_end(content_start, end)
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
        section = DocstringSection(name=name, start_line=start, end_line=section_end, header_line=start, entries=entries)
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
        kind = _entry_kind(section_name)
        while index < end:
            protected_end = self._protected_block_end(index, end)
            if protected_end is not None:
                index = protected_end
                continue
            match = _GOOGLE_ENTRY_RE.match(self.lines[index].text)
            if match is None and kind in (DocstringEntryKind.RETURN, DocstringEntryKind.YIELD, DocstringEntryKind.EXCEPTION):
                match = _GENERIC_ENTRY_RE.match(self.lines[index].text)
            if match is None:
                index += 1
                continue
            entry_end = self._entry_end(index, end, _indent_width(match.group("indent")))
            name = match.group("name").strip()
            type_text = match.groupdict().get("type")
            description_lines = [match.group("description").strip()]
            description_lines.extend(self.lines[line].text.strip() for line in range(index + 1, entry_end) if self.lines[line].text.strip())
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
            prefix = self.lines[index].text[: match.start("description")]
            self._add_reflow(
                DocstringBlockKind.SECTION_ENTRY, index, entry_end, lines=tuple(description_lines), initial_indent=prefix, subsequent_indent=" " * len(prefix.expandtabs(self.settings.indent_width))
            )
            index = entry_end
        return tuple(entries)

    def _numpy_entries(self, section_name: str, start: int, end: int) -> tuple[DocstringEntry, ...]:
        entries: list[DocstringEntry] = []
        index = start
        kind = _entry_kind(section_name)
        while index < end:
            protected_end = self._protected_block_end(index, end)
            if protected_end is not None:
                index = protected_end
                continue
            text = self.lines[index].text
            match = _NUMPY_ENTRY_RE.match(text)
            if match is not None:
                entry_end = self._entry_end(index, end, _indent_width(match.group("indent")))
                description_lines = [self.lines[line].text.strip() for line in range(index + 1, entry_end) if self.lines[line].text.strip()]
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
                    indent = self.lines[index + 1].text[: len(self.lines[index + 1].text) - len(self.lines[index + 1].text.lstrip(" \t"))]
                    self._add_reflow(DocstringBlockKind.SECTION_ENTRY, index + 1, entry_end, lines=tuple(description_lines), initial_indent=indent, subsequent_indent=indent)
                index = entry_end
                continue
            if kind in (DocstringEntryKind.RETURN, DocstringEntryKind.YIELD, DocstringEntryKind.EXCEPTION) and text.strip():
                entry_end = self._entry_end(index, end, _leading_width(text))
                description_lines = [self.lines[line].text.strip() for line in range(index + 1, entry_end) if self.lines[line].text.strip()]
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
                    indent = self.lines[index + 1].text[: len(self.lines[index + 1].text) - len(self.lines[index + 1].text.lstrip(" \t"))]
                    self._add_reflow(DocstringBlockKind.SECTION_ENTRY, index + 1, entry_end, lines=tuple(description_lines), initial_indent=indent, subsequent_indent=indent)
                index = entry_end
                continue
            index += 1
        return tuple(entries)

    def _parse_sphinx_field(self, start: int, end: int, match: re.Match[str]) -> tuple[DocstringBlock, int]:
        block_end = self._entry_end(start, end, _indent_width(match.group("indent")))
        field = match.group("field").lower()
        argument = (match.group("argument") or "").strip()
        description_lines = [match.group("description").strip()]
        description_lines.extend(self.lines[line].text.strip() for line in range(start + 1, block_end) if self.lines[line].text.strip())
        kind = _sphinx_entry_kind(field)
        entry = DocstringEntry(kind=kind, names=(argument,) if argument else (), type_text=None, description=" ".join(description_lines).strip(), start_line=start, end_line=block_end)
        self.entries.append(entry)
        prefix = self.lines[start].text[: match.start("description")]
        self._add_reflow(
            DocstringBlockKind.SPHINX_FIELD, start, block_end, lines=tuple(description_lines), initial_indent=prefix, subsequent_indent=" " * len(prefix.expandtabs(self.settings.indent_width))
        )
        return DocstringBlock(DocstringBlockKind.SPHINX_FIELD, start, block_end, entry=entry), block_end

    def _parse_list_item(self, start: int, end: int, match: re.Match[str]) -> tuple[DocstringBlock, int]:
        block_end = self._list_item_end(start, end, match)
        prefix = f'{match.group("indent")}{match.group("marker")} '
        lines = (match.group("text").strip(), *(self.lines[line].text.strip() for line in range(start + 1, block_end)))
        self._add_reflow(DocstringBlockKind.LIST_ITEM, start, block_end, lines=tuple(lines), initial_indent=prefix, subsequent_indent=" " * len(prefix.expandtabs(self.settings.indent_width)))
        return DocstringBlock(DocstringBlockKind.LIST_ITEM, start, block_end), block_end

    def _parse_block_quote(self, start: int, end: int, match: re.Match[str]) -> tuple[DocstringBlock, int]:
        prefix = f'{match.group("indent")}{match.group("quote")}'
        block_end = self._block_quote_end(start, end, prefix)
        texts = [self.lines[line].text[len(prefix) :].strip() for line in range(start, block_end)]
        self._add_reflow(DocstringBlockKind.BLOCK_QUOTE, start, block_end, lines=tuple(texts), initial_indent=prefix, subsequent_indent=prefix)
        return DocstringBlock(DocstringBlockKind.BLOCK_QUOTE, start, block_end), block_end

    def _add_reflow(self, kind: DocstringBlockKind, start: int, end: int, *, lines: tuple[str, ...], initial_indent: str, subsequent_indent: str) -> None:
        if not lines or not any(lines):
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

    def _fence_end(self, start: int, end: int, opening: str) -> int:
        index = start + 1
        while index < end:
            match = _FENCE_RE.match(self.lines[index].text)
            if match is not None and match.group("fence")[0] == opening[0] and len(match.group("fence")) >= len(opening) and not match.group("info").strip():
                return index + 1
            index += 1
        return end

    def _section_end(self, start: int, end: int) -> int:
        index = start
        while index < end:
            if self._section_at(index, end) is not None:
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
            return self._indented_body_end(index, end, _indent_width(directive.group("indent")))
        if self.settings.docstring_parse_literal_blocks and text.rstrip().endswith("::") and self._has_indented_body(index, end):
            return self._indented_body_end(index, end, _leading_width(text))
        if self.settings.docstring_parse_tables and (table_end := self._table_end(index, end)) is not None:
            return table_end
        if self.settings.docstring_parse_headings and self._is_heading(index, end):
            return index + 2 if index + 1 < end and _is_adornment(self.lines[index + 1].text) else index + 1
        if self.settings.docstring_parse_sphinx_fields and (field_match := _SPHINX_FIELD_RE.match(text)) is not None:
            return self._continuation_end(index, end, _indent_width(field_match.group("indent")))
        if self.settings.docstring_parse_list_items and (list_match := _LIST_RE.match(text)) is not None:
            return self._list_item_end(index, end, list_match)
        if self.settings.docstring_parse_block_quotes and (quote_match := _BLOCK_QUOTE_RE.match(text)) is not None:
            prefix = f'{quote_match.group("indent")}{quote_match.group("quote")}'
            return self._block_quote_end(index, end, prefix)
        return None

    def _list_item_end(self, start: int, end: int, match: re.Match[str]) -> int:
        base_indent = _indent_width(match.group("indent"))
        block_end = start + 1
        while block_end < end:
            text = self.lines[block_end].text
            if not text.strip() or _LIST_RE.match(text) is not None or _leading_width(text) <= base_indent:
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
        base_indent = _leading_width(self.lines[index].text)
        next_indent = _leading_width(self.lines[next_index].text)
        return next_indent > base_indent

    def _indented_body_end(self, start: int, end: int, base_indent: int) -> int:
        index = start + 1
        while index < end:
            text = self.lines[index].text
            indent = _leading_width(text)
            if text.strip() and indent <= base_indent:
                break
            index += 1
        return index

    def _entry_end(self, start: int, end: int, base_indent: int) -> int:
        index = start + 1
        while index < end:
            text = self.lines[index].text
            if not text.strip() or _leading_width(text) <= base_indent or self._protected_block_end(index, end) is not None:
                break
            index += 1
        return index

    def _continuation_end(self, start: int, end: int, base_indent: int) -> int:
        index = start + 1
        while index < end:
            text = self.lines[index].text
            if not text.strip():
                break
            indent = _leading_width(text)
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
    margin = source_indent if source_indent is not None else min((_leading_width(text) for _, _, text in raw_lines[1:] if text.strip()), default=0)
    lines = [
        DocstringValueLine(
            index=index,
            start_offset=line_start,
            end_offset=line_end,
            raw_text=raw_text,
            text=raw_text.lstrip(" \t") if index == 0 else _strip_indent(raw_text, margin),
            source_line_number=None if source_line_number is None else source_line_number + index,
        )
        for index, (line_start, line_end, raw_text) in enumerate(raw_lines)
    ]
    return tuple(lines)


def _entry_kind(section_name: str) -> DocstringEntryKind:
    """Return the semantic entry kind for a convention section."""
    normalized = section_name.lower()
    if normalized in {"args", "arguments", "keyword args", "keyword arguments", "other args", "other arguments", "parameters", "other parameters", "other params", "receives"}:
        return DocstringEntryKind.PARAMETER
    if normalized in {"return", "returns"}:
        return DocstringEntryKind.RETURN
    if normalized in {"yield", "yields"}:
        return DocstringEntryKind.YIELD
    if normalized in {"raises", "warns", "warnings"}:
        return DocstringEntryKind.EXCEPTION
    if normalized == "attributes":
        return DocstringEntryKind.ATTRIBUTE
    if normalized == "methods":
        return DocstringEntryKind.METHOD
    return DocstringEntryKind.FIELD


def _sphinx_entry_kind(field: str) -> DocstringEntryKind:
    """Return the semantic entry kind for a Sphinx field name."""
    if field in {"param", "parameter", "arg", "argument", "keyword", "kwarg"}:
        return DocstringEntryKind.PARAMETER
    if field in {"return", "returns", "rtype"}:
        return DocstringEntryKind.RETURN
    if field in {"yield", "yields", "ytype"}:
        return DocstringEntryKind.YIELD
    if field in {"raise", "raises", "except", "exception"}:
        return DocstringEntryKind.EXCEPTION
    return DocstringEntryKind.FIELD


def _is_adornment(text: str) -> bool:
    """Return whether text is a heading or section adornment line."""
    stripped = text.strip()
    return len(stripped) >= 3 and len(set(stripped)) == 1 and stripped[0] in "-=~`^:#*+"


def _is_doctest_prompt(text: str) -> bool:
    """Return whether text starts with a whitespace-delimited doctest prompt."""
    return text.lstrip().startswith(">>> ")


def _indent_width(text: str) -> int:
    """Return the tab-expanded width of text."""
    return len(text.expandtabs(8))


def _leading_width(text: str) -> int:
    """Return the tab-expanded width of leading whitespace."""
    return _indent_width(text[: len(text) - len(text.lstrip(" \t"))])


def _docstring_source_indent(statement: cst.SimpleStatementLine | cst.SimpleStatementSuite, *, code_range: cst_metadata.CodeRange, source_lines: list[str], indent_width: int) -> int:
    """Return the visual indentation margin for a simple docstring."""
    source_indent = _leading_width(source_lines[code_range.start.line - 1])
    return source_indent + indent_width if isinstance(statement, cst.SimpleStatementSuite) else source_indent


def _strip_indent(text: str, width: int) -> str:
    """Strip up to a tab-expanded indentation width from text."""
    index = 0
    column = 0
    while index < len(text) and text[index] in " \t" and column < width:
        column = ((column // 8) + 1) * 8 if text[index] == "\t" else column + 1
        index += 1
    return " " * max(column - width, 0) + text[index:]


def serialize_simple_docstring(value: str) -> str:
    """Serialize a string value as an equivalent triple-double-quoted literal."""
    body: list[str] = []
    for char in value:
        codepoint = ord(char)
        if char == "\\":
            body.append("\\\\")
        elif char == '"':
            body.append('\\"')
        elif char == "\n":
            body.append("\n")
        elif char == "\r":
            body.append("\\r")
        elif char == "\t":
            body.append("\\t")
        elif char == "\b":
            body.append("\\b")
        elif char == "\f":
            body.append("\\f")
        elif char == "\v":
            body.append("\\v")
        elif codepoint < 0x80 and char.isprintable():
            body.append(char)
        elif codepoint <= 0xFF:
            body.append(f"\\x{codepoint:02x}")
        elif codepoint <= 0xFFFF:
            body.append(f"\\u{codepoint:04x}")
        else:
            body.append(f"\\U{codepoint:08x}")
    literal = f'"""{"".join(body)}"""'
    expression = cst.parse_expression(literal)
    if not isinstance(expression, cst.SimpleString) or expression.evaluated_value != value:
        raise ValueError("Failed to serialize docstring value as an equivalent simple literal")
    return literal


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


def _source_for_range(code_range: cst_metadata.CodeRange, *, source_lines: list[str]) -> str:
    """Return the exact source inside a LibCST code range."""
    first_index = code_range.start.line - 1
    last_index = code_range.end.line - 1
    if first_index == last_index:
        return source_lines[first_index][code_range.start.column : code_range.end.column]
    lines = [source_lines[first_index][code_range.start.column :]]
    lines.extend(source_lines[first_index + 1 : last_index])
    lines.append(source_lines[last_index][: code_range.end.column])
    return "".join(lines)


def _simple_docstring_source_line_number(node: cst.SimpleString, *, source: str, physical_lines: tuple[DocstringLine, ...], code_range: cst_metadata.CodeRange) -> int | None:
    """Return the first source line when evaluated lines map unambiguously."""
    value = node.evaluated_value
    if not isinstance(value, str):
        return None
    logical_line_count = len(_value_lines(value, source_line_number=None, source_indent=None))
    if len(physical_lines) != logical_line_count:
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


def _source_lines(source: str) -> list[str]:
    """Split source into lines retaining only Python physical line endings."""
    lines: list[str] = []
    line_start = 0
    index = 0
    while index < len(source):
        if source[index] == "\r":
            index += 2 if index + 1 < len(source) and source[index + 1] == "\n" else 1
            lines.append(source[line_start:index])
            line_start = index
        elif source[index] == "\n":
            index += 1
            lines.append(source[line_start:index])
            line_start = index
        else:
            index += 1
    lines.append(source[line_start:])
    return lines
