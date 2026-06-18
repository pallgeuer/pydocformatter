from __future__ import annotations

import dataclasses
import re

import pydocformatter.rules.definitions.PDF.PDF as PDF_definition

SummaryLineTarget = PDF_definition.SummaryLineTarget


@dataclasses.dataclass(frozen=True)
class SummaryWordTarget:
    """The first word in a targeted summary line."""

    summary: SummaryLineTarget
    word: str
    text_start_column: int
    text_end_column: int

    @property
    def line(self) -> PDF_definition.DocstringValueLine:
        """Return the logical line containing the word."""
        return self.summary.line

    @property
    def docstring(self) -> PDF_definition.DocstringInfo:
        """Return the docstring containing the word."""
        return self.summary.docstring


def first_word_target(summary: SummaryLineTarget) -> SummaryWordTarget | None:
    """Return the first whitespace-delimited word in a summary target line."""
    match = re.search(r"\S+", summary.line.text)
    if match is None:
        return None
    return SummaryWordTarget(summary=summary, word=match.group(0), text_start_column=match.start(), text_end_column=match.end())


def line_numbers(target: SummaryLineTarget | SummaryWordTarget) -> tuple[int, ...]:
    """Return concrete source lines for a summary style target."""
    return PDF_definition.docstring_line_numbers(target.docstring, target.line)


def normalize_word(word: str) -> str:
    """Return Ruff/pydocstyle-style lowercase alphanumeric word content."""
    return "".join(character for character in word if character.isalnum()).lower()


def is_function_docstring(docstring: PDF_definition.DocstringInfo) -> bool:
    """Return whether a docstring belongs to a function or method."""
    return docstring.owner.kind is PDF_definition.DefinitionKind.FUNCTION
