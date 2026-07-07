"""Top-level module binding collection helpers.

Attributes:
    BindingKey (TypeAlias): Sortable one-based line and zero-based column key for source-position comparisons.
    TypeAliasMap (TypeAlias): Unshadowed source names mapped to absolute import-qualified names for type comparison.
"""

from __future__ import annotations

import bisect
import dataclasses
import enum
from collections.abc import Mapping

import libcst as cst
import libcst.metadata as cst_metadata

BindingKey = tuple[int, int]
TypeAliasMap = dict[str, str]


class BindingKind(enum.Enum):
    """Kinds of top-level bindings relevant to static matching.

    Attributes:
        QUALIFIED: Absolute import-qualified binding with a known target.
        UNKNOWN: Import-star, relative import, or other binding whose absolute target is not known cheaply.
        LOCAL: Local source binding that should shadow import-qualified matching.
    """

    QUALIFIED = "qualified"
    UNKNOWN = "unknown"
    LOCAL = "local"


@dataclasses.dataclass(frozen=True)
class BindingEvent:
    """One top-level binding event.

    Attributes:
        key (BindingKey): Source position where the binding is in effect.
        kind (BindingKind): Binding classification for static-name consumers.
        qualified_name (str | None): Absolute import-qualified name for qualified import bindings.
    """

    key: BindingKey
    kind: BindingKind
    qualified_name: str | None = None


@dataclasses.dataclass(frozen=True)
class BindingTimeline:
    """Ordered binding events for one top-level name.

    Attributes:
        keys (tuple[BindingKey, ...]): Sortable source-position keys for the binding events.
        events (tuple[BindingEvent, ...]): Binding events in source order.
    """

    keys: tuple[BindingKey, ...]
    events: tuple[BindingEvent, ...]

    def event_at(self, use_key: BindingKey) -> BindingEvent | None:
        """Return the last event before or at a source position.

        Args:
            use_key (BindingKey): Source position where a name is used.

        Returns:
            BindingEvent | None: Binding event in effect at the use position, or None when no event precedes it.
        """
        index = bisect.bisect_right(self.keys, use_key) - 1
        if index < 0:
            return None
        return self.events[index]


@dataclasses.dataclass(frozen=True)
class ModuleBindings:
    """Top-level bindings available for configured-name decisions.

    Attributes:
        timelines (dict[str, BindingTimeline]): Binding timelines keyed by source root name.
        star_timeline (BindingTimeline | None): Import-star events that make later roots uncertain.
        uncertain_import_roots (frozenset[str]): Import-bound roots found outside simple top-level import statements.
        uncertain_local_roots (frozenset[str]): Locally bound roots found inside compound or nested scopes.
    """

    timelines: dict[str, BindingTimeline]
    star_timeline: BindingTimeline | None
    uncertain_import_roots: frozenset[str]
    uncertain_local_roots: frozenset[str]

    def binding_at(self, root: str, use_key: BindingKey) -> BindingEvent | None:
        """Return the binding event in effect for a root at a source position.

        Args:
            root (str): Source root name to resolve.
            use_key (BindingKey): Source position where the root is used.

        Returns:
            BindingEvent | None: Binding event in effect at the use position, or None when the root is unbound.
        """
        timeline = self.timelines.get(root)
        root_event = timeline.event_at(use_key) if timeline is not None else None
        star_event = self.star_timeline.event_at(use_key) if self.star_timeline is not None else None
        if star_event is not None and (root_event is None or star_event.key > root_event.key):
            return star_event
        return root_event

    def has_uncertain_import_root(self, root: str) -> bool:
        """Return whether a root may be imported outside the top-level binding timeline.

        Args:
            root (str): Source root name to check.

        Returns:
            bool: Whether the root appeared in an import outside a simple top-level import statement.
        """
        return root in self.uncertain_import_roots

    def has_uncertain_local_root(self, root: str) -> bool:
        """Return whether a root may be locally rebound outside the top-level binding timeline.

        Args:
            root (str): Source root name to check.

        Returns:
            bool: Whether the root appeared in a local binding inside a compound or nested scope.
        """
        return root in self.uncertain_local_roots


def expression_name(expression: cst.BaseExpression) -> str | None:
    """Return a dotted static expression name.

    Args:
        expression (cst.BaseExpression): Expression to inspect.

    Returns:
        Dotted name for static name and attribute expressions, or None for dynamic expressions.
    """
    if isinstance(expression, cst.Name):
        return expression.value
    if isinstance(expression, cst.Attribute):
        parent = expression_name(expression.value)
        if parent is None:
            return None
        return f"{parent}.{expression.attr.value}"
    return None


def collect_top_level_bindings(module: cst.Module, *, positions: Mapping[cst.CSTNode, cst_metadata.CodeRange] | None = None) -> ModuleBindings:
    """Return top-level binding timelines for a module.

    Args:
        module (cst.Module): Parsed module whose top-level statements should be scanned.
        positions (Mapping[cst.CSTNode, cst_metadata.CodeRange] | None): Optional LibCST source positions used to make
            binding timelines source-position aware.

    Returns:
        ModuleBindings: Binding timelines and uncertain import roots collected from the module.
    """
    collector = _ModuleBindingCollector(positions)
    for statement in module.body:
        collector.collect_statement(statement)
    return collector.bindings()


