from __future__ import annotations

import dataclasses

from pydocformatter.config import FormatterSettings


@dataclasses.dataclass(frozen=True)
class Rule:
    """Metadata for one pydocformatter rule."""

    rule_code: str
    rule_name: str
    message: str
    fixable: bool


RuleFindingKey = tuple[Rule, str, bool]


@dataclasses.dataclass(frozen=True)
class RuleFinding:
    """A remaining rule issue after formatting has run."""

    rule: Rule
    line_numbers: tuple[int, ...]
    instance_message: str | None = None
    instance_fixable: bool | None = None

    @property
    def message(self) -> str:
        """Return the message for this finding."""
        return self.rule.message if self.instance_message is None else self.instance_message

    @property
    def fixable(self) -> bool:
        """Return whether this specific finding can be automatically fixed."""
        return self.rule.fixable if self.instance_fixable is None else self.instance_fixable

    @property
    def grouping_key(self) -> RuleFindingKey:
        """Return the key used to merge findings that differ only by line numbers."""
        return self.rule, self.message, self.fixable

    def with_line_numbers(self, line_numbers: tuple[int, ...]) -> RuleFinding:
        """Return this finding with updated line numbers."""
        return dataclasses.replace(self, line_numbers=line_numbers)


@dataclasses.dataclass(frozen=True)
class FormatterResult:
    """Formatter result for one display path."""

    path: str
    modified: bool
    findings: tuple[RuleFinding, ...]
    diagnostic_messages: tuple[str, ...] = ()


def format_file_exp(path: str, settings: FormatterSettings, fix: bool) -> FormatterResult:
    """Run the experimental formatter interface for one file."""
    with open(path, encoding="utf-8", newline="") as file:
        file.read()

    return FormatterResult(path=path, modified=False, findings=())


def format_source_exp(source: str, path: str, settings: FormatterSettings, fix: bool) -> tuple[str, FormatterResult]:
    """Run the experimental formatter interface for stdin source."""
    del settings, fix
    return source, FormatterResult(path=path, modified=False, findings=())
