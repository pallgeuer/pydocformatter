"""Comment structure detection helpers.

Attributes:
    DISABLED_CODE_RE (re.Pattern[str]): Conservative keyword detector for comment lines that likely contain disabled
        Python statements.
    LIST_RE (re.Pattern[str]): List-item parser used to preserve marker indentation while reflowing standalone comment
        prose.
    BLOCK_QUOTE_RE (re.Pattern[str]): Markdown block-quote parser that keeps nested quote prefixes attached to wrapped
        output lines.
    ATX_HEADING_RE (re.Pattern[str]): Markdown ATX heading detector used to keep standalone heading comments unchanged.
    HEADING_ADORNMENT_RE (re.Pattern[str]): Setext and reStructuredText adornment detector for preserving underlined or
        overlined headings.
    DIRECTIVE_RE (re.Pattern[str]): ReStructuredText directive opener detector used to preserve directive bodies by
        indentation.
    MARKDOWN_TABLE_DELIMITER_RE (re.Pattern[str]): Markdown pipe-table separator detector used as structural evidence
        for table preservation.
    REST_GRID_BORDER_RE (re.Pattern[str]): ReStructuredText grid-table border detector used to keep table rows aligned.
    REST_SIMPLE_BORDER_RE (re.Pattern[str]): ReStructuredText simple-table border detector used to preserve column
        layout.
    OPERATOR_LIKE_RE (re.Pattern[str]): Leading operator heuristic that keeps continuation-like trailing comments inline
        when extraction would be ambiguous.
"""

# Future imports
from __future__ import annotations

# Standard library imports
import re
import ast
import textwrap
import functools
import dataclasses
from typing import TYPE_CHECKING

# First-party imports
import pydocformatter.rules.definitions.PCF.PCF as PCF_definition
from pydocformatter.cli.settings_check import CommentTaskMarkerMode
from pydocformatter.rules.definition_helpers import inline_markup, text_layout


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.cli.settings_check import CheckSettings


DISABLED_CODE_RE = re.compile(r"\s*(?:if|for|while|def|class|try|except|print|return)\b")
LIST_RE = re.compile(r"^(?P<indent>[ \t]*)(?P<marker>(?:[-+*]|\d+[.)]))[ \t]+(?P<text>\S.*)$")
BLOCK_QUOTE_RE = re.compile(r"^(?P<prefix>(?:>[ \t]*)+)(?P<text>.*)$")
ATX_HEADING_RE = re.compile(r"^#{1,6}(?:[ \t]+|$)")
HEADING_ADORNMENT_RE = re.compile(r"^(?P<char>[=\-~`^\"'*+#:._])(?P=char){2,}[ \t]*$")
DIRECTIVE_RE = re.compile(r"^(?P<indent>[ \t]*)\.\.\s+[A-Za-z][\w-]*::(?:\s|$)")
MARKDOWN_TABLE_DELIMITER_RE = re.compile(r"^[ \t]*\|?(?:[ \t]*:?-{3,}:?[ \t]*\|)+[ \t]*:?-{3,}:?[ \t]*\|?[ \t]*$")
REST_GRID_BORDER_RE = re.compile(r"^[ \t]*\+(?:[-=]+\+)+[ \t]*$")
REST_SIMPLE_BORDER_RE = re.compile(r"^[ \t]*(?:={3,}|-{3,})(?:[ \t]+(?:={3,}|-{3,}))*[ \t]*$")
OPERATOR_LIKE_RE = re.compile(r"^(?:<=|>=|==|!=|->|=>|[-<>|&+*/%])(?:\s|$)")


@dataclasses.dataclass(frozen=True)
class TaskMarkerMatch:
    """Recognized task-marker comment content.

    Attributes:
        marker (str): Uppercase task label such as `TODO` without the trailing colon.
        text (str): Payload text following the task marker.
    """

    marker: str
    text: str


