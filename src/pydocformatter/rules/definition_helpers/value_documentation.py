"""Return, yield, and exception documentation helpers."""

# Future imports
from __future__ import annotations

# Standard library imports
import dataclasses
from typing import TYPE_CHECKING

# Third-party imports
import libcst as cst

# First-party imports
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
import pydocformatter.rules.definition_helpers.decorators as decorator_helpers
from pydocformatter.rules.definition_helpers import docstring_sections, exception_names


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.cli.settings_check import CheckSettings
    from pydocformatter.rules.definition import RuleContext
    from pydocformatter.rules.definitions.PDF.PDF import DocumentedFunctionFact, ExceptionOccurrence, FunctionFacts


@dataclasses.dataclass(frozen=True)
class DocumentedEntry:
    """One parsed docstring entry relevant to documentation rules.

    Attributes:
        name (str | None): Documented return, yield, or exception name, when the convention supplies one.
        line_numbers (tuple[int, ...]): One-based source lines occupied by the documented entry.
        has_content (bool): Whether the entry or section contains a documented name, type, or description payload.
        has_value_entry (bool): Whether the target is a value/description entry rather than a type-only reST field.
    """

    name: str | None
    line_numbers: tuple[int, ...]
    has_content: bool
    has_value_entry: bool


_ABSTRACT_DECORATOR_NAMES = {"abstractmethod", "abstractclassmethod", "abstractstaticmethod", "abstractproperty"}


def documented_function_facts(context: RuleContext) -> tuple[DocumentedFunctionFact, ...]:
    """Return documented non-stub function facts for value documentation rules.

    Args:
        context (RuleContext): Current file context with prepared PDF data and LibCST metadata.

    Returns:
        tuple[DocumentedFunctionFact, ...]: Function definitions with docstrings and collected return, yield, and
            exception facts.
    """
    data = PDF_definition.PDF.require_data(context)
    cached_facts = data._documented_function_facts
    if cached_facts is not None:
        return cached_facts
    facts = _collect_documented_function_facts(data)
    # Keep prepared data frozen externally while memoizing this expensive derived fact tuple.
    object.__setattr__(data, "_documented_function_facts", facts)
    return facts


def effective_exception_occurrences(facts: FunctionFacts, *, settings: CheckSettings) -> tuple[ExceptionOccurrence, ...]:
    """Return possible exception occurrences enabled for documentation checks.

    Args:
        facts (FunctionFacts): Function-body facts containing direct raises and syntactic assertions.
        settings (CheckSettings): Resolved settings controlling whether assertions contribute `AssertionError`.

    Returns:
        tuple[ExceptionOccurrence, ...]: Enabled exception occurrences in source traversal order.
    """
    if settings.docstring_include_assertion_errors:
        return facts.exception_occurrences
    return tuple(occurrence for occurrence in facts.exception_occurrences if occurrence.origin is PDF_definition.ExceptionOccurrenceOrigin.RAISE)


def _collect_documented_function_facts(data: PDF_definition.PDFCategoryData) -> tuple[DocumentedFunctionFact, ...]:
    """Collect documented non-stub function facts for prepared PDF data."""
    facts: list[DocumentedFunctionFact] = []
    for definition in data.definitions:
        if definition.kind is not PDF_definition.DefinitionKind.FUNCTION:
            continue
        docstring = data.docstring_for(definition)
        if docstring is None or _is_abstract(definition) or _is_stub_function(definition, docstring):
            continue
        facts.append((definition, docstring, data.function_facts_by_definition_id[id(definition)]))
    return tuple(facts)


def documented_entries(docstring: PDF_definition.DocstringInfo, kind: PDF_definition.DocstringEntryKind, *, require_content: bool) -> tuple[DocumentedEntry, ...]:
    """Return documented docstring entries of one semantic kind.

    Args:
        docstring (PDF_definition.DocstringInfo): Parsed docstring whose entries should be inspected.
        kind (PDF_definition.DocstringEntryKind): Semantic entry kind to collect.
        require_content (bool): Whether empty entries should be ignored.

    Returns:
        tuple[DocumentedEntry, ...]: Matching entries with names, line targets, and content flags.
    """
    entries: list[DocumentedEntry] = []
    for entry in docstring.structure.entries:
        if entry.kind is not kind or (require_content and not _entry_has_content(entry)):
            continue
        line = docstring.structure.lines[entry.start_line]
        names = entry.names or (None,)
        entries.extend(
            DocumentedEntry(
                name=name,
                line_numbers=PDF_definition.docstring_line_numbers(docstring, line),
                has_content=_entry_has_content(entry),
                has_value_entry=not docstring_sections.is_rest_type_field(entry.field_name),
            )
            for name in names
        )
    return tuple(entries)


def has_exception_documentation(docstring: PDF_definition.DocstringInfo) -> bool:
    """Return whether a docstring contains exception documentation structures.

    Args:
        docstring (PDF_definition.DocstringInfo): Parsed docstring to inspect for exception sections or fields.

    Returns:
        bool: Whether the docstring has recognized exception documentation.
    """
    return any(section.name.lower() in {"raise", "raises"} for section in docstring.structure.sections) or bool(
        documented_entries(docstring, PDF_definition.DocstringEntryKind.EXCEPTION, require_content=False)
    )


