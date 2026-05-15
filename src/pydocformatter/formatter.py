from __future__ import annotations

import dataclasses
import os
import typing

from pydocformatter.cli.settings_check import CheckSettings, LineEnding


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
    """Formatter result, including the possibly now-formatted source, for one display path."""

    path: str
    source: str | None
    modified: bool
    findings: tuple[RuleFinding, ...]
    errors: tuple[str, ...]


def format_file_exp(path: str, *, file: typing.TextIO | None = None, settings: CheckSettings, fix: bool) -> FormatterResult:
    """Run the experimental formatter interface for one file."""
    try:
        if file is None:
            with open(path, encoding="utf-8", newline="") as path_file:
                source = path_file.read()
        else:
            source = file.read()
    except UnicodeDecodeError as error:
        return FormatterResult(path=path, source=None, modified=False, findings=(), errors=(f"Failed to decode {path} as UTF-8: {error}",))
    except OSError as error:
        return FormatterResult(path=path, source=None, modified=False, findings=(), errors=(f"Failed to read file {path}: {error}",))

    result = format_source_exp(source, path, settings=settings, fix=fix)
    if result.source is None:
        raise AssertionError("format_source_exp() must return a valid source state")

    if file is None and fix and result.modified:
        try:
            with open(path, "w", encoding="utf-8", newline="") as path_file:
                path_file.write(result.source)
        except OSError as error:
            return FormatterResult(path=path, source=source, modified=False, findings=(), errors=(f"Failed to write file {path}: {error}",))

    return result


def format_source_exp(source: str, path: str, *, settings: CheckSettings, fix: bool) -> FormatterResult:
    """Run the experimental formatter interface for source text."""
    del settings, fix
    # TODO: Temporary placeholder code that must produce a non-None new_source (can just be source if nothing was or
    #       should be fixed, otherwise it should represent the new formatted source)
    new_source = source
    return FormatterResult(path=path, source=new_source, modified=(new_source != source), findings=(), errors=())


def resolve_line_ending(source: str, *, line_ending: LineEnding) -> str:
    """Return the concrete line ending to use for rewritten source."""
    if line_ending == LineEnding.AUTO:
        return detect_line_ending(source)
    elif line_ending == LineEnding.LF:
        return "\n"
    elif line_ending == LineEnding.CR_LF:
        return "\r\n"
    elif line_ending == LineEnding.NATIVE:
        return os.linesep
    else:
        raise ValueError(f"Unexpected line ending specification: {line_ending}")


def detect_line_ending(source: str) -> str:
    """Return the first line ending in source, defaulting to LF when absent."""
    for index, char in enumerate(source):
        if char == "\n":
            return "\n"
        if char == "\r":
            next_index = index + 1
            if next_index < len(source) and source[next_index] == "\n":
                return "\r\n"
            return "\r"
    return "\n"


def normalize_line_endings(text: str, *, line_ending: str) -> str:
    """Convert every line ending in text to line_ending."""
    return text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", line_ending)