def module_type_aliases(module: cst.Module) -> TypeAliasMap:
    """Return conservative absolute import aliases usable for type expression comparison.

    Args:
        module (cst.Module): Parsed source module whose top-level imports should be inspected.

    Returns:
        TypeAliasMap: Mapping from unshadowed source names to absolute qualified import names.
    """
    aliases: TypeAliasMap = {}
    for name, timeline in collect_top_level_bindings(module).timelines.items():
        qualified_name: str | None = None
        shadowed = False
        for event in timeline.events:
            if event.kind is BindingKind.QUALIFIED:
                qualified_name = event.qualified_name
            else:
                shadowed = True
        if qualified_name is not None and not shadowed:
            aliases[name] = qualified_name
    return aliases


class _ModuleBindingCollector:
    """Collect import and local bindings from top-level statements."""

    def __init__(self, positions: Mapping[cst.CSTNode, cst_metadata.CodeRange] | None) -> None:
        """Initialize an empty module binding collection."""
        self.positions = positions
        self.events: dict[str, list[BindingEvent]] = {}
        self.star_events: list[BindingEvent] = []
        self.uncertain_import_roots: set[str] = set()
        self.uncertain_local_roots: set[str] = set()

    def bindings(self) -> ModuleBindings:
        """Return immutable binding timelines for collected events."""
        return ModuleBindings(
            timelines={name: _timeline(events) for name, events in self.events.items()},
            star_timeline=_timeline(self.star_events) if self.star_events else None,
            uncertain_import_roots=frozenset(self.uncertain_import_roots),
            uncertain_local_roots=frozenset(self.uncertain_local_roots),
        )

    def collect_statement(self, statement: cst.BaseStatement) -> None:
        """Collect bindings introduced by one top-level statement."""
        key = self._event_key(statement)
        if isinstance(statement, cst.SimpleStatementLine) and all(isinstance(small_statement, cst.Import | cst.ImportFrom) for small_statement in statement.body):
            for small_statement in statement.body:
                if isinstance(small_statement, cst.Import):
                    self.collect_import(small_statement, key=key)
                elif isinstance(small_statement, cst.ImportFrom):
                    self.collect_import_from(small_statement, key=key)
            return
        for name in top_level_bound_names(statement):
            self._add_event(name, key=key, kind=BindingKind.LOCAL)
        nested_imports = _NestedImportCollector()
        statement.visit(nested_imports)
        self.uncertain_import_roots.update(nested_imports.roots)
        nested_bindings = _NestedLocalBindingCollector()
        statement.visit(nested_bindings)
        self.uncertain_local_roots.update(nested_bindings.roots)

    def collect_import(self, node: cst.Import, *, key: BindingKey) -> None:
        """Collect bindings introduced by one import statement."""
        for alias in node.names:
            imported_name = expression_name(alias.name)
            if imported_name is None:
                continue
            if alias.asname is not None:
                source_name = _asname_value(alias.asname)
                if source_name is not None:
                    self._add_event(source_name, key=key, kind=BindingKind.QUALIFIED, qualified_name=imported_name)
            else:
                source_root = imported_name.split(".", 1)[0]
                self._add_event(source_root, key=key, kind=BindingKind.QUALIFIED, qualified_name=source_root)

    def collect_import_from(self, node: cst.ImportFrom, *, key: BindingKey) -> None:
        """Collect bindings introduced by one from-import statement."""
        if isinstance(node.names, cst.ImportStar):
            self.star_events.append(BindingEvent(key=key, kind=BindingKind.UNKNOWN))
            return
        module_name = expression_name(node.module) if node.module is not None else None
        for alias in node.names:
            imported_name = expression_name(alias.name)
            if imported_name is None:
                continue
            if alias.asname is not None:
                source_name = _asname_value(alias.asname)
                if source_name is None:
                    continue
            else:
                source_name = imported_name.split(".", 1)[0]
            if module_name is None or node.relative:
                self._add_event(source_name, key=key, kind=BindingKind.UNKNOWN)
            else:
                self._add_event(source_name, key=key, kind=BindingKind.QUALIFIED, qualified_name=f"{module_name}.{imported_name}")

    def _add_event(self, name: str, *, key: BindingKey, kind: BindingKind, qualified_name: str | None = None) -> None:
        """Record one binding event for a top-level name."""
        self.events.setdefault(name, []).append(BindingEvent(key=key, kind=kind, qualified_name=qualified_name))

    def _event_key(self, statement: cst.BaseStatement) -> BindingKey:
        """Return the source position where a top-level statement has bound its names."""
        if self.positions is None:
            return (0, 0)
        position = self.positions.get(statement)
        if position is None:
            return (0, 0)
        return position_key(position.end)


