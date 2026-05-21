from __future__ import annotations

import dataclasses
import importlib.resources
import inspect
import pathlib

from pydocformatter.rules.base import RuleMetadata
from pydocformatter.rules.collection import RuleCollection

TEMPLATE_PATH = pathlib.Path(__file__).with_name("rule_template.md")


@dataclasses.dataclass(frozen=True)
class RuleSourceLocation:
    """Source location for a rule definition class."""

    file: str
    line: int


def load_rule_explanation(rule_class: type[object]) -> str:
    """Load the Markdown explanation file adjacent to a rule definition module."""
    module_name = rule_class.__module__
    package_name, _, module_basename = module_name.rpartition(".")
    if not package_name or not module_basename:
        raise FileNotFoundError(f"Rule class module does not have an adjacent package resource path: {module_name}")
    return importlib.resources.files(package_name).joinpath(f"{module_basename}.md").read_text(encoding="utf-8")


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
