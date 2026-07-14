"""Documentation site generation tests."""

# Future imports
from __future__ import annotations

# Standard library imports
import types
import typing
import pathlib
import tomllib

# Third-party imports
import pytest
import markdown as markdown_core
from tools.docs import generate_zensical

# First-party imports
import pydocformatter.rules.collection as rule_collection
import pydocformatter.rules.documentation as rule_documentation
from pydocformatter import docs_urls
from pydocformatter.cli import settings_check
from pydocformatter.rules.models import RuleSettingEffect, RuleSettingEffects


ROOT = pathlib.Path(__file__).resolve().parents[1]
FORBIDDEN_DOCS_DEPENDENCIES = {"mkdocs", "mkdocs-material", "mkdocs-redirects", "mkdocstrings", "mkdocstrings-python", "properdocs"}


def _render_markdown(text: str) -> str:
    """Render Markdown with the generated site's tabbed-example extensions."""
    return markdown_core.markdown(text, extensions=["pymdownx.superfences", "pymdownx.tabbed"], extension_configs={"pymdownx.tabbed": {"alternate_style": True}})


def _normalized_dependency_name(dependency: str) -> str:
    """Return the normalized project name from a dependency specifier."""
    name = dependency.split("[", maxsplit=1)[0]
    for separator in ("<", ">", "=", "!", "~", ";"):
        name = name.split(separator, maxsplit=1)[0]
    return name.strip().lower().replace("_", "-")


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

        assert section.count('<div class="pydocformatter-rule-table-wrapper" markdown="1">') == 1
        assert section.count("| Code | Name | Summary | Fix available | Enabled |") == 1
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

    for rule_class in rule_collection.RULE_COLLECTION.rules:
        convention_effects = {
            value: effect_values.effect
            for setting_effects in rule_class.meta.setting_effects
            if setting_effects.setting == "docstring_convention"
            for effect_values in setting_effects.effects
            for value in effect_values.values
            if isinstance(value, settings_check.DocstringConvention)
        }
        if convention_effects and any(convention_effects.get(convention) not in {RuleSettingEffect.IGNORED, RuleSettingEffect.DISABLED} for convention in settings_check.DocstringConvention):
            assert "| Convention |" in markdown
            assert "| Convention-gated |" not in markdown
            assert generate_zensical._enabled_text(rule_class) == "Convention"
            break
    else:
        raise AssertionError("Expected at least one convention-dependent rule")


def test_rule_index_labels_convention_explicit_rules(generated_site: tuple[pathlib.Path, pathlib.Path]) -> None:
    """The generated rule index must identify rules removed by every convention."""
    generated_docs_dir, _ = generated_site
    markdown = (generated_docs_dir / "rules.md").read_text(encoding="utf-8")

    for rule_class in rule_collection.RULE_COLLECTION.rules:
        convention_effects = {
            value: effect_values.effect
            for setting_effects in rule_class.meta.setting_effects
            if setting_effects.setting == "docstring_convention"
            for effect_values in setting_effects.effects
            for value in effect_values.values
            if isinstance(value, settings_check.DocstringConvention)
        }
        if convention_effects and all(convention_effects.get(convention) in {RuleSettingEffect.IGNORED, RuleSettingEffect.DISABLED} for convention in settings_check.DocstringConvention):
            assert "| Convention-explicit |" in markdown
            assert generate_zensical._enabled_text(rule_class) == "Convention-explicit"
            break
    else:
        raise AssertionError("Expected at least one convention-explicit rule")


def test_rule_index_explains_table_columns(generated_site: tuple[pathlib.Path, pathlib.Path]) -> None:
    """The generated rule index must explain compact table labels."""
    generated_docs_dir, _ = generated_site
    markdown = (generated_docs_dir / "rules.md").read_text(encoding="utf-8")
    explanation = markdown.split("### PCF:", maxsplit=1)[0]

    assert '<a id="rule-table-columns"></a>' in explanation
    assert "The `Fix available` column" in explanation
    assert "The `Enabled` column" in explanation
    for value in ("Always", "Usually", "Sometimes", "Never", "By default", "Requires explicit", "Convention", "Convention-explicit", "Setting-gated"):
        assert f"- `{value}`:" in explanation


def test_enabled_text_values_are_documented(generated_site: tuple[pathlib.Path, pathlib.Path]) -> None:
    """Every generated enabled-state label must be documented."""
    generated_docs_dir, _ = generated_site
    markdown = (generated_docs_dir / "rules.md").read_text(encoding="utf-8")
    explanation = markdown.split("### PCF:", maxsplit=1)[0]
    by_default_rule = next(rule_class for rule_class in rule_collection.RULE_COLLECTION.rules if generate_zensical._enabled_text(rule_class) == "By default")
    fake_setting_gated_rule = types.SimpleNamespace(meta=types.SimpleNamespace(code=by_default_rule.meta.code, setting_effects=(RuleSettingEffects(setting="future_setting", effects=()),)))
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
select = ["PCF001"]

