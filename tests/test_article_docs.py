"""Technical article documentation tests."""

# Future imports
from __future__ import annotations

# Standard library imports
import pathlib
import tomllib

# Third-party imports
from tools.docs import generate_zensical

# First-party imports
from tests import markdown_example_helpers


ROOT = pathlib.Path(__file__).resolve().parents[1]
ARTICLES_DIR = ROOT / "docs_site" / "articles"
DESIGN_ARTICLE_PATH = ARTICLES_DIR / "why-docstrings-are-hard-to-format-safely.md"
RUFF_ARTICLE_PATH = ARTICLES_DIR / "docstring-formatting-in-a-ruff-project.md"
DEMONSTRATION_PATH = ROOT / "docs_site" / "demonstration.md"


def test_article_navigation_follows_evaluation() -> None:
    """The articles must have a stable top-level navigation group."""
    nav = generate_zensical._nav()
    evaluation_index = nav.index({"Evaluation": [{"Comparison": "comparison.md"}, {"Demonstration": "demonstration.md"}]})

    assert nav[evaluation_index + 1] == {
        "Articles": [
            {"Why docstrings are hard to format safely": "articles/why-docstrings-are-hard-to-format-safely.md"},
            {"Docstring formatting in a Ruff project": "articles/docstring-formatting-in-a-ruff-project.md"},
        ]
    }


def test_ruff_article_uses_canonical_demonstration_configuration() -> None:
    """The practical article must not drift from the executable demonstration."""
    article = RUFF_ARTICLE_PATH.read_text(encoding="utf-8")
    demonstration = DEMONSTRATION_PATH.read_text(encoding="utf-8")
    article_config = tomllib.loads(markdown_example_helpers.marked_fence(article, "ruff-article-config", "toml"))
    demonstration_config = tomllib.loads(markdown_example_helpers.marked_fence(demonstration, "canonical-demo-config", "toml"))

    assert article_config == demonstration_config
    for command in ("uv run ruff check .", "uv run ruff format --check .", "uv run pydocfmt check --diff"):
        assert command in article
        assert command in demonstration
    assert "uv run ruff check --fix ." in article
    assert "uv run ruff format ." in article
    assert "uv run pydocfmt check --fix" in article
    assert "uv run black --check ." in article


def test_articles_are_grounded_and_mutually_discoverable() -> None:
    """Both articles must cite their contracts and lead to adoption resources."""
    design_article = DESIGN_ARTICLE_PATH.read_text(encoding="utf-8")
    ruff_article = RUFF_ARTICLE_PATH.read_text(encoding="utf-8")

    for expected in (
        "https://peps.python.org/pep-0257/",
        "https://docs.python.org/3/reference/datamodel.html",
        "../demonstration.md",
        "../formatting.md#safety-model",
        "../versioning.md#fix-guarantees",
        "docstring-formatting-in-a-ruff-project.md",
        "https://pypi.org/project/pydocformatter/",
        "../project/readme.md",
    ):
        assert expected in design_article
    for expected in (
        "https://docs.astral.sh/ruff/formatter/#docstring-formatting",
        "https://docs.astral.sh/ruff/integrations/",
        "../comparison.md#ruff",
        "../demonstration.md",
        "../rules/ruff-rule-links.md",
        "why-docstrings-are-hard-to-format-safely.md",
        "https://pypi.org/project/pydocformatter/",
        "../project/readme.md",
    ):
        assert expected in ruff_article
    assert "pydocfmt-example" not in design_article
    assert "pydocfmt-example" not in ruff_article


def test_primary_entry_points_cross_link_articles() -> None:
    """Repository and site discovery routes must expose the new articles."""
    design_url = "https://pallgeuer.github.io/pydocformatter/articles/why-docstrings-are-hard-to-format-safely/"
    ruff_url = "https://pallgeuer.github.io/pydocformatter/articles/docstring-formatting-in-a-ruff-project/"
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert design_url in readme
    assert ruff_url in readme
    required_links = {
        "docs_site/index.md": ("articles/why-docstrings-are-hard-to-format-safely.md", "articles/docstring-formatting-in-a-ruff-project.md"),
        "docs_site/comparison.md": ("articles/why-docstrings-are-hard-to-format-safely.md", "articles/docstring-formatting-in-a-ruff-project.md"),
        "docs_site/demonstration.md": ("articles/why-docstrings-are-hard-to-format-safely.md", "articles/docstring-formatting-in-a-ruff-project.md"),
        "docs_site/formatting.md": ("articles/why-docstrings-are-hard-to-format-safely.md",),
        "docs_site/faq.md": ("articles/docstring-formatting-in-a-ruff-project.md",),
    }
    for relative_path, targets in required_links.items():
        source = (ROOT / relative_path).read_text(encoding="utf-8")
        for target in targets:
            assert target in source, relative_path
