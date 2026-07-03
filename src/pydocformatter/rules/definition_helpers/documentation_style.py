"""Documentation wording style helpers."""

from __future__ import annotations

import dataclasses
import re

import pydocformatter.rules.violations as rule_violations
from pydocformatter.rules.models import RuleMetadata


@dataclasses.dataclass(frozen=True)
class DocumentedValueTarget:
    """One documented name and its prose description.

    Attributes:
        name: Documented parameter, attribute, or value name as written in the documentation.
        description: Description text associated with the documented name.
        line_numbers: One-based source lines occupied by the documentation target.
        extra_generic_sequences: Additional normalized token sequences that are generic for this specific target.
    """

    name: str
    description: str
    line_numbers: tuple[int, ...]
    extra_generic_sequences: frozenset[tuple[str, ...]] = frozenset()


@dataclasses.dataclass(frozen=True)
class DocumentedValueStylePolicy:
    """Generic wording policy for one documented-value kind.

    Attributes:
        nouns: Generic nouns that do not add meaning beyond the documented name.
        message_subject: Lowercase subject used in per-instance diagnostic messages.
    """

    nouns: frozenset[str]
    message_subject: str


def too_generic_violations(targets: tuple[DocumentedValueTarget, ...], *, rule: RuleMetadata, policy: DocumentedValueStylePolicy) -> tuple[rule_violations.RuleViolation, ...]:
    """Return violations for documented-value descriptions that only restate their names.

    Args:
        targets: Documented values to inspect.
        rule: Rule metadata used for diagnostics.
        policy: Wording policy for the documented value kind.

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
        name: Documented parameter or attribute name.
        description: Documentation prose associated with the name.
        policy: Generic nouns accepted by the target kind.
        extra_generic_sequences: Additional normalized token sequences that are generic for this target.

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
    sequences: set[tuple[str, ...]] = {
        name_tokens,
        ("the", *name_tokens),
        ("value", "of", *name_tokens),
        ("the", "value", "of", *name_tokens),
    }
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
