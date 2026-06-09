from __future__ import annotations

import ast
import dataclasses
import re
import textwrap

import libcst.metadata as cst_metadata

import pydocformatter.rules.collection as rule_collection
import pydocformatter.rules.definitions.PCF.PCF as PCF_definition
import pydocformatter.rules.edits as rule_edits
from pydocformatter.cli.settings_check import CheckSettings
from pydocformatter.rules.definition import RuleBase, RuleContext, RuleFixResult
from pydocformatter.rules.models import FixAvailability, RuleCode, RuleFinding, RuleMetadata

_DISABLED_CODE_RE = re.compile(r"\s*(?:if|for|while|def|class|try|except|print|return)\b")
_LIST_RE = re.compile(r"^(?P<indent>[ \t]*)(?P<marker>(?:[-+*]|\d+[.)]))[ \t]+(?P<text>\S.*)$")
_BLOCK_QUOTE_RE = re.compile(r"^(?P<prefix>(?:>[ \t]*)+)(?P<text>.*)$")
_ATX_HEADING_RE = re.compile(r"^#{1,6}(?:[ \t]+|$)")
_HEADING_ADORNMENT_RE = re.compile(r"^(?P<char>[=\-~`^\"'*+#:._])(?P=char){2,}[ \t]*$")
_FENCE_RE = re.compile(r"^[ \t]*(?P<fence>`{3,}|~{3,})")
_DIRECTIVE_RE = re.compile(r"^(?P<indent>[ \t]*)\.\.\s+[A-Za-z][\w-]*::(?:\s|$)")
_MARKDOWN_TABLE_DELIMITER_RE = re.compile(r"^[ \t]*\|?(?:[ \t]*:?-{3,}:?[ \t]*\|)+[ \t]*:?-{3,}:?[ \t]*\|?[ \t]*$")
_REST_GRID_BORDER_RE = re.compile(r"^[ \t]*\+(?:[-=]+\+)+[ \t]*$")
_REST_SIMPLE_BORDER_RE = re.compile(r"^[ \t]*(?:={3,}|-{3,})(?:[ \t]+(?:={3,}|-{3,}))*[ \t]*$")


@dataclasses.dataclass(frozen=True)
class _PlannedChange:
    """One standalone comment replacement and its original source lines."""

    edit: rule_edits.SourceEdit
    line_numbers: tuple[int, ...]


@rule_collection.register_rule_to(PCF_definition.PCF)
class PCF001StandaloneCommentFormatting(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PCF001"),
        name="standalone-comment-formatting",
        message="Standalone comment needs formatting",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="0.3.0",
    )

    @classmethod
    def check(cls, context: RuleContext) -> tuple[RuleFinding, ...]:
        """Return standalone comment formatting findings."""
        return tuple(RuleFinding(rule=cls.meta, line_numbers=change.line_numbers) for change in _planned_changes(context))

    @classmethod
    def fix(cls, context: RuleContext) -> RuleFixResult:
        """Apply standalone comment formatting fixes."""
        changes = _planned_changes(context)
        if not changes:
            return RuleFixResult(module=context.module)
        module = rule_edits.apply_source_edits(context.module, tuple(change.edit for change in changes))
        findings = tuple(RuleFinding(rule=cls.meta, line_numbers=change.line_numbers) for change in changes)
        return RuleFixResult(module=module, fixed_findings=findings)


def _planned_changes(context: RuleContext) -> tuple[_PlannedChange, ...]:
    """Return all standalone comment changes for the current source."""
    data = PCF_definition.PCF.require_data(context)
    changes: list[_PlannedChange] = []
    for run in data.standalone_runs:
        preserved = _preserved_indices(run, settings=context.settings)
        if _run_contains_code(run, preserved=preserved, settings=context.settings):
            continue
        index = 0
        while index < len(run.comments):
            if index in preserved:
                index += 1
                continue
            list_match = _LIST_RE.match(run.comments[index].body.rstrip()) if context.settings.comment_format_list_items else None
            quote_match = _BLOCK_QUOTE_RE.match(run.comments[index].body.rstrip()) if context.settings.comment_format_block_quotes else None
            if list_match is not None:
                end, output_lines = _format_list_item(run, index, preserved=preserved, settings=context.settings)
            elif quote_match is not None:
                end, output_lines = _format_block_quote(run, index, preserved=preserved, settings=context.settings)
            elif context.settings.comment_join_standalone_lines:
                end = _ordinary_paragraph_end(run, index, preserved=preserved, settings=context.settings)
                content = " ".join(comment.content for comment in run.comments[index:end])
                output_lines = _wrap_plain(content, indent=run.indent, settings=context.settings)
            else:
                end = index + 1
                output_lines = _wrap_plain(run.comments[index].content, indent=run.indent, settings=context.settings)
            change = _change_for_unit(data, run.comments[index:end], output_lines=output_lines, indent=run.indent, line_ending=context.line_ending)
            if change is not None:
                changes.append(change)
            index = end
    return tuple(changes)


