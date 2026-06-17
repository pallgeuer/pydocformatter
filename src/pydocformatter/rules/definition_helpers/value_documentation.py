from __future__ import annotations

import dataclasses

import libcst as cst

import pydocformatter.rules.definition_helpers.missing_documentation as missing_documentation
import pydocformatter.rules.definition_helpers.summary_style as summary_style
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
from pydocformatter.rules.definition import RuleContext
from pydocformatter.rules.models import RuleFinding, RuleMetadata


@dataclasses.dataclass(frozen=True)
class StatementTarget:
    """One detected function-body statement relevant to documentation rules."""

    line_numbers: tuple[int, ...]


@dataclasses.dataclass(frozen=True)
class RaisedException:
    """One directly raised exception relevant to documentation rules."""

    name: str
    line_numbers: tuple[int, ...]


@dataclasses.dataclass(frozen=True)
class DocumentedEntry:
    """One parsed docstring entry relevant to documentation rules."""

    name: str | None
    line_numbers: tuple[int, ...]
    has_content: bool


@dataclasses.dataclass(frozen=True)
class FunctionFacts:
    """Return, yield, and raise facts collected for one function."""

    meaningful_returns: tuple[StatementTarget, ...]
    explicit_none_returns: tuple[StatementTarget, ...]
    any_yields: tuple[StatementTarget, ...]
    meaningful_yields: tuple[StatementTarget, ...]
    explicit_none_yields: tuple[StatementTarget, ...]
    raised_exceptions: tuple[RaisedException, ...]


_ABSTRACT_DECORATOR_NAMES = {"abstractmethod", "abstractclassmethod", "abstractstaticmethod", "abstractproperty"}


def missing_return_findings(context: RuleContext, *, rule: RuleMetadata) -> tuple[RuleFinding, ...]:
    """Return PDF502 findings for undocumented meaningful return values."""
    findings: list[RuleFinding] = []
    for definition, docstring, facts in _documented_function_facts(context):
        return_targets = _value_documentation_targets(docstring, PDF_definition.DocstringEntryKind.RETURN)
        if (
            not facts.meaningful_returns
            or facts.any_yields
            or any(target.has_content for target in return_targets)
            or not missing_documentation.should_check_missing_documentation(definition, docstring, context=context, has_relevant_documentation=bool(return_targets))
        ):
            continue
        findings.append(RuleFinding(rule=rule, line_numbers=facts.meaningful_returns[0].line_numbers))
    return tuple(findings)


def extraneous_return_findings(context: RuleContext, *, rule: RuleMetadata) -> tuple[RuleFinding, ...]:
    """Return PDF503 findings for return docs on functions without meaningful returns."""
    findings: list[RuleFinding] = []
    for definition, docstring, facts in _documented_function_facts(context):
        del definition
        if facts.meaningful_returns and not facts.any_yields:
            continue
        for entry in _value_documentation_targets(docstring, PDF_definition.DocstringEntryKind.RETURN):
            if facts.explicit_none_returns and not facts.any_yields and entry.has_content:
                continue
            message = "Docstring has a return section for a generator; generator return values are stop values, not ordinary returns" if facts.any_yields else None
            findings.append(RuleFinding(rule=rule, line_numbers=entry.line_numbers, instance_message=message))
    return tuple(findings)


def missing_yield_findings(context: RuleContext, *, rule: RuleMetadata) -> tuple[RuleFinding, ...]:
    """Return PDF504 findings for undocumented meaningful yielded values."""
    findings: list[RuleFinding] = []
    for definition, docstring, facts in _documented_function_facts(context):
        yield_targets = _value_documentation_targets(docstring, PDF_definition.DocstringEntryKind.YIELD)
        if (
            not facts.meaningful_yields
            or any(target.has_content for target in yield_targets)
            or not missing_documentation.should_check_missing_documentation(definition, docstring, context=context, has_relevant_documentation=bool(yield_targets))
        ):
            continue
        findings.append(RuleFinding(rule=rule, line_numbers=facts.meaningful_yields[0].line_numbers))
    return tuple(findings)


