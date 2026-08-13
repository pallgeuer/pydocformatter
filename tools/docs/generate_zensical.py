"""Generate the Zensical documentation tree and configuration.

Attributes:
    ROOT (pathlib.Path): Repository root used to resolve source documents and generated output paths.
    DOCS_SITE_DIR (pathlib.Path): Hand-authored web documentation source copied into generated Zensical input.
    GENERATED_ROOT (pathlib.Path): Root directory for generated documentation artifacts.
    GENERATED_DOCS_DIR (pathlib.Path): Generated Zensical `docs_dir` populated by this script.
    TEMPLATE_PATH (pathlib.Path): Hand-authored Zensical template loaded before generated nav is injected.
    GENERATED_CONFIG_PATH (pathlib.Path): Generated Zensical configuration path consumed by local and CI builds.
    GENERATED_NAV_MARKER (str): Template marker replaced with deterministic generated navigation TOML.
    SOURCE_BLOB_URL (str): GitHub source browser base URL used for generated source links.
    SITE_URL (str): Canonical GitHub Pages URL expected in the generated Zensical configuration.
    PUBLIC_DOCS_DIR (pathlib.Path): Repository docs directory copied into the generated public reference section.
    DEVEL_DOCS_DIR (pathlib.Path): Repository docs directory intentionally omitted from the public site.
    REFERENCE_DOCS (dict[pathlib.Path, pathlib.Path]): Public repository docs mapped to generated reference paths.
    PROJECT_DOCS (dict[pathlib.Path, pathlib.Path]): Top-level project documents mapped to generated project paths.
    EXTERNAL_SOURCE_DOCS (set[pathlib.Path]): Repository documents linked to GitHub source instead of published pages.
    SOURCE_TO_GENERATED (dict[pathlib.Path, pathlib.Path]): Source-to-generated path map used for Markdown link
        rewriting.
    SETTING_ANCHOR_BY_KEY (dict[str, str]): Generated Settings page anchors keyed by public setting key.
    MARKDOWN_LINK_RE (re.Pattern[str]): Markdown inline-link matcher used for deterministic link rewriting.
    MARKDOWN_LIST_ITEM_RE (re.Pattern[str]): Markdown list-item matcher used for Zensical list spacing normalization.
    MARKDOWN_FENCE_RE (re.Pattern[str]): Markdown fenced-code opener or closer matcher used during list spacing
        normalization.
    EXAMPLE_OPENING_FENCE_RE (re.Pattern[str]): Structured pydocfmt-example opening fence matcher used during
        content-tab conversion.
    EXAMPLE_TABS_SEPARATOR (str): Invisible Markdown separator inserted between adjacent generated tab sets.
    OPTION_CODE_SPAN_RE (re.Pattern[str]): Markdown code-span matcher used for rule Options setting references.
"""

# Future imports
from __future__ import annotations

# Standard library imports
import re
import enum
import html
import json
import shutil
import inspect
import pathlib
import argparse
import posixpath
import dataclasses
import urllib.parse
from itertools import starmap
from types import GenericAlias
from typing import TYPE_CHECKING, Any

# Third-party imports
from la_dev_codex_plugins import markdown_tables

# First-party imports
import pydocformatter.settings as settings_core
import pydocformatter.rules.collection as rule_collection
import pydocformatter.rules.documentation as rule_documentation
from pydocformatter import docs_urls
from pydocformatter.cli import settings_check
from pydocformatter.rules.codes import RuleSelector
from pydocformatter.rules.models import RuleSettingEffect


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.definition import RuleBase, RuleCategoryBase
    from pydocformatter.rules.models import RuleMetadata


ROOT = pathlib.Path(__file__).resolve().parents[2]
DOCS_SITE_DIR = ROOT / "docs_site"
GENERATED_ROOT = ROOT / ".generated" / "zensical"
GENERATED_DOCS_DIR = GENERATED_ROOT / "docs"
TEMPLATE_PATH = ROOT / "zensical.template.toml"
GENERATED_CONFIG_PATH = ROOT / "zensical.generated.toml"
GENERATED_NAV_MARKER = "# __GENERATED_NAV__"
SOURCE_BLOB_URL = "https://github.com/pallgeuer/pydocformatter/blob/main"
SITE_URL = docs_urls.PUBLIC_DOCS_URL

PUBLIC_DOCS_DIR = ROOT / "docs" / "public"
DEVEL_DOCS_DIR = ROOT / "docs" / "devel"

REFERENCE_DOCS = {
    pathlib.Path("docs/public/cache_spec.md"): pathlib.Path("reference/cache.md"),
    pathlib.Path("docs/public/file_selection_spec.md"): pathlib.Path("reference/file-selection.md"),
    pathlib.Path("docs/public/markdown_spec.md"): pathlib.Path("reference/markdown-source.md"),
    pathlib.Path("docs/public/rule_selection_spec.md"): pathlib.Path("reference/rule-selection.md"),
    pathlib.Path("docs/public/rule_suppressions.md"): pathlib.Path("reference/rule-suppressions.md"),
    pathlib.Path("docs/public/settings_spec.md"): pathlib.Path("reference/settings-spec.md"),
    pathlib.Path("docs/public/ruff_rule_links.md"): pathlib.Path("rules/ruff-rule-links.md"),
}

PROJECT_DOCS = {
    pathlib.Path("README.md"): pathlib.Path("project/readme.md"),
    pathlib.Path("CHANGELOG.md"): pathlib.Path("project/changelog.md"),
    pathlib.Path("CONTRIBUTING.md"): pathlib.Path("project/contributing.md"),
    pathlib.Path("LICENSE.md"): pathlib.Path("project/license.md"),
}

