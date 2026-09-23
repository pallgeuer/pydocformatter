"""Public documentation URL helper tests."""

# Third-party imports
import pytest

# First-party imports
from pydocformatter import docs_urls


@pytest.mark.parametrize("text", ["", "---", " / "])
def test_slugify_rejects_text_without_url_safe_content(text: str) -> None:
    """Reject source text that cannot identify a documentation page."""
    with pytest.raises(ValueError, match="Cannot derive slug"):
        docs_urls.slugify(text)


def test_public_docs_url_returns_the_canonical_root_without_parts() -> None:
    """Empty and slash-only components must not add a path below the site root."""
    assert docs_urls.public_docs_url() == docs_urls.PUBLIC_DOCS_URL
    assert docs_urls.public_docs_url("", "/", "//") == docs_urls.PUBLIC_DOCS_URL


def test_public_docs_url_cleans_component_boundaries() -> None:
    """Join non-empty path components with one separator and a trailing slash."""
    assert docs_urls.public_docs_url("/rules/", "PDF/") == f"{docs_urls.PUBLIC_DOCS_URL}rules/PDF/"