[input]
# first

[output=unchanged]
```

```pydocfmt-example
[settings]
select = ["PCF002"]

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
    page = next(page for page in generate_zensical.rule_pages() if page.code == "PCF001")
    markdown = (generated_docs_dir / page.path).read_text(encoding="utf-8")

    settings_index = markdown.index('=== "Settings"')
    before_index = markdown.index('===+ "Before"')

    assert settings_index < before_index


def test_rule_examples_collapse_unchanged_before_after_tabs(generated_site: tuple[pathlib.Path, pathlib.Path]) -> None:
    """Generated unchanged examples must use a single selected Before equals After tab."""
    generated_docs_dir, _ = generated_site
    page = next(page for page in generate_zensical.rule_pages() if page.code == "PCF001")
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
    page = next(page for page in generate_zensical.rule_pages() if page.code == "PCF001")
    markdown = (generated_docs_dir / page.path).read_text(encoding="utf-8")

    assert "- [`line-length`](../settings.md#line-length):" in markdown
    assert "- `line-length`:" not in markdown


def test_category_options_link_to_settings(generated_site: tuple[pathlib.Path, pathlib.Path]) -> None:
    """Generated category Options tables must link setting names to Settings headings."""
    generated_docs_dir, _ = generated_site
    markdown = (generated_docs_dir / "rules" / "pcf.md").read_text(encoding="utf-8")

    assert "| [`line-length`](../settings.md#line-length)" in markdown
    assert "| `line-length`" not in markdown


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

    assert '<div class="pydocformatter-settings-table-wrapper" markdown="1">' in markdown
    assert "| Setting | CLI | Type | Default | Related rules |" in markdown
    assert "| Setting | Type | Default | CLI | Scope | Related rules |" not in markdown
    assert "- Scope:" not in markdown
    assert "[Settings specification](reference/settings-spec.md)" in markdown
    assert "[Settings spec](reference/settings-spec.md)" not in markdown


def test_settings_markdown_omits_empty_related_rules_table_columns() -> None:
    """Generated settings tables must omit unused Related rules columns."""
    markdown = generate_zensical._settings_markdown(generate_zensical.rule_pages())
    related_rules_by_field = generate_zensical._related_rules_by_field()

    for group in settings_check.SettingsGroup:
        definitions = [definition for definition in settings_check.SETTINGS_SCHEMA.definitions if definition.group == group]
        if not definitions:
            continue
        section = markdown.split(f"\n## {group.value}\n", maxsplit=1)[1].split("\n## ", maxsplit=1)[0]
        has_related_rules = any(definition.field in related_rules_by_field for definition in definitions)
        if has_related_rules:
            assert "| Setting | CLI | Type | Default | Related rules |" in section
        else:
            assert "| Setting | CLI | Type | Default |\n| --- | --- | --- | --- |" in section
            assert "| Related rules |" not in section


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


def test_links_between_moved_docs_are_rewritten(generated_site: tuple[pathlib.Path, pathlib.Path]) -> None:
    """Relative links between copied public docs must be rewritten to generated paths."""
    generated_docs_dir, _ = generated_site
    readme_text = (generated_docs_dir / "project" / "readme.md").read_text(encoding="utf-8")

    assert "](../reference/settings-spec.md)" in readme_text
    assert "](docs/public/settings_spec.md)" not in readme_text


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

    assert "**Options:**\n\n- `--help`" in readme_text
    assert "**Available hooks:**\n\n- `pydocfmt-fix`" in readme_text
    assert "<p><strong>Options:</strong>\n-" not in html
    assert "<p><strong>Available hooks:</strong>\n-" not in html
    assert "<li><code>--help</code>: Show help message and exit</li>" in html
    assert "<li><code>pydocfmt-fix</code>: Format and check docstrings and comments (modifies files)</li>" in html


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


def test_docs_dependency_group_is_mkdocs_free() -> None:
    """The docs dependency group must reject MkDocs and known compatibility packages."""
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    docs_dependencies = pyproject["dependency-groups"]["docs"]
    dependency_names = {_normalized_dependency_name(dependency) for dependency in docs_dependencies}

    assert dependency_names.isdisjoint(FORBIDDEN_DOCS_DEPENDENCIES)


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
