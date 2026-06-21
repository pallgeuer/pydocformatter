from __future__ import annotations

import ast
import re
import textwrap

import pydocformatter.rules.definitions.PCF.PCF as PCF_definition
from pydocformatter.cli.settings_check import CheckSettings

DISABLED_CODE_RE = re.compile(r"\s*(?:if|for|while|def|class|try|except|print|return)\b")
LIST_RE = re.compile(r"^(?P<indent>[ \t]*)(?P<marker>(?:[-+*]|\d+[.)]))[ \t]+(?P<text>\S.*)$")
BLOCK_QUOTE_RE = re.compile(r"^(?P<prefix>(?:>[ \t]*)+)(?P<text>.*)$")
ATX_HEADING_RE = re.compile(r"^#{1,6}(?:[ \t]+|$)")
HEADING_ADORNMENT_RE = re.compile(r"^(?P<char>[=\-~`^\"'*+#:._])(?P=char){2,}[ \t]*$")
FENCE_RE = re.compile(r"^[ \t]*(?P<fence>`{3,}|~{3,})")
DIRECTIVE_RE = re.compile(r"^(?P<indent>[ \t]*)\.\.\s+[A-Za-z][\w-]*::(?:\s|$)")
MARKDOWN_TABLE_DELIMITER_RE = re.compile(r"^[ \t]*\|?(?:[ \t]*:?-{3,}:?[ \t]*\|)+[ \t]*:?-{3,}:?[ \t]*\|?[ \t]*$")
REST_GRID_BORDER_RE = re.compile(r"^[ \t]*\+(?:[-=]+\+)+[ \t]*$")
REST_SIMPLE_BORDER_RE = re.compile(r"^[ \t]*(?:={3,}|-{3,})(?:[ \t]+(?:={3,}|-{3,}))*[ \t]*$")
OPERATOR_LIKE_RE = re.compile(r"^(?:<=|>=|==|!=|->|=>|[-<>|&+*/%])(?:\s|$)")


def preserved_indices(run: PCF_definition.StandaloneCommentRun, *, settings: CheckSettings) -> set[int]:
    """Return physical line indices protected by enabled structure detectors."""
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
            match = FENCE_RE.match(bodies[index])
            if match is None:
                index += 1
                continue
            fence = match.group("fence")
            end = index + 1
            while end < len(bodies):
                closing = FENCE_RE.match(bodies[end])
                if closing is not None and closing.end() == len(bodies[end]) and closing.group("fence")[0] == fence[0] and len(closing.group("fence")) >= len(fence):
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
    """Return indices belonging to conservatively detected Markdown or reST tables."""
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
    """Return whether one line is a conservatively detected table border."""
    return MARKDOWN_TABLE_DELIMITER_RE.fullmatch(body) is not None or REST_GRID_BORDER_RE.fullmatch(body) is not None or REST_SIMPLE_BORDER_RE.fullmatch(body) is not None


def run_contains_code(run: PCF_definition.StandaloneCommentRun, *, preserved: set[int], settings: CheckSettings) -> bool:
    """Return whether enabled detectors classify any part of a run as code."""
    lines = code_detection_lines(run, settings=settings)
    candidates = tuple(lines[index] for index in range(len(lines)) if index not in preserved and lines[index].strip())
    if settings.comment_detect_code and any(line.startswith("    ") or DISABLED_CODE_RE.match(line) is not None for line in candidates):
        return True
    stripped_candidates = tuple(candidate.strip() for candidate in candidates)
    multiline_candidates = multiline_code_candidates(lines, preserved=preserved)
    if settings.comment_detect_statements and (any(is_python_statement(candidate) for candidate in stripped_candidates) or any(is_python_statement(candidate) for candidate in multiline_candidates)):
        return True
    if settings.comment_detect_expressions and any(is_nontrivial_expression(candidate) for candidate in stripped_candidates):
        return True
    return bool(settings.comment_detect_expressions and any(is_nontrivial_expression(candidate) for candidate in multiline_candidates))


def code_detection_lines(run: PCF_definition.StandaloneCommentRun, *, settings: CheckSettings) -> tuple[str, ...]:
    """Return semantic lines after stripping enabled structure prefixes."""
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


def is_python_statement(text: str) -> bool:
    """Return whether text parses as Python containing a non-expression statement."""
    try:
        module = ast.parse(text)
    except SyntaxError:
        return False
    return bool(module.body) and any(not isinstance(statement, ast.Expr) for statement in module.body)


def is_nontrivial_expression(text: str) -> bool:
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


def trailing_content_is_unsafe(content: str, *, settings: CheckSettings) -> bool:
    """Return whether content should not be reinterpreted as standalone comment text."""
    raw_body = content.rstrip()
    body = raw_body.strip()
    if not body:
        return False
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
    if settings.comment_preserve_code_fences and FENCE_RE.match(body) is not None:
        return True
    if settings.comment_preserve_directives and DIRECTIVE_RE.match(body) is not None:
        return True
    if settings.comment_preserve_tables and is_table_border(body):
        return True
    if settings.comment_detect_code and (raw_body.startswith("    ") or DISABLED_CODE_RE.match(body) is not None):
        return True
    if settings.comment_detect_statements and is_python_statement(body):
        return True
    return bool(settings.comment_detect_expressions and is_nontrivial_expression(body))