def preserved_indices(run: PCF_definition.StandaloneCommentRun, *, settings: CheckSettings) -> set[int]:
    """Return physical line indices protected by enabled structure detectors.

    Args:
        run (PCF_definition.StandaloneCommentRun): Consecutive standalone comments to classify.
        settings (CheckSettings): Comment-formatting settings controlling which structures are preserved.

    Returns:
        set[int]: Zero-based indices into `run.comments` that should not be prose-formatted or code-detected.
    """
    preserved: set[int] = set()
    bodies = tuple(comment.body.rstrip() for comment in run.comments)
    if settings.comment_preserve_headings:
        for index, body in enumerate(bodies):
            if ATX_HEADING_RE.match(body.lstrip()) is not None:
                preserved.add(index)
        adornments = {index: match.group("char") for index, body in enumerate(bodies) if (match := HEADING_ADORNMENT_RE.fullmatch(body.strip())) is not None}
        overline_adornments: set[int] = set()
        for index, char in adornments.items():
            if index + 2 < len(bodies) and adornments.get(index + 2) == char and index + 1 not in adornments:
                preserved.update((index, index + 1, index + 2))
                overline_adornments.update((index, index + 2))
        for index in adornments.keys() - overline_adornments:
            if index > 0 and index - 1 not in adornments:
                preserved.update((index - 1, index))
    if settings.comment_preserve_doctests:
        for index, body in enumerate(bodies):
            if body.lstrip().startswith(">>>"):
                preserved.update(range(index, len(bodies)))
                break
    if settings.comment_preserve_code_fences:
        index = 0
        while index < len(bodies):
            match = inline_markup.FENCE_RE.match(bodies[index])
            if match is None:
                index += 1
                continue
            fence = match.group("fence")
            end = index + 1
            while end < len(bodies):
                closing = inline_markup.FENCE_RE.match(bodies[end])
                if closing is not None and closing.group("fence")[0] == fence[0] and len(closing.group("fence")) >= len(fence) and not closing.group("info").strip():
                    end += 1
                    break
                end += 1
            preserved.update(range(index, end))
            index = end
    if settings.comment_preserve_tables:
        preserved.update(table_indices(bodies))
    if settings.comment_preserve_directives:
        index = 0
        while index < len(bodies):
            match = DIRECTIVE_RE.match(bodies[index])
            if match is None:
                index += 1
                continue
            base_indent = len(match.group("indent").expandtabs(settings.indent_width))
            preserved.add(index)
            index += 1
            while index < len(bodies):
                body = bodies[index]
                content_indent = len(body.expandtabs(settings.indent_width)) - len(body.lstrip(" \t").expandtabs(settings.indent_width))
                if not body.strip() or content_indent <= base_indent:
                    break
                preserved.add(index)
                index += 1
    return preserved


def table_indices(bodies: tuple[str, ...]) -> set[int]:
    """Return indices belonging to conservatively detected Markdown or reST tables.

    Args:
        bodies (tuple[str, ...]): Comment body text for one standalone run, without syntactic comment markers.

    Returns:
        set[int]: Zero-based indices of lines that appear to participate in Markdown or reStructuredText tables.
    """
    indices: set[int] = set()
    for index, body in enumerate(bodies):
        if MARKDOWN_TABLE_DELIMITER_RE.fullmatch(body) is not None:
            start = index - 1 if index > 0 and "|" in bodies[index - 1] else index
            end = index + 1
            while end < len(bodies) and "|" in bodies[end]:
                end += 1
            indices.update(range(start, end))
        if REST_GRID_BORDER_RE.fullmatch(body) is not None:
            start = index
            while start > 0 and ("|" in bodies[start - 1] or REST_GRID_BORDER_RE.fullmatch(bodies[start - 1]) is not None):
                start -= 1
            end = index + 1
            while end < len(bodies) and ("|" in bodies[end] or REST_GRID_BORDER_RE.fullmatch(bodies[end]) is not None):
                end += 1
            indices.update(range(start, end))
        if REST_SIMPLE_BORDER_RE.fullmatch(body) is not None:
            if index > 0:
                indices.add(index - 1)
            indices.add(index)
            if index + 1 < len(bodies):
                indices.add(index + 1)
    return indices


def is_table_border(body: str) -> bool:
    """Return whether one line is a conservatively detected table border.

    Args:
        body (str): Comment body text without the syntactic comment marker.

    Returns:
        bool: Whether the body matches a Markdown or reStructuredText table delimiter.
    """
    return MARKDOWN_TABLE_DELIMITER_RE.fullmatch(body) is not None or REST_GRID_BORDER_RE.fullmatch(body) is not None or REST_SIMPLE_BORDER_RE.fullmatch(body) is not None


