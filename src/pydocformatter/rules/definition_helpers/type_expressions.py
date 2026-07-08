"""Conservative parsing helpers for annotation-like type expressions.

Attributes:
    TypeAliasMap (TypeAlias): Unshadowed source names mapped to absolute import-qualified names for type comparison.
"""

# Future imports
from __future__ import annotations

# Standard library imports
import ast
from typing import TYPE_CHECKING

# First-party imports
from pydocformatter.rules.definition_helpers import module_bindings


if TYPE_CHECKING:
    # Third-party imports
    import libcst as cst


TypeAliasMap = module_bindings.TypeAliasMap


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
    if not stripped:
        return None
    try:
        parsed = ast.parse(stripped, mode="eval")
    except SyntaxError:
        return None
    if not is_type_like_node(parsed.body, allow_sequence=False):
        return None
    if aliases:
        parsed = ast.Expression(body=_normalize_type_aliases(parsed.body, aliases))
        ast.fix_missing_locations(parsed)
    return parsed


def normalized_type_like_text(text: str) -> str | None:
    """Return AST-stable normalized spacing for a type-like expression.

    Args:
        text (str): Candidate type expression text whose internal spacing may need normalization.

    Returns:
        str | None: Normalized type text when spacing can be changed safely, or None when the text should be left
            unchanged.
    """
    stripped = text.strip()
    parsed = parse_type_like_expr(stripped)
    if parsed is None:
        return None
    normalized = ast.unparse(parsed)
    if normalized == stripped:
        return None
    if without_whitespace(normalized) != without_whitespace(stripped):
        return None
    reparsed = parse_type_like_expr(normalized)
    if reparsed is None or ast_dump(parsed) != ast_dump(reparsed):
        return None
    return normalized


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
    return ast.dump(parsed, include_attributes=False)


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
    if isinstance(node, ast.Name):
        return True
    if isinstance(node, ast.Attribute):
        return is_type_like_node(node.value, allow_sequence=False)
    if isinstance(node, ast.Subscript):
        return is_type_like_node(node.value, allow_sequence=False) and is_type_like_node(node.slice, allow_sequence=True)
    if isinstance(node, ast.Tuple | ast.List) and allow_sequence:
        return all(is_type_like_node(element, allow_sequence=True) for element in node.elts)
    if isinstance(node, ast.BinOp):
        return isinstance(node.op, ast.BitOr) and is_type_like_node(node.left, allow_sequence=False) and is_type_like_node(node.right, allow_sequence=False)
    if isinstance(node, ast.Constant):
        return node.value is None or node.value is Ellipsis
    return False


def _normalize_type_aliases(node: ast.expr, aliases: TypeAliasMap) -> ast.expr:
    """Return a copy of a parsed type expression with safe aliases expanded."""
    if isinstance(node, ast.Name):
        return _alias_node(aliases.get(node.id)) or node
    if isinstance(node, ast.Attribute):
        normalized_value = _normalize_type_aliases(node.value, aliases)
        if normalized_value is node.value:
            return node
        return ast.copy_location(ast.Attribute(value=normalized_value, attr=node.attr, ctx=node.ctx), node)
    if isinstance(node, ast.Subscript):
        return ast.copy_location(ast.Subscript(value=_normalize_type_aliases(node.value, aliases), slice=_normalize_type_aliases(node.slice, aliases), ctx=node.ctx), node)
    if isinstance(node, ast.Tuple):
        return ast.copy_location(ast.Tuple(elts=[_normalize_type_aliases(element, aliases) for element in node.elts], ctx=node.ctx), node)
    if isinstance(node, ast.List):
        return ast.copy_location(ast.List(elts=[_normalize_type_aliases(element, aliases) for element in node.elts], ctx=node.ctx), node)
    if isinstance(node, ast.BinOp):
        return ast.copy_location(ast.BinOp(left=_normalize_type_aliases(node.left, aliases), op=node.op, right=_normalize_type_aliases(node.right, aliases)), node)
    return node


def _alias_node(qualified_name: str | None) -> ast.expr | None:
    """Return an AST expression for a qualified alias target."""
    if qualified_name is None:
        return None
    parsed = ast.parse(qualified_name, mode="eval")
    return parsed.body
