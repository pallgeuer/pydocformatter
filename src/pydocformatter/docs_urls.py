"""Public documentation URL helpers.

Attributes:
    PUBLIC_DOCS_URL (str): Canonical root URL for the published documentation site.
"""

# Future imports
from __future__ import annotations

# Standard library imports
import re


PUBLIC_DOCS_URL = "https://pallgeuer.github.io/pydocformatter/"


def slugify(text: str) -> str:
    """Return a lowercase URL slug for public documentation pages.

    Args:
        text (str): Source text to convert to a URL slug.

    Returns:
        str: Lowercase hyphen-separated slug.

    Raises:
        ValueError: If no URL-safe slug can be derived from the source text.
    """
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    if not slug:
        raise ValueError(f"Cannot derive slug from {text!r}")
    return slug


def public_docs_url(*parts: str) -> str:
    """Return a canonical public documentation URL.

    Args:
        *parts (str): URL path parts to append below the documentation root.

    Returns:
        str: Absolute public documentation URL with a trailing slash.
    """
    cleaned_parts = tuple(part.strip("/") for part in parts if part.strip("/"))
    if not cleaned_parts:
        return PUBLIC_DOCS_URL
    return f"{PUBLIC_DOCS_URL}{'/'.join(cleaned_parts)}/"


def category_url(prefix: str) -> str:
    """Return the public documentation URL for a rule category.

    Args:
        prefix (str): Rule category prefix such as `PDF` or `PCF`.

    Returns:
        str: Absolute public category documentation URL.
    """
    return public_docs_url("rules", prefix.lower())


def rule_url(name: str) -> str:
    """Return the public documentation URL for a rule.

    Args:
        name (str): Rule name from rule metadata.

    Returns:
        str: Absolute public rule documentation URL.
    """
    return public_docs_url("rules", slugify(name))