def run_contains_code(run: PCF_definition.StandaloneCommentRun, *, preserved: set[int], settings: CheckSettings, ignore_task_markers: bool = False) -> bool:
    """Return whether enabled detectors classify any part of a run as code.

    Args:
        run (PCF_definition.StandaloneCommentRun): Consecutive standalone comments to inspect.
        preserved (set[int]): Comment indices already protected by structure detectors.
        settings (CheckSettings): Code-detection settings controlling statement, expression, and heuristic checks.
        ignore_task_markers (bool): Whether recognized task-marker units should be skipped by run-level code detection.

    Returns:
        bool: Whether enabled detectors classify any unpreserved candidate line or multiline segment as code-like.
    """
    lines = code_detection_lines(run, settings=settings)
    ignored = task_marker_unit_indices(run, preserved=preserved, settings=settings) if ignore_task_markers and task_markers_enabled(settings) else set()
    candidates = tuple(lines[index] for index in range(len(lines)) if index not in preserved and index not in ignored and lines[index].strip())
    if any(_text_matches_disabled_code_heuristic(line, settings=settings) for line in candidates):
        return True
    stripped_candidates = tuple(candidate.strip() for candidate in candidates)
    multiline_candidates = multiline_code_candidates(lines, preserved=preserved | ignored)
    if any(_text_is_code_like_statement(candidate, settings=settings) for candidate in stripped_candidates) or any(
        _text_is_code_like_statement(candidate, settings=settings) for candidate in multiline_candidates
    ):
        return True
    if any(_text_is_code_like_expression(candidate, settings=settings) for candidate in stripped_candidates):
        return True
    return any(_text_is_code_like_expression(candidate, settings=settings) for candidate in multiline_candidates)


def code_detection_lines(run: PCF_definition.StandaloneCommentRun, *, settings: CheckSettings) -> tuple[str, ...]:
    """Return semantic lines after stripping enabled structure prefixes.

    Args:
        run (PCF_definition.StandaloneCommentRun): Consecutive standalone comments to normalize for code detection.
        settings (CheckSettings): Settings controlling list-item and block-quote prefix handling.

    Returns:
        tuple[str, ...]: Candidate text lines aligned with `run.comments`.
    """
    lines: list[str] = []
    list_item_active = False
    for comment in run.comments:
        text = comment.raw_content.rstrip()
        body = comment.body.rstrip()
        if settings.comment_format_list_items:
            list_match = LIST_RE.match(body)
            if list_match is not None:
                text = list_match.group("text")
                list_item_active = True
            elif list_item_active and body[:1].isspace():
                text = body.strip()
            else:
                list_item_active = False
        if settings.comment_format_block_quotes:
            quote_match = BLOCK_QUOTE_RE.match(body)
            if quote_match is not None:
                text = quote_match.group("text")
        lines.append(text)
    return tuple(lines)


def multiline_code_candidates(lines: tuple[str, ...], *, preserved: set[int]) -> tuple[str, ...]:
    """Return dedented candidates from contiguous non-preserved line segments.

    Args:
        lines (tuple[str, ...]): Code-detection text lines aligned with a standalone run.
        preserved (set[int]): Indices that split and exclude protected structures.

    Returns:
        tuple[str, ...]: Non-empty dedented multiline candidates for AST-based code detection.
    """
    candidates: list[str] = []
    current: list[str] = []
    for index, line in enumerate(lines):
        if index in preserved:
            if current:
                candidates.append(textwrap.dedent("\n".join(current)).strip())
                current.clear()
            continue
        current.append(line)
    if current:
        candidates.append(textwrap.dedent("\n".join(current)).strip())
    return tuple(candidate for candidate in candidates if candidate)


def is_python_statement(text: str) -> bool:
    """Return whether text parses as Python containing a non-expression statement.

    Args:
        text (str): Candidate comment text to parse as a Python module.

    Returns:
        bool: Whether parsing succeeds and at least one top-level statement is not a bare expression.
    """
    try:
        module = ast.parse(text)
    except SyntaxError:
        return False
    return bool(module.body) and any(not isinstance(statement, ast.Expr) for statement in module.body)


def is_nontrivial_expression(text: str) -> bool:
    """Return whether text parses as a nontrivial Python expression.

    Args:
        text (str): Candidate comment text to parse in expression mode.

    Returns:
        bool: Whether parsing succeeds as an expression more complex than a bare name or scalar constant.
    """
    try:
        expression = ast.parse(text, mode="eval").body
    except SyntaxError:
        return False
    return isinstance(
        expression,
        (
            ast.Attribute,
            ast.Subscript,
            ast.Call,
            ast.BinOp,
            ast.BoolOp,
            ast.Compare,
            ast.UnaryOp,
            ast.IfExp,
            ast.Lambda,
            ast.List,
            ast.Tuple,
            ast.Set,
            ast.Dict,
            ast.ListComp,
            ast.SetComp,
            ast.DictComp,
            ast.GeneratorExp,
            ast.Await,
            ast.Yield,
            ast.YieldFrom,
            ast.NamedExpr,
        ),
    )


