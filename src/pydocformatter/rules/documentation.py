"""Rule Markdown documentation parsing."""

from __future__ import annotations

import dataclasses
import importlib.resources
import inspect
import pathlib
import re
import tomllib

from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.collection import RuleCollection
from pydocformatter.rules.models import FixAvailability, RuleCategoryMetadata, RuleMetadata

TEMPLATE_PATH = pathlib.Path(__file__).with_name("templates") / "rule_template.md"
CATEGORY_TEMPLATE_PATH = pathlib.Path(__file__).with_name("templates") / "rule_category_template.md"
_EXAMPLE_OPENING_FENCE_RE = re.compile(r"^(?P<fence>`{3,})pydocfmt-example[^\n]*$")
_SECTION_MARKERS = frozenset(("settings", "input", "output", "output=unchanged", "findings"))
_FINDING_RE = re.compile(r"^(?P<code>[A-Z]+[0-9]+): (?P<label>Line|Lines) (?P<lines>[0-9][0-9, -]*): (?P<message>.+)$")


class RuleMarkdownExampleParseError(ValueError):
    """Raised when a structured rule Markdown example is invalid."""


@dataclasses.dataclass(frozen=True)
class RuleMarkdownExample:
    """Structured rule Markdown example parsed from a ``pydocfmt-example`` block.

    Attributes:
        settings_text (str): TOML settings snippet declared for the example.
        input_source (str): Python source passed to pydocformatter.
        output_source (str): Expected fixed source, or the input source for unchanged examples.
        findings (tuple[tuple[RuleCode, tuple[int, ...], str], ...]): Expected diagnostics as rule code, line numbers,
            and message.
    """

    settings_text: str
    input_source: str
    output_source: str
    findings: tuple[tuple[RuleCode, tuple[int, ...], str], ...]


def rule_fix_text(rule: RuleMetadata) -> str:
    """Return user-facing fix availability text for one rule."""
    if rule.fix_availability == FixAvailability.ALWAYS:
        return "Fix is always available."
    elif rule.fix_availability == FixAvailability.USUALLY:
        return "Fix is usually available."
    elif rule.fix_availability == FixAvailability.SOMETIMES:
        return "Fix is sometimes available."
    elif rule.fix_availability == FixAvailability.NEVER:
        return "Fix is not available."
    else:
        raise AssertionError(f"Unexpected fix availability: {rule.fix_availability}")


@dataclasses.dataclass(frozen=True)
class RuleSourceLocation:
    """Source location for a rule definition class.

    Attributes:
        file (str): Source file that defines the rule class.
        line (int): One-based line number where the rule class is defined.
    """

    file: str
    line: int


def load_rule_explanation(rule_class: type[object]) -> str:
    """Load the Markdown explanation file adjacent to a rule definition module."""
    module_name = rule_class.__module__
    package_name, _, module_basename = module_name.rpartition(".")
    if not package_name or not module_basename:
        raise FileNotFoundError(f"Rule class module does not have an adjacent package resource path: {module_name}")
    return importlib.resources.files(package_name).joinpath(f"{module_basename}.md").read_text(encoding="utf-8")


def parse_rule_markdown_examples(markdown: str, *, rule_code: str) -> tuple[RuleMarkdownExample, ...]:
    """Parse structured examples from one rule Markdown document."""
    examples: list[RuleMarkdownExample] = []
    lines = markdown.splitlines(keepends=True)
    line_index = 0
    while line_index < len(lines):
        opening_match = _EXAMPLE_OPENING_FENCE_RE.fullmatch(lines[line_index].rstrip("\n"))
        if opening_match is None:
            line_index += 1
            continue
        fence = opening_match.group("fence")
        body_lines: list[str] = []
        line_index += 1
        while line_index < len(lines):
            if lines[line_index].strip() == fence:
                break
            body_lines.append(lines[line_index])
            line_index += 1
        else:
            raise RuleMarkdownExampleParseError(f"{rule_code} example {len(examples) + 1}: missing closing {fence} fence")
        examples.append(_parse_example_block("".join(body_lines), rule_code=rule_code, example_number=len(examples) + 1))
        line_index += 1
    return tuple(examples)


