# Future imports
from __future__ import annotations

# Standard library imports
import re
import pathlib
import tomllib
import collections
from typing import TYPE_CHECKING

# Third-party imports
import libcst as cst
import pytest

# First-party imports
import pydocformatter.rules.runner as rule_runner
import pydocformatter.rules.collection as rule_collection
import pydocformatter.rules.documentation as rule_documentation
from pydocformatter.cli import settings_check
from pydocformatter.rules import line_endings
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.models import RuleSettingEffect
from pydocformatter.source_path import SourcePathContext
from tests import markdown_example_helpers, markdown_table_helpers


if TYPE_CHECKING:
    # First-party imports
    import pydocformatter.rules.models as rule_models
    from pydocformatter.rules.definition import RuleBase


_RULE_SELECTION_SETTING_KEYS = frozenset(definition.key for definition in settings_check.SETTINGS_SCHEMA.definitions if definition.group == settings_check.SettingsGroup.RULE_SELECTION)
_REQUIRE_EXPLICIT_NOTICE = "Rule must by default be explicitly selected, unless it is removed from `require-explicit`."
_FENCED_CODE_BLOCK_RE = re.compile(r"^(`{3,}|~{3,}).*?^\1\s*$", re.DOTALL | re.MULTILINE)
_RUFF_RULE_REFERENCE_RE = re.compile(r"\b(?:(?:D|DOC|E|W|RUF)\d{3}|PLE\d{4})\b")
_PYDOCFORMATTER_RULE_REFERENCE_RE = re.compile(r"\bP[CD]F\d{3}\b")
_TEMPLATE_PLACEHOLDERS = ("Describe the rule's check", "This line says", "CODE101", "related-setting", "Topic name", "Briefly describe")
RUFF_RULE_TABLE_HEADERS = ("Code", "Name", "Message", "Fixable", "Since", "Support by pydocformatter")


def _rule_cases() -> tuple[tuple[str, type[RuleBase]], ...]:
    """Return built-in rule cases for pytest parametrization."""
    return tuple((rule_class.meta.code.tag, rule_class) for rule_class in rule_collection.RULE_COLLECTION.rules)


@pytest.mark.filterwarnings("ignore:invalid escape sequence.*:DeprecationWarning")
@pytest.mark.parametrize(("rule_code", "rule_class"), _rule_cases())
def test_rule_markdown_examples_match_rule_implementation(rule_code: str, rule_class: type[object]) -> None:
    """Execute every structured rule Markdown example against the documented rule."""
    executed_examples = _executed_rule_markdown_examples(rule_code, rule_class)

    for executed in executed_examples:
        _assert_clean_example_has_no_hidden_fix_changes(executed)
        _assert_initial_check_findings_accounted_after_fixing(executed)


def _executed_rule_markdown_examples(rule_code: str, rule_class: type[object]) -> tuple[markdown_example_helpers.MarkdownExampleOutcome, ...]:
    """Execute and return every structured example for one rule."""
    markdown = rule_documentation.load_rule_explanation(rule_class)
    examples = rule_documentation.parse_rule_markdown_examples(markdown, rule_code=rule_code)
    assert examples, f"{rule_code}: expected at least one structured pydocfmt-example block"

    executed_examples: list[markdown_example_helpers.MarkdownExampleOutcome] = []
    for index, example in enumerate(examples, start=1):
        _validate_rule_selection_settings(rule_code, index, example)
        executed_examples.append(
            markdown_example_helpers.execute_markdown_example(
                example, label=f"{rule_code} example {index}", fallback_path=f"{rule_code}_example_{index}.py", field_overrides=settings_check.CheckSettingsOverrides(select=(rule_code,))
            )
        )
    return tuple(executed_examples)


