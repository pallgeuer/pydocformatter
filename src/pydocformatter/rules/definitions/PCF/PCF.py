"""PCF comment-formatting rule category."""

# Future imports
from __future__ import annotations

# Standard library imports
import re
import enum
import dataclasses
from collections.abc import Mapping
from typing import TYPE_CHECKING

# Third-party imports
import libcst as cst
import libcst.metadata as cst_metadata

# First-party imports
import pydocformatter.rules.edits as rule_edits
import pydocformatter.rules.registration as rule_registration
from pydocformatter.rules.definition import RuleCategoryBase
from pydocformatter.rules.definition_helpers import source_text, text_layout
from pydocformatter.rules.models import RuleCategoryMetadata


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.definition import RuleCategoryContext, RuleContext


_ENCODING_COOKIE_RE = re.compile(r"^#.*?coding[:=][ \t]*[-_.a-zA-Z0-9]+")
_TYPE_DIRECTIVE_RE = re.compile(r"^#\s*type\s*:", re.IGNORECASE)
_TOOL_DIRECTIVE_RE = re.compile(
    r"^#\s*(?:noqa\b|nosec\b|nosemgrep\b|pydocfmt\b|pylint\b|pyright\b|mypy\b|ty\s*:|ruff\b|flake8\b|fmt\s*:|isort\s*:|pragma\b|noinspection\b|language\s*=|@formatter\s*:)", re.IGNORECASE
)


class CommentPlacement(enum.Enum):
    """Physical placement of a Python comment.

    Attributes:
        STANDALONE: A comment that occupies its own logical source line.
        TRAILING: A comment that follows code on the same logical source line.
    """

    STANDALONE = "standalone"
    TRAILING = "trailing"


class CommentKind(enum.Enum):
    """Semantic kind used to protect special comments from formatting.

    Attributes:
        REGULAR: Ordinary prose or code-like comments eligible for normal formatting policy.
        SHEBANG: Interpreter directive comments that must remain byte-for-byte stable.
        ENCODING_COOKIE: Python encoding declaration comments.
        TYPE_DIRECTIVE: Inline or standalone type-checker directive comments.
        TOOL_DIRECTIVE: Linter, formatter, coverage, or IDE directive comments.
    """

    REGULAR = "regular"
    SHEBANG = "shebang"
    ENCODING_COOKIE = "encoding-cookie"
    TYPE_DIRECTIVE = "type-directive"
    TOOL_DIRECTIVE = "tool-directive"


@dataclasses.dataclass(frozen=True)
class CommentInfo:
    """Lossless source information for one Python comment.

    Attributes:
        node (cst.Comment): LibCST comment node.
        range (cst_metadata.CodeRange): Source range occupied by the comment text.
        placement (CommentPlacement): Whether the comment is standalone or trailing.
        kind (CommentKind): Directive classification used to protect special comments.
        indent (str): Leading whitespace before a standalone comment marker.
        line_prefix (str): Source text before the comment on its physical line.
        text (str): Exact comment token text, including the leading hash.
        syntax_sensitive (bool): Whether moving this trailing comment could alter syntax around decorators, arguments,
            continuations, or compound headers.
    """

    node: cst.Comment
    range: cst_metadata.CodeRange
    placement: CommentPlacement
    kind: CommentKind
    indent: str
    line_prefix: str
    text: str
    syntax_sensitive: bool = False

    @property
    def raw_content(self) -> str:
        """Comment text after exactly one leading hash.

        Returns:
            str: Comment source with the syntactic `#` removed and all remaining marker/content text preserved.
        """
        return self.text.removeprefix("#")

    @property
    def body(self) -> str:
        """Comment text after one optional conventional marker space.

        Returns:
            str: Comment content used for prose and structure parsing.
        """
        content = self.raw_content
        return content.removeprefix(" ")

    @property
    def content(self) -> str:
        """Normalized comment content without surrounding whitespace.

        Returns:
            str: Trimmed payload after the syntactic comment marker.
        """
        return self.raw_content.strip()

    @property
    def is_empty(self) -> bool:
        """Whether the comment has no non-whitespace content.

        Returns:
            bool: Whether the comment payload is empty after whitespace trimming.
        """
        return not self.content

    @property
    def is_hash_only(self) -> bool:
        """Whether the comment consists only of hashes and whitespace.

        Returns:
            bool: Whether all characters are marker hashes or whitespace.
        """
        return not self.text.strip("# \t\f")