def _change_for_unit(
    data: PCF_definition.PCFCategoryData,
    comments: tuple[PCF_definition.CommentInfo, ...],
    *,
    output_lines: tuple[str, ...],
    indent: str,
    line_ending: str,
) -> _PlannedChange | None:
    """Build a planned replacement when generated unit source differs."""
    code_range = cst_metadata.CodeRange(start=comments[0].range.start, end=comments[-1].range.end)
    rendered = [PCF_definition.render_comment(output_lines[0], include_indent=False)]
    rendered.extend(PCF_definition.render_comment(line, indent=indent) for line in output_lines[1:])
    replacement = line_ending.join(rendered)
    if data.source_for(code_range) == replacement:
        return None
    return _PlannedChange(
        edit=rule_edits.SourceEdit(range=code_range, replacement=replacement),
        line_numbers=tuple(comment.range.start.line for comment in comments),
    )


def _wrap_plain(content: str, *, indent: str, settings: CheckSettings) -> tuple[str, ...]:
    """Wrap ordinary normalized comment content."""
    width = PCF_definition.available_comment_width(indent, line_length=settings.line_length, tab_width=settings.indent_width)
    return PCF_definition.wrap_comment_text(content, width=width)


def _format_list_item(
    run: PCF_definition.StandaloneCommentRun,
    index: int,
    *,
    preserved: set[int],
    settings: CheckSettings,
) -> tuple[int, tuple[str, ...]]:
    """Return the extent and hanging-indented output of one list item."""
    match = _LIST_RE.match(run.comments[index].body.rstrip())
    if match is None:
        raise AssertionError("List formatting requires a matching first line")
    prefix = _expanded_structure_prefix(f"{match.group('indent')}{match.group('marker')} ", indent=run.indent, tab_width=settings.indent_width)
    texts = [match.group("text").strip()]
    end = index + 1
    while end < len(run.comments) and end not in preserved:
        body = run.comments[end].body.rstrip()
        if _LIST_RE.match(body) is not None or _BLOCK_QUOTE_RE.match(body) is not None:
            break
        if not body[:1].isspace():
            break
        texts.append(body.strip())
        end += 1
    width = settings.line_length - PCF_definition.display_width(f"{run.indent}# ", tab_width=settings.indent_width)
    subsequent = " " * len(prefix)
    lines = PCF_definition.wrap_comment_text(" ".join(texts), width=width, initial_indent=prefix, subsequent_indent=subsequent)
    return end, lines


def _format_block_quote(
    run: PCF_definition.StandaloneCommentRun,
    index: int,
    *,
    preserved: set[int],
    settings: CheckSettings,
) -> tuple[int, tuple[str, ...]]:
    """Return the extent and prefix-preserving output of one block quote."""
    match = _BLOCK_QUOTE_RE.match(run.comments[index].body.rstrip())
    if match is None:
        raise AssertionError("Block quote formatting requires a matching first line")
    prefix = _expanded_structure_prefix(match.group("prefix"), indent=run.indent, tab_width=settings.indent_width)
    texts = [match.group("text").strip()]
    end = index + 1
    while end < len(run.comments) and end not in preserved:
        next_match = _BLOCK_QUOTE_RE.match(run.comments[end].body.rstrip())
        if next_match is None or _expanded_structure_prefix(next_match.group("prefix"), indent=run.indent, tab_width=settings.indent_width) != prefix:
            break
        texts.append(next_match.group("text").strip())
        end += 1
    width = settings.line_length - PCF_definition.display_width(f"{run.indent}# ", tab_width=settings.indent_width)
    lines = PCF_definition.wrap_comment_text(" ".join(texts), width=width, initial_indent=prefix, subsequent_indent=prefix)
    return end, lines


def _expanded_structure_prefix(prefix: str, *, indent: str, tab_width: int) -> str:
    """Expand tabs in a generated structure prefix at its source column."""
    base_width = PCF_definition.display_width(f"{indent}# ", tab_width=tab_width)
    return (" " * base_width + prefix).expandtabs(tab_width)[base_width:]


def _ordinary_paragraph_end(run: PCF_definition.StandaloneCommentRun, index: int, *, preserved: set[int], settings: CheckSettings) -> int:
    """Return the exclusive end of one ordinary prose paragraph."""
    end = index + 1
    while end < len(run.comments) and end not in preserved:
        body = run.comments[end].body.rstrip()
        if settings.comment_format_list_items and _LIST_RE.match(body) is not None:
            break
        if settings.comment_format_block_quotes and _BLOCK_QUOTE_RE.match(body) is not None:
            break
        end += 1
    return end