def extraneous_yield_findings(context: RuleContext, *, rule: RuleMetadata) -> tuple[RuleFinding, ...]:
    """Return PDF505 findings for yield docs on functions without meaningful yields."""
    findings: list[RuleFinding] = []
    for definition, docstring, facts in _documented_function_facts(context):
        del definition
        if facts.meaningful_yields:
            continue
        for entry in _value_documentation_targets(docstring, PDF_definition.DocstringEntryKind.YIELD):
            if facts.explicit_none_yields and entry.has_content:
                continue
            findings.append(RuleFinding(rule=rule, line_numbers=entry.line_numbers))
    return tuple(findings)


def missing_exception_findings(context: RuleContext, *, rule: RuleMetadata) -> tuple[RuleFinding, ...]:
    """Return PDF506 findings for directly raised exceptions missing from docs."""
    findings: list[RuleFinding] = []
    for definition, docstring, facts in _documented_function_facts(context):
        documented_names = tuple(entry.name for entry in _documented_entries(docstring, PDF_definition.DocstringEntryKind.EXCEPTION, require_content=False) if entry.name is not None)
        if not missing_documentation.should_check_missing_documentation(definition, docstring, context=context, has_relevant_documentation=_has_exception_documentation(docstring)):
            continue
        seen: list[str] = []
        for raised in facts.raised_exceptions:
            if any(_exception_names_match(raised.name, seen_name) for seen_name in seen):
                continue
            seen.append(raised.name)
            if not any(_exception_names_match(raised.name, documented_name) for documented_name in documented_names):
                findings.append(RuleFinding(rule=rule, line_numbers=raised.line_numbers, instance_message=f"Raised exception '{raised.name}' is missing docstring documentation"))
    return tuple(findings)


def extraneous_exception_findings(context: RuleContext, *, rule: RuleMetadata) -> tuple[RuleFinding, ...]:
    """Return PDF507 findings for exception docs absent from direct raises."""
    findings: list[RuleFinding] = []
    for definition, docstring, facts in _documented_function_facts(context):
        del definition
        for entry in _documented_entries(docstring, PDF_definition.DocstringEntryKind.EXCEPTION, require_content=False):
            if entry.name is not None and not any(_exception_names_match(raised.name, entry.name) for raised in facts.raised_exceptions):
                findings.append(RuleFinding(rule=rule, line_numbers=entry.line_numbers, instance_message=f"Docstring documents exception '{entry.name}' that is not explicitly raised"))
    return tuple(findings)


def _documented_function_facts(context: RuleContext) -> tuple[tuple[PDF_definition.DefinitionInfo, PDF_definition.DocstringInfo, FunctionFacts], ...]:
    data = PDF_definition.PDF.require_data(context)
    facts: list[tuple[PDF_definition.DefinitionInfo, PDF_definition.DocstringInfo, FunctionFacts]] = []
    for definition in data.definitions:
        if definition.kind is not PDF_definition.DefinitionKind.FUNCTION:
            continue
        docstring = data.docstring_for(definition)
        if docstring is None or _is_abstract(definition) or _is_stub_function(definition, docstring):
            continue
        facts.append((definition, docstring, _function_facts(definition, context=context)))
    return tuple(facts)


def _documented_entries(docstring: PDF_definition.DocstringInfo, kind: PDF_definition.DocstringEntryKind, *, require_content: bool) -> tuple[DocumentedEntry, ...]:
    entries: list[DocumentedEntry] = []
    skipped_exception_entries = _non_exception_documentation_entries(docstring) if kind is PDF_definition.DocstringEntryKind.EXCEPTION else set()
    for entry in docstring.structure.entries:
        if entry.kind is not kind or entry in skipped_exception_entries or (require_content and not _entry_has_content(entry)):
            continue
        line = docstring.structure.lines[entry.start_line]
        names = entry.names or (None,)
        for name in names:
            entries.append(
                DocumentedEntry(
                    name=name,
                    line_numbers=PDF_definition.docstring_line_numbers(docstring, line),
                    has_content=_entry_has_content(entry),
                )
            )
    return tuple(entries)


