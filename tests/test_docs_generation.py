"""Documentation site generation tests."""

# Future imports
from __future__ import annotations

# Standard library imports
import html
import types
import typing
import pathlib
import tomllib
import dataclasses

# Third-party imports
import pytest
import markdown as markdown_core
from la_dev_codex_plugins import markdown_tables
from tools.docs import generate_zensical

# First-party imports
import pydocformatter.rules.collection as rule_collection
import pydocformatter.rules.documentation as rule_documentation
from pydocformatter import docs_urls
from pydocformatter.cli import settings_check
from pydocformatter.rules.codes import RuleSelector
from pydocformatter.rules.models import RuleSettingEffect, RuleSettingEffects
from tests import markdown_table_helpers


ROOT = pathlib.Path(__file__).resolve().parents[1]
FORBIDDEN_DOCS_DEPENDENCIES = {"mdformat", "mkdocs", "mkdocs-material", "mkdocs-redirects", "mkdocstrings", "mkdocstrings-python", "properdocs"}
RULE_TABLE_HEADERS = ("Code", "Name", "Summary", "Fix available", "Enabled")
RULE_TABLE_WRAPPER = '<div class="pydocformatter-rule-table-wrapper" markdown="1">'
SETTINGS_TABLE_WRAPPER = '<div class="pydocformatter-settings-table-wrapper" markdown="1">'


def _render_markdown(text: str) -> str:
    """Render Markdown with the generated site's tabbed-example extensions."""
    return markdown_core.markdown(text, extensions=["pymdownx.superfences", "pymdownx.tabbed"], extension_configs={"pymdownx.tabbed": {"alternate_style": True}})


def _normalized_dependency_name(dependency: str) -> str:
    """Return the normalized project name from a dependency specifier."""
    name = dependency.split("[", maxsplit=1)[0]
    for separator in ("<", ">", "=", "!", "~", ";"):
        name = name.split(separator, maxsplit=1)[0]
    return name.strip().lower().replace("_", "-")


def _docstring_convention_effects(rule_class: type[typing.Any]) -> dict[settings_check.DocstringConvention, RuleSettingEffect]:
    """Return convention effects declared by one rule class."""
    return {convention: effect for convention in settings_check.DocstringConvention if (effect := rule_class.meta.setting_effect("docstring_convention", convention)) is not None}


def _requires_explicit(rule_class: type[typing.Any]) -> bool:
    """Return whether the default require-explicit selectors match a rule class."""
    return any(RuleSelector(selector).selects_code(rule_class.meta.code) for selector in settings_check.DEFAULT_REQUIRE_EXPLICIT)


def test_runtime_rule_url_slug_matches_generated_rule_page_slug() -> None:
    """Runtime rule URLs must use the same slugs as generated rule pages."""
    page_by_code = {page.code: page for page in generate_zensical.rule_pages()}

    for rule_class in rule_collection.RULE_COLLECTION.rules:
        rule = rule_class.meta
        assert docs_urls.rule_url(rule.name) == f"{docs_urls.PUBLIC_DOCS_URL}{page_by_code[rule.code.tag].path.with_suffix('').as_posix()}/"


