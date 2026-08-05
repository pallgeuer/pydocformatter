"""Summary word targeting helpers."""

# Future imports
from __future__ import annotations

# Standard library imports
import re
import dataclasses

# First-party imports
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
from pydocformatter.rules.definition_helpers import docstring_source
from pydocformatter.rules.definitions.PDF.PDF import SummaryLineTarget


@dataclasses.dataclass(frozen=True)
class SummaryWordTarget:
    """The first word in a targeted summary line.

    Attributes:
        summary (SummaryLineTarget): Summary line that contains the target word.
        word (str): First summary word selected for style checks.
        text_start_column (int): Zero-based column where `word` starts in the evaluated docstring line.
        text_end_column (int): Zero-based column just after `word` in the evaluated docstring line.
    """

    summary: SummaryLineTarget
    word: str
    text_start_column: int
    text_end_column: int

    @property
    def line(self) -> PDF_definition.DocstringValueLine:
        """Logical line containing the word.

        Returns:
            PDF_definition.DocstringValueLine: Parsed docstring value line that owns the target word.
        """
        return self.summary.line

    @property
    def docstring(self) -> PDF_definition.DocstringInfo:
        """Docstring containing the word.

        Returns:
            PDF_definition.DocstringInfo: Parsed docstring that owns the target word.
        """
        return self.summary.docstring


def first_word_target(summary: SummaryLineTarget) -> SummaryWordTarget | None:
    """Return the first whitespace-delimited word in a summary target line.

    Args:
        summary (SummaryLineTarget): Summary line selected by PDF category preparation.

    Returns:
        SummaryWordTarget | None: First word and its line-local columns, or None for an empty summary line.
    """
    match = re.search(r"\S+", summary.line.text)
    if match is None:
        return None
    return SummaryWordTarget(summary=summary, word=match.group(0), text_start_column=match.start(), text_end_column=match.end())


def line_numbers(target: SummaryLineTarget | SummaryWordTarget) -> tuple[int, ...]:
    """Return concrete source lines for a summary style target.

    Args:
        target (SummaryLineTarget | SummaryWordTarget): Summary line or summary word target.

    Returns:
        tuple[int, ...]: One-based physical source lines occupied by the target's docstring line.
    """
    return docstring_source.docstring_line_numbers(target.docstring, target.line)


def normalize_word(word: str) -> str:
    """Return Ruff/pydocstyle-style lowercase alphanumeric word content.

    Args:
        word (str): Raw first word extracted from a summary line.

    Returns:
        str: Lowercase alphanumeric-only content used by summary style checks.
    """
    return "".join(character for character in word if character.isalnum()).lower()


def is_function_docstring(docstring: PDF_definition.DocstringInfo) -> bool:
    """Return whether a docstring belongs to a function or method.

    Args:
        docstring (PDF_definition.DocstringInfo): Parsed docstring to classify by owner kind.

    Returns:
        bool: Whether the owner is a function definition.
    """
    return docstring.owner.kind is PDF_definition.DefinitionKind.FUNCTION


def is_test_function(definition: PDF_definition.DefinitionInfo) -> bool:
    """Return whether a function definition has a test-style name.

    Args:
        definition (PDF_definition.DefinitionInfo): Function definition to classify.

    Returns:
        bool: Whether the function name is `runTest` or starts with `test`.
    """
    name = definition.name
    return name == "runTest" or name.startswith("test")
