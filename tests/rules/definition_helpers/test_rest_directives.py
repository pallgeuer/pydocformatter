"""Tests for reStructuredText directive recognition helpers."""

# Third-party imports
import pytest

# First-party imports
from pydocformatter.rules.definition_helpers import rest_directives


@pytest.mark.parametrize("name", ["1", "note", "version-added", "some_name", "domain.sub_name+part", "py:function", "n\N{LATIN SMALL LETTER O WITH DIAERESIS}te"])
def test_recognizes_full_directive_type_grammar(name: str) -> None:
    match = rest_directives.directive_match(f"  .. {name}:: argument")

    assert match is not None
    assert match.group("indent") == "  "
    assert match.group("name") == name


@pytest.mark.parametrize(
    "text",
    [
        ".. note::text",
        ".. -note::",
        ".. note-::",
        ".. note__name::",
        ".. note..name::",
        ".. py::function:: value",
        ".. note::: value",
        ".. note  :: value",
        ".. note\t:: value",
        ".. note::\u00a0value",
    ],
)
def test_rejects_invalid_directive_boundaries(text: str) -> None:
    assert rest_directives.directive_match(text) is None


@pytest.mark.parametrize("text", [".. note::", ".. note ::", "\t..\tnote::\targument"])
def test_recognizes_empty_arguments_and_ascii_tab_separators(text: str) -> None:
    assert rest_directives.directive_match(text) is not None


@pytest.mark.parametrize("text", [".. py:function: signature", ".. py:function : signature"])
def test_recognizes_exactly_one_trailing_colon(text: str) -> None:
    match = rest_directives.malformed_directive_match(text)

    assert match is not None
    assert match.group("name") == "py:function"
    assert rest_directives.malformed_directive_match(".. py:function:: signature") is None


@pytest.mark.parametrize("text", [".. note:text", ".. note:: text", ".. note::: text", ".. note  : text", ".. note\t: text", ".. note:\u00a0text"])
def test_malformed_directive_requires_an_exact_delimiter_boundary(text: str) -> None:
    assert rest_directives.malformed_directive_match(text) is None