@dataclasses.dataclass(frozen=True)
class StandaloneCommentRun:
    """Consecutive regular non-empty standalone comments at one indentation.

    Attributes:
        comments (tuple[CommentInfo, ...]): Consecutive standalone comments in physical source order.
        range (cst_metadata.CodeRange): Source range spanning the entire run.
        indent (str): Shared indentation used when rewriting the run.
    """

    comments: tuple[CommentInfo, ...]
    range: cst_metadata.CodeRange
    indent: str


@dataclasses.dataclass(frozen=True)
class PCFCategoryData:
    """Prepared source and comment information shared by PCF rules.

    Attributes:
        source_lines (tuple[str, ...]): Original source split into physical lines.
        comments (tuple[CommentInfo, ...]): All collected comments in source order.
        standalone_runs (tuple[StandaloneCommentRun, ...]): Consecutive standalone comments eligible for block-level
            formatting.
        trailing_comments (tuple[CommentInfo, ...]): Trailing comments eligible for spacing or extraction rules.
    """

    source_lines: tuple[str, ...]
    comments: tuple[CommentInfo, ...]
    standalone_runs: tuple[StandaloneCommentRun, ...]
    trailing_comments: tuple[CommentInfo, ...]

    def source_for(self, code_range: cst_metadata.CodeRange) -> str:
        """Return exact source text for a half-open LibCST code range.

        Args:
            code_range (cst_metadata.CodeRange): One-based source range to slice from the original module text.

        Returns:
            str: Exact source text covered by the range.
        """
        return source_text.source_for_range(code_range, source_lines=self.source_lines)


@dataclasses.dataclass(frozen=True)
class _CollectedComment:
    """Comment node and syntax-sensitivity facts collected during traversal."""

    node: cst.Comment
    syntax_sensitive: bool


class _CommentCollector(cst.CSTVisitor):
    """Collect comments from a LibCST module."""

    def __init__(self) -> None:
        """Initialize an empty comment collection."""
        super().__init__()
        self.comments: list[_CollectedComment] = []
        self._stack: list[cst.CSTNode] = []

    def on_visit(self, node: cst.CSTNode) -> bool:
        """Track ancestors while visiting all nodes."""
        self._stack.append(node)
        return super().on_visit(node)

    def on_leave(self, original_node: cst.CSTNode) -> None:
        """Restore the ancestor stack after a node is visited."""
        super().on_leave(original_node)
        self._stack.pop()

    def visit_Comment(self, node: cst.Comment) -> None:
        """Collect one comment node."""
        self.comments.append(_CollectedComment(node=node, syntax_sensitive=_is_syntax_sensitive_trailing_position(self._stack)))


