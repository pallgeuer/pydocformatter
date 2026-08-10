"""Conservative parsing helpers for annotation-like type expressions.

Attributes:
    TypeAliasMap (TypeAlias): Unshadowed source names mapped to absolute import-qualified names for type comparison.
"""

# Future imports
from __future__ import annotations

# Standard library imports
import io
import ast
import keyword
import tokenize
import dataclasses
from typing import TYPE_CHECKING

# First-party imports
from pydocformatter.rules.definition_helpers import ascii_whitespace, module_bindings, unicode_safety


if TYPE_CHECKING:
    # Third-party imports
    import libcst as cst


TypeAliasMap = module_bindings.TypeAliasMap


@dataclasses.dataclass
class _TypeContext:
    """One non-recursive conservative type-expression parsing context."""

    kind: str
    allow_sequence: bool
    opened_as_trailer: bool = False
    expect_value: bool = True
    expect_attribute: bool = False
    saw_value: bool = False
    has_comma: bool = False
    union_active: bool = False
    value_is_sequence: bool = False


@dataclasses.dataclass(frozen=True)
class _ValidatedTypeTokens:
    """Validated significant tokens and normalization facts for a type expression."""

    tokens: tuple[tokenize.TokenInfo, ...]
    has_grouping: bool


def module_type_aliases(module: cst.Module) -> TypeAliasMap:
    """Return conservative absolute import aliases usable for type expression comparison.

    Args:
        module (cst.Module): Parsed source module whose top-level imports should be inspected.

    Returns:
        TypeAliasMap: Mapping from unshadowed source names to absolute qualified import names.
    """
    return module_bindings.module_type_aliases(module)


def parse_type_like_expr(text: str, *, aliases: TypeAliasMap | None = None) -> ast.Expression | None:
    """Parse text as a conservative type-like Python expression.

    Args:
        text (str): Candidate type expression text from a docstring or annotation.
        aliases (TypeAliasMap | None): Optional unshadowed import aliases to normalize before comparison.

    Returns:
        ast.Expression | None: Parsed expression when the text is syntactically valid and type-like, or None.
    """
    stripped = text.strip()
    if not stripped or "#" in stripped:
        return None
    parsed = _parse_type_like_ast(stripped)
    if parsed is None:
        return None
    if aliases:
        parsed = ast.Expression(body=_normalize_type_aliases(parsed.body, aliases))
    return parsed


def is_type_like_text(text: str) -> bool:
    """Return whether text follows the conservative type-expression grammar.

    Args:
        text (str): Candidate type expression text.

    Returns:
        bool: Whether the token stream is structurally type-like without invoking the Python parser.
    """
    stripped = text.strip()
    if stripped == "None":
        return True
    parts = stripped.split(".")
    if parts and all(part.isidentifier() and not keyword.iskeyword(part) for part in parts):
        return True
    return _validated_type_tokens(stripped) is not None


def is_quoted_type_like_text(text: str) -> bool:
    """Return whether text is one quoted conservative forward reference.

    Args:
        text (str): Candidate quoted forward-reference expression.

    Returns:
        bool: Whether text is one string literal whose value is type-like.
    """
    stripped = text.strip()
    try:
        tokens = tuple(
            token_info for token_info in tokenize.generate_tokens(io.StringIO(stripped).readline) if token_info.type not in {tokenize.ENCODING, tokenize.NL, tokenize.NEWLINE, tokenize.ENDMARKER}
        )
    except (IndentationError, SyntaxError, tokenize.TokenError):
        return False
    if len(tokens) != 1 or tokens[0].type != tokenize.STRING:
        return False
    try:
        value = ast.literal_eval(tokens[0].string)
    except (SyntaxError, ValueError):
        return False
    return isinstance(value, str) and is_type_like_text(value)


def normalized_type_like_text(text: str) -> str | None:
    """Return AST-stable normalized spacing for a type-like expression.

    Args:
        text (str): Candidate type expression text whose internal spacing may need normalization.

    Returns:
        str | None: Normalized type text when spacing can be changed safely, or None when the text should be left
            unchanged.
    """
    if unicode_safety.has_nonstandard_whitespace_or_control(text):
        return None
    stripped = text.strip(ascii_whitespace.SPACE_AND_TAB)
    validated = _validated_type_tokens(stripped)
    if validated is None or validated.has_grouping:
        return None
    parsed = _parse_type_like_ast(stripped)
    if parsed is None:
        return None
    normalized = _normalized_token_text(validated.tokens)
    if normalized == stripped:
        return None
    if without_whitespace(normalized) != without_whitespace(stripped):
        return None
    reparsed = _parse_type_like_ast(normalized)
    if reparsed is None or ast_dump(parsed) != ast_dump(reparsed):
        return None
    return normalized