def _non_exception_documentation_entries(docstring: PDF_definition.DocstringInfo) -> set[PDF_definition.DocstringEntry]:
    return {entry for section in docstring.structure.sections if section.name.lower() != "raises" for entry in section.entries}


def _has_exception_documentation(docstring: PDF_definition.DocstringInfo) -> bool:
    return any(section.name.lower() == "raises" for section in docstring.structure.sections) or bool(_documented_entries(docstring, PDF_definition.DocstringEntryKind.EXCEPTION, require_content=False))


def _value_documentation_targets(docstring: PDF_definition.DocstringInfo, kind: PDF_definition.DocstringEntryKind) -> tuple[DocumentedEntry, ...]:
    entries: list[DocumentedEntry] = []
    for section in docstring.structure.sections:
        if _section_entry_kind(section) is not kind:
            continue
        section_has_content = _section_has_content(docstring, section)
        line = docstring.structure.lines[section.header_line]
        entries.append(DocumentedEntry(name=None, line_numbers=PDF_definition.docstring_line_numbers(docstring, line), has_content=section_has_content))
    section_entries = {entry for section in docstring.structure.sections for entry in section.entries}
    for entry in docstring.structure.entries:
        if entry in section_entries or entry.kind is not kind:
            continue
        entry_has_content = _entry_has_content(entry)
        line = docstring.structure.lines[entry.start_line]
        entries.append(DocumentedEntry(name=None, line_numbers=PDF_definition.docstring_line_numbers(docstring, line), has_content=entry_has_content))
    return tuple(entries)


def _section_entry_kind(section: PDF_definition.DocstringSection) -> PDF_definition.DocstringEntryKind | None:
    normalized = section.name.lower()
    if normalized in {"return", "returns"}:
        return PDF_definition.DocstringEntryKind.RETURN
    if normalized in {"yield", "yields"}:
        return PDF_definition.DocstringEntryKind.YIELD
    return None


def _section_has_content(docstring: PDF_definition.DocstringInfo, section: PDF_definition.DocstringSection) -> bool:
    return any(docstring.structure.lines[index].text.strip() for index in range(section.content_start_line, section.end_line))


def _entry_has_content(entry: PDF_definition.DocstringEntry) -> bool:
    return bool(entry.names or entry.type_text or entry.description)


def _function_facts(definition: PDF_definition.DefinitionInfo, *, context: RuleContext) -> FunctionFacts:
    visitor = _FunctionBodyVisitor(context)
    definition.body.visit(visitor)
    return FunctionFacts(
        meaningful_returns=tuple(visitor.meaningful_returns),
        explicit_none_returns=tuple(visitor.explicit_none_returns),
        any_yields=tuple(visitor.any_yields),
        meaningful_yields=tuple(visitor.meaningful_yields),
        explicit_none_yields=tuple(visitor.explicit_none_yields),
        raised_exceptions=tuple(visitor.raised_exceptions),
    )


