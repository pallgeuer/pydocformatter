from __future__ import annotations

import collections
import dataclasses
import os
import typing

from pydocformatter.cli.settings_check import CheckSettings, LineEnding
from pydocformatter.rules.base import FixAvailability, RuleMetadata


@dataclasses.dataclass(frozen=True)
class RuleFinding:
    """A remaining rule issue after formatting has run.

    Attributes:
        rule (RuleMetadata): Rule metadata for the finding.
        line_numbers (tuple[int, ...]): One-based source line numbers associated with the finding.
        instance_message (str | None): Optional message overriding the rule default for this instance.
        instance_fixable (bool | None): Optional fixability overriding the rule default for this instance.
    """

    @dataclasses.dataclass(frozen=True, order=True)
    class Key:
        """Key used to merge findings that differ only by line numbers."""

        rule: RuleMetadata
        message: str
        fixable: bool

    rule: RuleMetadata
    line_numbers: tuple[int, ...]
    instance_message: str | None = None
    instance_fixable: bool | None = None

    @property
    def message(self) -> str:
        """Return the message for this finding.

        Returns:
            str: Instance-specific message when present, otherwise the rule default message.
        """
        return self.rule.message if self.instance_message is None else self.instance_message

    @property
    def fixable(self) -> bool:
        """Return whether this specific finding can be automatically fixed.

        Returns:
            bool: Instance-specific fixability when present, otherwise the rule default fixability.

        Raises:
            `ValueError`: If the rule is sometimes fixable and no instance-specific fixability is available.
        """
        if self.instance_fixable is not None:
            return self.instance_fixable
        if self.rule.fix_availability == FixAvailability.ALWAYS:
            return True
        elif self.rule.fix_availability == FixAvailability.NEVER:
            return False
        elif self.rule.fix_availability == FixAvailability.SOMETIMES:
            raise ValueError(f"{self.rule.code}: Findings for sometimes-fixable rules must specify instance_fixable")
        else:
            raise AssertionError(f"Unexpected fix availability: {self.rule.fix_availability}")

    @property
    def grouping_key(self) -> RuleFinding.Key:
        """Return the key used to merge findings that differ only by line numbers.

        Returns:
            RuleFinding.Key: Tuple of rule, resolved message, and resolved fixability.
        """
        return RuleFinding.Key(rule=self.rule, message=self.message, fixable=self.fixable)

    def with_line_numbers(self, line_numbers: tuple[int, ...]) -> RuleFinding:
        """Return this finding with updated line numbers.

        Args:
            line_numbers (tuple[int, ...]): Replacement one-based line numbers.

        Returns:
            RuleFinding: Copy of this finding with updated line numbers.
        """
        return dataclasses.replace(self, line_numbers=line_numbers)


@dataclasses.dataclass(frozen=True)
class FormatterResult:
    """Formatter result for one display path.

    Attributes:
        path (str): Display path used for diagnostics and diff headers.
        old_source (str | None): Source text before formatting, or None if source text could not be read or decoded.
        new_source (str | None): Source text after formatting, or None if no valid source state is available.
        modified (bool): Whether formatting changed the source and the result represents a successful source state.
        fixed_findings (collections.Counter[RuleMetadata]): Counts of fixed findings keyed by rule metadata.
        unfixed_findings (tuple[RuleFinding, ...]): Remaining rule findings after formatting, with line numbers aligned
            to new_source.
        errors (tuple[str, ...]): Operational errors that prevented normal formatting or writing.
    """

    path: str
    old_source: str | None
    new_source: str | None
    modified: bool
    fixed_findings: collections.Counter[RuleMetadata]
    unfixed_findings: tuple[RuleFinding, ...]
    errors: tuple[str, ...]


def format_file_exp(path: str, *, file: typing.TextIO | None = None, settings: CheckSettings, fix: bool, write: bool) -> FormatterResult:
    """Run the experimental formatter interface for one file.

    Args:
        path (str): Display path and filesystem path for the source file.
        file (typing.TextIO | None): Optional already-open text stream to read instead of opening `path`.
        settings (CheckSettings): Resolved formatter settings.
        fix (bool): Whether fixes should be applied to the returned source.
        write (bool): Whether modified source should be written back to disk when reading from `path`.

    Returns:
        FormatterResult: Formatting result with source text, findings, and operational errors.
    """
    try:
        if file is None:
            with open(path, encoding="utf-8", newline="") as path_file:
                source = path_file.read()
        else:
            source = file.read()
    except UnicodeDecodeError as error:
        return FormatterResult(
            path=path, old_source=None, new_source=None, modified=False, fixed_findings=collections.Counter(), unfixed_findings=(), errors=(f"Failed to decode {path} as UTF-8: {error}",)
        )
    except OSError as error:
        return FormatterResult(path=path, old_source=None, new_source=None, modified=False, fixed_findings=collections.Counter(), unfixed_findings=(), errors=(f"Failed to read file {path}: {error}",))

    result = format_source_exp(source, path, settings=settings, fix=fix)
    if result.old_source is None or result.new_source is None:
        raise AssertionError("format_source_exp() must return a valid source state")

    if file is None and fix and write and result.modified:
        try:
            with open(path, "w", encoding="utf-8", newline="") as path_file:
                path_file.write(result.new_source)
        except OSError as error:
            return FormatterResult(
                path=path,
                old_source=result.old_source,
                new_source=result.old_source,
                modified=False,
                fixed_findings=collections.Counter(),
                unfixed_findings=(),
                errors=(f"Failed to write file {path}: {error}",),
            )

    return result


def format_source_exp(source: str, path: str, *, settings: CheckSettings, fix: bool) -> FormatterResult:
    """Run the experimental formatter interface for source text.

    Args:
        source (str): Python source text to format.
        path (str): Display path used for diagnostics.
        settings (CheckSettings): Resolved formatter settings.
        fix (bool): Whether fixes should be applied to the returned source.

    Returns:
        FormatterResult: Formatting result for the supplied source text.
    """
    del settings, fix
    # TODO: Temporary placeholder code that must produce a non-None new_source (can just be source if nothing was or
    #       should be fixed, otherwise it should represent the new formatted source)
    new_source = source
    return FormatterResult(path=path, old_source=source, new_source=new_source, modified=(new_source != source), fixed_findings=collections.Counter(), unfixed_findings=(), errors=())


def resolve_line_ending(source: str, *, line_ending: LineEnding) -> str:
    """Return the concrete line ending to use for rewritten source.

    Args:
        source (str): Source text used when auto-detecting line endings.
        line_ending (LineEnding): Configured line ending mode.

    Returns:
        str: Concrete line ending string.

    Raises:
        `ValueError`: If `line_ending` is not a known `LineEnding` member.
    """
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
    """Return the first line ending in source, defaulting to LF when absent.

    Args:
        source (str): Source text to inspect.

    Returns:
        str: First detected line ending, or LF when the source contains no line endings.
    """
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
    """Convert every line ending in text to line_ending.

    Args:
        text (str): Text whose line endings should be normalized.
        line_ending (str): Replacement line ending.

    Returns:
        str: Text with all CRLF, CR, and LF endings converted to `line_ending`.
    """
    return text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", line_ending)