def normalized_type_spelling_text(text: str) -> str | None:
    """Return conservatively normalized docstring type spelling.

    Args:
        text (str): Semantic parsed type-slot text.

    Returns:
        str | None: Normalized spelling when a supported defect is present, or None otherwise.
    """
    if unicode_safety.has_nonstandard_whitespace_or_control(text):
        return None
    normalized = text
    if normalized.endswith("."):
        candidate = normalized[:-1].rstrip(ascii_whitespace.SPACE_AND_TAB)
        if is_type_like_text(candidate) or is_quoted_type_like_text(candidate):
            normalized = candidate
    while normalized.startswith("(") and normalized.endswith(")"):
        candidate = normalized[1:-1].strip(ascii_whitespace.SPACE_AND_TAB)
        parsed = parse_type_like_expr(normalized)
        candidate_parsed = parse_type_like_expr(candidate)
        if parsed is None or candidate_parsed is None or ast_dump(parsed) != ast_dump(candidate_parsed):
            break
        normalized = candidate
    if normalized == "none":
        normalized = "None"
    return normalized if normalized != text else None


def comparable_type_dump(text: str, *, aliases: TypeAliasMap | None = None) -> str | None:
    """Return a stable AST dump for comparable type text.

    Args:
        text (str): Candidate type expression text from a docstring or annotation.
        aliases (TypeAliasMap | None): Optional unshadowed import aliases to normalize before comparison.

    Returns:
        str | None: Attribute-free AST dump for comparable type text, or None when the text is not conservatively
            type-like.
    """
    parsed = parse_type_like_expr(text, aliases=aliases)
    if parsed is None:
        return None
    return ast_dump(parsed)


def ast_dump(parsed: ast.Expression) -> str:
    """Return an attribute-free AST dump for a parsed expression.

    Args:
        parsed (ast.Expression): Parsed expression whose structure should be compared independent of source offsets.

    Returns:
        str: Stable AST dump without line, column, or end-position attributes.
    """
    values: dict[int, str] = {}
    stack: list[tuple[ast.AST, bool]] = [(parsed, False)]
    while stack:
        node, visited = stack.pop()
        if not visited:
            stack.append((node, True))
            stack.extend((child, False) for child in reversed(tuple(ast.iter_child_nodes(node))))
            continue
        if isinstance(node, ast.Expression):
            value = f"Expression({values[id(node.body)]})"
        elif isinstance(node, ast.Name):
            value = f"Name({node.id!r})"
        elif isinstance(node, ast.Attribute):
            value = f"Attribute({values[id(node.value)]},{node.attr!r})"
        elif isinstance(node, ast.Subscript):
            value = f"Subscript({values[id(node.value)]},{values[id(node.slice)]})"
        elif isinstance(node, ast.Tuple):
            value = f"Tuple({','.join(values[id(element)] for element in node.elts)})"
        elif isinstance(node, ast.List):
            value = f"List({','.join(values[id(element)] for element in node.elts)})"
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            value = f"Union({values[id(node.left)]},{values[id(node.right)]})"
        elif isinstance(node, ast.Constant) and node.value is None:
            value = "None"
        elif isinstance(node, ast.Constant) and node.value is Ellipsis:
            value = "Ellipsis"
        else:
            value = type(node).__name__
        values[id(node)] = value
    return values[id(parsed)]


def without_whitespace(text: str) -> str:
    """Return text with all whitespace removed for token-preservation checks.

    Args:
        text (str): Source or normalized type text.

    Returns:
        str: Text collapsed by splitting on all whitespace and joining the tokens.
    """
    return "".join(text.split())


def is_type_like_node(node: ast.AST, *, allow_sequence: bool) -> bool:
    """Return whether an AST node is accepted as a conservative type-like expression.

    Args:
        node (ast.AST): Parsed AST node to classify.
        allow_sequence (bool): Whether tuple and list nodes are allowed at this position, as inside subscripts.

    Returns:
        bool: Whether the node uses only the small expression subset accepted for static docstring type comparison.
    """
    pending: list[tuple[ast.AST, bool]] = [(node, allow_sequence)]
    while pending:
        current, current_allow_sequence = pending.pop()
        if isinstance(current, ast.Name):
            continue
        if isinstance(current, ast.Attribute):
            pending.append((current.value, False))
            continue
        if isinstance(current, ast.Subscript):
            pending.extend(((current.value, False), (current.slice, True)))
            continue
        if isinstance(current, ast.Tuple | ast.List) and current_allow_sequence:
            pending.extend((element, True) for element in current.elts)
            continue
        if isinstance(current, ast.BinOp) and isinstance(current.op, ast.BitOr):
            pending.extend(((current.left, False), (current.right, False)))
            continue
        if isinstance(current, ast.Constant) and (current.value is None or current.value is Ellipsis):
            continue
        return False
    return True


