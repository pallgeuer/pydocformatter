from __future__ import annotations

import dataclasses
import enum
import re
from collections.abc import Mapping

import libcst as cst
import libcst.metadata as cst_metadata

import pydocformatter.rules.collection as rule_collection
from pydocformatter.rules.definition import RuleCategoryBase, RuleCategoryContext, RuleContext
from pydocformatter.rules.models import RuleCategoryMetadata

_ENCODING_COOKIE_RE = re.compile(r"^#.*?coding[:=][ \t]*[-_.a-zA-Z0-9]+")
_TYPE_DIRECTIVE_RE = re.compile(r"^#\s*type\s*:", re.IGNORECASE)
_TOOL_DIRECTIVE_RE = re.compile(r"^#\s*(?:noqa\b|pylint\b|pyright\b|mypy\b|ruff\b|flake8\b|fmt\s*:|isort\s*:|pragma\b)", re.IGNORECASE)


class CommentPlacement(enum.Enum):
    """Physical placement of a Python comment."""

    STANDALONE = "standalone"
    TRAILING = "trailing"


class CommentKind(enum.Enum):
    """Semantic kind used to protect special comments from formatting."""

    REGULAR = "regular"
    SHEBANG = "shebang"
    ENCODING_COOKIE = "encoding-cookie"
    TYPE_DIRECTIVE = "type-directive"
    TOOL_DIRECTIVE = "tool-directive"


@dataclasses.dataclass(frozen=True)
class CommentInfo:
    """Lossless source information for one Python comment."""

    node: cst.Comment
    range: cst_metadata.CodeRange
    placement: CommentPlacement
    kind: CommentKind
    indent: str
    text: str

    @property
    def content(self) -> str:
        """Return comment text without its leading hash or surrounding whitespace."""
        return self.text.removeprefix("#").strip()

    @property
    def is_empty(self) -> bool:
        """Return whether the comment has no non-whitespace content."""
        return not self.content


@dataclasses.dataclass(frozen=True)
class CommentBlock:
    """Consecutive regular standalone comments with one indentation level."""

    comments: tuple[CommentInfo, ...]
    range: cst_metadata.CodeRange
    indent: str


@dataclasses.dataclass(frozen=True)
class PCFCategoryData:
    """Prepared comment information shared by PCF rules."""

    comments: tuple[CommentInfo, ...]
    standalone_blocks: tuple[CommentBlock, ...]


class _CommentCollector(cst.CSTVisitor):
    """Collect comments from a LibCST module."""

    def __init__(self) -> None:
        super().__init__()
        self.comments: list[cst.Comment] = []

    def visit_Comment(self, node: cst.Comment) -> None:
        """Collect one comment node."""
        self.comments.append(node)


@rule_collection.register_rule_category
class PCF(RuleCategoryBase):
    """Comment formatting rule category."""

    meta = RuleCategoryMetadata(
        prefix="PCF",
        name="pydocformatter comment formatting",
        url="https://github.com/pallgeuer/pydocformatter",
    )

    @classmethod
    def prepare(cls, context: RuleCategoryContext) -> PCFCategoryData:
        """Collect and classify comments for one module."""
        del cls
        collector = _CommentCollector()
        context.module.visit(collector)
        parents = context.metadata_wrapper.resolve(cst_metadata.ParentNodeProvider)
        source_lines = _source_lines(context.module.code)
        comments = tuple(
            sorted(
                (_comment_info(node, positions=context.positions, parents=parents, source_lines=source_lines) for node in collector.comments),
                key=lambda comment: (comment.range.start.line, comment.range.start.column),
            )
        )
        return PCFCategoryData(comments=comments, standalone_blocks=_standalone_blocks(comments))

    @classmethod
    def require_data(cls, context: RuleContext) -> PCFCategoryData:
        """Return prepared PCF data or raise for an invalid rule context."""
        if not isinstance(context.category_data, PCFCategoryData):
            raise TypeError(f"{cls.meta.prefix} rules require PCFCategoryData")
        return context.category_data


def _comment_info(node: cst.Comment, *, positions: Mapping[cst.CSTNode, cst_metadata.CodeRange], parents: Mapping[cst.CSTNode, cst.CSTNode], source_lines: list[str]) -> CommentInfo:
    """Build source information for one comment node."""
    code_range = positions[node]
    parent = parents[node]
    placement = CommentPlacement.STANDALONE if isinstance(parent, cst.EmptyLine) else CommentPlacement.TRAILING
    source_line = source_lines[code_range.start.line - 1]
    line_prefix = source_line[: code_range.start.column]
    indent = line_prefix if placement == CommentPlacement.STANDALONE else line_prefix[: len(line_prefix) - len(line_prefix.lstrip(" \t\f"))]
    return CommentInfo(
        node=node,
        range=code_range,
        placement=placement,
        kind=_comment_kind(node.value, line=code_range.start.line, source_lines=source_lines),
        indent=indent,
        text=node.value,
    )


def _comment_kind(text: str, *, line: int, source_lines: list[str]) -> CommentKind:
    """Classify a comment that may need protection from ordinary formatting."""
    if line == 1 and text.startswith("#!"):
        return CommentKind.SHEBANG
    first_line_allows_second_cookie = line != 2 or not source_lines[0].strip() or source_lines[0].lstrip(" \t\f").startswith("#")
    if line <= 2 and first_line_allows_second_cookie and _ENCODING_COOKIE_RE.match(text):
        return CommentKind.ENCODING_COOKIE
    if _TYPE_DIRECTIVE_RE.match(text):
        return CommentKind.TYPE_DIRECTIVE
    if _TOOL_DIRECTIVE_RE.match(text):
        return CommentKind.TOOL_DIRECTIVE
    return CommentKind.REGULAR


def _standalone_blocks(comments: tuple[CommentInfo, ...]) -> tuple[CommentBlock, ...]:
    """Group eligible standalone comments into formatting blocks."""
    blocks: list[CommentBlock] = []
    current: list[CommentInfo] = []

    def flush() -> None:
        if not current:
            return
        blocks.append(
            CommentBlock(
                comments=tuple(current),
                range=cst_metadata.CodeRange(start=current[0].range.start, end=current[-1].range.end),
                indent=current[0].indent,
            )
        )
        current.clear()

    for comment in comments:
        eligible = comment.placement == CommentPlacement.STANDALONE and comment.kind == CommentKind.REGULAR and not comment.is_empty
        consecutive = not current or comment.range.start.line == current[-1].range.end.line + 1
        same_indent = not current or comment.indent == current[-1].indent
        if not eligible:
            flush()
        elif consecutive and same_indent:
            current.append(comment)
        else:
            flush()
            current.append(comment)
    flush()
    return tuple(blocks)


def _source_lines(source: str) -> list[str]:
    """Split source at Python physical line endings without Unicode separators."""
    lines: list[str] = []
    line_start = 0
    index = 0
    while index < len(source):
        if source[index] == "\r":
            lines.append(source[line_start:index])
            index += 2 if index + 1 < len(source) and source[index + 1] == "\n" else 1
            line_start = index
        elif source[index] == "\n":
            lines.append(source[line_start:index])
            index += 1
            line_start = index
        else:
            index += 1
    lines.append(source[line_start:])
    return lines