EXTERNAL_SOURCE_DOCS = {pathlib.Path("RELEASE.md")}
SOURCE_TO_GENERATED = REFERENCE_DOCS | PROJECT_DOCS
SETTING_ANCHOR_BY_KEY = {definition.key: definition.key for definition in settings_check.SETTINGS_SCHEMA.definitions if definition.available_in_toml}
MARKDOWN_LINK_RE = re.compile(r"(?P<prefix>!?\[[^\]]*\]\()(?P<target>[^)]+)(?P<suffix>\))")
MARKDOWN_LIST_ITEM_RE = re.compile(r"^(?: {0,3})(?:[-+*]|\d+[.)])(?=\s)")
MARKDOWN_FENCE_RE = re.compile(r"^(?: {0,3})(?P<fence>`{3,}|~{3,})")
EXAMPLE_OPENING_FENCE_RE = re.compile(r"^(?P<fence>`{3,})pydocfmt-example[^\n]*$")
EXAMPLE_TABS_SEPARATOR = "<!-- pydocformatter-example-tabs -->\n"
OPTION_CODE_SPAN_RE = re.compile(r"`([^`]+)`")


@dataclasses.dataclass(frozen=True)
class RulePage:
    """Generated URL metadata for one rule.

    Attributes:
        code (str): Rule code tag such as `PDF101`.
        name (str): Rule name from rule metadata.
        slug (str): Unique rule URL slug derived from the rule name.
        path (pathlib.Path): Generated Markdown path for the rule page, relative to the Zensical docs directory.
        category_prefix (str): Rule category prefix such as `PDF` or `PCF`.
    """

    code: str
    name: str
    slug: str
    path: pathlib.Path
    category_prefix: str