class _FunctionBodyVisitor(cst.CSTVisitor):
    """Collect top-level function behavior while skipping nested scopes."""

    def __init__(self, context: RuleContext) -> None:
        super().__init__()
        self.context = context
        self.meaningful_returns: list[StatementTarget] = []
        self.explicit_none_returns: list[StatementTarget] = []
        self.any_yields: list[StatementTarget] = []
        self.meaningful_yields: list[StatementTarget] = []
        self.explicit_none_yields: list[StatementTarget] = []
        self.raised_exceptions: list[RaisedException] = []

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        """Skip nested function bodies."""
        del node
        return False

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        """Skip nested class bodies."""
        del node
        return False

    def visit_Lambda(self, node: cst.Lambda) -> bool:
        """Skip lambda bodies."""
        del node
        return False

    def visit_Return(self, node: cst.Return) -> None:
        """Record meaningful return statements."""
        if node.value is None:
            return
        target = StatementTarget(line_numbers=_node_line_numbers(node, context=self.context))
        if _is_none_expression(node.value):
            self.explicit_none_returns.append(target)
        else:
            self.meaningful_returns.append(target)

    def visit_Yield(self, node: cst.Yield) -> None:
        """Record yield expressions."""
        target = StatementTarget(line_numbers=_node_line_numbers(node, context=self.context))
        self.any_yields.append(target)
        if node.value is None:
            return
        if isinstance(node.value, cst.From) or not _is_none_expression(node.value):
            self.meaningful_yields.append(target)
        else:
            self.explicit_none_yields.append(target)

    def visit_Raise(self, node: cst.Raise) -> None:
        """Record directly raised exception names."""
        name = _exception_name(node.exc)
        if name is not None:
            self.raised_exceptions.append(RaisedException(name=name, line_numbers=_node_line_numbers(node, context=self.context)))


def _is_abstract(definition: PDF_definition.DefinitionInfo) -> bool:
    return any((name := summary_style.decorator_qualified_name(decorator.decorator)) is not None and name.rpartition(".")[2] in _ABSTRACT_DECORATOR_NAMES for decorator in definition.decorators)


def _is_stub_function(definition: PDF_definition.DefinitionInfo, docstring: PDF_definition.DocstringInfo) -> bool:
    statements = _top_level_body_statements(definition, docstring)
    return len(statements) == 1 and _is_stub_statement(statements[0])


def _top_level_body_statements(definition: PDF_definition.DefinitionInfo, docstring: PDF_definition.DocstringInfo) -> tuple[cst.BaseStatement | cst.BaseSmallStatement, ...]:
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
    if isinstance(statement, cst.SimpleStatementLine):
        return len(statement.body) == 1 and _is_stub_statement(statement.body[0])
    if isinstance(statement, cst.Pass):
        return True
    if isinstance(statement, cst.Expr) and isinstance(statement.value, cst.Ellipsis):
        return True
    exception_name = _exception_name(statement.exc) if isinstance(statement, cst.Raise) else None
    return exception_name is not None and exception_name.rpartition(".")[2] == "NotImplementedError"


def _is_none_expression(expression: cst.BaseExpression) -> bool:
    return isinstance(expression, cst.Name) and expression.value == "None"


def _exception_name(expression: cst.BaseExpression | None) -> str | None:
    if expression is None:
        return None
    if isinstance(expression, cst.Call):
        return _exception_name(expression.func)
    if isinstance(expression, cst.Name):
        return expression.value if _looks_like_exception_name(expression.value) else None
    if isinstance(expression, cst.Attribute):
        parent = _exception_name_parent(expression.value)
        if parent is None:
            return expression.attr.value if _looks_like_exception_name(expression.attr.value) else None
        return f"{parent}.{expression.attr.value}" if _looks_like_exception_name(expression.attr.value) else None
    return None


def _looks_like_exception_name(name: str) -> bool:
    # Static-only heuristic: direct capitalized names are comparable, while dynamic/lowercase aliases are intentionally
    # ignored.
    return bool(name) and name[0].isupper()


def _exception_name_parent(expression: cst.BaseExpression) -> str | None:
    if isinstance(expression, cst.Name):
        return expression.value
    if isinstance(expression, cst.Attribute):
        parent = _exception_name_parent(expression.value)
        if parent is None:
            return None
        return f"{parent}.{expression.attr.value}"
    return None


def _exception_names_match(raised_name: str, documented_name: str) -> bool:
    if "." in raised_name and "." in documented_name:
        return raised_name == documented_name
    return raised_name.rpartition(".")[2] == documented_name.rpartition(".")[2]


def _node_line_numbers(node: cst.CSTNode, *, context: RuleContext) -> tuple[int, ...]:
    position = context.positions.get(node)
    if position is None:
        return (1,)
    return (position.start.line,)