def _assert_clean_example_has_no_hidden_fix_changes(executed: markdown_example_helpers.MarkdownExampleOutcome) -> None:
    """Check-clean documented examples must not be changed by a direct fix pass."""
    if any(finding.fixable for finding in executed.check_result.unfixed_findings):
        return

    module = cst.parse_module(executed.example.input_source)
    selected_rule_by_code = {selected_rule.rule.code: selected_rule for selected_rule in executed.selection.for_path(executed.path)}
    errors: list[str] = []
    fixed_module, fixed_findings, source_changed = rule_runner._run_fix_pass(
        module,
        path=executed.path,
        settings=executed.settings,
        line_ending=line_endings.resolve_line_ending(executed.example.input_source, line_ending=executed.settings.line_ending),
        execution_plan=executed.selection.execution_plan_for_path(executed.path),
        selected_rule_by_code=selected_rule_by_code,
        errors=errors,
        source_path=SourcePathContext.for_path(executed.path),
    )

    assert errors == [], f"{executed.label}: unexpected direct fix errors: {errors}"
    assert fixed_findings == (), f"{executed.label}: direct fix reported findings after a clean check"
    assert not source_changed, f"{executed.label}: direct fix changed source after a clean check"
    assert fixed_module.code == executed.example.input_source, f"{executed.label}: direct fix returned different source after a clean check"


def _assert_initial_check_findings_accounted_after_fixing(executed: markdown_example_helpers.MarkdownExampleOutcome) -> None:
    """Documented examples must account for every initial check finding as fixed or still unfixed."""
    line_ending = line_endings.resolve_line_ending(executed.example.input_source, line_ending=executed.settings.line_ending)
    module = cst.parse_module(executed.example.input_source)
    fixed_result = rule_runner.run_rule_plan(
        module,
        path=executed.path,
        settings=executed.settings,
        line_ending=line_ending,
        execution_plan=executed.selection.execution_plan_for_path(executed.path),
        fix=True,
        source_path=SourcePathContext.for_path(executed.path),
        source=executed.example.input_source,
    )

    assert fixed_result.errors == (), f"{executed.label}: unexpected fix errors: {fixed_result.errors}"
    initial_finding_counts = collections.Counter(_finding_correspondence_key(executed.check_result.unfixed_findings))
    accounted_finding_counts = collections.Counter(_finding_correspondence_key(fixed_result.fixed_findings + fixed_result.unfixed_findings))
    assert initial_finding_counts == accounted_finding_counts, f"{executed.label}: initial check findings were not accounted for as fixed or still unfixed"


def test_parse_rule_markdown_examples_preserves_nested_shorter_fences() -> None:
    """Nested shorter code fences do not close the outer example block."""
    examples = rule_documentation.parse_rule_markdown_examples(
        """````pydocfmt-example
[input]
# ```python
# value = 1
# ```

[output=unchanged]
````
""",
        rule_code="PCF001",
    )

    assert examples[0].input_source == "# ```python\n# value = 1\n# ```\n"


def test_rule_markdown_require_explicit_notices_match_default_setting() -> None:
    """Rules with the standard opt-in notice match the default require-explicit setting."""
    noticed_codes = frozenset(rule_code for rule_code, rule_class in _rule_cases() if _REQUIRE_EXPLICIT_NOTICE in rule_documentation.load_rule_explanation(rule_class))

    assert noticed_codes == frozenset(settings_check.DEFAULT_REQUIRE_EXPLICIT)


def test_rule_markdown_preambles_match_metadata() -> None:
    """Rule docs must start with canonical metadata-derived notices."""
    for rule_code, rule_class in _rule_cases():
        paragraphs = _leading_rule_markdown_paragraphs(rule_documentation.load_rule_explanation(rule_class))
        expected = [f"# {rule_class.meta.name} ({rule_code})", rule_documentation.rule_fix_text(rule_class.meta)]
        if (docstring_convention_notice := _expected_docstring_convention_notice(rule_class.meta)) is not None:
            expected.append(docstring_convention_notice)
        if rule_code in settings_check.DEFAULT_REQUIRE_EXPLICIT:
            expected.append(_REQUIRE_EXPLICIT_NOTICE)
        if rule_class.meta.incompatible_with:
            expected.append(_expected_incompatibility_notice(rule_class.meta))

        assert paragraphs == tuple(expected), f"{rule_code}: unexpected rule Markdown preamble"