def value_documentation_targets(docstring: PDF_definition.DocstringInfo, kind: PDF_definition.DocstringEntryKind) -> tuple[DocumentedEntry, ...]:
    """Return section and entry targets for return or yield documentation.

    Args:
        docstring (PDF_definition.DocstringInfo): Parsed docstring to inspect for return or yield structures.
        kind (PDF_definition.DocstringEntryKind): Value-documentation kind to collect.

    Returns:
        tuple[DocumentedEntry, ...]: Section headers and standalone fields that document the requested value kind.
    """
    entries: list[DocumentedEntry] = []
    for section in docstring.structure.sections:
        if _section_entry_kind(section) is not kind:
            continue
        section_has_content = _section_has_content(docstring, section)
        line = docstring.structure.lines[section.header_line]
        entries.append(DocumentedEntry(name=None, line_numbers=PDF_definition.docstring_line_numbers(docstring, line), has_content=section_has_content, has_value_entry=True))
    section_entries = {entry for section in docstring.structure.sections for entry in section.entries}
    for entry in docstring.structure.entries:
        if entry in section_entries or entry.kind is not kind:
            continue
        entry_has_content = _entry_has_content(entry)
        line = docstring.structure.lines[entry.start_line]
        entries.append(
            DocumentedEntry(
                name=None,
                line_numbers=PDF_definition.docstring_line_numbers(docstring, line),
                has_content=entry_has_content,
                has_value_entry=not docstring_sections.is_rest_type_field(entry.field_name),
            )
        )
    return tuple(entries)


def _section_entry_kind(section: PDF_definition.DocstringSection) -> PDF_definition.DocstringEntryKind | None:
    """Return the value-documentation entry kind implied by a section name."""
    normalized = section.name.lower()
    if normalized in {"return", "returns"}:
        return PDF_definition.DocstringEntryKind.RETURN
    if normalized in {"yield", "yields"}:
        return PDF_definition.DocstringEntryKind.YIELD
    return None


def _section_has_content(docstring: PDF_definition.DocstringInfo, section: PDF_definition.DocstringSection) -> bool:
    """Return whether a value documentation section has non-blank content lines."""
    return any(docstring.structure.lines[index].text.strip() for index in range(section.content_start_line, section.end_line))


def _entry_has_content(entry: PDF_definition.DocstringEntry) -> bool:
    """Return whether a parsed entry carries any documented payload."""
    return bool(entry.names or entry.type_info or entry.description)


def _is_abstract(definition: PDF_definition.DefinitionInfo) -> bool:
    """Return whether a function definition is decorated as abstract."""
    return any((name := decorator_helpers.decorator_qualified_name(decorator.decorator)) is not None and name.rpartition(".")[2] in _ABSTRACT_DECORATOR_NAMES for decorator in definition.decorators)


def _is_stub_function(definition: PDF_definition.DefinitionInfo, docstring: PDF_definition.DocstringInfo) -> bool:
    """Return whether the documented function body is a one-statement stub."""
    statements = _top_level_body_statements(definition, docstring)
    return len(statements) == 1 and _is_stub_statement(statements[0])


def _top_level_body_statements(definition: PDF_definition.DefinitionInfo, docstring: PDF_definition.DocstringInfo) -> tuple[cst.BaseStatement | cst.BaseSmallStatement, ...]:
    """Return top-level body statements excluding the owning docstring expression."""
    if isinstance(definition.body, cst.SimpleStatementSuite):
        return tuple(statement for statement in definition.body.body if statement is not docstring.expression)
    statements: list[cst.BaseStatement | cst.BaseSmallStatement] = []
    for statement in definition.body.body:
        if statement is docstring.statement:
            if isinstance(statement, cst.SimpleStatementLine):
                statements.extend(small_statement for small_statement in statement.body if small_statement is not docstring.expression)
            continue
        statements.append(statement)
    return tuple(statements)


def _is_stub_statement(statement: cst.BaseStatement | cst.BaseSmallStatement) -> bool:
    """Return whether a statement is a pass, ellipsis, or NotImplementedError stub."""
    if isinstance(statement, cst.SimpleStatementLine):
        return len(statement.body) == 1 and _is_stub_statement(statement.body[0])
    if isinstance(statement, cst.Pass):
        return True
    if isinstance(statement, cst.Expr) and isinstance(statement.value, cst.Ellipsis):
        return True
    exception_name = exception_names.exception_name(statement.exc) if isinstance(statement, cst.Raise) else None
    return exception_name is not None and exception_name.rpartition(".")[2] == "NotImplementedError"


def exception_names_match(raised_name: str, documented_name: str) -> bool:
    """Return whether a raised exception name matches a documented exception name.

    Args:
        raised_name (str): Exception name detected in a `raise` statement.
        documented_name (str): Exception name parsed from docstring documentation.

    Returns:
        bool: Whether fully qualified names match exactly or unqualified final name components match.
    """
    if "." in raised_name and "." in documented_name:
        return raised_name == documented_name
    return raised_name.rpartition(".")[2] == documented_name.rpartition(".")[2]