def task_markers_enabled(settings: CheckSettings) -> bool:
    """Return whether configured task marker recognition is enabled.

    Args:
        settings (CheckSettings): Comment settings defining task marker mode and labels.

    Returns:
        bool: Whether task marker matching should run.
    """
    return settings.comment_task_marker_mode != CommentTaskMarkerMode.NONE and bool(settings.comment_task_markers)


@functools.cache
def _task_marker_re(markers: tuple[str, ...]) -> re.Pattern[str]:
    """Return the cached task-marker parser for one marker tuple."""
    marker_pattern = "|".join(re.escape(marker) for marker in markers)
    return re.compile(rf"^(?P<marker>(?:{marker_pattern})):[ \t]*(?P<text>.*)$")


def task_marker_match(body: str, *, settings: CheckSettings) -> TaskMarkerMatch | None:
    """Return a recognized task-marker match for comment body text.

    Args:
        body (str): Comment body text without the syntactic comment marker.
        settings (CheckSettings): Settings defining recognized task marker labels and treatment.

    Returns:
        TaskMarkerMatch | None: Parsed task marker and payload, or None when the body is not a supported marker.
    """
    if not task_markers_enabled(settings):
        return None
    match = _task_marker_re(settings.comment_task_markers).match(body.rstrip())
    if match is None:
        return None
    return TaskMarkerMatch(marker=match.group("marker"), text=match.group("text").strip())


def task_marker_continuation_text(body: str, *, marker: str) -> str | None:
    """Return text from an exact task-marker continuation line.

    Args:
        body (str): Candidate continuation body without the syntactic comment marker.
        marker (str): Task marker whose hanging indentation width should be matched.

    Returns:
        str | None: Continuation payload text, empty string for a blank continuation, or None when indentation does not
            match.
    """
    prefix = " " * len(f"{marker}: ")
    if not body.startswith(prefix):
        return None
    text = body[len(prefix) :]
    if text[:1].isspace():
        return None
    return text.strip() if text else ""


def task_marker_unit_indices(run: PCF_definition.StandaloneCommentRun, *, preserved: set[int], settings: CheckSettings) -> set[int]:
    """Return indices belonging to recognized task-marker units.

    Args:
        run (PCF_definition.StandaloneCommentRun): Consecutive standalone comments to scan.
        preserved (set[int]): Structure-protected indices that cannot belong to task-marker units.
        settings (CheckSettings): Settings defining recognized task marker labels and treatment.

    Returns:
        set[int]: Zero-based indices covered by task-marker heads and exact hanging continuation lines.
    """
    indices: set[int] = set()
    index = 0
    while index < len(run.comments):
        if index in preserved:
            index += 1
            continue
        match = task_marker_match(run.comments[index].body.rstrip(), settings=settings)
        if match is None:
            index += 1
            continue
        indices.add(index)
        index += 1
        while index < len(run.comments) and index not in preserved and task_marker_continuation_text(run.comments[index].body.rstrip(), marker=match.marker) is not None:
            indices.add(index)
            index += 1
    return indices


def task_marker_body_is_code_like(text: str, *, settings: CheckSettings) -> bool:
    """Return whether task-marker payload text should be protected as code-like.

    Args:
        text (str): Task-marker payload line to inspect.
        settings (CheckSettings): Code-detection settings controlling the active heuristics.

    Returns:
        bool: Whether the task-marker payload should be normalized but not wrapped as prose.
    """
    body = text.strip()
    if not body:
        return False
    return _text_matches_disabled_code_heuristic(body, settings=settings) or _text_is_code_like_statement(body, settings=settings) or _text_is_code_like_expression(body, settings=settings)


def task_marker_texts_are_code_like(texts: tuple[str, ...], *, settings: CheckSettings) -> bool:
    """Return whether any task-marker payload line should be protected as code-like.

    Args:
        texts (tuple[str, ...]): Task-marker payload and continuation payload lines.
        settings (CheckSettings): Code-detection settings controlling the active heuristics.

    Returns:
        bool: Whether any payload line should make the whole task-marker unit avoid prose wrapping.
    """
    return any(task_marker_body_is_code_like(text, settings=settings) for text in texts)


