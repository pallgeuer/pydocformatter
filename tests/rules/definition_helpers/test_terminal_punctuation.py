"""Tests for terminal-punctuation policies."""

# Standard library imports
import typing

# Third-party imports
import pytest

# First-party imports
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
from pydocformatter.rules.definition_helpers import terminal_punctuation


def policy(**overrides: str) -> terminal_punctuation.TerminalPunctuationPolicy:
    """Return a terminal-punctuation policy with selected field overrides."""
    values = {"valid_endings": ".?!", "replaceable_endings": ",;", "nonfixable_endings": ":", "canonical_ending": "."}
    return terminal_punctuation.TerminalPunctuationPolicy(**(values | overrides))


def test_accepts_valid_terminal_punctuation_policy() -> None:
    """Accept disjoint classifications with a valid canonical ending."""
    assert policy().canonical_ending == "."


def test_shared_rule_policies_are_distinct_and_immutable() -> None:
    """Expose the two shared punctuation contracts used by summary and entry rules."""
    assert policy(valid_endings=".", nonfixable_endings=":?!\u2026") == terminal_punctuation.TRAILING_PERIOD_POLICY
    assert policy(valid_endings=".?!\u2026") == terminal_punctuation.TERMINAL_PUNCTUATION_POLICY


def test_trailing_period_policy_is_stricter_than_terminal_punctuation_policy() -> None:
    """Require every expressive-policy finding to also violate the strict policy."""
    strict = terminal_punctuation.TRAILING_PERIOD_POLICY
    expressive = terminal_punctuation.TERMINAL_PUNCTUATION_POLICY

    assert set(strict.valid_endings) < set(expressive.valid_endings)
    assert strict.replaceable_endings == expressive.replaceable_endings
    assert set(strict.nonfixable_endings) == set(expressive.nonfixable_endings) | (set(expressive.valid_endings) - set(strict.valid_endings))
    assert strict.canonical_ending == expressive.canonical_ending


@pytest.mark.parametrize(
    "kind",
    [
        PDF_definition.DocstringBlockKind.COLON_HEADER,
        PDF_definition.DocstringBlockKind.LIST_ITEM,
        PDF_definition.DocstringBlockKind.HEADING,
        PDF_definition.DocstringBlockKind.DOCTEST,
        PDF_definition.DocstringBlockKind.CODE_FENCE,
        PDF_definition.DocstringBlockKind.BLOCK_QUOTE,
        PDF_definition.DocstringBlockKind.TABLE,
        PDF_definition.DocstringBlockKind.DIRECTIVE,
        PDF_definition.DocstringBlockKind.DIRECTIVE_ISSUE,
        PDF_definition.DocstringBlockKind.LITERAL_BLOCK,
        PDF_definition.DocstringBlockKind.VERBATIM,
    ],
)
def test_recognizes_blocks_that_a_terminal_comma_may_introduce(kind: PDF_definition.DocstringBlockKind) -> None:
    """Keep comma protection narrower than the parser's complete structured-block inventory."""
    assert terminal_punctuation.comma_may_introduce_block(kind)


@pytest.mark.parametrize("kind", [None, PDF_definition.DocstringBlockKind.BLANK, PDF_definition.DocstringBlockKind.SECTION, PDF_definition.DocstringBlockKind.REST_FIELD])
def test_rejects_blocks_outside_the_comma_introduction_policy(kind: PDF_definition.DocstringBlockKind | None) -> None:
    """Exclude blocks whose adjacency does not make a comma structurally meaningful."""
    assert not terminal_punctuation.comma_may_introduce_block(kind)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"canonical_ending": ""}, "exactly one character"),
        ({"canonical_ending": ".."}, "exactly one character"),
        ({"canonical_ending": ";"}, "included in valid endings"),
        ({"valid_endings": "..?!"}, "valid_endings must not contain duplicate characters"),
        ({"replaceable_endings": ",;,"}, "replaceable_endings must not contain duplicate characters"),
        ({"nonfixable_endings": "::"}, "nonfixable_endings must not contain duplicate characters"),
        ({"replaceable_endings": ".,"}, "valid endings and replaceable endings must be disjoint"),
        ({"nonfixable_endings": "?:"}, "valid endings and non-fixable endings must be disjoint"),
        ({"replaceable_endings": ",;", "nonfixable_endings": ";:"}, "replaceable endings and non-fixable endings must be disjoint"),
    ],
)
def test_rejects_invalid_terminal_punctuation_policy(overrides: dict[str, str], message: str) -> None:
    """Reject contradictory punctuation classifications."""
    with pytest.raises(ValueError, match=message):
        policy(**overrides)


def test_rejects_non_string_terminal_punctuation_policy_field() -> None:
    """Reject non-string policy fields before inspecting their contents."""
    with pytest.raises(TypeError, match="valid_endings must be a string"):
        terminal_punctuation.TerminalPunctuationPolicy(valid_endings=typing.cast("str", 1), replaceable_endings=",;", nonfixable_endings=":", canonical_ending=".")