def _parse_example_block(body: str, *, rule_code: str, example_number: int) -> RuleMarkdownExample:
    """Parse one ``pydocfmt-example`` fence body."""
    sections: dict[str, str] = {}
    order: list[str] = []
    current_name: str | None = None
    current_lines: list[str] = []

    for line in body.splitlines(keepends=True):
        marker = _section_marker(line)
        if marker is None:
            if current_name is not None:
                current_lines.append(line)
            continue
        if current_name is not None:
            sections[current_name] = _section_body(current_lines)
        if marker in sections or marker in order:
            raise RuleMarkdownExampleParseError(f"{rule_code} example {example_number}: duplicate [{marker}] section")
        current_name = marker
        current_lines = []
        order.append(marker)

    if current_name is not None:
        sections[current_name] = _section_body(current_lines)
    if not order:
        raise RuleMarkdownExampleParseError(f"{rule_code} example {example_number}: expected structured sections")

    _validate_section_order(order, rule_code=rule_code, example_number=example_number)
    settings_text = _parse_example_settings(sections.get("settings", ""), rule_code=rule_code, example_number=example_number)
    input_source = sections["input"]
    if "output=unchanged" in sections:
        if sections["output=unchanged"]:
            raise RuleMarkdownExampleParseError(f"{rule_code} example {example_number}: [output=unchanged] must not have a body")
        output_source = input_source
    else:
        output_source = sections["output"]
        if output_source == input_source:
            raise RuleMarkdownExampleParseError(f"{rule_code} example {example_number}: use [output=unchanged] when output is identical to input")
    findings = _parse_findings(sections.get("findings", ""), rule_code=rule_code, example_number=example_number)
    return RuleMarkdownExample(settings_text=settings_text, input_source=input_source, output_source=output_source, findings=findings)


def _section_marker(line: str) -> str | None:
    """Return the structured example section name for a marker line."""
    marker = line.removesuffix("\n")
    if marker.endswith("\r"):
        marker = marker[:-1]
    if not marker.startswith("[") or not marker.endswith("]"):
        return None
    name = marker[1:-1]
    if name in _SECTION_MARKERS:
        return name
    return None


def _section_body(lines: list[str]) -> str:
    """Return section content without the blank separator before the next marker."""
    if lines and lines[-1] in ("\n", "\r\n"):
        return "".join(lines[:-1])
    return "".join(lines)


def _validate_section_order(order: list[str], *, rule_code: str, example_number: int) -> None:
    """Validate the section shape of one structured example."""
    if "input" not in order:
        raise RuleMarkdownExampleParseError(f"{rule_code} example {example_number}: missing [input] section")
    has_output = "output" in order
    has_unchanged_output = "output=unchanged" in order
    if has_output == has_unchanged_output:
        raise RuleMarkdownExampleParseError(f"{rule_code} example {example_number}: expected exactly one of [output] or [output=unchanged]")

    expected_order = ["settings", "input", "output" if has_output else "output=unchanged", "findings"]
    expected_order = [name for name in expected_order if name in order]
    if order != expected_order:
        raise RuleMarkdownExampleParseError(f"{rule_code} example {example_number}: expected section order {expected_order}, got {order}")


def _parse_example_settings(settings_text: str, *, rule_code: str, example_number: int) -> str:
    """Parse and validate one example settings block as TOML."""
    if not settings_text:
        return ""
    try:
        tomllib.loads(settings_text)
    except tomllib.TOMLDecodeError as error:
        raise RuleMarkdownExampleParseError(f"{rule_code} example {example_number}: invalid [settings] TOML: {error}") from error
    return settings_text