def _normalize_task_marker_lines(marker: str, texts: tuple[str, ...]) -> tuple[str, ...]:
    """Return task-marker lines normalized without prose wrapping."""
    prefix = f"{marker}: "
    lines = [prefix.rstrip() if not texts or not texts[0].strip() else prefix + texts[0].strip()]
    lines.extend(" " * len(prefix) + text.strip() if text.strip() else "" for text in texts[1:])
    return tuple(lines)


def format_task_marker_lines(marker: str, texts: tuple[str, ...], *, indent: str, settings: CheckSettings) -> tuple[str, ...]:
    """Return task-marker comment content lines with hanging indentation.

    Args:
        marker (str): Task label without the trailing colon.
        texts (tuple[str, ...]): Payload and continuation payload lines to normalize.
        indent (str): Source indentation before the syntactic comment marker.
        settings (CheckSettings): Wrapping, indentation, URL, and code-detection settings.

    Returns:
        tuple[str, ...]: Comment body lines after task-marker formatting.
    """
    prefix = f"{marker}: "
    if settings.comment_task_marker_mode == CommentTaskMarkerMode.NO_WRAP:
        return _normalize_task_marker_lines(marker, texts)
    body = " ".join(text for text in texts if text).strip()
    if not body:
        return (marker + ":",)
    if task_marker_texts_are_code_like(texts, settings=settings):
        return _normalize_task_marker_lines(marker, texts)
    width = PCF_definition.available_comment_width(indent, line_length=settings.line_length, tab_width=settings.indent_width)
    return text_layout.wrap_text(body, width=width, initial_indent=prefix, subsequent_indent=" " * len(prefix), tab_width=settings.indent_width, url_aware=settings.url_aware_wrapping)


def trailing_content_is_unsafe(content: str, *, settings: CheckSettings) -> bool:
    """Return whether content should not be reinterpreted as standalone comment text.

    Args:
        content (str): Raw trailing-comment content after the syntactic comment marker.
        settings (CheckSettings): Comment structure and code-detection settings used for content-aware extraction.

    Returns:
        bool: Whether extraction could change the meaning of code-like, structural, directive, or operator-like content.
    """
    raw_body = content.rstrip()
    body = raw_body.strip()
    if not body:
        return False
    if (task_marker := task_marker_match(body, settings=settings)) is not None:
        # Treat the marker payload as a task annotation, not as standalone list or operator-like content.
        return task_marker_body_is_code_like(task_marker.text, settings=settings)
    if OPERATOR_LIKE_RE.match(body) is not None:
        return True
    if settings.comment_format_list_items and LIST_RE.match(body) is not None:
        return True
    if settings.comment_format_block_quotes and BLOCK_QUOTE_RE.match(body) is not None:
        return True
    if settings.comment_preserve_headings and (ATX_HEADING_RE.match(body.lstrip()) is not None or HEADING_ADORNMENT_RE.fullmatch(body.strip()) is not None):
        return True
    if settings.comment_preserve_doctests and body.lstrip().startswith(">>>"):
        return True
    if settings.comment_preserve_code_fences and inline_markup.FENCE_RE.match(body) is not None:
        return True
    if settings.comment_preserve_directives and DIRECTIVE_RE.match(body) is not None:
        return True
    if settings.comment_preserve_tables and is_table_border(body):
        return True
    if _text_matches_disabled_code_heuristic(raw_body, settings=settings) or _text_matches_disabled_code_heuristic(body, settings=settings):
        return True
    if _text_is_code_like_statement(body, settings=settings):
        return True
    return _text_is_code_like_expression(body, settings=settings)


def _text_matches_disabled_code_heuristic(text: str, *, settings: CheckSettings) -> bool:
    """Return whether text matches the enabled disabled-code heuristic."""
    return bool(settings.comment_detect_code and (text.startswith("    ") or DISABLED_CODE_RE.match(text.strip()) is not None))


def _text_is_code_like_statement(text: str, *, settings: CheckSettings) -> bool:
    """Return whether text matches enabled statement detection."""
    return bool(settings.comment_detect_statements and is_python_statement(text.strip()))


def _text_is_code_like_expression(text: str, *, settings: CheckSettings) -> bool:
    """Return whether text matches enabled expression detection."""
    return bool(settings.comment_detect_expressions and is_nontrivial_expression(text.strip()))