@rule_registration.register_rule_category
class PCF(RuleCategoryBase[PCFCategoryData]):
    """Comment formatting rule category.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleCategoryMetadata(prefix="PCF", name="pydocformatter comment formatting", url="https://github.com/pallgeuer/pydocformatter")

    @classmethod
    def prepare(cls, context: RuleCategoryContext) -> PCFCategoryData:
        """Collect and classify comments for one module.

        Args:
            context (RuleCategoryContext): Parsed module, source lines, settings, and selected PCF rule classes.

        Returns:
            PCFCategoryData: Source lines, all comments, standalone runs, and trailing comments prepared for PCF rules.
        """
        del cls
        if "#" not in context.source:
            return PCFCategoryData(source_lines=context.source_lines, comments=(), standalone_runs=(), trailing_comments=())
        collector = _CommentCollector()
        context.module.visit(collector)
        source_lines_with_endings = context.source_lines
        source_lines = [line.rstrip("\r\n") for line in source_lines_with_endings]
        comments = tuple(
            sorted(
                (_comment_info(comment.node, positions=context.positions, source_lines=source_lines, syntax_sensitive=comment.syntax_sensitive) for comment in collector.comments),
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
        """Return prepared PCF data or raise for an invalid rule context.

        Args:
            context (RuleContext): Rule context whose category data should have been prepared by PCF.

        Returns:
            PCFCategoryData: Prepared comment data for the current module.

        Raises:
            TypeError: If the rule context does not contain PCF category data.
        """
        if not isinstance(context.category_data, PCFCategoryData):
            raise TypeError(f"{cls.meta.prefix} rules require PCFCategoryData")
        return context.category_data


def available_comment_width(indent: str, *, line_length: int, tab_width: int, prefix: str = "") -> int:
    """Return available content width after indentation and comment prefixes.

    Args:
        indent (str): Source indentation before the comment marker.
        line_length (int): Maximum configured output line width.
        tab_width (int): Tab stop width used when measuring indentation.
        prefix (str): Additional structural prefix, such as a task marker or list prefix, after `# `.

    Returns:
        int: Remaining display columns available for comment payload text.
    """
    return line_length - text_layout.display_width(f"{indent}# {prefix}", tab_width=tab_width)


def render_comment(content: str, *, indent: str = "", include_indent: bool = True) -> str:
    """Render one canonical comment line.

    Args:
        content (str): Comment payload after the canonical marker space.
        indent (str): Source indentation to include before the comment marker.
        include_indent (bool): Whether `indent` should be emitted in the returned line.

    Returns:
        str: Canonical standalone comment source without a line ending.
    """
    prefix = indent if include_indent else ""
    return f"{prefix}# {content}" if content else f"{prefix}#"


def render_inline_trailing_comment(code: str, content: str) -> str:
    """Return canonical inline trailing-comment source.

    Args:
        code (str): Source code before the trailing comment marker.
        content (str): Comment payload after the canonical marker space.

    Returns:
        str: Source line with two spaces before `#` and canonical marker spacing.
    """
    return f"{code}  # {content}" if content else f"{code}  #"


def planned_full_line_change(data: PCFCategoryData, comment: CommentInfo, replacement: str) -> rule_edits.PlannedSourceChange | None:
    """Return a full-line source change unless source already matches.

    Args:
        data (PCFCategoryData): Prepared PCF source lines used to compare existing source.
        comment (CommentInfo): Comment whose physical line should be replaced.
        replacement (str): Full replacement line without a line ending.

    Returns:
        rule_edits.PlannedSourceChange | None: Full-line replacement, or None when source already matches.
    """
    code_range = cst_metadata.CodeRange(start=cst_metadata.CodePosition(line=comment.range.start.line, column=0), end=comment.range.end)
    if data.source_for(code_range) == replacement:
        return None
    return rule_edits.PlannedSourceChange(edit=rule_edits.SourceEdit(range=code_range, replacement=replacement), line_numbers=(comment.range.start.line,), suppression_line_numbers=())


def _comment_info(node: cst.Comment, *, positions: Mapping[cst.CSTNode, cst_metadata.CodeRange], source_lines: list[str], syntax_sensitive: bool) -> CommentInfo:
    """Build source information for one comment node."""
    code_range = positions[node]
    source_line = source_lines[code_range.start.line - 1]
    line_prefix = source_line[: code_range.start.column]
    placement = CommentPlacement.STANDALONE if not line_prefix.strip(" \t\f") else CommentPlacement.TRAILING
    indent = line_prefix if placement == CommentPlacement.STANDALONE else line_prefix[: len(line_prefix) - len(line_prefix.lstrip(" \t\f"))]
    return CommentInfo(
        node=node,
        range=code_range,
        placement=placement,
        kind=_comment_kind(node.value, line=code_range.start.line, source_lines=source_lines),
        indent=indent,
        line_prefix=line_prefix,
        text=node.value,
        syntax_sensitive=syntax_sensitive if placement == CommentPlacement.TRAILING else False,
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


def _is_syntax_sensitive_trailing_position(stack: list[cst.CSTNode]) -> bool:
    """Return whether extracting a trailing comment would weaken syntax association."""
    if not stack:
        return False
    current = stack[-1]
    for parent_index in range(len(stack) - 2, -1, -1):
        parent = stack[parent_index]
        if isinstance(parent, cst.Decorator | cst.Arg | cst.ParenthesizedWhitespace):
            return True
        if isinstance(parent, cst.Match) and isinstance(current, cst.TrailingWhitespace):
            return True
        if isinstance(parent, cst.IndentedBlock | cst.SimpleStatementSuite) and isinstance(current, cst.TrailingWhitespace):
            return parent_index > 0
        current = parent
    return False


def _standalone_runs(comments: tuple[CommentInfo, ...]) -> tuple[StandaloneCommentRun, ...]:
    """Group physical standalone comments without applying formatting policy."""
    runs: list[StandaloneCommentRun] = []
    current: list[CommentInfo] = []

    def flush() -> None:
        if not current:
            return
        runs.append(StandaloneCommentRun(comments=tuple(current), range=cst_metadata.CodeRange(start=current[0].range.start, end=current[-1].range.end), indent=current[0].indent))
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
