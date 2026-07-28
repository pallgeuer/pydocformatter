"""Documentation wording style helpers."""

# Future imports
from __future__ import annotations

# Standard library imports
import re
import string
import dataclasses
from typing import TYPE_CHECKING

# First-party imports
import pydocformatter.rules.violations as rule_violations
from pydocformatter.rules.definition_helpers import ascii_whitespace, unicode_safety


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.models import RuleMetadata


@dataclasses.dataclass(frozen=True)
class DocumentedValueTarget:
    """One documented name and its prose description.

    Attributes:
        name (str): Documented parameter, attribute, or value name as written in the documentation.
        description (str): Description text associated with the documented name.
        line_numbers (tuple[int, ...]): One-based source lines occupied by the documentation target.
        extra_generic_sequences (frozenset[tuple[str, ...]]): Additional normalized token sequences that are generic for
            this specific target.
    """

    name: str
    description: str
    line_numbers: tuple[int, ...]
    extra_generic_sequences: frozenset[tuple[str, ...]] = frozenset()


@dataclasses.dataclass(frozen=True)
class DocumentedValueStylePolicy:
    """Generic wording policy for one documented-value kind.

    Attributes:
        nouns (frozenset[str]): Generic nouns that do not add meaning beyond the documented name.
        message_subject (str): Lowercase subject used in per-instance diagnostic messages.
    """

    nouns: frozenset[str]
    message_subject: str


def too_generic_violations(targets: tuple[DocumentedValueTarget, ...], *, rule: RuleMetadata, policy: DocumentedValueStylePolicy) -> tuple[rule_violations.RuleViolation, ...]:
    """Return violations for documented-value descriptions that only restate their names.

    Args:
        targets (tuple[DocumentedValueTarget, ...]): Documented values to inspect.
        rule (RuleMetadata): Rule metadata used for diagnostics.
        policy (DocumentedValueStylePolicy): Wording policy for the documented value kind.

    Returns:
        Violations for generic documentation descriptions.
    """
    return tuple(
        rule_violations.diagnostic(rule, target.line_numbers, instance_message=f"{policy.message_subject.capitalize()} '{target.name}' documentation is too generic")
        for target in targets
        if is_too_generic(target.name, target.description, policy=policy, extra_generic_sequences=target.extra_generic_sequences)
    )


def is_too_generic(name: str, description: str, *, policy: DocumentedValueStylePolicy, extra_generic_sequences: frozenset[tuple[str, ...]] = frozenset()) -> bool:
    """Return whether a description only restates a documented name with generic filler.

    Args:
        name (str): Documented parameter or attribute name.
        description (str): Documentation prose associated with the name.
        policy (DocumentedValueStylePolicy): Generic nouns accepted by the target kind.
        extra_generic_sequences (frozenset[tuple[str, ...]]): Additional normalized token sequences that are generic for
            this target.

    Returns:
        Whether the normalized description has no meaningful words beyond the documented name and generic filler.
    """
    name_tokens = _name_tokens(name)
    description_tokens = _text_tokens(description)
    if not name_tokens or not description_tokens:
        return False
    candidates = _generic_sequences(name_tokens, nouns=policy.nouns) | extra_generic_sequences
    return tuple(description_tokens) in candidates


def _generic_sequences(name_tokens: tuple[str, ...], *, nouns: frozenset[str]) -> frozenset[tuple[str, ...]]:
    """Return exact token sequences considered generic for a documented name."""
    sequences: set[tuple[str, ...]] = {name_tokens, ("the", *name_tokens), ("value", "of", *name_tokens), ("the", "value", "of", *name_tokens)}
    for noun in nouns:
        sequences.add((*name_tokens, noun))
        sequences.add(("the", *name_tokens, noun))
        sequences.add(("the", noun, *name_tokens))
    return frozenset(sequences)


def _name_tokens(name: str) -> tuple[str, ...]:
    """Return comparison tokens for a documented name."""
    stripped = name.strip("*")
    return tuple(token for token in _TOKEN_RE.findall(stripped.replace("_", " ").lower()) if token)


def _text_tokens(text: str) -> tuple[str, ...]:
    """Return normalized word tokens from documentation text."""
    return tuple(token for token in _TOKEN_RE.findall(text.lower()) if token)


_TOKEN_RE = re.compile(r"[a-z0-9]+")
_ASCII_LOWER_TRANSLATION = str.maketrans(string.ascii_uppercase, string.ascii_lowercase)
_ASCII_WORD_SEPARATOR = rf"[{re.escape(ascii_whitespace.SPACE_AND_TAB)}]+"
_ASCII_NAME_SEPARATOR = rf"[{re.escape(ascii_whitespace.SPACE_AND_TAB)}_.]+"


def matches_exact_description(description: str, sequences: frozenset[tuple[str, ...]]) -> bool:
    """Return whether prose exactly matches one normalized word sequence.

    Args:
        description (str): Description prose to compare.
        sequences (frozenset[tuple[str, ...]]): Accepted lowercase ASCII word sequences.

    Returns:
        bool: Whether the description differs only by ASCII case, surrounding whitespace, and sentence-ending
            punctuation.
    """
    normalized = _normalized_exact_description(description)
    if normalized is None:
        return False
    return any(re.fullmatch(_ASCII_WORD_SEPARATOR.join(map(re.escape, sequence)), normalized) is not None for sequence in sequences)


def matches_exact_named_description(description: str, name: str, templates: frozenset[tuple[tuple[str, ...], tuple[str, ...]]]) -> bool:
    """Return whether prose exactly matches one name-bearing template.

    Args:
        description (str): Description prose to compare.
        name (str): Documented name supplying the template's variable tokens.
        templates (frozenset[tuple[tuple[str, ...], tuple[str, ...]]]): Lowercase ASCII prefix and suffix token
            sequences surrounding the documented name.

    Returns:
        bool: Whether the description exactly matches one template after conservative name normalization.
    """
    normalized = _normalized_exact_description(description)
    if not name.isascii():
        return False
    name_tokens = _name_tokens(name)
    if normalized is None or not name_tokens:
        return False
    boundary_name = name.lstrip("*")
    leading_underscores = r"(?:_+)?" if boundary_name.startswith("_") else ""
    trailing_underscores = r"(?:_+)?" if boundary_name.endswith("_") else ""
    name_pattern = rf"\*{{0,2}}{leading_underscores}{_ASCII_NAME_SEPARATOR.join(map(re.escape, name_tokens))}{trailing_underscores}"
    for prefix, suffix in templates:
        parts = (*map(re.escape, prefix), name_pattern, *map(re.escape, suffix))
        if re.fullmatch(_ASCII_WORD_SEPARATOR.join(parts), normalized) is not None:
            return True
    return False


def _normalized_exact_description(description: str) -> str | None:
    """Return exact-matcher prose normalized at its outer boundary."""
    if unicode_safety.has_nonstandard_whitespace_or_control(description):
        return None
    normalized = description.strip(ascii_whitespace.SPACE_AND_TAB).translate(_ASCII_LOWER_TRANSLATION)
    normalized = normalized.rstrip(".?!").rstrip(ascii_whitespace.SPACE_AND_TAB)
    if not normalized or not normalized.isascii():
        return None
    return normalized


def exact_description_fragment_is_safe(text: str) -> bool:
    """Return whether one full fragment obeys the exact ASCII layout policy.

    Args:
        text (str): Evaluated fragment text before semantic boundary trimming.

    Returns:
        bool: Whether the fragment contains only ASCII text and no nonstandard whitespace or suspicious controls.
    """
    return text.isascii() and not unicode_safety.has_nonstandard_whitespace_or_control(text)