def _expected_docstring_convention_notice(rule: rule_models.RuleMetadata) -> str | None:
    """Return the canonical docstring-convention notice for rule metadata."""
    effects = _docstring_convention_effects(rule)
    disabled = tuple(convention for convention in settings_check.DocstringConvention if convention in effects[RuleSettingEffect.DISABLED])
    ignored = tuple(convention for convention in settings_check.DocstringConvention if convention in effects[RuleSettingEffect.IGNORED])

    if disabled and ignored:
        return f"Rule is disabled if `docstring-convention` is {_or_list(disabled)}, and ignored by broad selectors under {_and_list(ignored)}."
    if disabled:
        return f"Rule is disabled if `docstring-convention` is {_or_list(disabled)}."
    if ignored:
        if len(ignored) == len(tuple(settings_check.DocstringConvention)):
            return "Rule is ignored by broad selectors for all `docstring-convention` values."
        return f"Rule is ignored if `docstring-convention` is {_or_list(ignored)}."
    return None


def _docstring_convention_effects(rule: rule_models.RuleMetadata) -> dict[RuleSettingEffect, frozenset[settings_check.DocstringConvention]]:
    """Return disabled and ignored docstring conventions for a rule."""
    return {
        effect: frozenset(convention for convention in settings_check.DocstringConvention if rule.setting_effect("docstring_convention", convention) is effect)
        for effect in (RuleSettingEffect.DISABLED, RuleSettingEffect.IGNORED)
    }


def _leading_rule_markdown_paragraphs(markdown: str) -> tuple[str, ...]:
    """Return rule Markdown preamble paragraphs before the rule body."""
    preamble = markdown.split("\n## What it does", maxsplit=1)[0]
    return tuple(paragraph.strip() for paragraph in preamble.split("\n\n") if paragraph.strip())


def _expected_incompatibility_notice(rule: rule_models.RuleMetadata) -> str:
    """Return the canonical incompatibility notice for rule metadata."""
    return f"Rule is incompatible with {_joined_rule_codes(rule.incompatible_with)}."


def _joined_rule_codes(rule_codes: tuple[RuleCode, ...]) -> str:
    """Return rule codes as a human-readable list."""
    quoted = tuple(f"`{rule_code}`" for rule_code in rule_codes)
    if len(quoted) == 1:
        return quoted[0]
    if len(quoted) == 2:
        return f"{quoted[0]} and {quoted[1]}"
    return f"{', '.join(quoted[:-1])}, and {quoted[-1]}"


def test_rule_markdown_ruff_references_exist_in_rule_list() -> None:
    """Rule-level Ruff compatibility text must not mention unknown Ruff codes."""
    known_ruff_codes = _rule_list_ruff_codes()
    for rule_code, rule_class in _rule_cases():
        section = _markdown_section(rule_documentation.load_rule_explanation(rule_class), "Ruff compatibility")
        mentioned_codes = frozenset(_RUFF_RULE_REFERENCE_RE.findall(section))

        assert mentioned_codes <= known_ruff_codes, f"{rule_code}: unknown Ruff compatibility references: {sorted(mentioned_codes - known_ruff_codes)}"


def test_rule_markdown_ruff_none_sections_are_canonical() -> None:
    """Ruff compatibility sections must use None only when there is no Ruff prose."""
    for rule_code, rule_class in _rule_cases():
        section = _markdown_section(rule_documentation.load_rule_explanation(rule_class), "Ruff compatibility").strip()
        if section == "None.":
            assert not _RUFF_RULE_REFERENCE_RE.search(section), f"{rule_code}: Ruff compatibility None section mentions Ruff codes"
            continue

        assert not section.startswith("None."), f"{rule_code}: Ruff compatibility section must not combine None with prose"