def _normalize_type_aliases(node: ast.expr, aliases: TypeAliasMap) -> ast.expr:
    """Return a copy of a parsed type expression with safe aliases expanded."""
    normalized: dict[int, ast.expr] = {}
    stack: list[tuple[ast.expr, bool]] = [(node, False)]
    while stack:
        current, visited = stack.pop()
        if not visited:
            stack.append((current, True))
            stack.extend((child, False) for child in reversed(_type_expression_children(current)))
            continue
        if isinstance(current, ast.Name):
            replacement = _alias_node(aliases.get(current.id))
            normalized[id(current)] = current if replacement is None else ast.copy_location(replacement, current)
        elif isinstance(current, ast.Attribute):
            normalized_value = normalized[id(current.value)]
            normalized[id(current)] = current if normalized_value is current.value else ast.copy_location(ast.Attribute(value=normalized_value, attr=current.attr, ctx=current.ctx), current)
        elif isinstance(current, ast.Subscript):
            normalized[id(current)] = ast.copy_location(ast.Subscript(value=normalized[id(current.value)], slice=normalized[id(current.slice)], ctx=current.ctx), current)
        elif isinstance(current, ast.Tuple):
            normalized[id(current)] = ast.copy_location(ast.Tuple(elts=[normalized[id(element)] for element in current.elts], ctx=current.ctx), current)
        elif isinstance(current, ast.List):
            normalized[id(current)] = ast.copy_location(ast.List(elts=[normalized[id(element)] for element in current.elts], ctx=current.ctx), current)
        elif isinstance(current, ast.BinOp):
            normalized[id(current)] = ast.copy_location(ast.BinOp(left=normalized[id(current.left)], op=current.op, right=normalized[id(current.right)]), current)
        else:
            normalized[id(current)] = current
    return normalized[id(node)]


def _parse_type_like_ast(text: str) -> ast.Expression | None:
    """Parse and validate a conservative type expression."""
    try:
        parsed = ast.parse(text, mode="eval")
    except (RecursionError, SyntaxError):
        return None
    return parsed if is_type_like_node(parsed.body, allow_sequence=False) else None


def _validated_type_tokens(text: str) -> _ValidatedTypeTokens | None:
    """Return significant tokens when text follows the conservative type grammar."""
    if not text:
        return None
    tokens = _significant_type_tokens(text)
    if not tokens or any(token_info.type not in {tokenize.NAME, tokenize.OP} for token_info in tokens):
        return None
    contexts = [_TypeContext(kind="root", allow_sequence=False)]
    has_grouping = False
    for token_info in tokens:
        context = contexts[-1]
        value = token_info.string
        if context.expect_attribute:
            if token_info.type != tokenize.NAME or keyword.iskeyword(value):
                return None
            context.expect_attribute = False
            continue
        if context.expect_value:
            if token_info.type == tokenize.NAME:
                if keyword.iskeyword(value) and value != "None":
                    return None
                context.expect_value = False
                context.saw_value = True
                context.value_is_sequence = False
                continue
            if token_info.type == tokenize.OP and value == "...":
                context.expect_value = False
                context.saw_value = True
                context.value_is_sequence = False
                continue
            if token_info.type == tokenize.OP and value == "(":
                contexts.append(_TypeContext(kind="paren", allow_sequence=True))
                has_grouping = True
                continue
            if token_info.type == tokenize.OP and value == "[" and context.allow_sequence:
                contexts.append(_TypeContext(kind="list", allow_sequence=True))
                continue
            if token_info.type != tokenize.OP or value not in {")", "]"}:
                return None
        if token_info.type != tokenize.OP:
            return None
        if value == ".":
            if context.value_is_sequence:
                return None
            context.expect_attribute = True
            continue
        if value == "[":
            if context.value_is_sequence:
                return None
            contexts.append(_TypeContext(kind="subscript", allow_sequence=True, opened_as_trailer=True))
            continue
        if value == "|":
            if context.value_is_sequence:
                return None
            context.expect_value = True
            context.union_active = True
            continue
        if value == ",":
            if not context.allow_sequence or (context.union_active and context.value_is_sequence):
                return None
            context.expect_value = True
            context.has_comma = True
            context.union_active = False
            continue
        if value not in {")", "]"} or len(contexts) == 1:
            return None
        if (context.kind == "paren" and value != ")") or (context.kind in {"list", "subscript"} and value != "]"):
            return None
        if context.expect_attribute or (context.expect_value and context.saw_value and not context.has_comma):
            return None
        if context.kind == "subscript" and not context.saw_value:
            return None
        if context.union_active and context.value_is_sequence:
            return None
        is_sequence = context.value_is_sequence or context.kind == "list" or (context.kind == "paren" and (context.has_comma or not context.saw_value))
        contexts.pop()
        parent = contexts[-1]
        if context.opened_as_trailer:
            continue
        if is_sequence and not parent.allow_sequence:
            return None
        parent.expect_value = False
        parent.saw_value = True
        parent.value_is_sequence = is_sequence
    root = contexts[0]
    if len(contexts) != 1 or root.expect_value or root.expect_attribute or (root.union_active and root.value_is_sequence) or root.value_is_sequence:
        return None
    return _ValidatedTypeTokens(tokens=tokens, has_grouping=has_grouping)