class _NestedImportCollector(cst.CSTVisitor):
    """Collect import roots from statements outside simple top-level imports."""

    def __init__(self) -> None:
        """Initialize an empty imported-root collection."""
        super().__init__()
        self.roots: set[str] = set()

    def visit_Import(self, node: cst.Import) -> bool:
        """Collect roots bound by an import statement."""
        for alias in node.names:
            imported_name = expression_name(alias.name)
            if imported_name is None:
                continue
            asname = _asname_value(alias.asname) if alias.asname is not None else None
            self.roots.add(asname or imported_name.split(".", 1)[0])
        return False

    def visit_ImportFrom(self, node: cst.ImportFrom) -> bool:
        """Collect roots bound by a from-import statement."""
        if isinstance(node.names, cst.ImportStar):
            return False
        for alias in node.names:
            imported_name = expression_name(alias.name)
            if imported_name is None:
                continue
            asname = _asname_value(alias.asname) if alias.asname is not None else None
            self.roots.add(asname or imported_name.split(".", 1)[0])
        return False


class _NestedLocalBindingCollector(cst.CSTVisitor):
    """Collect local binding roots from compound or nested scopes."""

    def __init__(self) -> None:
        """Initialize an empty local-root collection."""
        super().__init__()
        self.roots: set[str] = set()

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        """Collect a function definition name and keep scanning its body."""
        self.roots.add(node.name.value)
        return True

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        """Collect a class definition name and keep scanning its body."""
        self.roots.add(node.name.value)
        return True

    def visit_Assign(self, node: cst.Assign) -> None:
        """Collect assignment target names."""
        for target in node.targets:
            self.roots.update(target_bound_names(target.target))

    def visit_AnnAssign(self, node: cst.AnnAssign) -> None:
        """Collect annotated assignment target names."""
        self.roots.update(target_bound_names(node.target))

    def visit_AugAssign(self, node: cst.AugAssign) -> None:
        """Collect augmented assignment target names."""
        self.roots.update(target_bound_names(node.target))

    def visit_For(self, node: cst.For) -> None:
        """Collect loop target names."""
        self.roots.update(target_bound_names(node.target))

    def visit_With(self, node: cst.With) -> None:
        """Collect context-manager alias names."""
        for item in node.items:
            if item.asname is not None:
                self.roots.update(target_bound_names(item.asname.name))

    def visit_ExceptHandler(self, node: cst.ExceptHandler) -> None:
        """Collect exception alias names."""
        if node.name is not None:
            self.roots.update(target_bound_names(node.name.name))


def top_level_bound_names(statement: cst.BaseStatement) -> set[str]:
    """Return names rebound by a top-level non-import statement.

    Args:
        statement (cst.BaseStatement): Top-level statement to inspect for direct binding targets.

    Returns:
        set[str]: Source root names rebound by the statement.
    """
    if isinstance(statement, cst.FunctionDef | cst.ClassDef):
        return {statement.name.value}
    if isinstance(statement, cst.SimpleStatementLine):
        simple_names: set[str] = set()
        for small_statement in statement.body:
            if isinstance(small_statement, cst.Assign):
                for target in small_statement.targets:
                    simple_names.update(target_bound_names(target.target))
            elif isinstance(small_statement, cst.AnnAssign | cst.AugAssign):
                simple_names.update(target_bound_names(small_statement.target))
        return simple_names
    if isinstance(statement, cst.For):
        return target_bound_names(statement.target)
    if isinstance(statement, cst.With):
        with_names: set[str] = set()
        for item in statement.items:
            if item.asname is not None:
                with_names.update(target_bound_names(item.asname.name))
        return with_names
    if isinstance(statement, cst.Try):
        except_names: set[str] = set()
        for handler in statement.handlers:
            if handler.name is not None:
                except_names.update(target_bound_names(handler.name.name))
        return except_names
    return set()


def target_bound_names(target: cst.BaseExpression) -> set[str]:
    """Return names bound by a simple assignment-like target.

    Args:
        target (cst.BaseExpression): Assignment, loop, context-manager, or exception alias target.

    Returns:
        set[str]: Simple source names bound by the target.
    """
    if isinstance(target, cst.Name):
        return {target.value}
    if isinstance(target, cst.Tuple | cst.List):
        names: set[str] = set()
        for element in target.elements:
            names.update(target_bound_names(element.value))
        return names
    return set()


def position_key(position: cst_metadata.CodePosition) -> BindingKey:
    """Return a sortable key for a LibCST source position.

    Args:
        position (cst_metadata.CodePosition): LibCST source position to convert.

    Returns:
        BindingKey: Comparable line and column tuple.
    """
    return (position.line, position.column)


def _timeline(events: list[BindingEvent]) -> BindingTimeline:
    """Return a timeline from collected events."""
    sorted_events = tuple(sorted(events, key=lambda event: event.key))
    return BindingTimeline(keys=tuple(event.key for event in sorted_events), events=sorted_events)


def _asname_value(asname: cst.AsName) -> str | None:
    """Return a simple import alias name."""
    if isinstance(asname.name, cst.Name):
        return asname.name.value
    return None
