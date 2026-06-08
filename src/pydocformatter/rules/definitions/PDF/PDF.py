from __future__ import annotations

import dataclasses
import enum
import re

import libcst as cst
import libcst.metadata as cst_metadata

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
                physical_lines=_physical_lines(code_range, source),
                value_lines=tuple(node.evaluated_value.splitlines()),
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