def _significant_type_tokens(text: str) -> tuple[tokenize.TokenInfo, ...] | None:
    """Return significant tokens while rejecting a continued top-level statement."""
    try:
        generated_tokens = tokenize.generate_tokens(io.StringIO(text).readline)
        tokens: list[tokenize.TokenInfo] = []
        terminated = False
        for token_info in generated_tokens:
            if token_info.type in {tokenize.ENCODING, tokenize.NL, tokenize.ENDMARKER}:
                continue
            if token_info.type == tokenize.NEWLINE:
                terminated = True
                continue
            if terminated:
                return None
            tokens.append(token_info)
    except tokenize.TokenError:
        return _fallback_significant_type_tokens(text)
    except (IndentationError, SyntaxError):
        return None
    return tuple(tokens)


def _fallback_significant_type_tokens(text: str) -> tuple[tokenize.TokenInfo, ...] | None:
    """Lex the conservative type grammar after tokenizer failure."""
    tokens: list[tokenize.TokenInfo] = []
    index = 0
    line = 1
    column = 0
    depth = 0
    terminated = False
    operator_chars = frozenset(".[](),|")
    while index < len(text):
        char = text[index]
        if char in " \t\f":
            index += 1
            column += 1
            continue
        if char == "\\" and index + 1 < len(text) and text[index + 1] == "\n":
            index += 2
            line += 1
            column = 0
            continue
        if char == "\\" and text[index + 1 : index + 3] == "\r\n":
            index += 3
            line += 1
            column = 0
            continue
        if char == "\\" and index + 1 < len(text) and text[index + 1] == "\r":
            return None
        if char == "\r" and text[index : index + 2] != "\r\n":
            return None
        if char == "\n" or text[index : index + 2] == "\r\n":
            index += 2 if char == "\r" else 1
            line += 1
            column = 0
            if depth == 0:
                terminated = True
            continue
        if terminated:
            return None
        token_start = (line, column)
        if text.startswith("...", index):
            value = "..."
            token_type = tokenize.OP
        elif char in operator_chars:
            value = char
            token_type = tokenize.OP
        else:
            end = index
            while end < len(text) and text[end] not in " \t\f\r\n\\#" and text[end] not in operator_chars:
                end += 1
            value = text[index:end]
            if not value or not value.isidentifier():
                return None
            token_type = tokenize.NAME
        index += len(value)
        column += len(value)
        if value in {"(", "["}:
            depth += 1
        elif value in {")", "]"}:
            depth = max(depth - 1, 0)
        tokens.append(tokenize.TokenInfo(token_type, value, token_start, (line, column), ""))
    return tuple(tokens)


def _normalized_token_text(tokens: tuple[tokenize.TokenInfo, ...]) -> str:
    """Return canonical spacing for validated type-expression tokens."""
    pieces: list[str] = []
    previous = ""
    for token_info in tokens:
        value = token_info.string
        if value == "|":
            pieces.append(" | ")
        elif value == ",":
            pieces.append(", ")
        elif value in {".", "[", "]", "(", ")"}:
            pieces.append(value)
        else:
            if previous and previous not in {".", "[", "(", "|", ","} and not pieces[-1].endswith((" ", ".", "[", "(")):
                pieces.append(" ")
            pieces.append(value)
        previous = value
    return "".join(pieces).rstrip()


def _type_expression_children(node: ast.expr) -> tuple[ast.expr, ...]:
    """Return child expressions of one accepted type-expression node."""
    if isinstance(node, ast.Attribute):
        return (node.value,)
    if isinstance(node, ast.Subscript):
        return node.value, node.slice
    if isinstance(node, ast.Tuple | ast.List):
        return tuple(node.elts)
    if isinstance(node, ast.BinOp):
        return node.left, node.right
    return ()


def _alias_node(qualified_name: str | None) -> ast.expr | None:
    """Return an AST expression for a qualified alias target."""
    if qualified_name is None:
        return None
    parsed = ast.parse(qualified_name, mode="eval")
    return parsed.body