def test_rule_markdown_rule_references_exist() -> None:
    """Rule docs must not mention unknown pydocformatter rule codes."""
    known_rule_codes = frozenset(rule_collection.RULE_COLLECTION.rule_class)
    for label, markdown in _rule_and_category_markdown_documents():
        mentioned_codes = frozenset(RuleCode(code) for code in _PYDOCFORMATTER_RULE_REFERENCE_RE.findall(_FENCED_CODE_BLOCK_RE.sub("", markdown)))

        assert mentioned_codes <= known_rule_codes, f"{label}: unknown pydocformatter rule references: {sorted(mentioned_codes - known_rule_codes)}"


def test_rule_markdown_tables_are_well_formed() -> None:
    """Markdown tables in rule docs must satisfy the full parser contract."""
    for label, markdown in _rule_and_category_markdown_documents():
        markdown_table_helpers.validate_tables(markdown, label=label)


def _rule_list_ruff_codes() -> frozenset[str]:
    """Return Ruff codes documented in the public Ruff rules table."""
    text = (pathlib.Path(__file__).resolve().parents[1] / "docs" / "public" / "ruff_rule_links.md").read_text(encoding="utf-8")
    table = markdown_table_helpers.table_after_heading(
        text, "## Ruff rules", label="docs/public/ruff_rule_links.md", expected_leading_lines=('<div class="pydocformatter-rule-table-wrapper" markdown="1">',)
    )
    assert markdown_table_helpers.table_headers(table, label="docs/public/ruff_rule_links.md") == RUFF_RULE_TABLE_HEADERS
    return frozenset(_plain_code_cell(row["Code"]) for row in markdown_table_helpers.table_rows(table, label="docs/public/ruff_rule_links.md"))


def _plain_code_cell(cell: str) -> str:
    """Return the visible rule code from a linked or code-formatted table cell."""
    match = re.fullmatch(r"\[`([^`]+)`\]\([^)]+\)", cell)
    if match:
        return match.group(1)
    return cell.strip("`")


def _rule_and_category_markdown_documents() -> tuple[tuple[str, str], ...]:
    """Return labels and Markdown text for built-in rule and category docs."""
    documents = [(rule_code, rule_documentation.load_rule_explanation(rule_class)) for rule_code, rule_class in _rule_cases()]
    documents.extend((category_class.meta.prefix, rule_documentation.load_rule_explanation(category_class)) for category_class in rule_collection.RULE_COLLECTION.categories)
    return tuple(documents)


def _markdown_section(markdown: str, heading: str) -> str:
    """Return the body of a level-two Markdown section."""
    marker = f"## {heading}"
    lines = markdown.splitlines()
    start = lines.index(marker) + 1
    end = next((index for index, line in enumerate(lines[start:], start=start) if line.startswith("## ")), len(lines))
    return "\n".join(lines[start:end])


def test_rule_and_category_markdown_do_not_contain_template_placeholders() -> None:
    """Built-in Markdown docs must not retain targeted template placeholders."""
    for rule_code, rule_class in _rule_cases():
        _assert_no_template_placeholders(f"{rule_code}", rule_documentation.load_rule_explanation(rule_class))
    for category_class in rule_collection.RULE_COLLECTION.categories:
        _assert_no_template_placeholders(category_class.meta.prefix, rule_documentation.load_rule_explanation(category_class))


def _assert_no_template_placeholders(label: str, markdown: str) -> None:
    """Assert targeted template placeholder text is absent from Markdown prose."""
    prose_markdown = _FENCED_CODE_BLOCK_RE.sub("", markdown)
    for placeholder in _TEMPLATE_PLACEHOLDERS:
        haystack = markdown if placeholder == "CODE101" else prose_markdown
        assert placeholder not in haystack, f"{label}: template placeholder remains: {placeholder}"