def _parse_findings(findings_text: str, *, rule_code: str, example_number: int) -> tuple[tuple[RuleCode, tuple[int, ...], str], ...]:
    """Parse an optional findings section."""
    findings: list[tuple[RuleCode, tuple[int, ...], str]] = []
    for line in findings_text.splitlines():
        if not line:
            continue
        match = _FINDING_RE.fullmatch(line)
        if match is None:
            raise RuleMarkdownExampleParseError(f"{rule_code} example {example_number}: invalid finding line: {line!r}")
        line_numbers = _parse_line_numbers(match.group("lines"), rule_code=rule_code, example_number=example_number)
        _validate_finding_line_label(match.group("label"), line_numbers, rule_code=rule_code, example_number=example_number)
        findings.append((RuleCode(match.group("code")), line_numbers, match.group("message")))
    return tuple(findings)


def _parse_line_numbers(text: str, *, rule_code: str, example_number: int) -> tuple[int, ...]:
    """Parse comma-separated line numbers and ranges."""
    line_numbers: list[int] = []
    for part in text.split(","):
        part = part.strip()
        if "-" in part:
            start_text, end_text = part.split("-", maxsplit=1)
            start = int(start_text.strip())
            end = int(end_text.strip())
            if start > end:
                raise RuleMarkdownExampleParseError(f"{rule_code} example {example_number}: invalid reversed finding range: {part!r}")
            line_numbers.extend(range(start, end + 1))
        else:
            line_numbers.append(int(part))
    return tuple(line_numbers)


def _validate_finding_line_label(label: str, line_numbers: tuple[int, ...], *, rule_code: str, example_number: int) -> None:
    """Validate the singular or plural finding line label."""
    expected_label = "Line" if len(line_numbers) == 1 else "Lines"
    if label != expected_label:
        raise RuleMarkdownExampleParseError(f"{rule_code} example {example_number}: expected {expected_label!r} for finding lines, got {label!r}")


def load_rule_category_explanation(category_class: type[object]) -> str:
    """Load Markdown documentation adjacent to a rule category module."""
    return load_rule_explanation(category_class)


def rule_explanation_body(rule_class: type[object]) -> str:
    """Return the Markdown explanation without the rule title and fixability lines."""
    explanation = load_rule_explanation(rule_class)
    lines = explanation.splitlines()
    if len(lines) >= 4 and lines[0].startswith("# ") and lines[1] == "" and lines[2].startswith("Fix is ") and lines[3] == "":
        return "\n".join(lines[4:]) + ("\n" if explanation.endswith("\n") else "")
    return explanation


def rule_source_location(rule_class: type[object]) -> RuleSourceLocation | None:
    """Return the source location of a rule class if it is available."""
    try:
        source_lines, line_number = inspect.getsourcelines(rule_class)
    except OSError:
        return None
    del source_lines
    source_file = inspect.getsourcefile(rule_class)
    if source_file is None:
        return None
    path = pathlib.Path(source_file)
    try:
        display_file = str(path.relative_to(pathlib.Path.cwd()))
    except ValueError:
        display_file = str(path)
    return RuleSourceLocation(file=display_file, line=line_number)


def undocumented_rules(collection: RuleCollection) -> tuple[RuleMetadata, ...]:
    """Return built-in rules whose adjacent Markdown explanation cannot be loaded."""
    missing: list[RuleMetadata] = []
    for rule_class in collection.rules:
        try:
            load_rule_explanation(rule_class)
        except FileNotFoundError:
            missing.append(rule_class.meta)
    return tuple(missing)


def undocumented_rule_categories(collection: RuleCollection) -> tuple[RuleCategoryMetadata, ...]:
    """Return built-in rule categories whose adjacent Markdown cannot be loaded."""
    missing: list[RuleCategoryMetadata] = []
    for category_class in collection.categories:
        try:
            load_rule_category_explanation(category_class)
        except FileNotFoundError:
            missing.append(category_class.meta)
    return tuple(missing)