def main() -> None:
    """Run the Zensical generation command."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    generate()


def generate() -> None:
    """Generate docs and configuration from project sources."""
    pages = rule_pages()
    _reset_generated_docs()
    _copy_authored_docs()
    _copy_project_docs()
    _copy_reference_docs()
    _write_rules(pages)
    _write_settings(pages)
    _write_api_reference_if_missing()
    _write_generated_config(pages)


def rule_pages() -> tuple[RulePage, ...]:
    """Return generated page metadata for all built-in rules.

    Returns:
        tuple[RulePage, ...]: Rule pages in rule collection order.

    Raises:
        ValueError: If two rules map to the same URL slug.
    """
    pages: list[RulePage] = []
    used_slugs: dict[str, str] = {}
    for rule_class in rule_collection.RULE_COLLECTION.rules:
        rule = rule_class.meta
        slug = docs_urls.slugify(rule.name)
        if existing_code := used_slugs.get(slug):
            raise ValueError(f"Rule slug collision: {existing_code} and {rule.code} both map to {slug!r}")
        used_slugs[slug] = rule.code.tag
        pages.append(RulePage(code=rule.code.tag, name=rule.name, slug=slug, path=pathlib.Path("rules") / f"{slug}.md", category_prefix=rule.code.prefix))
    return tuple(pages)


def _reset_generated_docs() -> None:
    """Recreate the generated docs directory."""
    if GENERATED_ROOT.exists():
        shutil.rmtree(GENERATED_ROOT)
    GENERATED_DOCS_DIR.mkdir(parents=True)


def _copy_authored_docs() -> None:
    """Copy hand-authored web docs into the generated docs tree."""
    shutil.copytree(DOCS_SITE_DIR, GENERATED_DOCS_DIR, dirs_exist_ok=True)
    _transform_copied_markdown_tree(GENERATED_DOCS_DIR)


def _copy_project_docs() -> None:
    """Copy top-level project documents into the generated docs tree."""
    for source, generated in PROJECT_DOCS.items():
        _copy_markdown_source(source, generated)


def _copy_reference_docs() -> None:
    """Copy explicitly public reference docs into the generated docs tree."""
    _validate_reference_doc_map()
    for source, generated in REFERENCE_DOCS.items():
        _copy_markdown_source(source, generated)


def _copy_markdown_source(source: pathlib.Path, generated: pathlib.Path) -> None:
    """Copy one Markdown source file, rewriting known moved links."""
    source_path = ROOT / source
    generated_path = GENERATED_DOCS_DIR / generated
    text = source_path.read_text(encoding="utf-8")
    text = _transform_source_markdown(text, source=source)
    text = _rewrite_links(text, source=source, generated=generated)
    generated_path.parent.mkdir(parents=True, exist_ok=True)
    generated_path.write_text(text, encoding="utf-8")


def _transform_source_markdown(text: str, *, source: pathlib.Path) -> str:
    """Apply public-site transforms for copied Markdown sources."""
    if source == pathlib.Path("CONTRIBUTING.md"):
        text = _remove_public_contributing_release_process(text)
    text = _separate_markdown_lists(text)
    return _transform_pydocfmt_examples(text, context=source.as_posix())


def _transform_copied_markdown_tree(root: pathlib.Path) -> None:
    """Apply public-site transforms to copied authored Markdown files."""
    for path in root.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        transformed = _separate_markdown_lists(text)
        transformed = _transform_pydocfmt_examples(transformed, context=path.relative_to(root).as_posix())
        if transformed != text:
            path.write_text(transformed, encoding="utf-8")


def _separate_markdown_lists(text: str) -> str:
    """Insert blank lines before copied Markdown list blocks when Zensical requires block separation."""
    lines = text.splitlines(keepends=True)
    output: list[str] = []
    fence: str | None = None
    list_context = False
    for line in lines:
        if fence is not None:
            output.append(line)
            if _closes_markdown_fence(line, fence):
                fence = None
            continue
        if opening_fence := _markdown_fence(line):
            output.append(line)
            fence = opening_fence
            list_context = False
            continue
        if not line.strip():
            output.append(line)
            list_context = False
            continue
        if _is_markdown_list_item(line):
            if output and output[-1].strip() and not list_context and not _allows_immediate_markdown_list(output[-1]):
                output.append(_blank_line_matching(output[-1]))
            output.append(line)
            list_context = True
            continue
        output.append(line)
        if list_context and line[:1].isspace():
            continue
        list_context = False
    return "".join(output)


def _markdown_fence(line: str) -> str | None:
    """Return the fence marker that starts a fenced code block."""
    match = MARKDOWN_FENCE_RE.match(line.rstrip("\r\n"))
    if match is None:
        return None
    fence = match.group("fence")
    if not isinstance(fence, str):
        raise TypeError("Markdown fence capture must be a string")
    return fence


def _closes_markdown_fence(line: str, fence: str) -> bool:
    """Return whether a Markdown line closes the active fenced code block."""
    return line.lstrip(" ").startswith(fence)


def _is_markdown_list_item(line: str) -> bool:
    """Return whether a Markdown line starts an unordered or ordered list item."""
    return MARKDOWN_LIST_ITEM_RE.match(line) is not None


def _allows_immediate_markdown_list(line: str) -> bool:
    """Return whether a Markdown line can be followed by a list without a separating blank line."""
    stripped = line.lstrip()
    return stripped.startswith("#")


def _blank_line_matching(line: str) -> str:
    """Return a blank line matching the neighboring Markdown line ending."""
    if line.endswith("\r\n"):
        return "\r\n"
    if line.endswith("\r"):
        return "\r"
    return "\n"


def _remove_public_contributing_release_process(text: str) -> str:
    """Remove maintainer-only release process details from public contributing docs."""
    lines = text.splitlines(keepends=True)
    output: list[str] = []
    index = 0
    while index < len(lines):
        stripped_line = lines[index].strip()
        if stripped_line == "- [Release process](#release-process)":
            index += 1
            continue
        if stripped_line == "## Release process":
            index += 1
            while index < len(lines) and not lines[index].startswith("## "):
                index += 1
            continue
        output.append(lines[index])
        index += 1
    return "".join(output)


def _validate_reference_doc_map() -> None:
    """Require public reference docs to live under docs/public and be mapped."""
    top_level = sorted(path.relative_to(ROOT) for path in (ROOT / "docs").glob("*.md"))
    if top_level:
        raise ValueError(f"Repository docs Markdown files must live under docs/public or docs/devel: {', '.join(str(path) for path in top_level)}")
    if not DEVEL_DOCS_DIR.is_dir():
        raise ValueError("Development docs directory is missing: docs/devel")
    public_source_root = PUBLIC_DOCS_DIR.relative_to(ROOT)
    out_of_tree = sorted(path for path in REFERENCE_DOCS if not path.is_relative_to(public_source_root))
    if out_of_tree:
        raise ValueError(f"Reference doc map must only publish docs/public files: {', '.join(str(path) for path in out_of_tree)}")
    discovered = {path.relative_to(ROOT) for path in PUBLIC_DOCS_DIR.rglob("*.md")}
    expected = set(REFERENCE_DOCS)
    missing = sorted(discovered - expected)
    stale = sorted(expected - discovered)
    if missing:
        raise ValueError(f"Public docs Markdown files need generated reference paths: {', '.join(str(path) for path in missing)}")
    if stale:
        raise ValueError(f"Reference doc map mentions missing files: {', '.join(str(path) for path in stale)}")


def _rewrite_links(text: str, *, source: pathlib.Path, generated: pathlib.Path) -> str:
    """Rewrite Markdown links whose source files move into generated docs sections."""

    def replace(match: re.Match[str]) -> str:
        target = match.group("target")
        rewritten = _rewrite_link_target(target, source=source, generated=generated)
        return f"{match.group('prefix')}{rewritten}{match.group('suffix')}"

    return MARKDOWN_LINK_RE.sub(replace, text)


def _rewrite_link_target(target: str, *, source: pathlib.Path, generated: pathlib.Path) -> str:
    """Rewrite a single Markdown link target when it points to a moved source document."""
    split_target = urllib.parse.urlsplit(target)
    if split_target.scheme or split_target.netloc or target.startswith("#") or split_target.path == "":
        return target
    source_target = (ROOT / source.parent / split_target.path).resolve()
    try:
        relative_source_target = source_target.relative_to(ROOT)
    except ValueError:
        return target
    generated_target = SOURCE_TO_GENERATED.get(relative_source_target)
    if generated_target is None:
        if relative_source_target in EXTERNAL_SOURCE_DOCS:
            source_url = urllib.parse.urlsplit(_source_url(relative_source_target))
            return urllib.parse.urlunsplit((source_url.scheme, source_url.netloc, source_url.path, split_target.query, split_target.fragment))
        if relative_source_target.suffix == ".md" and (ROOT / relative_source_target).exists():
            raise ValueError(f"Markdown link in {source} points to unpublished local document: {target}")
        return target
    relative_generated_target = posixpath.relpath(generated_target.as_posix(), start=generated.parent.as_posix())
    return urllib.parse.urlunsplit(("", "", relative_generated_target, split_target.query, split_target.fragment))


def _write_rules(rule_pages: tuple[RulePage, ...]) -> None:
    """Write rule index, category pages, and individual rule pages."""
    page_by_code = {page.code: page for page in rule_pages}
    _write_rules_index(rule_pages)
    for category_class in rule_collection.RULE_COLLECTION.categories:
        _write_category_page(category_class, rule_pages)
    for index, rule_class in enumerate(rule_collection.RULE_COLLECTION.rules):
        previous_page = rule_pages[index - 1] if index else None
        next_page = rule_pages[index + 1] if index + 1 < len(rule_pages) else None
        _write_rule_page(rule_class, page_by_code[rule_class.meta.code.tag], previous_page=previous_page, next_page=next_page)


def _write_rules_index(rule_pages: tuple[RulePage, ...]) -> None:
    """Write the generated rule index page."""
    lines = [
        "# Rules",
        "",
        "pydocformatter rules are grouped by code prefix. Rule pages are generated from the built-in rule registry and adjacent Markdown documentation.",
        "",
        "## Rule categories",
        "",
    ]
    for category_class in rule_collection.RULE_COLLECTION.categories:
        category = category_class.meta
        category_slug = category.prefix.lower()
        lines.append(f"- [{category.prefix}: {category.name}](rules/{category_slug}.md)")
    lines.extend((
        "",
        "## All rules",
        "",
        '<a id="rule-table-columns"></a>',
        "",
        "The `Fix available` column summarizes automatic fix availability:",
        "",
        "- `Always`: Every finding has a fix.",
        "- `Usually`: Every semantic violation kind has a correction, but instance-specific safety can prevent a fix.",
        "- `Sometimes`: At least one semantic violation kind is intentionally diagnostic-only while others have fixes.",
        "- `Never`: The rule is diagnostic-only.",
        "",
        "The `Enabled` column shows broad-selection (e.g. by the `ALL` selector) behavior:",
        "",
        "- `By default`: Selected by default.",
        "- `Requires explicit`: Not selected by broad selectors unless the exact rule code is also selected, because it is included in the default `require-explicit` setting.",
        "- `Convention`: Default selection depends on the active `docstring-convention` setting, with at least one convention selecting the rule by default.",
        "- `Convention opt-in`: Removed by every `docstring-convention` value. Ignored conventions can be restored by exact rule-code selection, while disabled conventions cannot.",
        "- `Setting-gated`: Default selection depends on a setting other than `docstring-convention`.",
        "",
        "The `Source contexts` column shows whether a rule applies to complete Python modules, standalone fragments, or both. Context applicability is a hard semantic boundary; exact rule selection does not restore an inapplicable rule.",
        "",
    ))
    page_by_code = {page.code: page for page in rule_pages}
    for category_class in rule_collection.RULE_COLLECTION.categories:
        category = category_class.meta
        category_rules = tuple(rule_class for rule_class in rule_collection.RULE_COLLECTION.rules if rule_class.meta.code.prefix == category.prefix)
        lines.extend((f"### {category.prefix}: {category.name}", ""))
        _extend_rule_table(lines, category_rules, page_by_code, rule_link_prefix="rules/")
        lines.append("")
    _write_generated_markdown(pathlib.Path("rules.md"), "\n".join(lines) + "\n")


def _write_category_page(category_class: type[RuleCategoryBase], rule_pages: tuple[RulePage, ...]) -> None:
    """Write one generated category page."""
    category = category_class.meta
    body = rule_documentation.load_rule_explanation(category_class).strip()
    if body.startswith("# "):
        body = "\n".join(body.splitlines()[1:]).lstrip()
    body = _link_options_settings(body, settings_path="../settings.md", context=f"{category.prefix} category")
    page_by_code = {page.code: page for page in rule_pages}
    category_rules = tuple(rule_class for rule_class in rule_collection.RULE_COLLECTION.rules if rule_class.meta.code.prefix == category.prefix)
    first_page = page_by_code[category_rules[0].meta.code.tag]
    last_page = page_by_code[category_rules[-1].meta.code.tag]
    lines = [
        f"# {category.name} ({category.prefix})",
        "",
        *_category_rule_nav_lines(first_page=first_page, last_page=last_page),
        "[Jump to rule table &darr;](#rules-in-this-category)",
        "",
        body,
        "",
        "## Rules in this category",
        "",
        "See [rule table column explanations](../rules.md#rule-table-columns).",
        "",
    ]
    _extend_rule_table(lines, category_rules, page_by_code, rule_link_prefix="")
    lines.extend(("", "[&larr; Back to all rules](../rules.md)", "", *_category_rule_nav_lines(first_page=first_page, last_page=last_page, position="bottom")))
    _write_generated_markdown(pathlib.Path("rules") / f"{category.prefix.lower()}.md", "\n".join(lines))


def _extend_rule_table(lines: list[str], rule_classes: tuple[type[RuleBase], ...], page_by_code: dict[str, RulePage], *, rule_link_prefix: str) -> None:
    """Append generated rule table rows."""
    lines.extend(('<div class="pydocformatter-rule-table-wrapper" markdown="1">', "", "| Code | Name | Summary | Fix available | Enabled | Source contexts |", "| --- | --- | --- | --- | --- | --- |"))
    for rule_class in rule_classes:
        rule = rule_class.meta
        page = page_by_code[rule.code.tag]
        columns = [f"[`{rule.code}`]({rule_link_prefix}{page.slug}.md)", f"`{rule.name}`", _escape_table_cell(rule.message)]
        columns.extend((rule.fix_availability.value, _enabled_text(rule_class), _source_contexts_text(rule)))
        lines.append(f"| {' | '.join(columns)} |")
    lines.extend(("", "</div>"))


def _write_rule_page(rule_class: type[RuleBase], page: RulePage, *, previous_page: RulePage | None, next_page: RulePage | None) -> None:
    """Write one generated rule detail page."""
    rule = rule_class.meta
    source_path = _class_source_path(rule_class)
    markdown_path = source_path.with_suffix(".md")
    raw_body = rule_documentation.load_rule_explanation(rule_class)
    description = _rule_description(raw_body, rule.message)
    body = _strip_first_heading(raw_body).lstrip()
    body = _link_options_settings(body, settings_path="../settings.md", context=rule.code.tag)
    body = _transform_pydocfmt_examples(body, context=rule.code.tag)
    body = _rewrite_links(body, source=markdown_path, generated=page.path)
    lines = [
        "---",
        f'description: "{_yaml_double_quoted(description)}"',
        "tags:",
        f"  - {rule.code.prefix}",
        f"  - {rule.code}",
        f"  - {rule.name}",
        "---",
        "",
        f"# {rule.name} ({rule.code})",
        "",
        *_rule_nav_lines(previous_page=previous_page, next_page=next_page),
        '<div class="pydocformatter-badges">',
        f'<span class="pydocformatter-badge">Added in {rule.stable_since}</span>',
        f'<span class="pydocformatter-badge">{rule.fix_availability.value} fix</span>',
        f'<span class="pydocformatter-badge">{_enabled_text(rule_class)}</span>',
        f'<span class="pydocformatter-badge">{_source_contexts_text(rule)}</span>',
        "</div>",
        "",
        f"Part of the [{rule.code.prefix} rule category]({rule.code.prefix.lower()}.md).",
        "",
        f"[View source]({_source_url(source_path)}) \u00b7 [View documentation source]({_source_url(markdown_path)}) \u00b7 [Search issues](https://github.com/pallgeuer/pydocformatter/issues?q={rule.code})",
        "",
        body,
        "",
        *_rule_nav_lines(previous_page=previous_page, next_page=next_page, position="bottom"),
    ]
    _write_generated_markdown(page.path, "\n".join(lines).rstrip() + "\n")


def _source_contexts_text(rule: RuleMetadata) -> str:
    """Return concise source-context applicability text for one rule."""
    labels = {"module": "Module", "fragment": "Fragment"}
    return " and ".join(labels[source_context.value] for source_context in rule.source_contexts)


def _rule_nav_lines(*, previous_page: RulePage | None, next_page: RulePage | None, position: str = "top") -> tuple[str, ...]:
    """Return a previous and next rule navigation block."""
    lines = [f'<nav class="pydocformatter-rule-nav pydocformatter-rule-nav--{position}" aria-label="Rule navigation">']
    if previous_page is not None:
        lines.append(_rule_nav_link(previous_page, relation="previous"))
    if next_page is not None:
        lines.append(_rule_nav_link(next_page, relation="next"))
    lines.extend(("</nav>", ""))
    return tuple(lines)


def _category_rule_nav_lines(*, first_page: RulePage, last_page: RulePage, position: str = "top") -> tuple[str, ...]:
    """Return a first and last rule navigation block for a category."""
    lines = [f'<nav class="pydocformatter-rule-nav pydocformatter-rule-nav--{position}" aria-label="Category rule navigation">']
    lines.extend((_rule_nav_link(first_page, relation="first"), _rule_nav_link(last_page, relation="last")))
    lines.extend(("</nav>", ""))
    return tuple(lines)


def _rule_nav_link(page: RulePage, *, relation: str) -> str:
    """Return one rule navigation link."""
    escaped_code = html.escape(page.code)
    escaped_name = html.escape(page.name)
    escaped_label = f"{escaped_code}: {escaped_name}"
    if relation == "previous":
        direction_text = "&larr; Previous rule"
    elif relation == "next":
        direction_text = "Next rule &rarr;"
    elif relation == "first":
        direction_text = "First rule"
    elif relation == "last":
        direction_text = "Last rule"
    else:
        raise ValueError(f"Unsupported rule navigation relation: {relation!r}")
    return f'<a class="pydocformatter-rule-nav__link pydocformatter-rule-nav__link--{relation}" href="{page.slug}.md" aria-label="{direction_text}: {escaped_label}"><span class="pydocformatter-rule-nav__direction">{direction_text}</span><span class="pydocformatter-rule-nav__target"><code>{escaped_code}</code> {escaped_name}</span></a>'


def _write_settings(rule_pages: tuple[RulePage, ...]) -> None:
    """Write the generated settings reference page."""
    _write_generated_markdown(pathlib.Path("settings.md"), _settings_markdown(rule_pages))


def _write_api_reference_if_missing() -> None:
    """Write a conservative API reference page when no authored page exists."""
    api_reference_path = GENERATED_DOCS_DIR / "api-reference.md"
    if api_reference_path.exists():
        return
    lines = [
        "# API reference",
        "",
        "pydocformatter's primary supported public interface is the `pydocfmt` command-line interface.",
        "",
        "Generated Python API reference pages are intentionally deferred while Zensical's native API-reference support matures. The project will evaluate API reference generation when it can be done without MkDocs, mkdocstrings, or any MkDocs compatibility dependency.",
        "",
        "Developers can inspect the source and type annotations in the [GitHub repository](https://github.com/pallgeuer/pydocformatter) for now.",
        "",
    ]
    _write_generated_markdown(pathlib.Path("api-reference.md"), "\n".join(lines))


def _settings_markdown(rule_pages: tuple[RulePage, ...]) -> str:
    """Return the generated settings reference page Markdown."""
    defaults = settings_check.CheckSettings()
    related_rules_by_field = _related_rules_by_field()
    page_by_code = {page.code: page for page in rule_pages}
    lines = [
        "# Settings",
        "",
        "The `pydocfmt check` tool is configurable via the settings below. The `Setting` column shows the TOML key used in configuration files under `[tool.pydocfmt]`, while the `CLI` column shows the corresponding `pydocfmt check` flag when one exists.",
        "",
        "Use `pydocfmt check --help` for command-line usage and `pydocfmt config` for CLI-based settings help. Use `pydocfmt config` to directly list all available settings, and pass an additional argument specifying one of the setting names (TOML key) in order to get specific help on that setting, e.g. `pydocfmt config require-explicit`.",
        "",
        "See [Configuration](configuration.md) for details on the settings loading behavior, and [Settings specification](reference/settings-spec.md) for detailed settings semantics.",
        "",
    ]
    for group in settings_check.SettingsGroup:
        definitions = [definition for definition in settings_check.SETTINGS_SCHEMA.definitions if definition.group == group]
        if not definitions:
            continue
        has_related_rules = any(definition.field in related_rules_by_field for definition in definitions)
        lines.extend((
            f"## {group.value}",
            "",
            '<div class="pydocformatter-settings-table-wrapper" markdown="1">',
            "",
            "| Setting | CLI | Type | Default | Related rules |" if has_related_rules else "| Setting | CLI | Type | Default |",
            "| --- | --- | --- | --- | --- |" if has_related_rules else "| --- | --- | --- | --- |",
        ))
        for definition in definitions:
            default_text = settings_core.format_value(getattr(defaults, definition.field), definition.value_type)
            setting_name = f"`{definition.key}`" if definition.available_in_toml else f"`{definition.field}`"
            cli_text = ", ".join(f"`{flag}`" for flag in definition.cli.flags) if definition.cli else "-"
            row = f"| {setting_name} | {cli_text} | {_table_code_cell(_type_text(definition.value_type))} | {_table_code_cell(default_text)} |"
            if has_related_rules:
                related_rules = _related_rule_links(related_rules_by_field.get(definition.field, ()), page_by_code, limit=4) or "-"
                row = f"{row} {related_rules} |"
            lines.append(row)
        lines.extend(("", "</div>", ""))
        for definition in definitions:
            lines.extend(_setting_detail_lines(definition, defaults, related_rules_by_field.get(definition.field, ()), page_by_code))
    return "\n".join(lines).rstrip() + "\n"


def _setting_detail_lines(definition: settings_core.SettingDefinition[Any], defaults: settings_check.CheckSettings, related_rules: tuple[str, ...], page_by_code: dict[str, RulePage]) -> list[str]:
    """Return detail section lines for one setting."""
    heading = definition.key if definition.available_in_toml else definition.field
    default_text = settings_core.format_value(getattr(defaults, definition.field), definition.value_type)
    lines = [f"### `{heading}`", "", definition.documentation, "", f"- Type: `{_type_text(definition.value_type)}`", f"- Default: `{default_text}`"]
    if definition.cli:
        lines.append(f"- CLI: {', '.join(f'`{flag}`' for flag in definition.cli.flags)}")
    if related_rules:
        lines.append(f"- Related rules: {_related_rule_links(related_rules, page_by_code)}")
    if definition.available_in_toml:
        example = definition.example or f"{definition.key} = {default_text}"
        lines.extend(("", "```toml", "[tool.pydocfmt]", example, "```"))
    lines.append("")
    return lines


def _related_rules_by_field() -> dict[str, tuple[str, ...]]:
    """Return rule codes keyed by controlling settings field."""
    field_by_key = {definition.key: definition.field for definition in settings_check.SETTINGS_SCHEMA.definitions if definition.available_in_toml}
    related: dict[str, list[str]] = {}
    for rule_class in rule_collection.RULE_COLLECTION.rules:
        rule_code = rule_class.meta.code.tag
        for setting_effects in rule_class.meta.setting_effects:
            _append_related_rule(related, field=setting_effects.setting, rule_code=rule_code)
        for field in _documented_related_setting_fields(rule_class, field_by_key):
            _append_related_rule(related, field=field, rule_code=rule_code)
    return {field: tuple(codes) for field, codes in related.items()}


def _append_related_rule(related: dict[str, list[str]], *, field: str, rule_code: str) -> None:
    """Append a related rule code without duplicating existing entries."""
    codes = related.setdefault(field, [])
    if rule_code not in codes:
        codes.append(rule_code)


def _documented_related_setting_fields(rule_class: type[RuleBase], field_by_key: dict[str, str]) -> tuple[str, ...]:
    """Return settings fields documented in a rule Markdown Options section."""
    fields: list[str] = []
    in_options = False
    for line in rule_documentation.load_rule_explanation(rule_class).splitlines():
        if line.startswith("## "):
            in_options = line.strip() == "## Options"
            continue
        if not in_options or not line.startswith("- "):
            continue
        option_prefix = line.split(":", maxsplit=1)[0]
        for option_key in OPTION_CODE_SPAN_RE.findall(option_prefix):
            for field in _setting_fields_for_option_key(option_key, field_by_key, rule_code=rule_class.meta.code.tag):
                if field not in fields:
                    fields.append(field)
    return tuple(fields)


def _setting_fields_for_option_key(option_key: str, field_by_key: dict[str, str], *, rule_code: str) -> tuple[str, ...]:
    """Return settings fields matched by one documented option key."""
    if option_key.endswith("*"):
        prefix = option_key[:-1]
        fields = tuple(field for key, field in field_by_key.items() if key.startswith(prefix))
        if not fields:
            raise ValueError(f"{rule_code}: Unknown documented setting wildcard {option_key!r}")
        return fields
    try:
        return (field_by_key[option_key],)
    except KeyError:
        raise ValueError(f"{rule_code}: Unknown documented setting option {option_key!r}") from None


def _related_rule_links(related_rules: tuple[str, ...], page_by_code: dict[str, RulePage], *, limit: int | None = None) -> str:
    """Return settings-page links for related rule codes."""
    displayed_rules = related_rules if limit is None else related_rules[:limit]
    links = [f"[`{code}`]({page_by_code[code].path.as_posix()})" for code in displayed_rules]
    if len(related_rules) > len(displayed_rules):
        links.append("...")
    return ", ".join(links)


def _link_options_settings(markdown: str, *, settings_path: str, context: str) -> str:
    """Link documented Options settings to the generated Settings page."""
    try:
        parsed_tables = markdown_tables.parse_markdown_tables(markdown)
    except markdown_tables.MarkdownTableError as error:
        raise ValueError(f"{context}: {error}") from error
    first_table_cells = {row.line_number: row.cells[0] for table in parsed_tables for row in table.rows if row.cells}
    lines: list[str] = []
    in_options = False
    for line_number, line in enumerate(markdown.splitlines(), start=1):
        if line.startswith("## "):
            in_options = line.strip() == "## Options"
            lines.append(line)
            continue
        if not in_options:
            lines.append(line)
            continue
        if line.startswith("- "):
            prefix, separator, suffix = line.partition(":")
            lines.append(f"{_link_option_setting_spans(prefix, settings_path=settings_path, context=context)}{separator}{suffix}")
            continue
        if line_number in first_table_cells:
            lines.append(_link_option_table_setting_cell(line, first_table_cells[line_number], settings_path=settings_path, context=context))
            continue
        lines.append(line)
    return "\n".join(lines)


def _link_option_setting_spans(text: str, *, settings_path: str, context: str) -> str:
    """Link exact setting code spans inside one option name field."""

    def replace(match: re.Match[str]) -> str:
        option_key = match.group(1)
        return _setting_link(option_key, settings_path=settings_path, context=context)

    return OPTION_CODE_SPAN_RE.sub(replace, text)


def _link_option_table_setting_cell(line: str, first_cell: str, *, settings_path: str, context: str) -> str:
    """Link the first Markdown table cell when it names a documented setting."""
    linked_first_cell = _link_option_setting_spans(first_cell, settings_path=settings_path, context=context)
    if linked_first_cell == first_cell:
        return line
    prefix, separator, suffix = line.partition(first_cell)
    if not separator or prefix.strip() not in {"", "|"} or not suffix.lstrip().startswith("|"):
        raise ValueError(f"{context}: Parsed first table cell does not match its source row structure")
    return f"{prefix}{linked_first_cell}{suffix}"


def _setting_link(option_key: str, *, settings_path: str, context: str) -> str:
    """Return a Settings page link for one documented setting key."""
    try:
        anchor = SETTING_ANCHOR_BY_KEY[option_key]
    except KeyError:
        raise ValueError(f"{context}: Unknown documented setting option {option_key!r}") from None
    return f"[`{option_key}`]({settings_path}#{anchor})"


def _write_generated_config(rule_pages: tuple[RulePage, ...]) -> None:
    """Write zensical.generated.toml from the template and generated navigation."""
    del rule_pages
    template = TEMPLATE_PATH.read_text(encoding="utf-8").rstrip()
    nav = f"# Generated navigation. Do not edit by hand.\n{_nav_toml()}"
    if GENERATED_NAV_MARKER not in template:
        raise ValueError(f"{TEMPLATE_PATH.name} must contain {GENERATED_NAV_MARKER!r}")
    generated = template.replace(GENERATED_NAV_MARKER, nav) + "\n"
    GENERATED_CONFIG_PATH.write_text(generated, encoding="utf-8")


def _nav() -> list[Any]:
    """Return the generated Zensical navigation."""
    return [
        {"Overview": "index.md"},
        {"Tutorial": "tutorial.md"},
        {"Installation": "installation.md"},
        {"Usage": [{"Checking": "checking.md"}, {"Formatting": "formatting.md"}, {"Configuration": "configuration.md"}, {"Integrations": "integrations.md"}]},
        {"Rules": [{"Overview": "rules.md"}, {"PCF: Comment rules": "rules/pcf.md"}, {"PDF: Docstring rules": "rules/pdf.md"}, {"Ruff rule links": "rules/ruff-rule-links.md"}]},
        {"Settings": "settings.md"},
        {
            "Reference": [
                {"Persistent cache": "reference/cache.md"},
                {"File selection": "reference/file-selection.md"},
                {"Markdown source": "reference/markdown-source.md"},
                {"Rule selection": "reference/rule-selection.md"},
                {"Rule suppressions": "reference/rule-suppressions.md"},
                {"Settings specification": "reference/settings-spec.md"},
            ]
        },
        {"Project": [{"GitHub Readme": "project/readme.md"}, {"Contributing": "project/contributing.md"}, {"Changelog": "project/changelog.md"}, {"License": "project/license.md"}]},
        {"FAQ": "faq.md"},
        {"Versioning": "versioning.md"},
        {"API reference": "api-reference.md"},
    ]


def _nav_toml() -> str:
    """Return the generated navigation as deterministic TOML."""
    lines = ["nav = ["]
    for item in _nav():
        lines.extend(_toml_nav_item_lines(item, indent="  "))
    lines.append("]")
    return "\n".join(lines)


def _toml_nav_item_lines(item: Any, *, indent: str) -> list[str]:
    """Return TOML lines for one navigation item."""
    if isinstance(item, str):
        return [f"{indent}{_toml_string(item)},"]
    if isinstance(item, dict) and len(item) == 1:
        title, value = next(iter(item.items()))
        if not isinstance(title, str):
            raise TypeError(f"Unsupported navigation title: {title!r}")
        if isinstance(value, str):
            return [f"{indent}{{{_toml_key(title)} = {_toml_string(value)}}},"]
        if not isinstance(value, list):
            raise TypeError(f"Unsupported navigation value: {value!r}")
        lines = [f"{indent}{{{_toml_key(title)} = ["]
        for child in value:
            lines.extend(_toml_nav_item_lines(child, indent=f"{indent}  "))
        lines.append(f"{indent}]}},")
        return lines
    raise TypeError(f"Unsupported navigation item: {item!r}")


def _toml_key(value: str) -> str:
    """Return a quoted TOML key."""
    return json.dumps(value)


def _toml_string(value: str) -> str:
    """Return a quoted TOML string."""
    return json.dumps(value)


def _enabled_text(rule_class: type[RuleBase]) -> str:
    """Return compact rule activation text."""
    rule = rule_class.meta
    explicit_selectors = tuple(RuleSelector(selector) for selector in settings_check.DEFAULT_REQUIRE_EXPLICIT)
    convention_effects = tuple(rule.setting_effect("docstring_convention", convention) for convention in settings_check.DocstringConvention)
    if all(effect in {RuleSettingEffect.IGNORED, RuleSettingEffect.DISABLED} for effect in convention_effects):
        return "Convention opt-in"
    if any(selector.selects_code(rule.code) for selector in explicit_selectors):
        return "Requires explicit"
    if any(effect is not None for effect in convention_effects):
        return "Convention"
    if rule.setting_effects:
        return "Setting-gated"
    return "By default"


def _transform_pydocfmt_examples(markdown: str, *, context: str) -> str:
    """Convert structured pydocfmt examples to Zensical content tabs."""
    lines = markdown.splitlines(keepends=True)
    output: list[str] = []
    line_index = 0
    example_number = 1
    while line_index < len(lines):
        opening_match = EXAMPLE_OPENING_FENCE_RE.fullmatch(lines[line_index].rstrip("\n"))
        if opening_match is None:
            output.append(lines[line_index])
            line_index += 1
            continue
        fence = opening_match.group("fence")
        block_lines = [lines[line_index]]
        line_index += 1
        while line_index < len(lines):
            block_lines.append(lines[line_index])
            if lines[line_index].strip() == fence:
                break
            line_index += 1
        else:
            raise rule_documentation.RuleMarkdownExampleParseError(f"{context} example {example_number}: missing closing {fence} fence")
        parsed = rule_documentation.parse_rule_markdown_examples("".join(block_lines), rule_code=context)
        if len(parsed) != 1:
            raise ValueError(f"{context} example {example_number}: expected one parsed example, got {len(parsed)}")
        output.append(_example_tabs(parsed[0]))
        line_index += 1
        if _next_nonblank_line_is_example(lines, line_index):
            output.append(EXAMPLE_TABS_SEPARATOR)
        example_number += 1
    return "".join(output)


def _next_nonblank_line_is_example(lines: list[str], line_index: int) -> bool:
    """Return whether the next nonblank source line opens another structured example."""
    while line_index < len(lines) and not lines[line_index].strip():
        line_index += 1
    return line_index < len(lines) and EXAMPLE_OPENING_FENCE_RE.fullmatch(lines[line_index].rstrip("\n")) is not None


def _example_tabs(example: rule_documentation.RuleMarkdownExample) -> str:
    """Return a content tab set for one structured rule example."""
    lines: list[str] = []
    if example.settings_text:
        lines.extend(('=== "Settings"', "", _indented_fence("toml", example.settings_text), ""))
    before_title = _example_before_title(example)
    if example.input_source == example.output_source:
        lines.extend((f'===+ "{before_title}"', "", _indented_fence("python", example.input_source)))
    else:
        lines.extend((f'===+ "{before_title}"', "", _indented_fence("python", example.input_source), "", '=== "After"', "", _indented_fence("python", example.output_source)))
    if example.findings:
        findings = "\n".join(starmap(_finding_text, example.findings)) + "\n"
        lines.extend(("", '=== "Findings"', "", _indented_fence("text", findings)))
    return "\n".join(lines) + "\n"


def _example_before_title(example: rule_documentation.RuleMarkdownExample) -> str:
    """Return the selected source tab title for one generated example."""
    title = "Before = After" if example.input_source == example.output_source else "Before"
    if example.path is not None:
        return f"{title} ({_escape_tab_title_path(example.path)})"
    return title


def _escape_tab_title_path(path: str) -> str:
    """Return a Markdown-escaped path for use inside a tab title."""
    return path.replace("\\", "\\\\").replace("_", "\\_")


def _indented_fence(language: str, source: str) -> str:
    """Return an indented fenced code block for a content tab."""
    code = source if source.endswith("\n") else source + "\n"
    fenced = f"```{language}\n{code}```\n"
    return "".join(f"    {line}" for line in fenced.splitlines(keepends=True)).rstrip()


def _finding_text(code: object, line_numbers: tuple[int, ...], message: str) -> str:
    """Return display text for one documented finding."""
    label = "Line" if len(line_numbers) == 1 else "Lines"
    line_text = _line_numbers_text(line_numbers)
    return f"{code}: {label} {line_text}: {message}"


def _line_numbers_text(line_numbers: tuple[int, ...]) -> str:
    """Return compact line-number text."""
    ranges: list[str] = []
    start = previous = line_numbers[0]
    for line_number in line_numbers[1:]:
        if line_number == previous + 1:
            previous = line_number
            continue
        ranges.append(str(start) if start == previous else f"{start}-{previous}")
        start = previous = line_number
    ranges.append(str(start) if start == previous else f"{start}-{previous}")
    return ", ".join(ranges)


def _rule_description(markdown: str, fallback: str) -> str:
    """Return the first paragraph under What it does."""
    lines = markdown.splitlines()
    try:
        heading_index = lines.index("## What it does")
    except ValueError:
        return fallback
    paragraph: list[str] = []
    for line in lines[heading_index + 1 :]:
        if not line.strip():
            if paragraph:
                break
            continue
        if line.startswith("#"):
            break
        paragraph.append(line.strip())
    return " ".join(paragraph) or fallback


def _strip_first_heading(markdown: str) -> str:
    """Remove the first H1 from a Markdown document."""
    lines = markdown.splitlines(keepends=True)
    if lines and lines[0].startswith("# "):
        return "".join(lines[1:])
    return markdown


def _class_source_path(class_type: type[object]) -> pathlib.Path:
    """Return a project-relative source path for a class."""
    source_file = inspect.getsourcefile(class_type)
    if source_file is None:
        raise ValueError(f"Cannot locate source for {class_type!r}")
    return pathlib.Path(source_file).resolve().relative_to(ROOT)


def _source_url(path: pathlib.Path) -> str:
    """Return the GitHub source URL for a project-relative path."""
    return f"{SOURCE_BLOB_URL}/{path.as_posix()}"


def _write_generated_markdown(path: pathlib.Path, text: str) -> None:
    """Write generated Markdown under the generated docs directory."""
    output_path = GENERATED_DOCS_DIR / path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        normalized = markdown_tables.normalize_markdown_tables(text)
    except markdown_tables.MarkdownTableError as error:
        raise ValueError(f"{path.as_posix()}: {error}") from error
    output_path.write_text(normalized, encoding="utf-8")


def _escape_table_cell(text: str) -> str:
    """Escape text for a Markdown table cell."""
    return text.replace("|", "\\|").replace("\n", " ")


def _table_code_cell(text: str) -> str:
    """Return inline code HTML that is safe inside a Markdown table cell."""
    return f"<code>{html.escape(text, quote=False).replace('|', '&#124;').replace(chr(10), ' ')}</code>"


def _yaml_double_quoted(text: str) -> str:
    """Escape a YAML double-quoted scalar body."""
    return text.replace("\\", "\\\\").replace('"', '\\"')


def _type_text(value_type: object) -> str:
    """Return compact public type text for a setting value."""
    if value_type is settings_core.StringList:
        return "list[str]"
    if value_type is settings_core.StringMap:
        return "dict[str, str]"
    if value_type is settings_core.MultiStringMap:
        return "dict[str, list[str]]"
    if value_type is settings_core.PerFileSettingsMap:
        return "dict[str, dict[str, object]]"
    if isinstance(value_type, GenericAlias):
        return str(value_type)
    if isinstance(value_type, type) and issubclass(value_type, enum.StrEnum):
        return " | ".join(member.value for member in value_type)
    if isinstance(value_type, type):
        return value_type.__name__
    return str(value_type)


if __name__ == "__main__":
    main()