def _or_list(conventions: tuple[settings_check.DocstringConvention, ...]) -> str:
    """Return convention values joined with `or`."""
    return _joined_conventions(conventions, conjunction="or")


def _and_list(conventions: tuple[settings_check.DocstringConvention, ...]) -> str:
    """Return convention values joined with `and`."""
    return _joined_conventions(conventions, conjunction="and")


def _joined_conventions(conventions: tuple[settings_check.DocstringConvention, ...], *, conjunction: str) -> str:
    """Return convention values as a human-readable list."""
    quoted = tuple(f"`{convention.value}`" for convention in conventions)
    if len(quoted) == 1:
        return quoted[0]
    if len(quoted) == 2:
        return f"{quoted[0]} {conjunction} {quoted[1]}"
    return f"{', '.join(quoted[:-1])}, {conjunction} {quoted[-1]}"


def test_parse_rule_markdown_examples_rejects_reversed_finding_ranges() -> None:
    """Finding ranges must not silently collapse to no lines."""
    with pytest.raises(rule_documentation.RuleMarkdownExampleParseError, match="invalid reversed finding range"):
        rule_documentation.parse_rule_markdown_examples(
            """```pydocfmt-example
[input]
pass

[output=unchanged]
[findings]
PDF101: Lines 5-3: Example message
```
""",
            rule_code="PDF101",
        )


def test_parse_rule_markdown_examples_rejects_mismatched_finding_line_labels() -> None:
    """Finding line labels must match singular and plural line references."""
    with pytest.raises(rule_documentation.RuleMarkdownExampleParseError, match="expected 'Line'"):
        rule_documentation.parse_rule_markdown_examples(
            """```pydocfmt-example
[input]
pass

[output=unchanged]
[findings]
PDF101: Lines 5: Example message
```
""",
            rule_code="PDF101",
        )

    with pytest.raises(rule_documentation.RuleMarkdownExampleParseError, match="expected 'Lines'"):
        rule_documentation.parse_rule_markdown_examples(
            """```pydocfmt-example
[input]
pass

[output=unchanged]
[findings]
PDF101: Line 3-4: Example message
```
""",
            rule_code="PDF101",
        )


def test_parse_rule_markdown_examples_treats_degenerate_ranges_as_single_lines() -> None:
    """A degenerate finding range is singular because it expands to one line."""
    examples = rule_documentation.parse_rule_markdown_examples(
        """```pydocfmt-example
[input]
pass

[output=unchanged]
[findings]
PDF101: Line 4-4: Example message
```
""",
        rule_code="PDF101",
    )

    assert examples[0].findings == ((RuleCode("PDF101"), (4,), "Example message"),)

    with pytest.raises(rule_documentation.RuleMarkdownExampleParseError, match="expected 'Line'"):
        rule_documentation.parse_rule_markdown_examples(
            """```pydocfmt-example
[input]
pass

[output=unchanged]
[findings]
PDF101: Lines 4-4: Example message
```
""",
            rule_code="PDF101",
        )


def test_parse_rule_markdown_examples_requires_finding_messages() -> None:
    """Finding lines must include the exact expected message."""
    with pytest.raises(rule_documentation.RuleMarkdownExampleParseError, match="invalid finding line"):
        rule_documentation.parse_rule_markdown_examples(
            """```pydocfmt-example
[input]
pass

[output=unchanged]
[findings]
PDF101: Line 4
```
""",
            rule_code="PDF101",
        )

    # The \x20 preserves an intentionally blank finding message without source trailing whitespace.
    with pytest.raises(rule_documentation.RuleMarkdownExampleParseError, match="invalid finding line"):
        rule_documentation.parse_rule_markdown_examples(
            """```pydocfmt-example
[input]
pass

[output=unchanged]
[findings]
PDF101: Line 4:\x20
```
""",
            rule_code="PDF101",
        )


