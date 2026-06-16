from __future__ import annotations

import dataclasses
import re

import libcst as cst

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


_PROPERTY_DECORATORS = {
    "property",
    "builtins.property",
    "enum.property",
    "functools.cached_property",
    "abc.abstractproperty",
    "types.DynamicClassAttribute",
}
_PROPERTY_ACCESSOR_DECORATOR_NAMES = {"getter", "setter", "deleter"}


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


def is_test_function(docstring: PDF_definition.DocstringInfo) -> bool:
    """Return whether a function docstring belongs to a test-style function."""
    name = docstring.owner.name
    return name == "runTest" or name.startswith("test")


def is_property_function(docstring: PDF_definition.DocstringInfo) -> bool:
    """Return whether a function docstring belongs to a property-like function."""
    return any((decorator_name := decorator_qualified_name(decorator.decorator)) is not None and _is_property_decorator_name(decorator_name) for decorator in docstring.owner.decorators)


def _is_property_decorator_name(decorator_name: str) -> bool:
    """Return whether a decorator name identifies a property-like decorator."""
    parent, _, accessor = decorator_name.rpartition(".")
    return decorator_name in _PROPERTY_DECORATORS or (bool(parent) and accessor in _PROPERTY_ACCESSOR_DECORATOR_NAMES)


def decorator_qualified_name(expression: cst.BaseExpression) -> str | None:
    """Return a dotted decorator name, unwrapping decorator calls."""
    if isinstance(expression, cst.Call):
        return decorator_qualified_name(expression.func)
    if isinstance(expression, cst.Name):
        return expression.value
    if isinstance(expression, cst.Attribute):
        parent = decorator_qualified_name(expression.value)
        if parent is None:
            return None
        return f"{parent}.{expression.attr.value}"
    return None