def _preserved_indices(run: PCF_definition.StandaloneCommentRun, *, settings: CheckSettings) -> set[int]:
    """Return physical line indices protected by enabled structure detectors."""
    preserved: set[int] = set()
    bodies = tuple(comment.body.rstrip() for comment in run.comments)
    if settings.comment_preserve_headings:
        for index, body in enumerate(bodies):
            if _ATX_HEADING_RE.match(body.lstrip()) is not None:
                preserved.add(index)
        adornments = {index: match.group("char") for index, body in enumerate(bodies) if (match := _HEADING_ADORNMENT_RE.fullmatch(body.strip())) is not None}
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
            match = _FENCE_RE.match(bodies[index])
            if match is None:
                index += 1
                continue
            fence = match.group("fence")
            end = index + 1
            while end < len(bodies):
                closing = _FENCE_RE.match(bodies[end])
                if closing is not None and closing.end() == len(bodies[end]) and closing.group("fence")[0] == fence[0] and len(closing.group("fence")) >= len(fence):
                    end += 1
                    break
                end += 1
            preserved.update(range(index, end))
            index = end
    if settings.comment_preserve_tables:
        preserved.update(_table_indices(bodies))
    if settings.comment_preserve_directives:
        index = 0
        while index < len(bodies):
            match = _DIRECTIVE_RE.match(bodies[index])
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


def _table_indices(bodies: tuple[str, ...]) -> set[int]:
    """Return indices belonging to conservatively detected Markdown or reST tables."""
    indices: set[int] = set()
    for index, body in enumerate(bodies):
        if _MARKDOWN_TABLE_DELIMITER_RE.fullmatch(body) is not None:
            start = index - 1 if index > 0 and "|" in bodies[index - 1] else index
            end = index + 1
            while end < len(bodies) and "|" in bodies[end]:
                end += 1
            indices.update(range(start, end))
        if _REST_GRID_BORDER_RE.fullmatch(body) is not None:
            start = index
            while start > 0 and ("|" in bodies[start - 1] or _REST_GRID_BORDER_RE.fullmatch(bodies[start - 1]) is not None):
                start -= 1
            end = index + 1
            while end < len(bodies) and ("|" in bodies[end] or _REST_GRID_BORDER_RE.fullmatch(bodies[end]) is not None):
                end += 1
            indices.update(range(start, end))
        if _REST_SIMPLE_BORDER_RE.fullmatch(body) is not None:
            if index > 0:
                indices.add(index - 1)
            indices.add(index)
            if index + 1 < len(bodies):
                indices.add(index + 1)
    return indices


def _run_contains_code(run: PCF_definition.StandaloneCommentRun, *, preserved: set[int], settings: CheckSettings) -> bool:
    """Return whether enabled detectors classify any part of a run as code."""
    lines = _code_detection_lines(run, settings=settings)
    candidates = tuple(lines[index] for index in range(len(lines)) if index not in preserved and lines[index].strip())
    if settings.comment_detect_code and any(line.startswith("    ") or _DISABLED_CODE_RE.match(line) is not None for line in candidates):
        return True
    stripped_candidates = tuple(candidate.strip() for candidate in candidates)
    multiline_candidates = _multiline_code_candidates(lines, preserved=preserved)
    if settings.comment_detect_statements and (any(_is_python_statement(candidate) for candidate in stripped_candidates) or any(_is_python_statement(candidate) for candidate in multiline_candidates)):
        return True
    if settings.comment_detect_expressions and any(_is_nontrivial_expression(candidate) for candidate in stripped_candidates):
        return True
    return bool(settings.comment_detect_expressions and any(_is_nontrivial_expression(candidate) for candidate in multiline_candidates))


def _code_detection_lines(run: PCF_definition.StandaloneCommentRun, *, settings: CheckSettings) -> tuple[str, ...]:
    """Return semantic lines after stripping enabled structure prefixes."""
    lines: list[str] = []
    list_item_active = False
    for comment in run.comments:
        text = comment.raw_content.rstrip()
        body = comment.body.rstrip()
        if settings.comment_format_list_items:
            list_match = _LIST_RE.match(body)
            if list_match is not None:
                text = list_match.group("text")
                list_item_active = True
            elif list_item_active and body[:1].isspace():
                text = body.strip()
            else:
                list_item_active = False
        if settings.comment_format_block_quotes:
            quote_match = _BLOCK_QUOTE_RE.match(body)
            if quote_match is not None:
                text = quote_match.group("text")
        lines.append(text)
    return tuple(lines)


def _multiline_code_candidates(lines: tuple[str, ...], *, preserved: set[int]) -> tuple[str, ...]:
    """Return dedented candidates from contiguous non-preserved line segments."""
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


def _is_python_statement(text: str) -> bool:
    """Return whether text parses as Python containing a non-expression statement."""
    try:
        module = ast.parse(text)
    except SyntaxError:
        return False
    return bool(module.body) and any(not isinstance(statement, ast.Expr) for statement in module.body)


def _is_nontrivial_expression(text: str) -> bool:
    """Return whether text parses as a nontrivial Python expression."""
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