def test_parse_rule_markdown_examples_preserves_exact_finding_messages() -> None:
    """Finding messages are parsed exactly and duplicate finding locations are preserved."""
    examples = rule_documentation.parse_rule_markdown_examples(
        """```pydocfmt-example
[input]
pass

[output=unchanged]
[findings]
PDF101: Line 4: First exact message
PDF101: Line 4: Second exact message: with colon
```
""",
        rule_code="PDF101",
    )

    assert examples[0].findings == ((RuleCode("PDF101"), (4,), "First exact message"), (RuleCode("PDF101"), (4,), "Second exact message: with colon"))


def test_parse_rule_markdown_examples_rejects_output_matching_input() -> None:
    """Unchanged examples must use the explicit unchanged output marker."""
    with pytest.raises(rule_documentation.RuleMarkdownExampleParseError, match=r"use \[output=unchanged\]"):
        rule_documentation.parse_rule_markdown_examples(
            """```pydocfmt-example
[input]
value = "kept"

[output]
value = "kept"
```
""",
            rule_code="PDF000",
        )


def test_parse_rule_markdown_examples_preserves_section_source_text() -> None:
    """Section parsing keeps byte-relevant source text inside the section body."""
    examples = rule_documentation.parse_rule_markdown_examples(
        """```pydocfmt-example
[input]
value = "kept"

[output]
value = "changed"
```
""",
        rule_code="PDF000",
    )

    assert examples[0].input_source == 'value = "kept"\n'
    assert examples[0].output_source == 'value = "changed"\n'


def test_parse_rule_markdown_examples_preserves_bracketed_input_source_lines() -> None:
    """Input-like bracketed source lines are not treated as invalid markers."""
    examples = rule_documentation.parse_rule_markdown_examples(
        """```pydocfmt-example
[input]
[input_map]
value = "kept"

[output=unchanged]
```
""",
        rule_code="PDF000",
    )

    assert examples[0].input_source == '[input_map]\nvalue = "kept"\n'
    assert examples[0].output_source == examples[0].input_source


def test_parse_rule_markdown_examples_allows_input_paths() -> None:
    """An input marker can carry a path for path-sensitive rules."""
    examples = rule_documentation.parse_rule_markdown_examples(
        """```pydocfmt-example
[input=package/__init__.py]
value = "kept"

[output=unchanged]
```
""",
        rule_code="PDF000",
    )

    assert examples[0].path == "package/__init__.py"


def test_parse_rule_markdown_examples_rejects_invalid_input_paths() -> None:
    """Input path markers must contain a non-empty display path without marker syntax."""
    for marker in ("[input=]", "[input = package/module.py]", "[input=package].py]"):
        with pytest.raises(rule_documentation.RuleMarkdownExampleParseError, match=r"invalid \[input=PATH\] marker"):
            rule_documentation.parse_rule_markdown_examples(
                f"""```pydocfmt-example
{marker}
value = "kept"

[output=unchanged]
```
""",
                rule_code="PDF000",
            )


def _validate_rule_selection_settings(rule_code: str, example_number: int, example: rule_documentation.RuleMarkdownExample) -> None:
    """Validate test-owned rule-selection settings are not overridden by examples."""
    if not example.settings_text:
        return
    try:
        settings = tomllib.loads(example.settings_text)
    except tomllib.TOMLDecodeError as error:
        raise AssertionError(f"{rule_code} example {example_number}: invalid [settings] TOML: {error}") from error
    rule_selection_settings = tuple(sorted(_RULE_SELECTION_SETTING_KEYS & settings.keys()))
    if rule_selection_settings:
        raise AssertionError(f"{rule_code} example {example_number}: rule-selection settings are controlled by the test: {', '.join(rule_selection_settings)}")


def _finding_correspondence_key(findings: tuple[rule_models.RuleFinding, ...]) -> tuple[tuple[RuleCode, tuple[int, ...], bool], ...]:
    """Return the comparable shape for check/fix correspondence."""
    return tuple((finding.rule.code, finding.line_numbers, finding.fixable) for finding in findings)
