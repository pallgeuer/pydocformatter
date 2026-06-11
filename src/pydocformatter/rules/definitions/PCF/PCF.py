from __future__ import annotations

import dataclasses
import enum
import re
from collections.abc import Mapping

import libcst as cst
import libcst.metadata as cst_metadata

import pydocformatter.rules.definition_helpers.text_layout as text_layout
import pydocformatter.rules.registration as rule_registration
from pydocformatter.rules.definition import RuleCategoryBase, RuleCategoryContext, RuleContext
from pydocformatter.rules.models import RuleCategoryMetadata

_ENCODING_COOKIE_RE = re.compile(r"^#.*?coding[:=][ \t]*[-_.a-zA-Z0-9]+")
_TYPE_DIRECTIVE_RE = re.compile(r"^#\s*type\s*:", re.IGNORECASE)
_TOOL_DIRECTIVE_RE = re.compile(
    r"^#\s*(?:noqa\b|nosec\b|nosemgrep\b|pylint\b|pyright\b|mypy\b|ruff\b|flake8\b|fmt\s*:|isort\s*:|pragma\b)",
    re.IGNORECASE,
)


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
    line_prefix: str
    text: str

    @property
    def raw_content(self) -> str:
        """Return comment text after exactly one leading hash."""
        return self.text.removeprefix("#")

    @property
    def body(self) -> str:
        """Return comment text after one optional conventional marker space."""
        content = self.raw_content
        return content[1:] if content.startswith(" ") else content

    @property
    def content(self) -> str:
        """Return normalized comment content without surrounding whitespace."""
        return self.raw_content.strip()

    @property
    def is_empty(self) -> bool:
        """Return whether the comment has no non-whitespace content."""
        return not self.content

    @property
    def is_hash_only(self) -> bool:
        """Return whether the comment consists only of hashes and whitespace."""
        return not self.text.strip("# \t\f")


@dataclasses.dataclass(frozen=True)
class StandaloneCommentRun:
    """Consecutive regular non-empty standalone comments at one indentation."""

    comments: tuple[CommentInfo, ...]
    range: cst_metadata.CodeRange
    indent: str


@dataclasses.dataclass(frozen=True)
class PCFCategoryData:
    """Prepared source and comment information shared by PCF rules."""

    source_lines: tuple[str, ...]
    comments: tuple[CommentInfo, ...]
    standalone_runs: tuple[StandaloneCommentRun, ...]
    trailing_comments: tuple[CommentInfo, ...]

    def source_for(self, code_range: cst_metadata.CodeRange) -> str:
        """Return exact source text for a half-open LibCST code range."""
        start_line = code_range.start.line - 1
        end_line = code_range.end.line - 1
        if start_line == end_line:
            return self.source_lines[start_line][code_range.start.column : code_range.end.column]
        parts = [self.source_lines[start_line][code_range.start.column :]]
        parts.extend(self.source_lines[start_line + 1 : end_line])
        parts.append(self.source_lines[end_line][: code_range.end.column])
        return "".join(parts)


class _CommentCollector(cst.CSTVisitor):
    """Collect comments from a LibCST module."""

    def __init__(self) -> None:
        super().__init__()
        self.comments: list[cst.Comment] = []

    def visit_Comment(self, node: cst.Comment) -> None:
        """Collect one comment node."""
        self.comments.append(node)


@rule_registration.register_rule_category
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
        source_lines_with_endings = tuple(_source_lines_with_endings(context.module.code))
        source_lines = [line.rstrip("\r\n") for line in source_lines_with_endings]
        comments = tuple(
            sorted(
                (_comment_info(node, positions=context.positions, parents=parents, source_lines=source_lines) for node in collector.comments),
                key=lambda comment: (comment.range.start.line, comment.range.start.column),
            )
        )
        return PCFCategoryData(
            source_lines=source_lines_with_endings,
            comments=comments,
            standalone_runs=_standalone_runs(comments),
            trailing_comments=tuple(comment for comment in comments if comment.placement == CommentPlacement.TRAILING),
        )

    @classmethod
    def require_data(cls, context: RuleContext) -> PCFCategoryData:
        """Return prepared PCF data or raise for an invalid rule context."""
        if not isinstance(context.category_data, PCFCategoryData):
            raise TypeError(f"{cls.meta.prefix} rules require PCFCategoryData")
        return context.category_data


def available_comment_width(indent: str, *, line_length: int, tab_width: int, prefix: str = "") -> int:
    """Return available content width after indentation and comment prefixes."""
    return line_length - text_layout.display_width(f"{indent}# {prefix}", tab_width=tab_width)


def render_comment(content: str, *, indent: str = "", include_indent: bool = True) -> str:
    """Render one canonical comment line."""
    prefix = indent if include_indent else ""
    return f"{prefix}# {content}" if content else f"{prefix}#"


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
        line_prefix=line_prefix,
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


def _standalone_runs(comments: tuple[CommentInfo, ...]) -> tuple[StandaloneCommentRun, ...]:
    """Group physical standalone comments without applying formatting policy."""
    runs: list[StandaloneCommentRun] = []
    current: list[CommentInfo] = []

    def flush() -> None:
        if not current:
            return
        runs.append(
            StandaloneCommentRun(
                comments=tuple(current),
                range=cst_metadata.CodeRange(start=current[0].range.start, end=current[-1].range.end),
                indent=current[0].indent,
            )
        )
        current.clear()

    for comment in comments:
        eligible = comment.placement == CommentPlacement.STANDALONE and comment.kind == CommentKind.REGULAR and not comment.is_empty and not comment.is_hash_only
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
    return tuple(runs)


def _source_lines_with_endings(source: str) -> list[str]:
    """Split source while preserving Python physical line endings."""
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
