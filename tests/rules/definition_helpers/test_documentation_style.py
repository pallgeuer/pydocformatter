"""Tests for documentation wording style helpers."""

# Third-party imports
import pytest

# First-party imports
from pydocformatter.rules.definition_helpers import documentation_style


_SEQUENCES = frozenset({("the", "return", "value")})
_NAMED_TEMPLATES = frozenset({(("the",), ("value",))})


@pytest.mark.parametrize("description", ["The return value", "the RETURN value.", " \tThe return value?! \t"])
def test_exact_description_matching_normalizes_only_outer_style(description: str) -> None:
    """Ignore ASCII case, outer whitespace, and sentence endings."""
    assert documentation_style.matches_exact_description(description, _SEQUENCES)


@pytest.mark.parametrize(
    "description",
    ["The return-value.", "`The return value`", '"The return value."', "The return value:", "The return value in bytes.", "The return value\u00a0", "The\freturn value.", "\vThe return value.\v"],
)
def test_exact_description_matching_rejects_internal_or_non_ascii_variants(description: str) -> None:
    """Reject markup, internal punctuation, extra words, and nonstandard whitespace."""
    assert not documentation_style.matches_exact_description(description, _SEQUENCES)


@pytest.mark.parametrize("text", [" The return value. ", "\tThe return value.\t"])
def test_exact_description_fragment_safety_accepts_ascii_space_and_tab(text: str) -> None:
    """Accept only the layout characters owned by exact description matching."""
    assert documentation_style.exact_description_fragment_is_safe(text)


@pytest.mark.parametrize("text", ["The\freturn value.", "\vThe return value.\v", "\u2003The return value.", "The return value.\u00a0"])
def test_exact_description_fragment_safety_rejects_controls_and_non_ascii_text(text: str) -> None:
    """Reject full fragments whose trimmed boundaries would hide unsafe text."""
    assert not documentation_style.exact_description_fragment_is_safe(text)


@pytest.mark.parametrize(
    ("name", "description"),
    [
        ("max_retries", "The max retries value."),
        ("max_retries", "The max_retries value."),
        ("errors.ValueError", "The errors.ValueError value."),
        ("*args", "The args value."),
        ("**kwargs", "The **kwargs value."),
    ],
)
def test_exact_named_description_uses_existing_name_token_style(name: str, description: str) -> None:
    """Normalize stars, underscores, dots, and ASCII case inside name spans."""
    assert documentation_style.matches_exact_named_description(description, name, _NAMED_TEMPLATES)


@pytest.mark.parametrize(
    ("name", "description"),
    [
        ("_run", "The _run value."),
        ("_run", "The run value."),
        ("__init__", "The __init__ value."),
        ("__init__", "The init value."),
        ("run_", "The run_ value."),
        ("_Client.__init__", "The _Client.__init__ value."),
    ],
)
def test_exact_named_description_preserves_or_omits_documented_boundary_underscores(name: str, description: str) -> None:
    """Accept boundary underscores only when the documented name supplies them."""
    assert documentation_style.matches_exact_named_description(description, name, _NAMED_TEMPLATES)


@pytest.mark.parametrize("description", ["The _run value.", "The run_ value.", "The __run__ value."])
def test_exact_named_description_does_not_add_boundary_underscores(description: str) -> None:
    """Reject boundary underscores that are absent from the documented name."""
    assert not documentation_style.matches_exact_named_description(description, "run", _NAMED_TEMPLATES)


def test_exact_named_description_requires_complete_qualified_name() -> None:
    """Do not collapse qualified names to their final component."""
    assert not documentation_style.matches_exact_named_description("The ValueError value.", "errors.ValueError", _NAMED_TEMPLATES)


@pytest.mark.parametrize(("name", "description"), [("***", "The value."), ("caf\u00e9", "The caf value."), ("value", "")])
def test_exact_named_description_rejects_empty_or_non_ascii_inputs(name: str, description: str) -> None:
    """Reject names or descriptions that cannot be normalized conservatively."""
    assert not documentation_style.matches_exact_named_description(description, name, _NAMED_TEMPLATES)
