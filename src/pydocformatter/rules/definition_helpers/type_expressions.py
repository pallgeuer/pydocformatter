"""Conservative parsing helpers for annotation-like type expressions.

Attributes:
    TypeAliasMap (TypeAlias): Unshadowed source names mapped to absolute import-qualified names for type comparison.
"""

from __future__ import annotations

import ast

import libcst as cst

TypeAliasMap = dict[str, str]


def module_type_aliases(module: cst.Module) -> TypeAliasMap:
    """Return conservative absolute import aliases usable for type expression comparison.

    Args:
        module (cst.Module): Parsed source module whose top-level imports should be inspected.

    Returns:
        TypeAliasMap: Mapping from unshadowed source names to absolute qualified import names.
    """
    aliases: TypeAliasMap = {}
    shadowed_names: set[str] = set()
    for statement in module.body:
        if isinstance(statement, cst.SimpleStatementLine) and all(isinstance(small_statement, cst.Import | cst.ImportFrom) for small_statement in statement.body):
            for small_statement in statement.body:
                if isinstance(small_statement, cst.Import):
                    _record_import_aliases(small_statement, aliases)
                elif isinstance(small_statement, cst.ImportFrom):
                    _record_import_from_aliases(small_statement, aliases)
            continue
        shadowed_names.update(_top_level_bound_names(statement))
    for name in shadowed_names:
        aliases.pop(name, None)
    return aliases


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


def _record_import_aliases(statement: cst.Import, aliases: TypeAliasMap) -> None:
    """Record aliases introduced by an absolute import statement."""
    for alias in statement.names:
        qualified_name = _cst_qualified_name(alias.name)
        if qualified_name is None:
            continue
        asname = _asname_value(alias.asname)
        binding = asname or qualified_name.split(".", maxsplit=1)[0]
        aliases[binding] = qualified_name if asname is not None else binding


def _record_import_from_aliases(statement: cst.ImportFrom, aliases: TypeAliasMap) -> None:
    """Record aliases introduced by an absolute from-import statement."""
    if statement.relative:
        return
    if statement.module is None or isinstance(statement.names, cst.ImportStar):
        return
    module_name = _cst_qualified_name(statement.module)
    if module_name is None:
        return
    for alias in statement.names:
        imported_name = _cst_qualified_name(alias.name)
        if imported_name is None:
            continue
        binding = _asname_value(alias.asname) or imported_name.split(".", maxsplit=1)[0]
        aliases[binding] = f"{module_name}.{imported_name}"


def _top_level_bound_names(statement: cst.BaseStatement) -> set[str]:
    """Return names rebound by a top-level non-import statement."""
    if isinstance(statement, cst.FunctionDef | cst.ClassDef):
        return {statement.name.value}
    if isinstance(statement, cst.SimpleStatementLine):
        names: set[str] = set()
        for small_statement in statement.body:
            if isinstance(small_statement, cst.Assign):
                for target in small_statement.targets:
                    names.update(_target_bound_names(target.target))
            elif isinstance(small_statement, cst.AnnAssign | cst.AugAssign):
                names.update(_target_bound_names(small_statement.target))
        return names
    return set()


def _target_bound_names(target: cst.BaseExpression) -> set[str]:
    """Return names bound by a simple assignment target."""
    if isinstance(target, cst.Name):
        return {target.value}
    if isinstance(target, cst.Tuple | cst.List):
        names: set[str] = set()
        for element in target.elements:
            names.update(_target_bound_names(element.value))
        return names
    return set()


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
        return ast.copy_location(
            ast.Subscript(value=_normalize_type_aliases(node.value, aliases), slice=_normalize_type_aliases(node.slice, aliases), ctx=node.ctx),
            node,
        )
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


def _asname_value(asname: cst.AsName | None) -> str | None:
    """Return a simple import alias binding name."""
    if asname is None or not isinstance(asname.name, cst.Name):
        return None
    return asname.name.value


def _cst_qualified_name(expression: cst.BaseExpression) -> str | None:
    """Return a dotted name for static CST name and attribute expressions."""
    if isinstance(expression, cst.Name):
        return expression.value
    if isinstance(expression, cst.Attribute):
        parent = _cst_qualified_name(expression.value)
        if parent is None:
            return None
        return f"{parent}.{expression.attr.value}"
    return None
