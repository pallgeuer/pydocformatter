"""Tests for conservative type-expression parsing helpers."""

# Future imports
from __future__ import annotations

# Standard library imports
import ast

# Third-party imports
import pytest

# First-party imports
from pydocformatter.rules.definition_helpers import type_expressions


@pytest.mark.parametrize(
    "text",
    [
        "int",
        "pkg.Type",
        "None",
        "list[int | pkg.Type]",
        "Callable[[int, str], tuple[int, ...]]",
        "(int | str)",
        "dict[str, list[tuple[int, ...]]]",
        "Container[([int])]",
        "Container[((int, str))]",
        "list[\nint | str\n]",
        "(int\n| str)",
        "int\\\n| str",
    ],
)
def test_is_type_like_text_accepts_the_conservative_grammar(text: str) -> None:
    """Accept names, qualified names, unions, subscripts, and subscript sequences."""
    assert type_expressions.is_type_like_text(text)


@pytest.mark.parametrize(
    "text",
    ["", "x x", "factory()", "{int}", "42", "int + str", "int, str", "[int]", "list[]", "A | [B]", "([])", "(())", "((int,))", "([int])", "((int, str))", "A | ([B])", "A\n.B", "A\n[B]", "A |\nB"],
)
def test_is_type_like_text_rejects_non_type_expression_forms(text: str) -> None:
    """Reject calls, operators, literals, and top-level sequences."""
    assert not type_expressions.is_type_like_text(text)


def test_is_type_like_text_is_iterative_for_deeply_nested_subscripts(monkeypatch: pytest.MonkeyPatch) -> None:
    """Validate deep nesting without calling the recursive Python expression parser."""
    monkeypatch.setattr(type_expressions, "ast", None)
    valid = f"{'list[' * 3000}int{']' * 3000}"
    invalid = f"{'(' * 3000}[int]{')' * 3000}"

    assert type_expressions.is_type_like_text(valid)
    assert not type_expressions.is_type_like_text(invalid)


@pytest.mark.parametrize(
    ("text", "expected"),
    [('"pkg.Model"', True), ("'list[int | None]'", True), ('"list[\\nint | None\\n]"', True), ('"int\\n| str"', False), ('"ordinary prose"', False), ('"int" "str"', False), ("int", False)],
)
def test_is_quoted_type_like_text_requires_one_type_like_string_literal(text: str, expected: bool) -> None:
    """Accept only a single quoted forward reference with type-like contents."""
    assert type_expressions.is_quoted_type_like_text(text) is expected


def test_parse_type_like_expr_uses_the_ast_path_without_token_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep AST-backed comparisons independent from the PDF414 token-only parser."""
    monkeypatch.setattr(type_expressions, "_validated_type_tokens", pytest.fail)

    assert type_expressions.parse_type_like_expr("dict[str, list[int | None]]") is not None


def test_parse_type_like_expr_preserves_conservative_comment_rejection() -> None:
    """Reject comments even though the Python parser discards them."""
    assert type_expressions.parse_type_like_expr("int  # explanatory prose") is None
    assert type_expressions.parse_type_like_expr("list[  # explanatory prose\nint]") is None


def test_parse_type_like_expr_handles_recursive_parser_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Treat parser recursion limits as an unsupported expression."""

    def recursive_parse(*_args: object, **_kwargs: object) -> ast.Expression:
        del _args, _kwargs
        raise RecursionError

    monkeypatch.setattr(type_expressions.ast, "parse", recursive_parse)

    assert type_expressions.parse_type_like_expr("int") is None


def test_parse_type_like_expr_rejects_input_beyond_the_ast_recursion_limit() -> None:
    """Return safely when a valid token stream exceeds the Python AST parser's depth."""
    assert type_expressions.parse_type_like_expr(" | ".join(("Type",) * 3000)) is None


def test_ast_helpers_process_deep_parsed_types_iteratively() -> None:
    """Avoid Python recursion while validating, normalizing, and dumping a deep AST."""
    node: ast.expr = ast.Name(id="Type", ctx=ast.Load())
    for _ in range(500):
        node = ast.Attribute(value=node, attr="member", ctx=ast.Load())

    assert type_expressions.is_type_like_node(node, allow_sequence=False)
    normalized = type_expressions._normalize_type_aliases(node, {"Type": "package.Type"})
    assert type_expressions.ast_dump(ast.Expression(body=normalized)).startswith("Expression(Attribute(")


def test_normalized_type_like_text_preserves_structure() -> None:
    """Normalize token spacing while retaining qualified union operands."""
    assert type_expressions.normalized_type_like_text("dict[ str, list[int|pkg.Type ] ]") == "dict[str, list[int | pkg.Type]]"