@pytest.fixture
def generated_site(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> tuple[pathlib.Path, pathlib.Path]:
    """Generate the documentation site source into a temporary directory."""
    generated_root = tmp_path / ".generated" / "zensical"
    generated_docs_dir = generated_root / "docs"
    generated_config_path = tmp_path / "zensical.generated.toml"
    monkeypatch.setattr(generate_zensical, "GENERATED_ROOT", generated_root)
    monkeypatch.setattr(generate_zensical, "GENERATED_DOCS_DIR", generated_docs_dir)
    monkeypatch.setattr(generate_zensical, "GENERATED_CONFIG_PATH", generated_config_path)

    generate_zensical.generate()

    return generated_docs_dir, generated_config_path


def test_generated_markdown_tables_use_canonical_style(generated_site: tuple[pathlib.Path, pathlib.Path]) -> None:
    """Every generated Markdown table must already use the shared canonical style."""
    generated_docs_dir, _ = generated_site
    failures = []
    for path in generated_docs_dir.rglob("*.md"):
        result = markdown_tables.format_markdown_tables_file(path, check=True)
        failures.extend((*result.changes, *result.issues))

    assert not failures


def test_rule_pages_have_unique_slugs() -> None:
    """Generated rule slugs must be unique."""
    pages = generate_zensical.rule_pages()
    slugs = [page.slug for page in pages]

    assert len(slugs) == len(set(slugs))


def test_rule_pages_follow_rule_collection_order() -> None:
    """Generated rule page metadata must follow built-in rule order."""
    pages = generate_zensical.rule_pages()

    assert tuple(page.code for page in pages) == tuple(rule_class.meta.code.tag for rule_class in rule_collection.RULE_COLLECTION.rules)
    assert all(page.path == pathlib.Path("rules") / f"{page.slug}.md" for page in pages)


def test_rule_index_contains_all_rules(generated_site: tuple[pathlib.Path, pathlib.Path]) -> None:
    """The generated rule index must link every built-in rule."""
    generated_docs_dir, _ = generated_site
    markdown = (generated_docs_dir / "rules.md").read_text(encoding="utf-8")

    for page in generate_zensical.rule_pages():
        assert f"[`{page.code}`](rules/{page.slug}.md)" in markdown


def test_rule_index_lists_categories_with_prefix_first(generated_site: tuple[pathlib.Path, pathlib.Path]) -> None:
    """The generated rule index category list must prefix linked category names with rule codes."""
    generated_docs_dir, _ = generated_site
    markdown = (generated_docs_dir / "rules.md").read_text(encoding="utf-8")

    assert "## Rule categories" in markdown
    for category_class in rule_collection.RULE_COLLECTION.categories:
        category = category_class.meta
        assert f"- [{category.prefix}: {category.name}](rules/{category.prefix.lower()}.md)" in markdown
        assert f"[{category.name} (`{category.prefix}`)]" not in markdown


def test_rule_index_groups_all_rules_by_category(generated_site: tuple[pathlib.Path, pathlib.Path]) -> None:
    """The generated all-rules section must contain one table per rule category."""
    generated_docs_dir, _ = generated_site
    markdown = (generated_docs_dir / "rules.md").read_text(encoding="utf-8")

    for category_class in rule_collection.RULE_COLLECTION.categories:
        category = category_class.meta
        heading = f"### {category.prefix}: {category.name}"
        _, section_after_heading = markdown.split(heading, maxsplit=1)
        section = section_after_heading.split("\n### ", maxsplit=1)[0]
        table = markdown_table_helpers.table_after_heading(markdown, heading, label="generated rules Markdown", expected_leading_lines=(RULE_TABLE_WRAPPER,))

        assert section.count('<div class="pydocformatter-rule-table-wrapper" markdown="1">') == 1
        assert markdown_table_helpers.table_headers(table, label="generated rules Markdown") == RULE_TABLE_HEADERS
        for rule_class in rule_collection.RULE_COLLECTION.rules:
            rule = rule_class.meta
            if rule.code.prefix == category.prefix:
                assert f"[`{rule.code}`]" in section
            else:
                assert f"[`{rule.code}`]" not in section


def test_rule_index_labels_convention_rules(generated_site: tuple[pathlib.Path, pathlib.Path]) -> None:
    """The generated rule index must identify convention-dependent rules."""
    generated_docs_dir, _ = generated_site
    markdown = (generated_docs_dir / "rules.md").read_text(encoding="utf-8")
    convention_rule_codes: list[str] = []

    for rule_class in rule_collection.RULE_COLLECTION.rules:
        convention_effects = _docstring_convention_effects(rule_class)
        if (
            convention_effects
            and not _requires_explicit(rule_class)
            and any(convention_effects.get(convention) not in {RuleSettingEffect.IGNORED, RuleSettingEffect.DISABLED} for convention in settings_check.DocstringConvention)
        ):
            convention_rule_codes.append(rule_class.meta.code.tag)
            assert generate_zensical._enabled_text(rule_class) == "Convention"

    assert convention_rule_codes
    rows = tuple(
        row
        for table in markdown_table_helpers.tables_with_headers(markdown, RULE_TABLE_HEADERS, label="generated rules Markdown")
        for row in markdown_table_helpers.table_rows(table, label="generated rules Markdown")
    )
    assert sum(row["Enabled"] == "Convention" for row in rows) == len(convention_rule_codes)
    assert all(row["Enabled"] != "Convention-gated" for row in rows)


def test_rule_index_labels_convention_opt_in_rules(generated_site: tuple[pathlib.Path, pathlib.Path]) -> None:
    """The generated rule index must identify rules removed by every convention."""
    generated_docs_dir, _ = generated_site
    markdown = (generated_docs_dir / "rules.md").read_text(encoding="utf-8")
    convention_opt_in_rule_codes: list[str] = []

    for rule_class in rule_collection.RULE_COLLECTION.rules:
        convention_effects = _docstring_convention_effects(rule_class)
        if convention_effects and all(convention_effects.get(convention) in {RuleSettingEffect.IGNORED, RuleSettingEffect.DISABLED} for convention in settings_check.DocstringConvention):
            convention_opt_in_rule_codes.append(rule_class.meta.code.tag)
            assert generate_zensical._enabled_text(rule_class) == "Convention opt-in"

    assert convention_opt_in_rule_codes
    rows = tuple(
        row
        for table in markdown_table_helpers.tables_with_headers(markdown, RULE_TABLE_HEADERS, label="generated rules Markdown")
        for row in markdown_table_helpers.table_rows(table, label="generated rules Markdown")
    )
    assert sum(row["Enabled"] == "Convention opt-in" for row in rows) == len(convention_opt_in_rule_codes)
    assert "Convention-explicit" not in markdown


def test_rule_index_labels_require_explicit_rules(generated_site: tuple[pathlib.Path, pathlib.Path]) -> None:
    """The generated rule index must identify every default require-explicit rule."""
    generated_docs_dir, _ = generated_site
    markdown = (generated_docs_dir / "rules.md").read_text(encoding="utf-8")
    require_explicit_rule_codes: list[str] = []

    for rule_class in rule_collection.RULE_COLLECTION.rules:
        if _requires_explicit(rule_class):
            require_explicit_rule_codes.append(rule_class.meta.code.tag)
            assert generate_zensical._enabled_text(rule_class) == "Requires explicit"

    assert require_explicit_rule_codes
    rows = tuple(
        row
        for table in markdown_table_helpers.tables_with_headers(markdown, RULE_TABLE_HEADERS, label="generated rules Markdown")
        for row in markdown_table_helpers.table_rows(table, label="generated rules Markdown")
    )
    assert sum(row["Enabled"] == "Requires explicit" for row in rows) == len(require_explicit_rule_codes)


def test_rule_index_explains_table_columns(generated_site: tuple[pathlib.Path, pathlib.Path]) -> None:
    """The generated rule index must explain compact table labels."""
    generated_docs_dir, _ = generated_site
    markdown = (generated_docs_dir / "rules.md").read_text(encoding="utf-8")
    explanation = markdown.split("### PCF:", maxsplit=1)[0]

    assert '<a id="rule-table-columns"></a>' in explanation
    assert "The `Fix available` column" in explanation
    assert "The `Enabled` column" in explanation
    for value in ("Always", "Usually", "Sometimes", "Never", "By default", "Requires explicit", "Convention", "Convention opt-in", "Setting-gated"):
        assert f"- `{value}`:" in explanation


def test_enabled_text_values_are_documented(generated_site: tuple[pathlib.Path, pathlib.Path]) -> None:
    """Every generated enabled-state label must be documented."""
    generated_docs_dir, _ = generated_site
    markdown = (generated_docs_dir / "rules.md").read_text(encoding="utf-8")
    explanation = markdown.split("### PCF:", maxsplit=1)[0]
    by_default_rule = next(rule_class for rule_class in rule_collection.RULE_COLLECTION.rules if generate_zensical._enabled_text(rule_class) == "By default")
    fake_setting_gated_rule = types.SimpleNamespace(meta=dataclasses.replace(by_default_rule.meta, setting_effects=(RuleSettingEffects(setting="future_setting", effects=()),)))
    labels = {generate_zensical._enabled_text(rule_class) for rule_class in rule_collection.RULE_COLLECTION.rules}
    labels.add(generate_zensical._enabled_text(typing.cast("type[typing.Any]", fake_setting_gated_rule)))

    for label in labels:
        assert f"- `{label}`:" in explanation


def test_category_pages_include_category_rules(generated_site: tuple[pathlib.Path, pathlib.Path]) -> None:
    """Generated category pages must include their registered rules."""
    generated_docs_dir, _ = generated_site

    for category_class in rule_collection.RULE_COLLECTION.categories:
        category = category_class.meta
        markdown = (generated_docs_dir / "rules" / f"{category.prefix.lower()}.md").read_text(encoding="utf-8")
        assert '<div class="pydocformatter-rule-table-wrapper" markdown="1">' in markdown
        assert "See [rule table column explanations](../rules.md#rule-table-columns)." in markdown
        for rule_class in rule_collection.RULE_COLLECTION.rules:
            if rule_class.meta.code.prefix == category.prefix:
                assert f"[`{rule_class.meta.code}`]" in markdown


def test_category_pages_include_first_and_last_rule_navigation(generated_site: tuple[pathlib.Path, pathlib.Path]) -> None:
    """Generated category pages must link their first and last rules at the top and bottom."""
    generated_docs_dir, _ = generated_site
    page_by_code = {page.code: page for page in generate_zensical.rule_pages()}

    for category_class in rule_collection.RULE_COLLECTION.categories:
        category = category_class.meta
        category_rules = tuple(rule_class.meta for rule_class in rule_collection.RULE_COLLECTION.rules if rule_class.meta.code.prefix == category.prefix)
        first_page = page_by_code[category_rules[0].code.tag]
        last_page = page_by_code[category_rules[-1].code.tag]
        markdown = (generated_docs_dir / "rules" / f"{category.prefix.lower()}.md").read_text(encoding="utf-8")

        assert markdown.count('<nav class="pydocformatter-rule-nav pydocformatter-rule-nav--top" aria-label="Category rule navigation">') == 1
        assert markdown.count('<nav class="pydocformatter-rule-nav pydocformatter-rule-nav--bottom" aria-label="Category rule navigation">') == 1
        assert markdown.count(f'href="{first_page.slug}.md"') == 2
        assert markdown.count(f"<code>{first_page.code}</code> {first_page.name}") == 2
        assert markdown.count(f'href="{last_page.slug}.md"') == 2
        assert markdown.count(f"<code>{last_page.code}</code> {last_page.name}") == 2
        assert markdown.count("First rule") == 4
        assert markdown.count("Last rule") == 4
        assert "&larr; First rule" not in markdown
        assert "Last rule &rarr;" not in markdown


def test_category_pages_include_directional_quick_links(generated_site: tuple[pathlib.Path, pathlib.Path]) -> None:
    """Generated category pages must link down to their table and back to all rules."""
    generated_docs_dir, _ = generated_site

    for category_class in rule_collection.RULE_COLLECTION.categories:
        category = category_class.meta
        markdown = (generated_docs_dir / "rules" / f"{category.prefix.lower()}.md").read_text(encoding="utf-8")

        jump_link = "[Jump to rule table &darr;](#rules-in-this-category)"
        assert markdown.count(jump_link) == 1
        assert markdown.index(jump_link) < markdown.index("## What it does")
        assert markdown.count("[&larr; Back to all rules](../rules.md)") == 1


def test_rule_pages_include_source_links(generated_site: tuple[pathlib.Path, pathlib.Path]) -> None:
    """Generated rule pages must link implementation and Markdown sources."""
    generated_docs_dir, _ = generated_site
    first_page = generate_zensical.rule_pages()[0]
    markdown = (generated_docs_dir / first_page.path).read_text(encoding="utf-8")

    assert "View source" in markdown
    assert "View documentation source" in markdown
    assert "https://github.com/pallgeuer/pydocformatter/blob/main/src/pydocformatter/rules/definitions/" in markdown


def test_rule_pages_include_previous_and_next_rule_navigation(generated_site: tuple[pathlib.Path, pathlib.Path]) -> None:
    """Generated rule pages must link adjacent rules in collection order."""
    generated_docs_dir, _ = generated_site
    pages = generate_zensical.rule_pages()
    first_page = pages[0]
    middle_index = len(pages) // 2
    middle_page = pages[middle_index]
    last_page = pages[-1]

    first_markdown = (generated_docs_dir / first_page.path).read_text(encoding="utf-8")
    middle_markdown = (generated_docs_dir / middle_page.path).read_text(encoding="utf-8")
    last_markdown = (generated_docs_dir / last_page.path).read_text(encoding="utf-8")

    assert first_markdown.count('<nav class="pydocformatter-rule-nav pydocformatter-rule-nav--top" aria-label="Rule navigation">') == 1
    assert first_markdown.count('<nav class="pydocformatter-rule-nav pydocformatter-rule-nav--bottom" aria-label="Rule navigation">') == 1
    assert "pydocformatter-rule-nav__link--previous" not in first_markdown
    assert first_markdown.count(f'href="{pages[1].slug}.md"') == 2
    assert first_markdown.count(f"<code>{pages[1].code}</code> {pages[1].name}") == 2

    assert middle_markdown.count(f'href="{pages[middle_index - 1].slug}.md"') == 2
    assert middle_markdown.count(f'href="{pages[middle_index + 1].slug}.md"') == 2
    assert middle_markdown.count("&larr; Previous rule") == 4
    assert middle_markdown.count("Next rule &rarr;") == 4

    assert last_markdown.count(f'href="{pages[-2].slug}.md"') == 2
    assert last_markdown.count(f"<code>{pages[-2].code}</code> {pages[-2].name}") == 2
    assert "pydocformatter-rule-nav__link--next" not in last_markdown


def test_rule_examples_are_transformed(generated_site: tuple[pathlib.Path, pathlib.Path]) -> None:
    """Structured rule examples must become web-friendly content tabs."""
    generated_docs_dir, _ = generated_site
    first_page = generate_zensical.rule_pages()[0]
    markdown = (generated_docs_dir / first_page.path).read_text(encoding="utf-8")

    assert "```pydocfmt-example" not in markdown
    assert '===+ "Before"' in markdown
    assert "```python" in markdown


def test_all_generated_pydocfmt_examples_are_transformed(generated_site: tuple[pathlib.Path, pathlib.Path]) -> None:
    """Every generated Markdown page must convert structured pydocfmt examples."""
    generated_docs_dir, _ = generated_site
    offenders = sorted(path.relative_to(generated_docs_dir).as_posix() for path in generated_docs_dir.rglob("*.md") if "```pydocfmt-example" in path.read_text(encoding="utf-8"))

    assert offenders == []


def test_readme_examples_generate_valid_tab_sets(generated_site: tuple[pathlib.Path, pathlib.Path]) -> None:
    """README examples must render the tabs declared by each example."""
    generated_docs_dir, _ = generated_site
    source = (ROOT / "README.md").read_text(encoding="utf-8")
    examples = rule_documentation.parse_rule_markdown_examples(source, rule_code="README")
    markdown = (generated_docs_dir / "project" / "readme.md").read_text(encoding="utf-8")

    assert examples
    assert "```pydocfmt-example" not in markdown
    for example in examples:
        tabs = generate_zensical._example_tabs(example)
        assert tabs in markdown
        assert tabs.count('=== "Settings"') == bool(example.settings_text)
        assert tabs.count('===+ "Before') == 1
        assert tabs.count('=== "After"') == (example.input_source != example.output_source)
        assert tabs.count('=== "Findings"') == bool(example.findings)
        assert _render_markdown(tabs).count('class="tabbed-set') == 1


def test_reference_pydocfmt_examples_are_transformed(generated_site: tuple[pathlib.Path, pathlib.Path]) -> None:
    """Structured examples in copied reference docs must become content tabs."""
    generated_docs_dir, _ = generated_site
    markdown = (generated_docs_dir / "reference" / "rule-suppressions.md").read_text(encoding="utf-8")

    assert "```pydocfmt-example" not in markdown
    assert '=== "Settings"' in markdown
    assert '===+ "Before = After"' in markdown


def test_adjacent_pydocfmt_examples_generate_separate_tab_sets() -> None:
    """Adjacent structured examples must not merge into one tabbed set."""
    source = """```pydocfmt-example
[settings]
select = ["PCF000"]

[input]
# first

[output=unchanged]
```

```pydocfmt-example
[settings]
select = ["PCF001"]

[input]
value = 1 # comment

[output=unchanged]
```
"""
    transformed = generate_zensical._transform_pydocfmt_examples(source, context="TEST")

    assert transformed.count(generate_zensical.EXAMPLE_TABS_SEPARATOR) == 1
    assert transformed.count('=== "Settings"') == 2
    assert _render_markdown(transformed).count('class="tabbed-set') == 2


def test_generated_adjacent_examples_render_as_separate_tab_sets(generated_site: tuple[pathlib.Path, pathlib.Path]) -> None:
    """Generated pages with source-adjacent examples must render one tab set per example."""
    generated_docs_dir, _ = generated_site
    suppressions_source = (ROOT / "docs" / "public" / "rule_suppressions.md").read_text(encoding="utf-8")
    suppressions_markdown = (generated_docs_dir / "reference" / "rule-suppressions.md").read_text(encoding="utf-8")
    pdf502_source = (ROOT / "src" / "pydocformatter" / "rules" / "definitions" / "PDF" / "PDF502_missing_return_documentation.md").read_text(encoding="utf-8")
    pdf502_markdown = (generated_docs_dir / "rules" / "missing-return-documentation.md").read_text(encoding="utf-8")

    assert _render_markdown(suppressions_markdown).count('class="tabbed-set') == len(rule_documentation.parse_rule_markdown_examples(suppressions_source, rule_code="SUPPRESSIONS"))
    assert _render_markdown(pdf502_markdown).count('class="tabbed-set') == len(rule_documentation.parse_rule_markdown_examples(pdf502_source, rule_code="PDF502"))


def test_rule_examples_select_before_tab_when_settings_exist(generated_site: tuple[pathlib.Path, pathlib.Path]) -> None:
    """Generated examples with settings must still select the Before tab by default."""
    generated_docs_dir, _ = generated_site
    page = next(page for page in generate_zensical.rule_pages() if page.code == "PCF000")
    markdown = (generated_docs_dir / page.path).read_text(encoding="utf-8")

    settings_index = markdown.index('=== "Settings"')
    before_index = markdown.index('===+ "Before"')

    assert settings_index < before_index


def test_rule_examples_collapse_unchanged_before_after_tabs(generated_site: tuple[pathlib.Path, pathlib.Path]) -> None:
    """Generated unchanged examples must use a single selected Before equals After tab."""
    generated_docs_dir, _ = generated_site
    page = next(page for page in generate_zensical.rule_pages() if page.code == "PCF000")
    markdown = (generated_docs_dir / page.path).read_text(encoding="utf-8")
    collapsed_section = markdown.split('===+ "Before = After"', maxsplit=1)[1].split("\n===+", maxsplit=1)[0]

    assert '=== "After"' not in collapsed_section


def test_rule_examples_preserve_path_in_collapsed_tab_title(generated_site: tuple[pathlib.Path, pathlib.Path]) -> None:
    """Generated path-sensitive unchanged examples must keep the path in trailing parentheses."""
    generated_docs_dir, _ = generated_site
    page = next(page for page in generate_zensical.rule_pages() if page.code == "PDF520")
    markdown = (generated_docs_dir / page.path).read_text(encoding="utf-8")
    collapsed_section = markdown.split('===+ "Before = After (package/\\_private.py)"', maxsplit=1)[1].split("\n===+", maxsplit=1)[0]

    assert '===+ "Before = After (package/\\_private.py)"' in markdown
    assert "Before = After: package/_private.py" not in markdown
    assert '=== "Findings"' in collapsed_section


def test_rule_examples_put_path_titles_in_trailing_parentheses() -> None:
    """Path-specific changed examples must use trailing parentheses in tab titles."""
    example = rule_documentation.RuleMarkdownExample(path="package/module.py", settings_text="", input_source="before\n", output_source="after\n", findings=())

    assert '===+ "Before (package/module.py)"' in generate_zensical._example_tabs(example)


def test_rule_examples_escape_markdown_in_path_titles() -> None:
    """Path-specific examples must render Markdown-sensitive path characters literally."""
    example = rule_documentation.RuleMarkdownExample(path="package/__init__.py", settings_text="", input_source="before\n", output_source="after\n", findings=())

    assert '===+ "Before (package/\\_\\_init\\_\\_.py)"' in generate_zensical._example_tabs(example)


def test_rule_options_link_to_settings(generated_site: tuple[pathlib.Path, pathlib.Path]) -> None:
    """Generated rule Options entries must link setting names to Settings headings."""
    generated_docs_dir, _ = generated_site
    page = next(page for page in generate_zensical.rule_pages() if page.code == "PCF000")
    markdown = (generated_docs_dir / page.path).read_text(encoding="utf-8")

    assert "- [`line-length`](../settings.md#line-length):" in markdown
    assert "- `line-length`:" not in markdown


def test_category_options_link_to_settings(generated_site: tuple[pathlib.Path, pathlib.Path]) -> None:
    """Generated category Options tables must link setting names to Settings headings."""
    generated_docs_dir, _ = generated_site
    markdown = (generated_docs_dir / "rules" / "pcf.md").read_text(encoding="utf-8")

    assert "| [`line-length`](../settings.md#line-length)" in markdown
    assert "| `line-length`" not in markdown


def test_category_options_link_only_the_structural_first_cell() -> None:
    """Link the parsed first cell without replacing matching text in later cells."""
    markdown = "## Options\n\n| Setting | Effect |\n|---------|--------|\n| `line-length` | Compare `line-length` values. |"

    linked = generate_zensical._link_options_settings(markdown, settings_path="../settings.md", context="example")

    assert "| [`line-length`](../settings.md#line-length) | Compare `line-length` values. |" in linked


def test_option_table_link_rejects_inconsistent_first_cell_structure() -> None:
    """Reject a parsed first cell that is not positioned as the source row's first cell."""
    with pytest.raises(ValueError, match="does not match its source row structure"):
        generate_zensical._link_option_table_setting_cell("prefix `line-length` | Effect |", "`line-length`", settings_path="../settings.md", context="example")


def test_rule_page_footer_tags_order_category_before_code(generated_site: tuple[pathlib.Path, pathlib.Path]) -> None:
    """Generated rule page tag chips must list category, rule code, then rule name."""
    generated_docs_dir, _ = generated_site
    first_page = generate_zensical.rule_pages()[0]
    markdown = (generated_docs_dir / first_page.path).read_text(encoding="utf-8")
    _, frontmatter, _ = markdown.split("---\n", maxsplit=2)

    assert f"tags:\n  - {first_page.category_prefix}\n  - {first_page.code}\n  - {first_page.name}\n" in frontmatter


def test_settings_markdown_contains_schema_settings() -> None:
    """Generated settings Markdown must include every schema definition."""
    markdown = generate_zensical._settings_markdown(generate_zensical.rule_pages())

    for definition in settings_check.SETTINGS_SCHEMA.definitions:
        setting_name = definition.key if definition.available_in_toml else definition.field
        assert f"### `{setting_name}`" in markdown


def test_settings_markdown_explains_table_columns() -> None:
    """Generated settings Markdown must explain table columns and CLI help."""
    markdown = generate_zensical._settings_markdown(generate_zensical.rule_pages())
    introduction = markdown.split("\n## ", maxsplit=1)[0]

    for expected in ("`Setting` column", "TOML key", "`CLI` column", "`pydocfmt check` flag", "`pydocfmt check --help`", "`pydocfmt config`", "`pydocfmt config require-explicit`"):
        assert expected in introduction


def test_settings_markdown_tables_are_compact_without_scope() -> None:
    """Generated settings Markdown must use compact tables without scope text."""
    markdown = generate_zensical._settings_markdown(generate_zensical.rule_pages())
    tables = markdown_table_helpers.validate_tables(markdown, label="generated settings Markdown")

    assert '<div class="pydocformatter-settings-table-wrapper" markdown="1">' in markdown
    assert any(markdown_table_helpers.table_headers(table, label="generated settings Markdown") == ("Setting", "CLI", "Type", "Default", "Related rules") for table in tables)
    assert all("Scope" not in markdown_table_helpers.table_headers(table, label="generated settings Markdown") for table in tables)
    assert "- Scope:" not in markdown
    assert "[Settings specification](reference/settings-spec.md)" in markdown
    assert "[Settings spec](reference/settings-spec.md)" not in markdown


def test_settings_markdown_tables_have_consistent_cell_counts() -> None:
    """Generated settings tables must satisfy the full parser contract."""
    markdown = generate_zensical._settings_markdown(generate_zensical.rule_pages())
    tables = markdown_table_helpers.validate_tables(markdown, label="generated settings Markdown")

    assert len(tables) == len(settings_check.SettingsGroup)
    assert all(markdown_table_helpers.table_headers(table, label="generated settings Markdown")[:4] == ("Setting", "CLI", "Type", "Default") for table in tables)


def test_settings_markdown_enum_type_table_cells_render_readable_pipes() -> None:
    """Generated enum type cells must render pipe separators without visible escapes."""
    markdown = generate_zensical._settings_markdown(generate_zensical.rule_pages())
    rows = (
        row for table in markdown_tables.parse_markdown_tables(markdown) for row in markdown_table_helpers.table_rows(table, label="generated settings Markdown") if row["Setting"] == "`line-ending`"
    )
    row = next(rows)
    rendered = html.unescape(markdown_core.markdown(f"| Type |\n| --- |\n| {row['Type']} |\n", extensions=["tables"]))

    assert "<code>auto | lf | cr-lf | native</code>" in rendered
    assert "\\|" not in rendered


def test_settings_markdown_omits_empty_related_rules_table_columns() -> None:
    """Generated settings tables must omit unused Related rules columns."""
    markdown = generate_zensical._settings_markdown(generate_zensical.rule_pages())
    related_rules_by_field = generate_zensical._related_rules_by_field()

    for group in settings_check.SettingsGroup:
        definitions = [definition for definition in settings_check.SETTINGS_SCHEMA.definitions if definition.group == group]
        if not definitions:
            continue
        table = markdown_table_helpers.table_after_heading(markdown, f"## {group.value}", label="generated settings Markdown", expected_leading_lines=(SETTINGS_TABLE_WRAPPER,))
        headers = markdown_table_helpers.table_headers(table, label="generated settings Markdown")
        has_related_rules = any(definition.field in related_rules_by_field for definition in definitions)
        if has_related_rules:
            assert headers == ("Setting", "CLI", "Type", "Default", "Related rules")
        else:
            assert headers == ("Setting", "CLI", "Type", "Default")


def test_settings_markdown_links_related_rules() -> None:
    """Generated settings Markdown must link related rules to generated rule pages."""
    pages = generate_zensical.rule_pages()
    markdown = generate_zensical._settings_markdown(pages)
    page_by_code = {page.code: page for page in pages}

    for rule_class in rule_collection.RULE_COLLECTION.rules:
        if rule_class.meta.setting_effects:
            code = rule_class.meta.code.tag
            assert f"[`{code}`]({page_by_code[code].path.as_posix()})" in markdown
            break
    else:
        raise AssertionError("Expected at least one rule with setting effects")


def test_settings_related_rules_include_documented_rule_options() -> None:
    """Generated settings related rules must include rule Markdown option references."""
    field_by_key = {definition.key: definition.field for definition in settings_check.SETTINGS_SCHEMA.definitions if definition.available_in_toml}
    related_rules_by_field = generate_zensical._related_rules_by_field()
    documented_rule_count = 0

    for rule_class in rule_collection.RULE_COLLECTION.rules:
        rule_code = rule_class.meta.code.tag
        documented_fields = generate_zensical._documented_related_setting_fields(rule_class, field_by_key)
        if documented_fields:
            documented_rule_count += 1
        for field in documented_fields:
            assert rule_code in related_rules_by_field[field]

    assert documented_rule_count > 0


def test_settings_markdown_truncates_long_related_rule_lists() -> None:
    """Generated settings tables must truncate long related-rule lists."""
    page_by_code = {page.code: page for page in generate_zensical.rule_pages()}
    related_rules = generate_zensical._related_rules_by_field()["docstring_convention"]
    links = generate_zensical._related_rule_links(related_rules, page_by_code, limit=4)

    assert len(related_rules) > 4
    assert links.endswith(", ...")
    assert related_rules[3] in links
    assert related_rules[4] not in links


def test_settings_markdown_detail_sections_list_all_related_rules() -> None:
    """Generated setting detail sections must list all related rules."""
    page_by_code = {page.code: page for page in generate_zensical.rule_pages()}
    related_rules = generate_zensical._related_rules_by_field()["docstring_convention"]
    links = generate_zensical._related_rule_links(related_rules, page_by_code)

    assert not links.endswith(", ...")
    assert related_rules[-1] in links


def test_reference_doc_map_covers_all_public_docs() -> None:
    """Every public docs Markdown file must have a generated reference path."""
    discovered = {path.relative_to(ROOT) for path in (ROOT / "docs" / "public").rglob("*.md")}
    expected = set(generate_zensical.REFERENCE_DOCS)

    assert discovered == expected
    assert not tuple((ROOT / "docs").glob("*.md"))
    assert all(path.is_relative_to(pathlib.Path("docs/public")) for path in expected)


def test_persistent_cache_reference_is_published_with_rewritten_links(generated_site: tuple[pathlib.Path, pathlib.Path]) -> None:
    """The dedicated cache reference must be copied into the generated public site."""
    generated_docs_dir, _ = generated_site
    cache_reference = generated_docs_dir / "reference" / "cache.md"

    assert cache_reference.is_file()
    text = cache_reference.read_text(encoding="utf-8")
    assert "## Positive-hit contract" in text
    assert "## Population and mode reuse" in text
    assert "## Failures, portability, and trust" in text
    assert "[Settings specification](settings-spec.md#persistent-clean-proof-cache)" in text
    assert "[File selection](file-selection.md#file-selection-algorithm)" in text


def test_devel_docs_are_not_copied(generated_site: tuple[pathlib.Path, pathlib.Path]) -> None:
    """Development-only docs must not be copied into the generated site."""
    generated_docs_dir, _ = generated_site

    assert not (generated_docs_dir / "reference" / "rule-implementation.md").exists()
    assert not (generated_docs_dir / "devel").exists()


def test_project_docs_are_copied(generated_site: tuple[pathlib.Path, pathlib.Path]) -> None:
    """Configured public project documents must be copied into the generated site."""
    generated_docs_dir, _ = generated_site

    for generated in generate_zensical.PROJECT_DOCS.values():
        assert (generated_docs_dir / generated).is_file()
    assert not (generated_docs_dir / "project" / "release.md").exists()


def test_contributing_release_process_is_removed_from_public_copy(generated_site: tuple[pathlib.Path, pathlib.Path]) -> None:
    """Public contributing docs must omit maintainer-only release instructions."""
    generated_docs_dir, _ = generated_site
    contributing_text = (generated_docs_dir / "project" / "contributing.md").read_text(encoding="utf-8")

    assert "Release Process" not in contributing_text
    assert "Release process" not in contributing_text
    assert "release checklist" not in contributing_text


@pytest.mark.parametrize(("target", "expected"), [("CONTRIBUTING.md", "contributing.md"), ("CHANGELOG.md", "changelog.md"), ("LICENSE.md", "license.md")])
def test_links_between_moved_docs_are_rewritten(target: str, expected: str) -> None:
    """Relative links between copied public docs must be rewritten to generated paths."""
    rewritten = generate_zensical._rewrite_link_target(target, source=pathlib.Path("README.md"), generated=pathlib.Path("project/readme.md"))

    assert rewritten == expected


def test_generated_readme_uses_absolute_project_document_links(generated_site: tuple[pathlib.Path, pathlib.Path]) -> None:
    """Generated README project links must remain valid without a relative base URL."""
    generated_docs_dir, _ = generated_site
    readme_text = (generated_docs_dir / "project" / "readme.md").read_text(encoding="utf-8")

    assert "[Contributing](https://pallgeuer.github.io/pydocformatter/project/contributing/)" in readme_text
    assert "[Changelog](https://pallgeuer.github.io/pydocformatter/project/changelog/)" in readme_text
    assert "[GNU General Public License v3.0 or later](https://pallgeuer.github.io/pydocformatter/project/license/)" in readme_text
    assert "](CONTRIBUTING.md)" not in readme_text
    assert "](CHANGELOG.md)" not in readme_text
    assert "](LICENSE.md)" not in readme_text


def test_links_from_rule_docs_to_moved_docs_are_rewritten(generated_site: tuple[pathlib.Path, pathlib.Path]) -> None:
    """Relative links from rule docs to copied public docs must be rewritten to generated paths."""
    generated_docs_dir, _ = generated_site
    unused_suppression_text = (generated_docs_dir / "rules" / "unused-suppression.md").read_text(encoding="utf-8")

    assert "[Rule suppressions](../reference/rule-suppressions.md)" in unused_suppression_text
    assert "../../../../../docs/public/rule_suppressions.md" not in unused_suppression_text


def test_copied_markdown_lists_render_as_lists(generated_site: tuple[pathlib.Path, pathlib.Path]) -> None:
    """Copied project Markdown lists must remain lists in the generated site renderer."""
    generated_docs_dir, _ = generated_site
    readme_text = (generated_docs_dir / "project" / "readme.md").read_text(encoding="utf-8")
    html = _render_markdown(readme_text)

    assert "## What it does\n\n- Reflows docstring and comment prose" in readme_text
    assert "<p>- Reflows docstring and comment prose" not in html
    assert "<li>Reflows docstring and comment prose" in html


def test_markdown_list_separation_skips_fenced_code() -> None:
    """List spacing normalization must not rewrite fenced code examples."""
    markdown = "**Options:**\n- parsed\n\n```text\nlabel:\n- literal\n```\n"
    transformed = generate_zensical._separate_markdown_lists(markdown)

    assert transformed.startswith("**Options:**\n\n- parsed")
    assert "label:\n- literal" in transformed


def test_external_source_docs_link_to_github(generated_site: tuple[pathlib.Path, pathlib.Path]) -> None:
    """Links to intentionally unpublished source docs must point to GitHub."""
    del generated_site
    target = generate_zensical._rewrite_link_target("RELEASE.md", source=pathlib.Path("CONTRIBUTING.md"), generated=pathlib.Path("project/contributing.md"))

    assert target == "https://github.com/pallgeuer/pydocformatter/blob/main/RELEASE.md"


def test_generated_config_has_expected_site_url(generated_site: tuple[pathlib.Path, pathlib.Path]) -> None:
    """The generated Zensical config must point at the GitHub Pages site."""
    _, generated_config_path = generated_site
    config = tomllib.loads(generated_config_path.read_text(encoding="utf-8"))

    assert config["project"]["site_url"] == generate_zensical.SITE_URL


def test_generated_config_uses_zensical_paths(generated_site: tuple[pathlib.Path, pathlib.Path]) -> None:
    """The generated config must use Zensical-owned generated paths."""
    _, generated_config_path = generated_site
    config = tomllib.loads(generated_config_path.read_text(encoding="utf-8"))

    assert generated_config_path.name == "zensical.generated.toml"
    assert config["project"]["docs_dir"] == ".generated/zensical/docs"
    assert "edit_uri" not in config["project"]
    assert "content.action.view" not in config["project"]["theme"]["features"]


def test_generated_config_uses_expected_nav_labels(generated_site: tuple[pathlib.Path, pathlib.Path]) -> None:
    """The generated config must use expected navigation labels."""
    _, generated_config_path = generated_site
    text = generated_config_path.read_text(encoding="utf-8")
    config = tomllib.loads(text)
    nav = config["project"]["nav"]
    rules_nav = next(item["Rules"] for item in nav if "Rules" in item)
    reference_nav = next(item["Reference"] for item in nav if "Reference" in item)
    project_nav = next(item["Project"] for item in nav if "Project" in item)

    assert '"Persistent cache"' in text
    assert '"Settings specification"' in text
    assert '"Ruff rule links"' in text
    assert '"GitHub Readme"' in text
    assert '"Settings spec"' not in text
    assert '"Rule list"' not in text
    assert '"README" = "project/readme.md"' not in text
    assert "rules/ruff-rule-links.md" in text
    assert "reference/ruff-rule-links.md" not in text
    assert "reference/rule-list.md" not in text
    assert "reference/rule-implementation.md" not in text
    assert reference_nav[0] == {"Persistent cache": "reference/cache.md"}
    assert rules_nav[-1] == {"Ruff rule links": "rules/ruff-rule-links.md"}
    assert {"Ruff rule links": "rules/ruff-rule-links.md"} not in reference_nav
    assert project_nav == [{"GitHub Readme": "project/readme.md"}, {"Contributing": "project/contributing.md"}, {"Changelog": "project/changelog.md"}, {"License": "project/license.md"}]


def test_generated_config_does_not_contain_mkdocs(generated_site: tuple[pathlib.Path, pathlib.Path]) -> None:
    """The generated config must not contain MkDocs compatibility wiring."""
    _, generated_config_path = generated_site
    text = generated_config_path.read_text(encoding="utf-8").lower()

    assert "mkdocs" not in text
    assert "mkdocstrings" not in text
    assert "redirects" not in text


def test_docs_dependency_group_omits_unused_or_compatibility_packages() -> None:
    """The docs dependency group must reject unused or compatibility packages."""
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    docs_dependencies = pyproject["dependency-groups"]["docs"]
    dependency_names = {_normalized_dependency_name(dependency) for dependency in docs_dependencies}

    assert dependency_names.isdisjoint(FORBIDDEN_DOCS_DEPENDENCIES)


def test_project_metadata_and_documentation_publish_compatibility_contract() -> None:
    """Project metadata and primary documentation must publish the supported compatibility contract."""
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    classifiers = set(pyproject["project"]["classifiers"])

    assert "Operating System :: OS Independent" not in classifiers
    assert {"Operating System :: MacOS :: MacOS X", "Operating System :: POSIX", "Operating System :: POSIX :: Linux"} <= classifiers
    implementation_classifiers = {classifier for classifier in classifiers if classifier.startswith("Programming Language :: Python :: Implementation :: ")}
    assert implementation_classifiers == {"Programming Language :: Python :: Implementation :: CPython"}
    for relative_path in ("README.md", "CONTRIBUTING.md", "docs_site/installation.md", "docs_site/faq.md"):
        text = (ROOT / relative_path).read_text(encoding="utf-8")
        for expected in ("CPython 3.11", "PyPy", "GraalPy", "Jython", "IronPython", "Ubuntu 20.04", "macOS 14", "POSIX Linux", "Windows", "WSL"):
            assert expected in text, f"{relative_path} does not document {expected}"
        assert "officially supports CPython" in text
        assert "Compatibility with PyPy and GraalPy is intended but is not currently verified or guaranteed" in text
        assert "Jython and IronPython are unsupported" in text
    installation = (ROOT / "docs_site" / "installation.md").read_text(encoding="utf-8")
    assert "LibCST's native parser does not publish binary wheels for these implementations" in installation


def test_generated_docs_do_not_include_api_reference_pages(generated_site: tuple[pathlib.Path, pathlib.Path]) -> None:
    """The generated site must not include custom Python API reference pages."""
    generated_docs_dir, _ = generated_site

    assert not (generated_docs_dir / "api").exists()
    assert not list(generated_docs_dir.glob("api/*.md"))


def test_api_reference_page_explains_deferred_api_reference(generated_site: tuple[pathlib.Path, pathlib.Path]) -> None:
    """The API reference page must explain why generated API docs are deferred."""
    generated_docs_dir, _ = generated_site
    text = (generated_docs_dir / "api-reference.md").read_text(encoding="utf-8").lower()

    for expected in ("pydocfmt", "api reference", "deferred", "zensical", "native"):
        assert expected in text
