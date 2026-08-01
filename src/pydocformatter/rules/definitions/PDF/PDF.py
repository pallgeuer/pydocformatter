"""PDF docstring-formatting rule category.

Attributes:
    DocstringOwner (TypeAlias): Union of definition and attribute records that can own an attached or conventional
        docstring.
    DocumentedFunctionFact (TypeAlias): Cached tuple pairing a function definition, its parsed docstring, and its
        return/yield/raise inventory.
"""

# Future imports
from __future__ import annotations

# Standard library imports
import re
import enum
import typing
import dataclasses
from collections.abc import Iterator, Mapping, Sequence
from types import MappingProxyType

# Third-party imports
import libcst as cst
import libcst.metadata as cst_metadata

# First-party imports
import pydocformatter.rules.edits as rule_edits
import pydocformatter.rules.registration as rule_registration
from pydocformatter import docs_urls
from pydocformatter.cli import settings_check
from pydocformatter.rules.definition import RuleCategoryBase
from pydocformatter.rules.definition_helpers import (
    ascii_whitespace,
    colon_boundaries,
    docstring_sections,
    exception_names,
    inline_markup,
    module_bindings,
    source_text,
    string_literals,
    text_layout,
    type_expressions,
    typed_documentation_models,
    unicode_safety,
)
from pydocformatter.rules.models import RuleCategoryMetadata


if typing.TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.definition import RuleCategoryContext, RuleContext


_SIMPLE_STRING_PARTS_UNSET = object()
_FOLLOWING_BLOCK_KIND_UNSET = object()


class DefinitionKind(enum.Enum):
    """Kinds of Python owners that may have docstrings.

    Attributes:
        MODULE: A Python module-level docstring owner.
        CLASS: A class docstring owner.
        FUNCTION: A function, method, or nested function docstring owner.
        ATTRIBUTE: An assignment documented by an adjacent attribute docstring.
    """

    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    ATTRIBUTE = "attribute"


class DocstringKind(enum.Enum):
    """LibCST string-expression shapes accepted as Python docstrings.

    Attributes:
        SIMPLE: A single `cst.SimpleString` docstring literal.
        CONCATENATED: An implicitly concatenated docstring expression.
    """

    SIMPLE = "simple"
    CONCATENATED = "concatenated"


class DocstringBlockKind(enum.Enum):
    """Semantic block kinds recognized inside docstrings.

    Attributes:
        BLANK: A blank logical docstring line.
        SUMMARY: The first prose line or compact summary block.
        PARAGRAPH: A wrap-eligible prose paragraph.
        SECTION: A recognized convention section including its header and body.
        SECTION_HEADER: The heading line or underline that names a section.
        SECTION_ENTRY: One parsed Google or NumPy section entry.
        CONVENTION_ENTRY_ISSUE: One diagnosed convention entry line protected from prose reflow.
        COLON_HEADER: A standalone colon-ended line protected as a structure boundary.
        LIST_ITEM: A Markdown or reStructuredText list item.
        HEADING: A Markdown or reStructuredText heading protected from prose reflow.
        DOCTEST: A doctest prompt block protected from prose reflow.
        CODE_FENCE: A fenced code block protected from prose reflow.
        BLOCK_QUOTE: A Markdown block quote.
        TABLE: A Markdown or reStructuredText table protected from prose reflow.
        DIRECTIVE: A reStructuredText directive and its indented body.
        LITERAL_BLOCK: A reStructuredText literal block.
        REST_FIELD: A parsed reStructuredText field list entry.
        VERBATIM: Any protected block whose source should be preserved as-is.
    """

    BLANK = "blank"
    SUMMARY = "summary"
    PARAGRAPH = "paragraph"
    SECTION = "section"
    SECTION_HEADER = "section-header"
    SECTION_ENTRY = "section-entry"
    CONVENTION_ENTRY_ISSUE = "convention-entry-issue"
    COLON_HEADER = "colon-header"
    LIST_ITEM = "list-item"
    HEADING = "heading"
    DOCTEST = "doctest"
    CODE_FENCE = "code-fence"
    BLOCK_QUOTE = "block-quote"
    TABLE = "table"
    DIRECTIVE = "directive"
    LITERAL_BLOCK = "literal-block"
    REST_FIELD = "rest-field"
    VERBATIM = "verbatim"


class DocstringEntryKind(enum.Enum):
    """Semantic entry kinds exposed to convention-aware rules.

    Attributes:
        PARAMETER: Documentation for one function parameter.
        RETURN: Documentation for a returned value.
        YIELD: Documentation for a yielded value.
        EXCEPTION: Documentation for raised exceptions.
        WARNING: Documentation for emitted warnings.
        ATTRIBUTE: Documentation for an instance or class attribute.
        METHOD: Documentation for a method entry in a class docstring.
        FIELD: A generic or unclassified reStructuredText field.
    """

    PARAMETER = "parameter"
    RETURN = "return"
    YIELD = "yield"
    EXCEPTION = "exception"
    WARNING = "warning"
    ATTRIBUTE = "attribute"
    METHOD = "method"
    FIELD = "field"


def is_exception_name_entry_kind(kind: DocstringEntryKind) -> bool:
    """Return whether an entry kind uses exception-name syntax.

    Args:
        kind (DocstringEntryKind): Semantic entry kind to classify.

    Returns:
        bool: Whether the kind shares exception-name entry semantics.
    """
    return kind is DocstringEntryKind.EXCEPTION or kind is DocstringEntryKind.WARNING


class ConventionEntryIssueKind(enum.Enum):
    """Kinds of high-confidence malformed convention entries.

    Attributes:
        GOOGLE_UNBALANCED_TYPE: Google entry with an unbalanced parenthesized type.
        GOOGLE_UNBALANCED_METHOD_SIGNATURE: Google method entry with an unbalanced signature.
        GOOGLE_MISSING_TYPE: Google entry with empty type parentheses.
        GOOGLE_MISSING_SEPARATOR: Google entry without the colon before its description.
        GOOGLE_ENTRY_INDENTATION: Complete Google entry not indented beyond its section header.
        GOOGLE_CONTINUATION_INDENTATION: Google description line not indented beyond its entry.
        NUMPY_UNBALANCED_METHOD_SIGNATURE: NumPy method entry with an unbalanced signature.
        NUMPY_MISSING_TYPE: NumPy entry with a colon but no following type.
        NUMPY_MISSING_SEPARATOR: NumPy entry without the colon before its type.
        NUMPY_CONTINUATION_INDENTATION: NumPy description line not indented beyond its entry.
        REST_MISSING_CLOSING_DELIMITER: Recognized reStructuredText field without its closing colon.
        REST_MISSING_ARGUMENT: Recognized named reStructuredText field without an entry name.
        REST_UNEXPECTED_ARGUMENT: Owner-wide reStructuredText field with an entry name.
    """

    GOOGLE_UNBALANCED_TYPE = "google-unbalanced-type"
    GOOGLE_UNBALANCED_METHOD_SIGNATURE = "google-unbalanced-method-signature"
    GOOGLE_MISSING_TYPE = "google-missing-type"
    GOOGLE_MISSING_SEPARATOR = "google-missing-separator"
    GOOGLE_ENTRY_INDENTATION = "google-entry-indentation"
    GOOGLE_CONTINUATION_INDENTATION = "google-continuation-indentation"
    NUMPY_UNBALANCED_METHOD_SIGNATURE = "numpy-unbalanced-method-signature"
    NUMPY_MISSING_TYPE = "numpy-missing-type"
    NUMPY_MISSING_SEPARATOR = "numpy-missing-separator"
    NUMPY_CONTINUATION_INDENTATION = "numpy-continuation-indentation"
    REST_MISSING_CLOSING_DELIMITER = "rest-missing-closing-delimiter"
    REST_MISSING_ARGUMENT = "rest-missing-argument"
    REST_UNEXPECTED_ARGUMENT = "rest-unexpected-argument"


@dataclasses.dataclass(frozen=True)
class ConventionEntryReplacement:
    """One exact evaluated-line replacement for a convention entry issue.

    Attributes:
        start_column (int): Zero-based replacement start column in the parsed line text.
        end_column (int): Zero-based exclusive replacement end column in the parsed line text.
        text (str): Replacement evaluated text.
    """

    start_column: int
    end_column: int
    text: str


@dataclasses.dataclass(frozen=True)
class ConventionEntryIssue:
    """One high-confidence convention entry syntax or indentation issue.

    Attributes:
        kind (ConventionEntryIssueKind): Stable issue classification used by diagnostic rules.
        start_line (int): Logical docstring line containing the issue.
        names (tuple[str, ...]): Confidently recovered entry names in source order.
        field_name (str | None): Normalized reStructuredText field name, without colons.
        replacement (ConventionEntryReplacement | None): Exact repair when the parser can prove one.
    """

    kind: ConventionEntryIssueKind
    start_line: int
    names: tuple[str, ...] = ()
    field_name: str | None = None
    replacement: ConventionEntryReplacement | None = None


_CONVENTION_ENTRY_ISSUE_PRECEDENCE: Mapping[ConventionEntryIssueKind, int] = MappingProxyType({
    ConventionEntryIssueKind.GOOGLE_UNBALANCED_TYPE: 1,
    ConventionEntryIssueKind.GOOGLE_UNBALANCED_METHOD_SIGNATURE: 1,
    ConventionEntryIssueKind.GOOGLE_MISSING_TYPE: 1,
    ConventionEntryIssueKind.GOOGLE_MISSING_SEPARATOR: 2,
    ConventionEntryIssueKind.GOOGLE_ENTRY_INDENTATION: 3,
    ConventionEntryIssueKind.GOOGLE_CONTINUATION_INDENTATION: 4,
    ConventionEntryIssueKind.NUMPY_UNBALANCED_METHOD_SIGNATURE: 1,
    ConventionEntryIssueKind.NUMPY_MISSING_TYPE: 1,
    ConventionEntryIssueKind.NUMPY_MISSING_SEPARATOR: 2,
    ConventionEntryIssueKind.NUMPY_CONTINUATION_INDENTATION: 3,
    ConventionEntryIssueKind.REST_MISSING_CLOSING_DELIMITER: 1,
    ConventionEntryIssueKind.REST_MISSING_ARGUMENT: 2,
    ConventionEntryIssueKind.REST_UNEXPECTED_ARGUMENT: 3,
})


@dataclasses.dataclass(frozen=True)
class DocstringValueLine:
    """One logical line in an evaluated docstring value.

    Attributes:
        index (int): Zero-based logical line index in the evaluated docstring value.
        start_offset (int): Start offset of the logical line in the evaluated docstring value.
        end_offset (int): End offset of the logical line in the evaluated docstring value.
        raw_text (str): Evaluated line text, including indentation that belongs to the docstring value.
        text (str): Content after removing the docstring margin used for semantic parsing and reflow.
        raw_indent (str): Leading whitespace present in `raw_text`.
        text_indent (str): Leading whitespace present in `text`.
        text_raw_start_column (int): Raw-text column where `text` starts.
        text_virtual_prefix_length (int): Virtual indentation added for parser alignment but absent from raw source.
        source_line_number (int | None): One-based physical source line number, if the value line maps cleanly to
            source.
    """

    index: int
    start_offset: int
    end_offset: int
    raw_text: str
    text: str
    raw_indent: str
    text_indent: str
    text_raw_start_column: int
    text_virtual_prefix_length: int
    source_line_number: int | None


@dataclasses.dataclass(frozen=True)
class DocstringTypeSlot:
    """Source spans for one parsed convention type slot.

    Attributes:
        line_index (int): Logical docstring value line that owns the type slot.
        full_start_column (int): Start column of the complete convention type slot.
        full_end_column (int): Exclusive end column of the complete convention type slot.
        semantic_start_column (int): Start column of the semantic type spelling.
        semantic_end_column (int): Exclusive end column of the semantic type spelling.
    """

    line_index: int
    full_start_column: int
    full_end_column: int
    semantic_start_column: int
    semantic_end_column: int


@dataclasses.dataclass(frozen=True)
class DocstringTypeInfo:
    """Semantic text and optional source span for one parsed convention type.

    Attributes:
        text (str): Semantic type text without outer convention spaces or tabs.
        slot (DocstringTypeSlot | None): Source-mapped convention slot, if one is available.
    """

    text: str
    slot: DocstringTypeSlot | None


@dataclasses.dataclass(frozen=True)
class DocstringTypeEditSlot:
    """Parser-owned source bounds for editing one convention type clause.

    Attributes:
        line_index (int): Logical docstring value line that owns the editable type clause.
        insertion_column (int): Column where a missing type clause can be inserted.
        removal_start_column (int | None): Start column of the complete removable type clause, if present.
        removal_end_column (int | None): Exclusive end column of the complete removable type clause, if present.
    """

    line_index: int
    insertion_column: int
    removal_start_column: int | None
    removal_end_column: int | None


@dataclasses.dataclass(frozen=True)
class DocstringNameSlot:
    """Source span for one parsed convention entry name.

    Attributes:
        line_index (int): Logical docstring value line that owns the name.
        start_column (int): Start column of the parsed name.
        end_column (int): Exclusive end column of the parsed name.
    """

    line_index: int
    start_column: int
    end_column: int


@dataclasses.dataclass(frozen=True)
class DocstringEntry:
    """One parsed convention section entry or reST field.

    Attributes:
        kind (DocstringEntryKind): Semantic documentation role inferred from the section or field name.
        names (tuple[str, ...]): Parameter, exception, warning, attribute, or field argument names documented by this
            entry.
        name_slots (tuple[DocstringNameSlot | None, ...]): Source spans aligned one-for-one with names.
        type_info (DocstringTypeInfo | None): Semantic parsed type and its optional source slot.
        description (str): Entry description text after the entry head.
        description_lines (tuple[DocstringTextFragment, ...]): Source-mapped fragments that make up the parsed entry
            description.
        start_line (int): First logical docstring line occupied by the entry.
        end_line (int): Last logical docstring line occupied by the entry.
        type_edit_slot (DocstringTypeEditSlot | None): Parser-owned insertion and removal bounds for a convention type
            clause, if available.
        following_description_block_kind (DocstringBlockKind | None): Protected structural block immediately after the
            final parsed description fragment but still owned by the entry.
        field_name (str | None): Original reStructuredText field name, without the surrounding colons.
        field_argument (str | None): Original reStructuredText field argument, if the field syntax supplied one.
    """

    kind: DocstringEntryKind
    names: tuple[str, ...]
    name_slots: tuple[DocstringNameSlot | None, ...]
    type_info: DocstringTypeInfo | None
    description: str
    description_lines: tuple[DocstringTextFragment, ...]
    start_line: int
    end_line: int
    type_edit_slot: DocstringTypeEditSlot | None = None
    following_description_block_kind: DocstringBlockKind | None = None
    field_name: str | None = None
    field_argument: str | None = None

    def __post_init__(self) -> None:
        """Validate that semantic names and source slots stay aligned."""
        if len(self.name_slots) != len(self.names):
            raise ValueError("Docstring entry name slots must align with names")


@dataclasses.dataclass(frozen=True)
class DocstringTextFragment:
    """One source-mapped fragment of logical docstring text.

    Attributes:
        text (str): Fragment text after semantic indentation trimming.
        line_index (int): Logical docstring value line that owns the fragment.
        full_start_offset (int): Start offset of the pre-trim fragment span in the evaluated docstring value.
        full_end_offset (int): End offset of the pre-trim fragment span in the evaluated docstring value.
        start_offset (int): Start offset of the fragment in the evaluated docstring value.
        end_offset (int): End offset of the fragment in the evaluated docstring value.
    """

    text: str
    line_index: int
    full_start_offset: int
    full_end_offset: int
    start_offset: int
    end_offset: int


@dataclasses.dataclass(frozen=True)
class ReflowRegionRun:
    """One contiguous source run of reflowable lines.

    Attributes:
        start_line (int): First logical docstring line in the contiguous run.
        end_line (int): Last logical docstring line in the contiguous run.
        lines (tuple[DocstringTextFragment, ...]): Reflowable fragments from the run in source order.
    """

    start_line: int
    end_line: int
    lines: tuple[DocstringTextFragment, ...]


@dataclasses.dataclass(frozen=True)
class ReflowRegion:
    """A contiguous semantic region whose lines may be merged before wrapping.

    Attributes:
        kind (DocstringBlockKind): Semantic block kind that controls wrapping policy.
        start_line (int): First logical docstring line covered by the region.
        end_line (int): Last logical docstring line covered by the region.
        start_offset (int): Start offset of the region in the evaluated docstring value.
        end_offset (int): End offset of the region in the evaluated docstring value.
        lines (tuple[DocstringTextFragment, ...]): Reflowable fragments grouped under this region.
        initial_indent (str): Indentation to use for the first rendered output line.
        subsequent_indent (str): Indentation to use for continuation output lines.
    """

    kind: DocstringBlockKind
    start_line: int
    end_line: int
    start_offset: int
    end_offset: int
    lines: tuple[DocstringTextFragment, ...]
    initial_indent: str
    subsequent_indent: str


@dataclasses.dataclass(frozen=True)
class DocstringBlock:
    """One nested semantic block in a docstring.

    Attributes:
        kind (DocstringBlockKind): Semantic role of this parsed block.
        start_line (int): First logical docstring line included in the block.
        end_line (int): Last logical docstring line included in the block.
        children (tuple[DocstringBlock, ...]): Nested blocks parsed inside this block.
        entry (DocstringEntry | None): Parsed convention entry represented by this block, when applicable.
    """

    kind: DocstringBlockKind
    start_line: int
    end_line: int
    children: tuple[DocstringBlock, ...] = ()
    entry: DocstringEntry | None = None


@dataclasses.dataclass(frozen=True)
class DocstringSection:
    """One convention-specific docstring section.

    Attributes:
        name (str): Section heading text as it appears in the docstring.
        start_line (int): First logical docstring line included in the section.
        end_line (int): Last logical docstring line included in the section.
        header_line (int): Logical line containing the section heading.
        content_start_line (int): First logical line after the heading and any underline.
        entries (tuple[DocstringEntry, ...]): Parsed entries contained directly in the section.
    """

    name: str
    start_line: int
    end_line: int
    header_line: int
    content_start_line: int
    entries: tuple[DocstringEntry, ...]


@dataclasses.dataclass(frozen=True)
class FinalConventionSectionSpacing:
    """Spacing facts for the final recognized convention section.

    Attributes:
        section (DocstringBlock): Final convention section block in a docstring.
        final_content_line (int | None): Last nonblank logical line in that section, if one exists.
        trailing_blank_line (int | None): Blank logical line immediately after the section content, if present.
    """

    section: DocstringBlock
    final_content_line: int | None
    trailing_blank_line: int | None


@dataclasses.dataclass(frozen=True)
class DocstringOutputLine:
    """One output logical docstring line for whole-literal rendering.

    Attributes:
        original (DocstringValueLine | None): Existing value line to preserve when no replacement text is supplied.
        source (str | None): Replacement source text for this logical line, when it differs from evaluated text.
        value (str | None): Replacement evaluated value text for this logical line.
        strip_docstring_margin (bool): Whether to render `original` after removing the docstring margin.
    """

    original: DocstringValueLine | None = None
    source: str | None = dataclasses.field(kw_only=True)
    value: str | None = dataclasses.field(kw_only=True)
    strip_docstring_margin: bool = False


class DocstringOutputSeparatorFallback(enum.Enum):
    """Separator fallback direction for whole-literal rendering.

    Attributes:
        OPENING: Prefer inserting separator whitespace after the opening quotes.
        CLOSING: Prefer inserting separator whitespace before the closing quotes.
        BOTH: Allow fallback whitespace on both quote boundaries.
    """

    OPENING = "opening"
    CLOSING = "closing"
    BOTH = "both"


@dataclasses.dataclass(frozen=True)
class DocstringStructure:
    """Convention-aware semantic structure prepared for one docstring.

    Attributes:
        convention (settings_check.DocstringConvention): Convention used to parse sections and entries.
        lines (tuple[DocstringValueLine, ...]): Logical evaluated-value lines in source order.
        blocks (tuple[DocstringBlock, ...]): Top-level semantic blocks parsed from the docstring.
        sections (tuple[DocstringSection, ...]): Recognized convention sections in source order.
        entries (tuple[DocstringEntry, ...]): Parsed documentation entries from sections and fields.
        convention_entry_issues (tuple[ConventionEntryIssue, ...]): High-confidence malformed convention entries that
            remain outside semantic entry collections.
        reflow_regions (tuple[ReflowRegion, ...]): Text regions that rules may safely reflow.
    """

    convention: settings_check.DocstringConvention
    lines: tuple[DocstringValueLine, ...]
    blocks: tuple[DocstringBlock, ...]
    sections: tuple[DocstringSection, ...]
    entries: tuple[DocstringEntry, ...]
    convention_entry_issues: tuple[ConventionEntryIssue, ...]
    reflow_regions: tuple[ReflowRegion, ...]


@dataclasses.dataclass(frozen=True)
class DefinitionInfo:
    """Convention-neutral information about one documentable definition.

    Attributes:
        node (cst.Module | cst.ClassDef | cst.FunctionDef): LibCST node that owns the docstring slot.
        kind (DefinitionKind): Kind of Python definition represented by the node.
        name (str): Local definition name, or an empty string for the module.
        qualified_name (str): Dotted name relative to the module root.
        parent (DefinitionInfo | None): Containing definition, or None for the module.
        body (cst.Module | cst.BaseSuite): Body searched for the definition's docstring and nested definitions.
        asynchronous (bool): Whether a function definition uses `async def`.
        decorators (tuple[cst.Decorator, ...]): Decorators attached to a function or class definition.
        parameters (cst.Parameters | None): Function parameters for callable definitions.
        returns (cst.Annotation | None): Function return annotation, if one is present.
    """

    node: cst.Module | cst.ClassDef | cst.FunctionDef
    kind: DefinitionKind
    name: str
    qualified_name: str
    parent: DefinitionInfo | None
    body: cst.Module | cst.BaseSuite
    asynchronous: bool
    decorators: tuple[cst.Decorator, ...]
    parameters: cst.Parameters | None
    returns: cst.Annotation | None


@dataclasses.dataclass(frozen=True)
class AttributeInfo:
    """Convention-neutral information about one documented attribute.

    Attributes:
        node (cst.Assign | cst.AnnAssign): Assignment node that declares or defines the attribute.
        kind (DefinitionKind): Always `DefinitionKind.ATTRIBUTE` for attribute inventory and documentation targets.
        name (str): Primary attribute name used for diagnostics and lookup.
        qualified_name (str): Dotted attribute name relative to the module root.
        parent (DefinitionInfo): Definition whose body contains the assignment.
        targets (tuple[str, ...]): All simple assignment target names documented by the same docstring.
        line_numbers (tuple[int, ...]): One-based source lines occupied by supported assignment targets.
        target_line_numbers (tuple[tuple[int, ...], ...]): One-based source lines for each target in `targets`.
        instance (bool): Whether the attribute comes from a `self.*` assignment in an `__init__` body.
    """

    node: cst.Assign | cst.AnnAssign
    kind: DefinitionKind
    name: str
    qualified_name: str
    parent: DefinitionInfo
    targets: tuple[str, ...]
    line_numbers: tuple[int, ...]
    target_line_numbers: tuple[tuple[int, ...], ...]
    instance: bool


DocstringOwner = DefinitionInfo | AttributeInfo


@dataclasses.dataclass(frozen=True)
class DocstringLine:
    """One physical source line occupied by a docstring expression.

    Attributes:
        line_number (int): One-based physical source line number.
        start_column (int): Zero-based source column where the docstring occupies this physical line.
        end_column (int): Zero-based source column immediately after the occupied span.
        source (str): Exact source text occupied by the docstring on this physical line.
    """

    line_number: int
    start_column: int
    end_column: int
    source: str


@dataclasses.dataclass(frozen=True)
class DocstringInfo:
    """Lossless source and owner information for one existing docstring.

    Attributes:
        node (cst.SimpleString | cst.ConcatenatedString): String expression node that forms the docstring.
        expression (cst.Expr): Expression statement wrapping the string expression.
        statement (cst.SimpleStatementLine | cst.SimpleStatementSuite): Full simple statement that contains the
            docstring expression.
        owner (DocstringOwner): Definition or attribute assignment documented by this string.
        kind (DocstringKind): Source string shape used for safe rewrite decisions.
        range (cst_metadata.CodeRange): Source range occupied by the string expression.
        source (str): Exact source text of the string expression.
        value (str): Evaluated Python string value of the docstring.
        physical_lines (tuple[DocstringLine, ...]): Physical source lines occupied by the docstring expression.
        value_lines (tuple[str, ...]): Evaluated docstring value split into logical lines.
        structure (DocstringStructure): Convention-aware parsed structure for the evaluated value.
    """

    node: cst.SimpleString | cst.ConcatenatedString
    expression: cst.Expr
    statement: cst.SimpleStatementLine | cst.SimpleStatementSuite
    owner: DocstringOwner
    kind: DocstringKind
    range: cst_metadata.CodeRange
    source: str
    value: str
    physical_lines: tuple[DocstringLine, ...]
    value_lines: tuple[str, ...]
    structure: DocstringStructure
    _simple_string_parts: tuple[string_literals.SimpleStringPart, ...] | object | None = dataclasses.field(default=_SIMPLE_STRING_PARTS_UNSET, init=False, repr=False, compare=False)
    _unicode_occurrences: tuple[unicode_safety.SuspiciousUnicodeOccurrence, ...] | None = dataclasses.field(default=None, init=False, repr=False, compare=False)

    @property
    def simple_string_parts(self) -> tuple[string_literals.SimpleStringPart, ...] | None:
        """Evaluated simple-string leaves and source maps, lazily cached.

        Returns:
            tuple[string_literals.SimpleStringPart, ...] | None: Ordered evaluated leaves with source maps when the
                expression can be analyzed.
        """
        cached = self._simple_string_parts
        if cached is _SIMPLE_STRING_PARTS_UNSET:
            cached = string_literals.simple_string_parts(self.node, value=self.value)
            object.__setattr__(self, "_simple_string_parts", cached)
        return typing.cast("tuple[string_literals.SimpleStringPart, ...] | None", cached)

    @property
    def source_map(self) -> string_literals.SimpleStringSourceMap | None:
        """Lossless source map for a single simple-string docstring.

        Returns:
            string_literals.SimpleStringSourceMap | None: Body mapping when the source spelling is supported.
        """
        parts = self.simple_string_parts
        return parts[0].source_map if isinstance(self.node, cst.SimpleString) and parts is not None and len(parts) == 1 else None

    @property
    def unicode_occurrences(self) -> tuple[unicode_safety.SuspiciousUnicodeOccurrence, ...]:
        """Suspicious Unicode classifications, lazily cached.

        Returns:
            tuple[unicode_safety.SuspiciousUnicodeOccurrence, ...]: Reportable occurrences in evaluated-value order.
        """
        cached = self._unicode_occurrences
        if cached is None:
            cached = unicode_safety.suspicious_unicode_occurrences(self.value)
            object.__setattr__(self, "_unicode_occurrences", cached)
        return cached

    @property
    def has_unicode_rewrite_barrier(self) -> bool:
        """Whether canonical payload rewriting must preserve the value unchanged.

        Returns:
            bool: Whether any suspicious Unicode occurrence blocks reconstruction.
        """
        return bool(self.unicode_occurrences)


@dataclasses.dataclass(frozen=True)
class SummaryLineTarget:
    """One parsed summary line targeted by first-line style rules.

    Attributes:
        docstring (DocstringInfo): Docstring that owns the target summary line.
        block (DocstringBlock): Summary block containing the target line.
        line (DocstringValueLine): Logical value line inspected or rewritten by summary rules.
    """

    docstring: DocstringInfo
    block: DocstringBlock
    line: DocstringValueLine
    _following_block_kind: DocstringBlockKind | object | None = dataclasses.field(default=_FOLLOWING_BLOCK_KIND_UNSET, init=False, repr=False, compare=False)

    @property
    def following_block_kind(self) -> DocstringBlockKind | None:
        """Cached next nonblank top-level block kind.

        Returns:
            Next nonblank top-level block kind, or None when the summary is final.
        """
        kind = self._following_block_kind
        if kind is _FOLLOWING_BLOCK_KIND_UNSET:
            kind = next((following_kind for block, following_kind in _blocks_with_following_nonblank_kind(self.docstring.structure.blocks, recursive=False) if block is self.block), None)
            object.__setattr__(self, "_following_block_kind", kind)
        return typing.cast("DocstringBlockKind | None", kind)


@dataclasses.dataclass(frozen=True)
class EntryDescriptionLineTarget:
    """One source-mapped documentation entry description fragment.

    Attributes:
        docstring (DocstringInfo): Parsed docstring that owns the entry.
        fragment (DocstringTextFragment): Source-mapped description fragment selected for a style check.
        following_block_kinds (tuple[DocstringBlockKind, ...]): Structural block kinds immediately following the
            description.
    """

    docstring: DocstringInfo
    fragment: DocstringTextFragment
    following_block_kinds: tuple[DocstringBlockKind, ...] = ()

    @property
    def line(self) -> DocstringValueLine:
        """Logical docstring line containing the fragment.

        Returns:
            Logical docstring value line that owns the source-mapped description fragment.
        """
        return self.docstring.structure.lines[self.fragment.line_index]


@dataclasses.dataclass(frozen=True)
class StatementTarget:
    """One detected function-body statement relevant to documentation rules.

    Attributes:
        line_numbers (tuple[int, ...]): One-based source lines associated with the statement.
    """

    line_numbers: tuple[int, ...]


class ExceptionOccurrenceOrigin(enum.Enum):
    """Origins of possible exception occurrences.

    Attributes:
        RAISE: Exception occurrence from an explicit `raise` statement.
        ASSERT: Possible `AssertionError` occurrence from an `assert` statement.
    """

    RAISE = "raise"
    ASSERT = "assert"


@dataclasses.dataclass(frozen=True)
class ExceptionOccurrence:
    """One possible exception occurrence relevant to documentation rules.

    Attributes:
        name (str): Best-effort exception class name used for documentation comparison.
        line_numbers (tuple[int, ...]): One-based source lines associated with the originating statement.
        origin (ExceptionOccurrenceOrigin): Syntax that produced the possible exception occurrence.
    """

    name: str
    line_numbers: tuple[int, ...]
    origin: ExceptionOccurrenceOrigin


@dataclasses.dataclass(frozen=True)
class FunctionFacts:
    """Return, yield, and exception facts collected for one function.

    Attributes:
        meaningful_returns (tuple[StatementTarget, ...]): Return statements that produce a non-None value.
        explicit_none_returns (tuple[StatementTarget, ...]): Return statements whose expression is explicitly `None`.
        any_yields (tuple[StatementTarget, ...]): Yield or yield-from statements regardless of yielded value.
        meaningful_yields (tuple[StatementTarget, ...]): Yield statements that may produce a non-None value.
        explicit_none_yields (tuple[StatementTarget, ...]): Yield statements whose expression is explicitly `None`.
        exception_occurrences (tuple[ExceptionOccurrence, ...]): Directly raised exceptions and syntactic assertions
            detected in the function body.
    """

    meaningful_returns: tuple[StatementTarget, ...]
    explicit_none_returns: tuple[StatementTarget, ...]
    any_yields: tuple[StatementTarget, ...]
    meaningful_yields: tuple[StatementTarget, ...]
    explicit_none_yields: tuple[StatementTarget, ...]
    exception_occurrences: tuple[ExceptionOccurrence, ...]


DocumentedFunctionFact = tuple[DefinitionInfo, DocstringInfo, FunctionFacts]


@dataclasses.dataclass(frozen=True)
class PDFCategoryData:
    """Prepared definitions and docstrings shared by PDF rules.

    Attributes:
        definitions (tuple[DefinitionInfo, ...]): Documentable module, class, and function owners.
        attributes (tuple[AttributeInfo, ...]): Supported module, class, and `__init__` instance attribute assignments.
        docstrings (tuple[DocstringInfo, ...]): Existing docstrings paired with their parsed structure and owner.
        summary_line_targets (tuple[SummaryLineTarget, ...]): First summary lines for all parsed docstring owners; rules
            apply owner-specific policy.
        summary_terminal_line_targets (tuple[SummaryLineTarget, ...]): Summary lines eligible for terminal-punctuation
            checks.
        function_facts_by_definition_id (Mapping[int, FunctionFacts]): Return, yield, and exception facts indexed by
            owning function definition identity.
    """

    definitions: tuple[DefinitionInfo, ...]
    attributes: tuple[AttributeInfo, ...]
    docstrings: tuple[DocstringInfo, ...]
    summary_line_targets: tuple[SummaryLineTarget, ...]
    summary_terminal_line_targets: tuple[SummaryLineTarget, ...]
    function_facts_by_definition_id: Mapping[int, FunctionFacts]
    _docstrings_by_owner_id: dict[int, DocstringInfo] | None = dataclasses.field(default=None, init=False, repr=False, compare=False)
    _attributes_by_owner_id: Mapping[int, tuple[AttributeInfo, ...]] | None = dataclasses.field(default=None, init=False, repr=False, compare=False)
    _attached_attribute_docstrings_by_owner_id: Mapping[int, Mapping[str, tuple[DocstringInfo, ...]]] | None = dataclasses.field(default=None, init=False, repr=False, compare=False)
    _documented_function_facts: tuple[DocumentedFunctionFact, ...] | None = dataclasses.field(default=None, init=False, repr=False, compare=False)
    _typed_documentation_targets: dict[typed_documentation_models.TypedDocumentationSubject, tuple[typed_documentation_models.TypedDocumentationTarget, ...]] | None = dataclasses.field(
        default=None, init=False, repr=False, compare=False
    )
    _module_bindings: module_bindings.ModuleBindings | None = dataclasses.field(default=None, init=False, repr=False, compare=False)
    _type_aliases: type_expressions.TypeAliasMap | None = dataclasses.field(default=None, init=False, repr=False, compare=False)
    _entry_description_first_line_targets: tuple[EntryDescriptionLineTarget, ...] | None = dataclasses.field(default=None, init=False, repr=False, compare=False)
    _entry_description_terminal_line_targets: tuple[EntryDescriptionLineTarget, ...] | None = dataclasses.field(default=None, init=False, repr=False, compare=False)

    def docstring_for(self, definition: DefinitionInfo) -> DocstringInfo | None:
        """Return the docstring owned by a definition, if one exists.

        Args:
            definition (DefinitionInfo): Module, class, or function definition whose direct docstring should be
                retrieved.

        Returns:
            The cached docstring whose owner is the definition, or None when the definition is undocumented.
        """
        docstrings_by_owner_id = self._docstrings_by_owner_id
        if docstrings_by_owner_id is None:
            docstrings_by_owner_id = {}
            for docstring in self.docstrings:
                if isinstance(docstring.owner, DefinitionInfo):
                    docstrings_by_owner_id.setdefault(id(docstring.owner), docstring)
            object.__setattr__(self, "_docstrings_by_owner_id", docstrings_by_owner_id)
        return docstrings_by_owner_id.get(id(definition))

    def attributes_for(self, owner: DefinitionInfo) -> tuple[AttributeInfo, ...]:
        """Return collected attributes for an owner.

        Args:
            owner (DefinitionInfo): Definition whose assigned attributes should be exposed to attribute-documentation
                rules.

        Returns:
            Attribute facts collected directly below the owner, preserving collection order.
        """
        attributes_by_owner_id = self._attributes_by_owner_id
        if attributes_by_owner_id is None:
            mutable_index: dict[int, list[AttributeInfo]] = {}
            for attribute in self.attributes:
                mutable_index.setdefault(id(attribute.parent), []).append(attribute)
            attributes_by_owner_id = MappingProxyType({owner_id: tuple(owner_attributes) for owner_id, owner_attributes in mutable_index.items()})
            object.__setattr__(self, "_attributes_by_owner_id", attributes_by_owner_id)
        return attributes_by_owner_id.get(id(owner), ())

    def attached_attribute_docstrings_by_name(self, owner: DefinitionInfo) -> Mapping[str, tuple[DocstringInfo, ...]]:
        """Return attached attribute docstrings for an owner indexed by target name.

        Args:
            owner (DefinitionInfo): Definition whose attribute-level string literals should be grouped by assigned
                target.

        Returns:
            Read-only mapping from attribute target name to all attached docstrings collected for that name.
        """
        docstrings_by_owner_id = self._attached_attribute_docstrings_by_owner_id
        if docstrings_by_owner_id is None:
            mutable_index: dict[int, dict[str, list[DocstringInfo]]] = {}
            for docstring in self.docstrings:
                docstring_owner = docstring.owner
                if not isinstance(docstring_owner, AttributeInfo):
                    continue
                owner_docstrings = mutable_index.setdefault(id(docstring_owner.parent), {})
                for name in dict.fromkeys(docstring_owner.targets):
                    owner_docstrings.setdefault(name, []).append(docstring)
            docstrings_by_owner_id = MappingProxyType({
                owner_id: MappingProxyType({name: tuple(name_docstrings) for name, name_docstrings in owner_docstrings.items()}) for owner_id, owner_docstrings in mutable_index.items()
            })
            object.__setattr__(self, "_attached_attribute_docstrings_by_owner_id", docstrings_by_owner_id)
        return docstrings_by_owner_id.get(id(owner), MappingProxyType({}))

    def entry_description_first_line_targets(self) -> tuple[EntryDescriptionLineTarget, ...]:
        """Return cached first nonempty entry-description fragments.

        Returns:
            Entry description targets used by first-word style rules.
        """
        targets = self._entry_description_first_line_targets
        if targets is None:
            targets = _entry_description_line_targets(self.docstrings, first=True)
            object.__setattr__(self, "_entry_description_first_line_targets", targets)
        return targets

    def entry_description_terminal_line_targets(self) -> tuple[EntryDescriptionLineTarget, ...]:
        """Return cached final nonempty entry-description fragments.

        Returns:
            Entry description targets used by terminal-punctuation rules.
        """
        targets = self._entry_description_terminal_line_targets
        if targets is None:
            targets = _entry_description_line_targets(self.docstrings, first=False)
            object.__setattr__(self, "_entry_description_terminal_line_targets", targets)
        return targets


@dataclasses.dataclass(frozen=True)
class _AttributeCollection:
    """Attributes and docstring targets collected from adjacent attribute string literals."""

    attributes: tuple[AttributeInfo, ...]
    docstring_targets: tuple[_DocstringTarget, ...]


@dataclasses.dataclass(frozen=True)
class _DocstringTarget:
    """One possible docstring expression awaiting owner-aware parsing."""

    expression: cst.Expr
    statement: cst.SimpleStatementLine | cst.SimpleStatementSuite
    owner: DocstringOwner


@dataclasses.dataclass(frozen=True)
class _MalformedEntryConfidence:
    """Owner names that can make malformed entry syntax high-confidence."""

    parameter_names: frozenset[str] = frozenset()
    attribute_names: frozenset[str] = frozenset()
    method_names: frozenset[str] = frozenset()


@dataclasses.dataclass(frozen=True)
class _AttributeTarget:
    """One supported attribute target extracted from an assignment."""

    name: str
    line_numbers: tuple[int, ...]


@dataclasses.dataclass
class _MutableFunctionFacts:
    """Mutable function-body facts collected during the definition traversal."""

    meaningful_returns: list[StatementTarget] = dataclasses.field(default_factory=list)
    explicit_none_returns: list[StatementTarget] = dataclasses.field(default_factory=list)
    any_yields: list[StatementTarget] = dataclasses.field(default_factory=list)
    meaningful_yields: list[StatementTarget] = dataclasses.field(default_factory=list)
    explicit_none_yields: list[StatementTarget] = dataclasses.field(default_factory=list)
    exception_occurrences: list[ExceptionOccurrence] = dataclasses.field(default_factory=list)

    def frozen(self) -> FunctionFacts:
        """Return immutable function facts for rule consumption."""
        return FunctionFacts(
            meaningful_returns=tuple(self.meaningful_returns),
            explicit_none_returns=tuple(self.explicit_none_returns),
            any_yields=tuple(self.any_yields),
            meaningful_yields=tuple(self.meaningful_yields),
            explicit_none_yields=tuple(self.explicit_none_yields),
            exception_occurrences=tuple(self.exception_occurrences),
        )


class _DefinitionCollector(cst.CSTVisitor):
    """Collect documentable definitions and their existing docstrings."""

    def __init__(self, context: RuleCategoryContext) -> None:
        """Initialize definition and docstring collection for one module."""
        super().__init__()
        self.context = context
        self.source_lines = context.source_lines
        self.definitions: list[DefinitionInfo] = []
        self.docstring_targets: list[_DocstringTarget] = []
        self.function_facts_by_definition_id: dict[int, FunctionFacts] = {}
        self.function_fact_stack: list[_MutableFunctionFacts] = []
        self.lambda_depth = 0
        self.stack: list[DefinitionInfo] = []

        module_definition = DefinitionInfo(
            node=context.module,
            kind=DefinitionKind.MODULE,
            name="<module>",
            qualified_name="<module>",
            parent=None,
            body=context.module,
            asynchronous=False,
            decorators=(),
            parameters=None,
            returns=None,
        )
        self.definitions.append(module_definition)
        self.stack.append(module_definition)
        self._collect_docstring(module_definition)

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        """Collect a class and make it the current definition owner."""
        definition = DefinitionInfo(
            node=node,
            kind=DefinitionKind.CLASS,
            name=node.name.value,
            qualified_name=_qualified_name(self.stack[-1], node.name.value),
            parent=self.stack[-1],
            body=node.body,
            asynchronous=False,
            decorators=tuple(node.decorators),
            parameters=None,
            returns=None,
        )
        self.definitions.append(definition)
        self.stack.append(definition)
        self._collect_docstring(definition)

    def leave_ClassDef(self, original_node: cst.ClassDef) -> None:
        """Restore the enclosing definition after visiting a class."""
        del original_node
        self.stack.pop()

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        """Collect a function and make it the current definition owner."""
        definition = DefinitionInfo(
            node=node,
            kind=DefinitionKind.FUNCTION,
            name=node.name.value,
            qualified_name=_qualified_name(self.stack[-1], node.name.value),
            parent=self.stack[-1],
            body=node.body,
            asynchronous=node.asynchronous is not None,
            decorators=tuple(node.decorators),
            parameters=node.params,
            returns=node.returns,
        )
        self.definitions.append(definition)
        self.stack.append(definition)
        self._collect_docstring(definition)
        self.function_fact_stack.append(_MutableFunctionFacts())

    def leave_FunctionDef(self, original_node: cst.FunctionDef) -> None:
        """Restore the enclosing definition after visiting a function."""
        del original_node
        definition = self.stack.pop()
        self.function_facts_by_definition_id[id(definition)] = self.function_fact_stack.pop().frozen()

    def visit_Lambda(self, node: cst.Lambda) -> None:
        """Track lambda scope while collecting function facts."""
        del node
        self.lambda_depth += 1

    def leave_Lambda(self, original_node: cst.Lambda) -> None:
        """Restore the enclosing scope after visiting a lambda."""
        del original_node
        self.lambda_depth -= 1

    def visit_Return(self, node: cst.Return) -> None:
        """Record a top-level return statement for the current function."""
        facts = self._current_function_facts()
        if facts is None or node.value is None:
            return
        target = StatementTarget(line_numbers=_node_line_numbers(node, context=self.context))
        if _is_none_expression(node.value):
            facts.explicit_none_returns.append(target)
        else:
            facts.meaningful_returns.append(target)

    def visit_Yield(self, node: cst.Yield) -> None:
        """Record a top-level yield expression for the current function."""
        facts = self._current_function_facts()
        if facts is None:
            return
        target = StatementTarget(line_numbers=_node_line_numbers(node, context=self.context))
        facts.any_yields.append(target)
        if node.value is None:
            return
        if isinstance(node.value, cst.From) or not _is_none_expression(node.value):
            facts.meaningful_yields.append(target)
        else:
            facts.explicit_none_yields.append(target)

    def visit_Raise(self, node: cst.Raise) -> None:
        """Record a top-level direct raise statement for the current function."""
        facts = self._current_function_facts()
        if facts is None:
            return
        name = exception_names.exception_name(node.exc)
        if name is not None:
            facts.exception_occurrences.append(ExceptionOccurrence(name=name, line_numbers=_node_line_numbers(node, context=self.context), origin=ExceptionOccurrenceOrigin.RAISE))

    def visit_Assert(self, node: cst.Assert) -> None:
        """Record a top-level syntactic assertion for the current function."""
        facts = self._current_function_facts()
        if facts is not None:
            facts.exception_occurrences.append(ExceptionOccurrence(name="AssertionError", line_numbers=_node_line_numbers(node, context=self.context), origin=ExceptionOccurrenceOrigin.ASSERT))

    def _current_function_facts(self) -> _MutableFunctionFacts | None:
        """Return the current function fact builder, if statement facts should be collected."""
        if self.lambda_depth or self.stack[-1].kind is not DefinitionKind.FUNCTION:
            return None
        return self.function_fact_stack[-1]

    def _collect_docstring(self, owner: DefinitionInfo) -> None:
        """Collect an owner's first string expression when it is a docstring."""
        first_expression = _first_expression(owner.body)
        if first_expression is None:
            return
        expression, statement = first_expression
        if isinstance(expression.value, (cst.SimpleString, cst.ConcatenatedString)):
            self.docstring_targets.append(_DocstringTarget(expression=expression, statement=statement, owner=owner))


class _AttributeDocstringCollector:
    """Collect attribute docstrings recognized by common documentation tools."""

    def __init__(self, context: RuleCategoryContext, definitions: Sequence[DefinitionInfo]) -> None:
        """Index collected definitions before scanning for adjacent attribute docstrings."""
        self.context = context
        self.definitions_by_node_id = {id(definition.node): definition for definition in definitions}
        self._attributes: list[AttributeInfo] = []
        self._docstring_targets: list[_DocstringTarget] = []

    def collect(self) -> _AttributeCollection:
        """Return collected attribute inventory and docstrings in source order."""
        module_definition = self.definitions_by_node_id[id(self.context.module)]
        self._scan_statements(self.context.module.body, module_definition)
        return _AttributeCollection(attributes=tuple(self._attributes), docstring_targets=tuple(self._docstring_targets))

    def _scan_suite(self, suite: cst.BaseSuite, owner: DefinitionInfo) -> None:
        """Scan a simple or indented suite for attribute docstring patterns."""
        if isinstance(suite, cst.SimpleStatementSuite):
            self._scan_small_statements(suite.body, owner, suite, previous_assignment=None)
        else:
            self._scan_statements(typing.cast("Sequence[cst.BaseStatement]", suite.body), owner)

    def _scan_statements(self, statements: Sequence[cst.BaseStatement], owner: DefinitionInfo) -> None:
        """Scan a sequence of compound or simple statements under an owner."""
        previous_assignment: AttributeInfo | None = None
        for statement in statements:
            if isinstance(statement, cst.SimpleStatementLine):
                pending_assignment = None if statement.leading_lines else previous_assignment
                previous_assignment = self._scan_small_statements(statement.body, owner, statement, previous_assignment=pending_assignment)
            else:
                previous_assignment = None
                self._scan_compound_statement(statement, owner)

    def _scan_small_statements(
        self, statements: Sequence[cst.BaseSmallStatement], owner: DefinitionInfo, statement: cst.SimpleStatementLine | cst.SimpleStatementSuite, *, previous_assignment: AttributeInfo | None
    ) -> AttributeInfo | None:
        """Scan semicolon-separated small statements and return a pending assignment."""
        pending_assignment = previous_assignment
        for small_statement in statements:
            if isinstance(small_statement, cst.Expr):
                self._collect_after_assignment(small_statement, statement, pending_assignment)
                pending_assignment = None
                continue
            pending_assignment = _attribute_info(small_statement, owner, context=self.context)
            if pending_assignment is not None:
                self._attributes.append(pending_assignment)
        return pending_assignment

    def _collect_after_assignment(self, expression: cst.Expr, statement: cst.SimpleStatementLine | cst.SimpleStatementSuite, assignment: AttributeInfo | None) -> None:
        """Collect a string expression immediately following an attribute assignment."""
        if assignment is None or not isinstance(expression.value, (cst.SimpleString, cst.ConcatenatedString)):
            return
        self._docstring_targets.append(_DocstringTarget(expression=expression, statement=statement, owner=assignment))

    def _scan_compound_statement(self, statement: cst.BaseStatement, owner: DefinitionInfo) -> None:
        """Recurse into compound statements that can contain attribute docstrings."""
        if isinstance(statement, cst.ClassDef):
            self._scan_suite(statement.body, self.definitions_by_node_id[id(statement)])
            return
        if isinstance(statement, cst.FunctionDef):
            self._scan_suite(statement.body, self.definitions_by_node_id[id(statement)])
            return
        if isinstance(statement, cst.If):
            self._scan_suite(statement.body, owner)
            self._scan_if_orelse(statement.orelse, owner)
            return
        if isinstance(statement, (cst.For, cst.While)):
            self._scan_suite(statement.body, owner)
            if statement.orelse is not None:
                self._scan_suite(statement.orelse.body, owner)
            return
        if isinstance(statement, cst.With):
            self._scan_suite(statement.body, owner)
            return
        if isinstance(statement, (cst.Try, cst.TryStar)):
            self._scan_suite(statement.body, owner)
            for handler in statement.handlers:
                self._scan_suite(handler.body, owner)
            if statement.orelse is not None:
                self._scan_suite(statement.orelse.body, owner)
            if statement.finalbody is not None:
                self._scan_suite(statement.finalbody.body, owner)
            return
        if isinstance(statement, cst.Match):
            for case in statement.cases:
                self._scan_suite(case.body, owner)

    def _scan_if_orelse(self, orelse: cst.Else | cst.If | None, owner: DefinitionInfo) -> None:
        """Scan an if/elif/else continuation for attribute docstrings."""
        if orelse is None:
            return
        if isinstance(orelse, cst.If):
            self._scan_compound_statement(orelse, owner)
        else:
            self._scan_suite(orelse.body, owner)


@rule_registration.register_rule_category
class PDF(RuleCategoryBase[PDFCategoryData]):
    """Docstring formatting rule category.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleCategoryMetadata(prefix="PDF", name="pydocformatter docstring formatting", url=docs_urls.category_url("PDF"))

    @classmethod
    def prepare(cls, context: RuleCategoryContext) -> PDFCategoryData:
        """Collect documentable definitions and existing docstrings.

        Args:
            context (RuleCategoryContext): Parsed module and settings shared by every PDF rule for the current file.

        Returns:
            Shared category data containing definitions, attributes, docstrings, and precomputed summary targets.
        """
        del cls
        collector = _DefinitionCollector(context)
        context.module.visit(collector)
        attribute_collector = _AttributeDocstringCollector(context, collector.definitions)
        attribute_collection = attribute_collector.collect()
        definitions = tuple(collector.definitions)
        targets = (*collector.docstring_targets, *attribute_collection.docstring_targets)
        if context.settings.docstring_convention in {settings_check.DocstringConvention.GOOGLE, settings_check.DocstringConvention.NUMPY, settings_check.DocstringConvention.REST}:
            attribute_names_by_parent_id, method_names_by_parent_id = _malformed_entry_inventories(definitions=definitions, attributes=attribute_collection.attributes)
        else:
            attribute_names_by_parent_id, method_names_by_parent_id = {}, {}
        docstrings = tuple(
            sorted(
                (
                    docstring
                    for target in targets
                    if (
                        docstring := _docstring_info(
                            target.expression,
                            target.statement,
                            owner=target.owner,
                            context=context,
                            malformed_entry_confidence=_malformed_entry_confidence(
                                target.owner, attribute_names_by_parent_id=attribute_names_by_parent_id, method_names_by_parent_id=method_names_by_parent_id
                            ),
                        )
                    )
                    is not None
                ),
                key=_docstring_sort_key,
            )
        )
        return PDFCategoryData(
            definitions=definitions,
            attributes=attribute_collection.attributes,
            docstrings=docstrings,
            summary_line_targets=summary_first_line_targets(docstrings),
            summary_terminal_line_targets=summary_terminal_line_targets(docstrings),
            function_facts_by_definition_id=MappingProxyType(collector.function_facts_by_definition_id),
        )

    @classmethod
    def suppression_expression_ranges(cls, data: PDFCategoryData | None) -> tuple[cst_metadata.CodeRange, ...]:
        """Return recognized docstring ranges eligible for complete-expression suppression.

        Args:
            data (PDFCategoryData | None): Prepared definitions and docstrings for the current module.

        Returns:
            tuple[cst_metadata.CodeRange, ...]: Exact primary and supported attached docstring expression ranges.
        """
        del cls
        return () if data is None else tuple(docstring.range for docstring in data.docstrings)

    @classmethod
    def require_data(cls, context: RuleContext) -> PDFCategoryData:
        """Return prepared PDF data or raise for an invalid rule context.

        Args:
            context (RuleContext): Rule execution context expected to carry the PDF category preparation result.

        Returns:
            Prepared PDF category data for the current file.

        Raises:
            TypeError: Raised when the context was not prepared by the PDF rule category.
        """
        if not isinstance(context.category_data, PDFCategoryData):
            raise TypeError(f"{cls.meta.prefix} rules require PDFCategoryData")
        return context.category_data


def is_adornment(text: str) -> bool:
    """Return whether text is a heading or section adornment line.

    Args:
        text (str): Logical docstring line text to classify.

    Returns:
        True when the line consists only of a repeated reStructuredText-style adornment character.
    """
    return _is_adornment(text)


def final_convention_section(docstring: DocstringInfo) -> DocstringBlock | None:
    """Return the final top-level convention section, if there is one.

    Args:
        docstring (DocstringInfo): Parsed docstring whose convention-aware block tree should be inspected.

    Returns:
        The final non-blank section block, or None when the convention has no parseable sections or the docstring ends with another block kind.
    """
    if not docstring_sections.convention_parses_sections(docstring.structure.convention):
        return None
    non_blank_blocks = tuple(block for block in docstring.structure.blocks if block.kind is not DocstringBlockKind.BLANK)
    if not non_blank_blocks or non_blank_blocks[-1].kind is not DocstringBlockKind.SECTION:
        return None
    return non_blank_blocks[-1]


def final_convention_section_spacing(docstring: DocstringInfo) -> FinalConventionSectionSpacing | None:
    """Return final convention section content and trailing blank facts.

    Args:
        docstring (DocstringInfo): Parsed docstring whose last convention section should be analyzed.

    Returns:
        Section spacing facts for the final section, or None when there is no final parseable convention section.
    """
    section = final_convention_section(docstring)
    if section is None:
        return None
    return FinalConventionSectionSpacing(
        section=section, final_content_line=_final_section_content_line(docstring, section), trailing_blank_line=_final_section_trailing_blank_line(docstring, section)
    )


def docstring_line_source(line: DocstringValueLine, *, source_map: string_literals.SimpleStringSourceMap, strip_docstring_margin: bool) -> str:
    """Return source spelling for a logical docstring line.

    Args:
        line (DocstringValueLine): Evaluated-value line whose source body slice should be reconstructed.
        source_map (string_literals.SimpleStringSourceMap): Lossless simple-string source mapping.
        strip_docstring_margin (bool): Whether to discard the literal indentation margin and keep only text content with
            virtual indentation.

    Returns:
        Source text for the line body, preserving escapes unless margin stripping is requested.
    """
    if not strip_docstring_margin:
        return source_map.owned_source_for_value_slice(line.start_offset, line.end_offset)
    start_offset = line.start_offset + line.text_raw_start_column
    return f"{' ' * line.text_virtual_prefix_length}{source_map.owned_source_for_value_slice(start_offset, line.end_offset)}"


def _final_section_content_line(docstring: DocstringInfo, section: DocstringBlock) -> int | None:
    """Return the final non-header, non-blank line in a convention section."""
    header = next((child for child in section.children if child.kind is DocstringBlockKind.SECTION_HEADER), None)
    header_lines = range(header.start_line, header.end_line) if header is not None else range(0)
    for index in range(section.end_line - 1, section.start_line - 1, -1):
        if index in header_lines:
            continue
        if docstring.structure.lines[index].text.strip():
            return index
    return None


def _final_section_trailing_blank_line(docstring: DocstringInfo, section: DocstringBlock) -> int | None:
    """Return the retained trailing blank line after final section content."""
    trailing_child_blank = section.children[-1] if section.children and section.children[-1].kind is DocstringBlockKind.BLANK else None
    if trailing_child_blank is not None:
        return _first_non_closing_quote_prefix_line(docstring, start=trailing_child_blank.start_line, end=trailing_child_blank.end_line)
    blank_block = next((block for block in docstring.structure.blocks if block.start_line == section.end_line and block.kind is DocstringBlockKind.BLANK), None)
    if blank_block is None:
        return None
    return _first_non_closing_quote_prefix_line(docstring, start=blank_block.start_line, end=blank_block.end_line)


def _first_non_closing_quote_prefix_line(docstring: DocstringInfo, *, start: int, end: int) -> int | None:
    """Return the first blank line that is not only a same-line closing quote prefix."""
    for index in range(start, end):
        if not is_same_line_closing_delimiter_prefix(docstring, docstring.structure.lines[index]):
            return index
    return None


_LIST_RE = re.compile(r"^(?P<indent>[ \t]*)(?P<marker>(?:[-+*]|\d+[.)]))[ \t]+(?P<text>.*)$")
_BLOCK_QUOTE_RE = re.compile(r"^(?P<indent>[ \t]*)(?P<quote>(?:>[ \t]*)+)(?P<text>.*)$")
_DIRECTIVE_RE = re.compile(r"^(?P<indent>[ \t]*)\.\.[ \t]+(?P<name>[\w-]+)::(?P<argument>.*)$")
_REST_FIELD_RE = re.compile(r"^(?P<indent>[ \t]*):(?P<field>[\w-]+)(?:[ \t]+(?P<argument>[^:]*?\S))?[ \t]*:[ \t]*(?P<description>.*)$")
_GOOGLE_FLAT_ENTRY_RE = re.compile(r"^(?P<indent>[ \t]*)(?P<name>\*{0,2}[A-Za-z_][\w.]*)(?:[ \t]*\((?P<type>[^)]+)\))?[ \t]*:[ \t]*(?P<description>.*)$")
_GOOGLE_CANDIDATE_RE = re.compile(r"^(?P<indent>[ \t]*)(?P<name>\*{0,2}[A-Za-z_][\w.]*)(?P<tail>.*)$")
_METHOD_ENTRY_CANDIDATE_RE = re.compile(r"^(?P<indent>[ \t]*)(?P<name>[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)(?P<tail>.*)$")
_GENERIC_ENTRY_PATTERN = re.compile(r"^(?P<indent>[ \t]*)(?P<name>[^:]+):[ \t]*(?P<description>.*)$")
_NUMPY_ENTRY_RE = re.compile(r"^(?P<indent>[ \t]*)(?P<name>\*{0,2}[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*(?:[ \t]*,[ \t]*\*{0,2}[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)*)[ \t]*:[ \t]*(?P<type>.+)$")
_NUMPY_EXCEPTION_ENTRY_RE = re.compile(r"^(?P<indent>[ \t]*)(?P<name>[^:]+?)[ \t]*:[ \t]*(?P<description>.*)$")
_ENTRY_NAME_RE = re.compile(r"\*{0,2}[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*")
_NUMPY_NAME_LIST_RE = re.compile(r"\*{0,2}[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*(?:[ \t]*,[ \t]*\*{0,2}[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)*")
_NUMPY_MISSING_SEPARATOR_RE = re.compile(rf"(?P<names>{_NUMPY_NAME_LIST_RE.pattern})[ \t]+(?P<type>.+)")
_EXCEPTION_NAME_RE = re.compile(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*")
_EXCEPTION_NAME_SEPARATOR_RE = re.compile(r"\s*(?:,|\|)\s*")
_ATX_HEADING_RE = re.compile(r"^[ \t]{0,3}#{1,6}[ \t]+\S")
_MARKDOWN_TABLE_DELIMITER_RE = re.compile(r"^[ \t]*\|?[ \t]*:?-{3,}:?[ \t]*(?:\|[ \t]*:?-{3,}:?[ \t]*)+\|?[ \t]*$")
_REST_GRID_BORDER_RE = re.compile(r"^[ \t]*\+(?:[-=]+\+)+[ \t]*$")
_REST_SIMPLE_BORDER_RE = re.compile(r"^[ \t]*={3,}(?:[ \t]+={3,})+[ \t]*$")


@dataclasses.dataclass(frozen=True)
class _ConventionEntryMatch:
    """Recovered fields from one convention entry declaration.

    Attributes:
        indent (str): Leading whitespace before the entry name.
        name (str): Entry name or generic declaration head.
        name_start (int): Zero-based source column where the entry name begins.
        name_end (int): Zero-based exclusive source column where the entry name ends.
        type_text (str | None): Parenthesized Google type without delimiters, when present.
        type_start (int | None): Zero-based source column where the type begins.
        type_end (int | None): Zero-based exclusive source column where the type ends.
        signature_text (str | None): Balanced method signature including its outer parentheses, when present.
        description (str): Inline description after the declaration separator.
        description_start (int): Zero-based source column where the description begins.
    """

    indent: str
    name: str
    name_start: int
    name_end: int
    type_text: str | None
    type_start: int | None
    type_end: int | None
    signature_text: str | None
    description: str
    description_start: int


def _match_google_entry(text: str, *, require_indent: bool = True) -> _ConventionEntryMatch | None:
    """Return explicit fields when text is a complete Google entry."""
    regex_match = _GOOGLE_FLAT_ENTRY_RE.match(text)
    if regex_match is not None and (not require_indent or bool(regex_match.group("indent"))):
        type_text = regex_match.group("type")
        if type_text is None:
            return _entry_match_from_regex(regex_match)
        if not type_text.strip(ascii_whitespace.SPACE_AND_TAB):
            return None
        opening = regex_match.start("type") - 1
        if opening >= 0 and text[opening] == "(" and _balanced_delimiter_end(text, opening) == regex_match.end("type"):
            return _entry_match_from_regex(regex_match)
    candidate = _GOOGLE_CANDIDATE_RE.match(text)
    if candidate is None or (require_indent and not candidate.group("indent")):
        return None
    tail_start = candidate.start("tail")
    opening = tail_start
    while opening < len(text) and text[opening] in ascii_whitespace.SPACE_AND_TAB:
        opening += 1
    if opening >= len(text) or text[opening] != "(":
        return None
    closing = _balanced_delimiter_end(text, opening)
    if closing is None or not text[opening + 1 : closing].strip(ascii_whitespace.SPACE_AND_TAB):
        return None
    colon = closing + 1
    while colon < len(text) and text[colon] in ascii_whitespace.SPACE_AND_TAB:
        colon += 1
    if colon >= len(text) or text[colon] != ":":
        return None
    description_start = colon + 1
    while description_start < len(text) and text[description_start] in ascii_whitespace.SPACE_AND_TAB:
        description_start += 1
    return _ConventionEntryMatch(
        indent=candidate.group("indent"),
        name=candidate.group("name"),
        name_start=candidate.start("name"),
        name_end=candidate.end("name"),
        type_text=text[opening + 1 : closing],
        type_start=opening + 1,
        type_end=closing,
        signature_text=None,
        description=text[description_start:],
        description_start=description_start,
    )


def _match_google_entry_for_kind(text: str, kind: DocstringEntryKind, *, require_indent: bool = True) -> _ConventionEntryMatch | None:
    """Return a Google entry match using method-signature syntax for method sections."""
    if kind is DocstringEntryKind.METHOD and (method_match := _match_google_method_entry(text, require_indent=require_indent)) is not None:
        return method_match
    return _match_google_entry(text, require_indent=require_indent)


def _match_google_method_entry(text: str, *, require_indent: bool = True) -> _ConventionEntryMatch | None:
    """Return explicit fields for a balanced Google method-signature entry."""
    signature = _match_method_signature_head(text, require_indent=require_indent)
    if signature is None:
        return None
    candidate, opening, closing = signature
    colon = closing + 1
    while colon < len(text) and text[colon] in ascii_whitespace.SPACE_AND_TAB:
        colon += 1
    if colon >= len(text) or text[colon] != ":":
        return None
    description_start = colon + 1
    while description_start < len(text) and text[description_start] in ascii_whitespace.SPACE_AND_TAB:
        description_start += 1
    return _ConventionEntryMatch(
        indent=candidate.group("indent"),
        name=candidate.group("name"),
        name_start=candidate.start("name"),
        name_end=candidate.end("name"),
        type_text=None,
        type_start=None,
        type_end=None,
        signature_text=text[opening : closing + 1],
        description=text[description_start:],
        description_start=description_start,
    )


def _match_numpy_method_entry(text: str) -> _ConventionEntryMatch | None:
    """Return explicit fields for a balanced NumPy method-signature entry."""
    signature = _match_method_signature_head(text, require_indent=False)
    if signature is None:
        return None
    candidate, opening, closing = signature
    if text[closing + 1 :].strip():
        return None
    return _ConventionEntryMatch(
        indent=candidate.group("indent"),
        name=candidate.group("name"),
        name_start=candidate.start("name"),
        name_end=candidate.end("name"),
        type_text=None,
        type_start=None,
        type_end=None,
        signature_text=text[opening : closing + 1],
        description="",
        description_start=len(text),
    )


def _match_method_signature_head(text: str, *, require_indent: bool) -> tuple[re.Match[str], int, int] | None:
    """Return a method candidate and its balanced signature bounds."""
    candidate = _METHOD_ENTRY_CANDIDATE_RE.match(text)
    if candidate is None or (require_indent and not candidate.group("indent")):
        return None
    opening = candidate.start("tail")
    while opening < len(text) and text[opening] in ascii_whitespace.SPACE_AND_TAB:
        opening += 1
    if opening >= len(text) or text[opening] != "(":
        return None
    closing = _balanced_delimiter_end(text, opening)
    if closing is None:
        return None
    return candidate, opening, closing


def _match_generic_entry(text: str, *, require_indent: bool = True) -> _ConventionEntryMatch | None:
    """Return explicit fields when text is a generic colon-separated entry."""
    regex_match = _GENERIC_ENTRY_PATTERN.match(text)
    if regex_match is None or (require_indent and not regex_match.group("indent")):
        return None
    return _entry_match_from_regex(regex_match)


def _entry_match_from_regex(regex_match: re.Match[str]) -> _ConventionEntryMatch:
    """Return explicit convention fields recovered by an entry regex."""
    type_text = regex_match.groupdict().get("type")
    return _ConventionEntryMatch(
        indent=regex_match.group("indent"),
        name=regex_match.group("name"),
        name_start=regex_match.start("name"),
        name_end=regex_match.end("name"),
        type_text=type_text,
        type_start=regex_match.start("type") if type_text is not None else None,
        type_end=regex_match.end("type") if type_text is not None else None,
        signature_text=None,
        description=regex_match.group("description"),
        description_start=regex_match.start("description"),
    )


def _type_info(line_index: int, text: str, full_start_column: int, full_end_column: int) -> DocstringTypeInfo | None:
    """Return parsed type text and convention-space-trimmed source bounds."""
    full_text = text[full_start_column:full_end_column]
    leading = len(full_text) - len(full_text.lstrip(ascii_whitespace.SPACE_AND_TAB))
    trailing = len(full_text) - len(full_text.rstrip(ascii_whitespace.SPACE_AND_TAB))
    semantic_start_column = full_start_column + leading
    semantic_end_column = full_end_column - trailing
    if semantic_start_column >= semantic_end_column:
        return None
    return DocstringTypeInfo(
        text=text[semantic_start_column:semantic_end_column],
        slot=DocstringTypeSlot(
            line_index=line_index, full_start_column=full_start_column, full_end_column=full_end_column, semantic_start_column=semantic_start_column, semantic_end_column=semantic_end_column
        ),
    )


def _google_type_edit_slot(line_index: int, match: _ConventionEntryMatch) -> DocstringTypeEditSlot:
    """Return parser-owned bounds for inserting or removing a Google type clause."""
    removal_start = match.name_end if match.type_start is not None and match.type_end is not None else None
    removal_end = match.type_end + 1 if match.type_end is not None else None
    return DocstringTypeEditSlot(line_index=line_index, insertion_column=match.name_end, removal_start_column=removal_start, removal_end_column=removal_end)


def _balanced_delimiter_end(text: str, opening: int) -> int | None:
    """Return the closing index for a quote-aware nested delimiter expression."""
    pairs = {"(": ")", "[": "]", "{": "}"}
    closings = frozenset(pairs.values())
    stack = [text[opening]]
    quote = ""
    triple = False
    index = opening + 1
    while index < len(text):
        character = text[index]
        if quote:
            if character == "\\":
                index += 2
                continue
            width = 3 if triple else 1
            if text.startswith(quote * width, index):
                quote = ""
                triple = False
                index += width
                continue
            index += 1
            continue
        if character in {"'", '"'}:
            quote = character
            triple = text.startswith(character * 3, index)
            index += 3 if triple else 1
            continue
        if character in pairs:
            stack.append(character)
        elif character in closings:
            if pairs[stack[-1]] != character:
                return None
            stack.pop()
            if not stack:
                return index
        index += 1
    return None


class _DocstringParser:
    """Parse one evaluated docstring value into conservative semantic blocks."""

    def __init__(self, value: str, *, settings: settings_check.CheckSettings, source_line_number: int | None, source_indent: int | None, malformed_entry_confidence: _MalformedEntryConfidence) -> None:
        """Prepare parser state for one evaluated docstring value."""
        self.value = value
        self.settings = settings
        self.malformed_entry_confidence = malformed_entry_confidence
        self.lines = _value_lines(value, source_line_number=source_line_number, source_indent=source_indent)
        self.blocks: list[DocstringBlock] = []
        self.sections: list[DocstringSection] = []
        self.entries: list[DocstringEntry] = []
        self.convention_entry_issues: dict[int, ConventionEntryIssue] = {}
        self.reflow_regions: list[ReflowRegion] = []
        self.missing_separator_type_cache: dict[str, bool] = {}
        self.summary_pending = True

    def parse(self) -> DocstringStructure:
        """Return the complete semantic structure."""
        self.blocks.extend(self._parse_range(0, len(self.lines)))
        return DocstringStructure(
            convention=self.settings.docstring_convention,
            lines=self.lines,
            blocks=tuple(self.blocks),
            sections=tuple(sorted(self.sections, key=lambda section: (section.start_line, section.end_line))),
            entries=tuple(sorted(self.entries, key=lambda entry: (entry.start_line, entry.end_line))),
            convention_entry_issues=tuple(sorted(self.convention_entry_issues.values(), key=lambda issue: issue.start_line)),
            reflow_regions=tuple(sorted(self.reflow_regions, key=lambda region: (region.start_line, region.end_line))),
        )

    def _parse_range(self, start: int, end: int) -> list[DocstringBlock]:
        """Parse a half-open logical line range into semantic docstring blocks."""
        blocks: list[DocstringBlock] = []
        index = start
        while index < end:
            text = self.lines[index].text
            if not text.strip():
                block_end = index + 1
                while block_end < end and not self.lines[block_end].text.strip():
                    block_end += 1
                blocks.append(DocstringBlock(DocstringBlockKind.BLANK, index, block_end))
                index = block_end
                continue
            section = self._section_at(index, end)
            if section is not None:
                section_block, index = self._parse_section(index, end, section)
                blocks.append(section_block)
                self.summary_pending = False
                continue
            if self.settings.docstring_parse_code_fences and (fence := inline_markup.FENCE_RE.match(text)) is not None:
                block_end = self._fence_end(index, end, fence.group("fence"))
                blocks.append(DocstringBlock(DocstringBlockKind.CODE_FENCE, index, block_end))
                index = block_end
                self.summary_pending = False
                continue
            if self.settings.docstring_parse_doctests and _is_doctest_prompt(text):
                block_end = index + 1
                while block_end < end and self.lines[block_end].text.strip():
                    block_end += 1
                blocks.append(DocstringBlock(DocstringBlockKind.DOCTEST, index, block_end))
                index = block_end
                self.summary_pending = False
                continue
            if self.settings.docstring_parse_directives and (directive := _DIRECTIVE_RE.match(text)) is not None:
                block_end = self._indented_body_end(index, end, text_layout.leading_width(directive.group("indent")))
                blocks.append(DocstringBlock(DocstringBlockKind.DIRECTIVE, index, block_end))
                index = block_end
                self.summary_pending = False
                continue
            if self.settings.docstring_parse_literal_blocks and text.rstrip().endswith("::") and self._has_indented_body(index, end):
                block_end = self._indented_body_end(index, end, text_layout.leading_width(text))
                blocks.append(DocstringBlock(DocstringBlockKind.LITERAL_BLOCK, index, block_end))
                index = block_end
                self.summary_pending = False
                continue
            if self.settings.docstring_parse_tables and (table_end := self._table_end(index, end)) is not None:
                blocks.append(DocstringBlock(DocstringBlockKind.TABLE, index, table_end))
                index = table_end
                self.summary_pending = False
                continue
            if self.settings.docstring_parse_headings and (self._is_heading(index, end)):
                block_end = index + 2 if index + 1 < end and _is_adornment(self.lines[index + 1].text) else index + 1
                blocks.append(DocstringBlock(DocstringBlockKind.HEADING, index, block_end))
                index = block_end
                self.summary_pending = False
                continue
            parses_rest_fields = self._parses_rest_fields()
            if parses_rest_fields:
                self._record_missing_rest_delimiter(index)
            if index in self.convention_entry_issues:
                blocks.append(DocstringBlock(DocstringBlockKind.CONVENTION_ENTRY_ISSUE, index, index + 1))
                index += 1
                self.summary_pending = False
                continue
            if parses_rest_fields and (field_match := _REST_FIELD_RE.match(text)) is not None:
                block, index = self._parse_rest_field(index, end, field_match)
                blocks.append(block)
                self.summary_pending = False
                continue
            if self.settings.docstring_parse_list_items and (list_match := _LIST_RE.match(text)) is not None:
                block, index = self._parse_list_item(index, end, list_match)
                blocks.append(block)
                self.summary_pending = False
                continue
            if self.settings.docstring_parse_block_quotes and (quote_match := _BLOCK_QUOTE_RE.match(text)) is not None:
                block, index = self._parse_block_quote(index, end, quote_match)
                blocks.append(block)
                self.summary_pending = False
                continue
            if self._is_colon_header(index):
                blocks.append(DocstringBlock(DocstringBlockKind.COLON_HEADER, index, index + 1))
                index += 1
                self.summary_pending = False
                continue
            if text[:1].isspace():
                block_end = index + 1
                while block_end < end and (not self.lines[block_end].text.strip() or self.lines[block_end].text[:1].isspace()):
                    block_end += 1
                block_end = self._trim_trailing_blank_lines(index, block_end)
                blocks.append(DocstringBlock(DocstringBlockKind.VERBATIM, index, block_end))
                index = block_end
                self.summary_pending = False
                continue
            block_end = self._plain_block_end(index, end)
            kind = DocstringBlockKind.SUMMARY if self.summary_pending else DocstringBlockKind.PARAGRAPH
            blocks.append(DocstringBlock(kind, index, block_end))
            self._add_reflow(kind, index, block_end, lines=self._stripped_reflow_lines(index, block_end), initial_indent="", subsequent_indent="")
            self.summary_pending = False
            index = block_end
        return blocks

    def _plain_block_end(self, start: int, end: int) -> int:
        """Return the end of one plain prose block."""
        block_end = start + 1
        while block_end < end and self.lines[block_end].text.strip() and not self._starts_special(block_end, end) and not self.lines[block_end].text[:1].isspace():
            if self._is_colon_header(block_end):
                if self._allows_colon_continuation(block_end - 1, block_end):
                    block_end += 1
                break
            block_end += 1
        return block_end

    def _starts_special(self, index: int, end: int) -> bool:
        """Return whether a line begins a structure that should stop paragraph collection."""
        text = self.lines[index].text
        parses_rest_fields = self._parses_rest_fields()
        return (
            self._section_at(index, end) is not None
            or (self.settings.docstring_parse_code_fences and inline_markup.FENCE_RE.match(text) is not None)
            or (self.settings.docstring_parse_doctests and _is_doctest_prompt(text))
            or (self.settings.docstring_parse_directives and _DIRECTIVE_RE.match(text) is not None)
            or (self.settings.docstring_parse_literal_blocks and text.rstrip().endswith("::") and self._has_indented_body(index, end))
            or (self.settings.docstring_parse_tables and self._table_end(index, end) is not None)
            or (self.settings.docstring_parse_headings and self._is_heading(index, end))
            or index in self.convention_entry_issues
            or (parses_rest_fields and self._missing_rest_delimiter_issue(index) is not None)
            or (parses_rest_fields and _REST_FIELD_RE.match(text) is not None)
            or (self.settings.docstring_parse_list_items and _LIST_RE.match(text) is not None)
            or (self.settings.docstring_parse_block_quotes and _BLOCK_QUOTE_RE.match(text) is not None)
        )

    def _is_colon_header(self, index: int) -> bool:
        """Return whether a line should be treated as a colon-ended structure boundary."""
        return colon_boundaries.is_colon_header_text(self.lines[index].text, require_unindented=True)

    def _allows_colon_continuation(self, previous_index: int, colon_index: int) -> bool:
        """Return whether a colon-ended line may continue the previous prose line."""
        return colon_boundaries.allows_colon_continuation(self.lines[previous_index].text, self.lines[colon_index].text)

    def _section_at(self, index: int, end: int, *, max_indent: int | None = None) -> str | None:
        """Return a recognized convention section name at a line index."""
        convention = self.settings.docstring_convention
        if not docstring_sections.convention_parses_sections(convention):
            return None
        text = self.lines[index].text
        if max_indent is not None and text_layout.leading_width(text) > max_indent:
            return None
        stripped = text.strip()
        candidate = stripped[:-1].rstrip() if stripped.endswith(":") else stripped
        names = docstring_sections.GOOGLE_SECTIONS if convention == settings_check.DocstringConvention.GOOGLE else docstring_sections.NUMPY_SECTIONS
        if candidate.lower() not in names:
            return None
        if convention == settings_check.DocstringConvention.NUMPY and index + 1 < end and _is_adornment(self.lines[index + 1].text):
            return candidate
        if convention == settings_check.DocstringConvention.GOOGLE:
            return candidate
        return candidate if not stripped.endswith(":") else None

    def _parses_rest_fields(self) -> bool:
        """Return whether the active convention parses reStructuredText fields."""
        return self.settings.docstring_convention == settings_check.DocstringConvention.REST

    def _parse_section(self, start: int, end: int, name: str) -> tuple[DocstringBlock, int]:
        """Parse a recognized Google or NumPy section and its child blocks."""
        content_start = start + 1
        if content_start < end and _is_adornment(self.lines[content_start].text):
            content_start += 1
        section_end = self._section_end(content_start, end, text_layout.leading_width(self.lines[start].text))
        section_indent = text_layout.leading_width(self.lines[start].raw_indent)
        entries = self._section_entries(name, content_start, section_end, section_indent=section_indent, section_text_indent=self.lines[start].text_indent)
        children: list[DocstringBlock] = [DocstringBlock(DocstringBlockKind.SECTION_HEADER, start, content_start)]
        if entries:
            entry_by_start = {entry.start_line: entry for entry in entries}
            index = content_start
            previous_summary = self.summary_pending
            self.summary_pending = False
            while index < section_end:
                entry = entry_by_start.get(index)
                if entry is not None:
                    children.append(DocstringBlock(DocstringBlockKind.SECTION_ENTRY, entry.start_line, entry.end_line, entry=entry))
                    index = entry.end_line
                    continue
                next_entry = min((entry_start for entry_start in entry_by_start if entry_start > index), default=section_end)
                children.extend(self._parse_range(index, next_entry))
                index = next_entry
            self.summary_pending = previous_summary
        else:
            previous_summary = self.summary_pending
            self.summary_pending = False
            children.extend(self._parse_range(content_start, section_end))
            self.summary_pending = previous_summary
        section = DocstringSection(name=name, start_line=start, end_line=section_end, header_line=start, content_start_line=content_start, entries=entries)
        self.sections.append(section)
        self.entries.extend(entries)
        return DocstringBlock(DocstringBlockKind.SECTION, start, section_end, children=tuple(children)), section_end

    def _section_entries(self, name: str, start: int, end: int, *, section_indent: int, section_text_indent: str) -> tuple[DocstringEntry, ...]:
        """Return entries parsed from a convention section body."""
        if self.settings.docstring_convention == settings_check.DocstringConvention.GOOGLE:
            return self._google_entries(name, start, end, section_indent=section_indent, section_text_indent=section_text_indent)
        if self.settings.docstring_convention == settings_check.DocstringConvention.NUMPY:
            return self._numpy_entries(name, start, end)
        return ()

    def _google_entries(self, section_name: str, start: int, end: int, *, section_indent: int, section_text_indent: str) -> tuple[DocstringEntry, ...]:
        """Return Google-style entries parsed from a section body."""
        entries: list[DocstringEntry] = []
        index = start
        kind = _entry_kind(section_name)
        detects_malformed = kind in {DocstringEntryKind.PARAMETER, DocstringEntryKind.ATTRIBUTE, DocstringEntryKind.METHOD} or is_exception_name_entry_kind(kind)
        while index < end:
            protected_end = self._protected_block_end(index, end)
            if protected_end is not None:
                index = protected_end
                continue
            text = self.lines[index].text
            match = _match_google_entry_for_kind(text, kind)
            if match is None and (kind in {DocstringEntryKind.RETURN, DocstringEntryKind.YIELD} or is_exception_name_entry_kind(kind)):
                match = _match_generic_entry(text)
            if match is not None and is_exception_name_entry_kind(kind) and _exception_names(match.name.strip()) is None:
                self._record_google_head_issue(index, kind=kind)
                index = self._entry_end(index, end, text_layout.leading_width(match.indent))
                continue
            complete_match = _match_google_entry_for_kind(text, kind, require_indent=False)
            if complete_match is None and is_exception_name_entry_kind(kind):
                complete_match = _match_generic_entry(text, require_indent=False)
            if detects_malformed and complete_match is not None and text_layout.leading_width(self.lines[index].raw_indent) <= section_indent:
                names = _entry_names(kind, complete_match.name.strip())
                credible = names is not None and (
                    (is_exception_name_entry_kind(kind) and all(_is_exception_like_name(name) for name in names))
                    or (len(names) == 1 and self._google_name_is_credible(kind, names[0], closed_parenthesized=complete_match.type_text is not None or complete_match.signature_text is not None))
                )
                if credible:
                    self._record_convention_entry_issue(
                        ConventionEntryIssue(
                            kind=ConventionEntryIssueKind.GOOGLE_ENTRY_INDENTATION,
                            start_line=index,
                            names=names,
                            replacement=ConventionEntryReplacement(0, len(self.lines[index].text_indent), f"{section_text_indent}{text_layout.indent_unit(self.settings)}"),
                        )
                    )
                match = None
            if match is None:
                if detects_malformed:
                    self._record_google_head_issue(index, kind=kind)
                none_entry = _google_none_value_entry(kind, text, start=index)
                if none_entry is not None:
                    entries.append(none_entry)
                    index = none_entry.end_line
                    continue
                index += 1
                continue
            entry_end = self._entry_end(index, end, text_layout.leading_width(match.indent))
            name = match.name.strip()
            type_text = match.type_text
            type_start = match.type_start
            type_end = match.type_end
            first_description = match.description.strip()
            description_fragments = []
            first_description_line = self._reflow_line_from_text_span(index, match.description_start, len(self.lines[index].text))
            if first_description_line is not None and first_description_line.text:
                description_fragments.append(first_description_line)
            description_fragments.extend(self._stripped_reflow_lines(index + 1, entry_end, skip_empty=True))
            description_lines = [line.text for line in description_fragments]
            names = _entry_names(kind, name)
            if names is None:
                index = entry_end
                continue
            if kind in {DocstringEntryKind.RETURN, DocstringEntryKind.YIELD} and type_text is None:
                names = ()
                type_text = name
                type_start = match.name_start
                type_end = match.name_end
            type_info = (
                _type_info(index, text, type_start, type_end)
                if type_text is not None
                and type_start is not None
                and type_end is not None
                and kind in {DocstringEntryKind.PARAMETER, DocstringEntryKind.RETURN, DocstringEntryKind.YIELD, DocstringEntryKind.ATTRIBUTE, DocstringEntryKind.METHOD}
                else None
            )
            entry = DocstringEntry(
                kind=kind,
                names=names,
                name_slots=_name_slots_from_text(index, match.name, names, start_column=match.name_start),
                type_info=type_info if type_info is not None else DocstringTypeInfo(text=type_text.strip(), slot=None) if type_text else None,
                description=" ".join(description_lines).strip(),
                description_lines=tuple(description_fragments),
                start_line=index,
                end_line=entry_end,
                type_edit_slot=_google_type_edit_slot(index, match),
            )
            entries.append(entry)
            if not first_description and entry_end == index + 1:
                self._record_google_continuation_issue(index + 1, end, entry=entry, entry_indent=text_layout.leading_width(self.lines[index].raw_indent))
            unit = text_layout.indent_unit(self.settings)
            prefix = f"{unit}{self.lines[index].text[len(match.indent) : match.description_start]}"
            if description_lines and not first_description and not prefix.endswith((" ", "\t")):
                prefix = f"{prefix} "
            self._add_reflow(DocstringBlockKind.SECTION_ENTRY, index, entry_end, lines=tuple(description_fragments), initial_indent=prefix, subsequent_indent=unit * 2)
            index = entry_end
        return tuple(entries)

    def _numpy_entries(self, section_name: str, start: int, end: int) -> tuple[DocstringEntry, ...]:
        """Return NumPy-style entries parsed from a section body."""
        entries: list[DocstringEntry] = []
        index = start
        kind = _entry_kind(section_name)
        detects_malformed = kind in {DocstringEntryKind.PARAMETER, DocstringEntryKind.ATTRIBUTE, DocstringEntryKind.METHOD}
        while index < end:
            protected_end = self._protected_block_end(index, end)
            if protected_end is not None:
                index = protected_end
                continue
            text = self.lines[index].text
            exception_match = _NUMPY_EXCEPTION_ENTRY_RE.match(text) if is_exception_name_entry_kind(kind) else None
            if exception_match is not None:
                entry_end = self._entry_end(index, end, text_layout.leading_width(exception_match.group("indent")))
                names = _exception_names(exception_match.group("name"))
                if names is not None:
                    first_description_line = self._reflow_line_from_text_span(index, exception_match.start("description"), len(self.lines[index].text))
                    description_fragments = []
                    if first_description_line is not None and first_description_line.text:
                        description_fragments.append(first_description_line)
                    description_fragments.extend(self._stripped_reflow_lines(index + 1, entry_end, skip_empty=True))
                    description_lines = [line.text for line in description_fragments]
                    entry = DocstringEntry(
                        kind=kind,
                        names=names,
                        name_slots=_name_slots_from_text(index, exception_match.group("name"), names, start_column=exception_match.start("name")),
                        type_info=None,
                        description=" ".join(description_lines),
                        description_lines=tuple(description_fragments),
                        start_line=index,
                        end_line=entry_end,
                    )
                    entries.append(entry)
                    if not description_lines and entry_end == index + 1:
                        self._record_numpy_continuation_issue(index + 1, end, entry=entry, entry_indent=text_layout.leading_width(self.lines[index].raw_indent))
                    if description_lines:
                        self._add_reflow(
                            DocstringBlockKind.SECTION_ENTRY,
                            index,
                            entry_end,
                            lines=tuple(description_fragments),
                            initial_indent=self.lines[index].text[: exception_match.start("description")],
                            subsequent_indent=text_layout.indent_unit(self.settings),
                        )
                index = entry_end
                continue
            method_match = _match_numpy_method_entry(text) if kind is DocstringEntryKind.METHOD else None
            if method_match is not None:
                names = (method_match.name.strip(),)
                entry = self._numpy_continuation_entry(
                    index,
                    end,
                    kind=kind,
                    names=names,
                    name_slots=_name_slots_from_text(index, method_match.name, names, start_column=method_match.name_start),
                    type_info=None,
                    entry_indent=text_layout.leading_width(method_match.indent),
                )
                entries.append(entry)
                index = entry.end_line
                continue
            match = _NUMPY_ENTRY_RE.match(text)
            if match is not None:
                names = _entry_names(kind, match.group("name"))
                if names is None:
                    index = self._entry_end(index, end, text_layout.leading_width(match.group("indent")))
                    continue
                type_info = (
                    _type_info(index, text, match.start("type"), match.end("type"))
                    if kind in {DocstringEntryKind.PARAMETER, DocstringEntryKind.RETURN, DocstringEntryKind.YIELD, DocstringEntryKind.ATTRIBUTE, DocstringEntryKind.METHOD}
                    else None
                )
                entry = self._numpy_continuation_entry(
                    index,
                    end,
                    kind=kind,
                    names=names,
                    name_slots=_name_slots_from_text(index, match.group("name"), names, start_column=match.start("name")),
                    type_info=type_info if type_info is not None else DocstringTypeInfo(text=match.group("type").strip(), slot=None),
                    entry_indent=text_layout.leading_width(match.group("indent")),
                )
                entries.append(entry)
                index = entry.end_line
                continue
            if detects_malformed:
                self._record_numpy_head_issue(index, kind=kind)
            if (kind in {DocstringEntryKind.RETURN, DocstringEntryKind.YIELD} or is_exception_name_entry_kind(kind)) and text.strip():
                entry_end = self._entry_end(index, end, text_layout.leading_width(text))
                description_fragments = list(self._stripped_reflow_lines(index + 1, entry_end, skip_empty=True))
                description_lines = [line.text for line in description_fragments]
                if is_exception_name_entry_kind(kind):
                    names = _exception_names(text.strip())
                    if names is None:
                        index = entry_end
                        continue
                else:
                    names = ()
                type_info = (
                    _type_info(index, text, len(text) - len(text.lstrip(ascii_whitespace.SPACE_AND_TAB)), len(text.rstrip(ascii_whitespace.SPACE_AND_TAB)))
                    if kind in {DocstringEntryKind.RETURN, DocstringEntryKind.YIELD}
                    else None
                )
                entry = DocstringEntry(
                    kind=kind,
                    names=names,
                    name_slots=_name_slots_from_text(index, text, names),
                    type_info=None if is_exception_name_entry_kind(kind) else type_info if type_info is not None else DocstringTypeInfo(text=text.strip(), slot=None),
                    description=" ".join(description_lines),
                    description_lines=tuple(description_fragments),
                    start_line=index,
                    end_line=entry_end,
                )
                entries.append(entry)
                if not description_lines and entry_end == index + 1:
                    self._record_numpy_continuation_issue(index + 1, end, entry=entry, entry_indent=text_layout.leading_width(self.lines[index].raw_indent))
                if description_lines:
                    self._add_reflow(
                        DocstringBlockKind.SECTION_ENTRY,
                        index + 1,
                        entry_end,
                        lines=tuple(description_fragments),
                        initial_indent=text_layout.indent_unit(self.settings),
                        subsequent_indent=text_layout.indent_unit(self.settings),
                    )
                index = entry_end
                continue
            index += 1
        return tuple(entries)

    def _numpy_continuation_entry(
        self, index: int, end: int, *, kind: DocstringEntryKind, names: tuple[str, ...], name_slots: tuple[DocstringNameSlot | None, ...], type_info: DocstringTypeInfo | None, entry_indent: int
    ) -> DocstringEntry:
        """Parse a NumPy entry whose description begins on a continuation line."""
        entry_end = self._entry_end(index, end, entry_indent)
        description_fragments = tuple(self._stripped_reflow_lines(index + 1, entry_end, skip_empty=True))
        description_lines = tuple(line.text for line in description_fragments)
        entry = DocstringEntry(
            kind=kind, names=names, name_slots=name_slots, type_info=type_info, description=" ".join(description_lines), description_lines=description_fragments, start_line=index, end_line=entry_end
        )
        if not description_lines and entry_end == index + 1:
            self._record_numpy_continuation_issue(index + 1, end, entry=entry, entry_indent=text_layout.leading_width(self.lines[index].raw_indent))
        if description_lines:
            self._add_reflow(
                DocstringBlockKind.SECTION_ENTRY,
                index + 1,
                entry_end,
                lines=description_fragments,
                initial_indent=text_layout.indent_unit(self.settings),
                subsequent_indent=text_layout.indent_unit(self.settings),
            )
        return entry

    def _record_google_head_issue(self, index: int, *, kind: DocstringEntryKind) -> None:
        """Record a high-confidence malformed Google entry head."""
        text = self.lines[index].text
        match = (_METHOD_ENTRY_CANDIDATE_RE if kind is DocstringEntryKind.METHOD else _GOOGLE_CANDIDATE_RE).match(text)
        if (
            is_exception_name_entry_kind(kind)
            and (match is None or not match.group("tail").lstrip(ascii_whitespace.SPACE_AND_TAB).startswith("("))
            and (exception_head := _google_exception_missing_separator(text)) is not None
        ):
            exception_names, head_end = exception_head
            self._record_convention_entry_issue(
                ConventionEntryIssue(kind=ConventionEntryIssueKind.GOOGLE_MISSING_SEPARATOR, start_line=index, names=exception_names, replacement=ConventionEntryReplacement(head_end, head_end, ":"))
            )
            return
        if match is None:
            return
        name = match.group("name")
        raw_tail = match.group("tail")
        tail = raw_tail.lstrip(ascii_whitespace.SPACE_AND_TAB)
        tail_start = match.start("tail") + len(raw_tail) - len(tail)
        names = (name,)
        replacement = None
        if not tail.startswith("("):
            if is_exception_name_entry_kind(kind) or tail.startswith(":") or not self._google_name_is_credible(kind, name, closed_parenthesized=False):
                return
            issue_kind = ConventionEntryIssueKind.GOOGLE_MISSING_SEPARATOR
            replacement = ConventionEntryReplacement(match.end("name"), match.end("name"), ":")
        else:
            closing = _balanced_delimiter_end(tail, 0)
            if closing is None:
                if not self._google_name_is_credible(kind, name, closed_parenthesized=False):
                    return
                issue_kind = ConventionEntryIssueKind.GOOGLE_UNBALANCED_METHOD_SIGNATURE if kind is DocstringEntryKind.METHOD else ConventionEntryIssueKind.GOOGLE_UNBALANCED_TYPE
            elif not tail[1:closing].strip(ascii_whitespace.SPACE_AND_TAB):
                if not self._google_name_is_credible(kind, name, closed_parenthesized=True):
                    return
                issue_kind = ConventionEntryIssueKind.GOOGLE_MISSING_TYPE
            else:
                after_type = tail[closing + 1 :].lstrip(ascii_whitespace.SPACE_AND_TAB)
                if after_type.startswith(":") or not self._google_name_is_credible(kind, name, closed_parenthesized=True):
                    return
                issue_kind = ConventionEntryIssueKind.GOOGLE_MISSING_SEPARATOR
                separator_column = tail_start + closing + 1
                replacement = ConventionEntryReplacement(separator_column, separator_column, ":")
        self._record_convention_entry_issue(ConventionEntryIssue(kind=issue_kind, start_line=index, names=names, replacement=replacement))

    def _google_name_is_credible(self, kind: DocstringEntryKind, name: str, *, closed_parenthesized: bool) -> bool:
        """Return whether a recovered Google name is sufficiently entry-like."""
        confidence = self.malformed_entry_confidence
        if kind is DocstringEntryKind.PARAMETER:
            return closed_parenthesized or name.lstrip("*") in confidence.parameter_names
        if kind is DocstringEntryKind.ATTRIBUTE:
            return closed_parenthesized or name in confidence.attribute_names
        if kind is DocstringEntryKind.METHOD:
            return closed_parenthesized or name in confidence.method_names
        if is_exception_name_entry_kind(kind):
            names = _exception_names(name)
            return names is not None and all(_is_exception_like_name(exception_name) for exception_name in names)
        return False

    def _record_google_continuation_issue(self, index: int, end: int, *, entry: DocstringEntry, entry_indent: int) -> None:
        """Record an under-indented immediate Google entry description."""
        if index < end:
            text = self.lines[index].text
            generic_match = _match_generic_entry(text, require_indent=False) if is_exception_name_entry_kind(entry.kind) else None
            if _match_google_entry_for_kind(text, entry.kind, require_indent=False) is not None or (generic_match is not None and _exception_names(generic_match.name) is not None):
                return
        if not self._is_incorrect_continuation(index, end, entry_indent=entry_indent):
            return
        line = self.lines[index]
        desired_indent = f"{self.lines[entry.start_line].text_indent}{text_layout.indent_unit(self.settings)}"
        self._record_convention_entry_issue(
            ConventionEntryIssue(
                kind=ConventionEntryIssueKind.GOOGLE_CONTINUATION_INDENTATION, start_line=index, names=entry.names, replacement=ConventionEntryReplacement(0, len(line.text_indent), desired_indent)
            )
        )

    def _record_numpy_head_issue(self, index: int, *, kind: DocstringEntryKind) -> None:
        """Record a high-confidence malformed NumPy entry head."""
        text = self.lines[index].text
        stripped = text.strip()
        if kind is DocstringEntryKind.METHOD and (method_candidate := _METHOD_ENTRY_CANDIDATE_RE.fullmatch(text)) is not None:
            tail = method_candidate.group("tail").lstrip(ascii_whitespace.SPACE_AND_TAB)
            if tail.startswith("(") and _balanced_delimiter_end(tail, 0) is None and self._numpy_names_are_credible(kind, (method_candidate.group("name"),)):
                self._record_convention_entry_issue(ConventionEntryIssue(kind=ConventionEntryIssueKind.NUMPY_UNBALANCED_METHOD_SIGNATURE, start_line=index, names=(method_candidate.group("name"),)))
                return
        missing_type = re.fullmatch(r"(?P<names>.+?)[ \t]*:[ \t]*", stripped)
        if missing_type is not None and (names := _strict_numpy_names(missing_type.group("names"))) is not None and self._numpy_names_are_credible(kind, names):
            self._record_convention_entry_issue(ConventionEntryIssue(kind=ConventionEntryIssueKind.NUMPY_MISSING_TYPE, start_line=index, names=names))
            return
        candidate = _NUMPY_MISSING_SEPARATOR_RE.fullmatch(stripped)
        if (
            candidate is None
            or (names := _strict_numpy_names(candidate.group("names"))) is None
            or not self._numpy_names_are_credible(kind, names)
            or not self._is_missing_separator_type(candidate.group("type"))
        ):
            return
        leading = len(text) - len(text.lstrip(ascii_whitespace.SPACE_AND_TAB))
        separator_column = leading + candidate.end("names")
        self._record_convention_entry_issue(
            ConventionEntryIssue(kind=ConventionEntryIssueKind.NUMPY_MISSING_SEPARATOR, start_line=index, names=names, replacement=ConventionEntryReplacement(separator_column, separator_column, ":"))
        )

    def _numpy_names_are_credible(self, kind: DocstringEntryKind, names: tuple[str, ...]) -> bool:
        """Return whether recovered NumPy names match their owner inventory."""
        confidence = self.malformed_entry_confidence
        if kind is DocstringEntryKind.PARAMETER:
            return all(name.lstrip("*") in confidence.parameter_names for name in names)
        if kind is DocstringEntryKind.ATTRIBUTE:
            return all(name in confidence.attribute_names for name in names)
        if kind is DocstringEntryKind.METHOD:
            return all(name in confidence.method_names for name in names)
        return False

    def _record_numpy_continuation_issue(self, index: int, end: int, *, entry: DocstringEntry, entry_indent: int) -> None:
        """Record an under-indented immediate NumPy entry description."""
        if index < end:
            text = self.lines[index].text
            if (
                _NUMPY_ENTRY_RE.match(text) is not None
                or (entry.kind is DocstringEntryKind.METHOD and _match_numpy_method_entry(text) is not None)
                or (is_exception_name_entry_kind(entry.kind) and _is_numpy_exception_entry(text))
                or (entry.kind in {DocstringEntryKind.RETURN, DocstringEntryKind.YIELD} and self._is_missing_separator_type(text.strip()))
            ):
                return
        if not self._is_incorrect_continuation(index, end, entry_indent=entry_indent):
            return
        line = self.lines[index]
        desired_indent = f"{self.lines[entry.start_line].text_indent}{text_layout.indent_unit(self.settings)}"
        self._record_convention_entry_issue(
            ConventionEntryIssue(
                kind=ConventionEntryIssueKind.NUMPY_CONTINUATION_INDENTATION, start_line=index, names=entry.names, replacement=ConventionEntryReplacement(0, len(line.text_indent), desired_indent)
            )
        )

    def _is_missing_separator_type(self, text: str) -> bool:
        """Return a docstring-local cached conservative type classification."""
        cached = self.missing_separator_type_cache.get(text)
        if cached is None:
            cached = _is_missing_separator_type(text)
            self.missing_separator_type_cache[text] = cached
        return cached

    def _is_incorrect_continuation(self, index: int, end: int, *, entry_indent: int) -> bool:
        """Return whether one immediate line is a certain under-indented continuation."""
        if index >= end:
            return False
        line = self.lines[index]
        text = line.text
        if not text.strip() or text_layout.leading_width(line.raw_indent) > entry_indent:
            return False
        if self._section_at(index, end) is not None or self._protected_block_end(index, end) is not None or _is_adornment(text):
            return False
        return any(character.isalnum() for character in text)

    def _record_missing_rest_delimiter(self, index: int) -> None:
        """Record a recognized reStructuredText field without its closing delimiter."""
        issue = self._missing_rest_delimiter_issue(index)
        if issue is not None:
            self._record_convention_entry_issue(issue)

    def _missing_rest_delimiter_issue(self, index: int) -> ConventionEntryIssue | None:
        """Return a recognized reStructuredText field missing its closing delimiter."""
        line_text = self.lines[index].text
        leading = len(line_text) - len(line_text.lstrip(ascii_whitespace.SPACE_AND_TAB))
        text = line_text[leading:]
        if not text.startswith(":") or text.startswith("::"):
            return None
        field_match = re.match(r":(?P<field>[\w-]+)(?=$|[ \t])", text)
        if field_match is None or ":" in text[field_match.end() :]:
            return None
        field = field_match.group("field").lower()
        metadata = docstring_sections.rest_field_metadata(field)
        if metadata is None:
            return None
        credible, replacement = self._missing_rest_delimiter_analysis(text, leading=leading, field_match=field_match, family=metadata[0])
        if not credible:
            return None
        return ConventionEntryIssue(kind=ConventionEntryIssueKind.REST_MISSING_CLOSING_DELIMITER, start_line=index, field_name=field, replacement=replacement)

    def _missing_rest_delimiter_analysis(self, text: str, *, leading: int, field_match: re.Match[str], family: docstring_sections.RestFieldFamily) -> tuple[bool, ConventionEntryReplacement | None]:
        """Return whether a malformed field is credible and its safe delimiter repair."""
        if family.argument_policy is not docstring_sections.RestFieldArgumentPolicy.REQUIRED:
            if text[field_match.end() :].strip(ascii_whitespace.SPACE_AND_TAB):
                return False, None
            delimiter_column = leading + len(text.rstrip(ascii_whitespace.SPACE_AND_TAB))
            return True, ConventionEntryReplacement(delimiter_column, delimiter_column, ":")
        tail_start = field_match.end()
        raw_tail = text[tail_start:]
        if family.kind == DocstringEntryKind.EXCEPTION.value:
            exception_head = _google_exception_missing_separator(raw_tail)
            if exception_head is not None:
                _, head_end = exception_head
            else:
                stripped_tail = raw_tail.strip(ascii_whitespace.SPACE_AND_TAB)
                names = _exception_names(stripped_tail)
                if names is None or not all(_is_exception_like_name(name) for name in names):
                    return False, None
                head_end = len(raw_tail.rstrip(ascii_whitespace.SPACE_AND_TAB))
            delimiter_column = leading + tail_start + head_end
            return True, ConventionEntryReplacement(delimiter_column, delimiter_column, ":")
        if family.kind == DocstringEntryKind.PARAMETER.value:
            owner_names = self.malformed_entry_confidence.parameter_names
            owner_matches = tuple(match for match in _ENTRY_NAME_RE.finditer(raw_tail) if match.group().lstrip("*") in owner_names and _entry_name_match_is_token(raw_tail, match))
            eligible_matches = tuple(match for match in owner_matches if not (prefix := raw_tail[: match.start()].strip(ascii_whitespace.SPACE_AND_TAB)) or self._is_missing_separator_type(prefix))
            first_argument = raw_tail.strip(ascii_whitespace.SPACE_AND_TAB).split(None, 1)[0] if raw_tail.strip(ascii_whitespace.SPACE_AND_TAB) else ""
            credible = _ENTRY_NAME_RE.fullmatch(first_argument) is not None or bool(eligible_matches)
            if not credible or len(owner_matches) != 1 or len(eligible_matches) != 1:
                return credible, None
            match = eligible_matches[0]
        elif family.kind == DocstringEntryKind.ATTRIBUTE.value:
            owner_names = self.malformed_entry_confidence.attribute_names
            stripped_tail = raw_tail.strip(ascii_whitespace.SPACE_AND_TAB)
            first_argument = stripped_tail.split(None, 1)[0] if stripped_tail else ""
            if _ENTRY_NAME_RE.fullmatch(first_argument) is None:
                return False, None
            if first_argument not in owner_names:
                return True, None
            match = _ENTRY_NAME_RE.search(raw_tail)
            if match is None:
                return True, None
        else:
            return False, None
        delimiter_column = leading + tail_start + match.end()
        return True, ConventionEntryReplacement(delimiter_column, delimiter_column, ":")

    def _record_convention_entry_issue(self, issue: ConventionEntryIssue) -> None:
        """Record the highest-priority malformed entry issue for one line."""
        existing = self.convention_entry_issues.get(issue.start_line)
        if existing is None or _CONVENTION_ENTRY_ISSUE_PRECEDENCE[issue.kind] < _CONVENTION_ENTRY_ISSUE_PRECEDENCE[existing.kind]:
            self.convention_entry_issues[issue.start_line] = issue

    def _parse_rest_field(self, start: int, end: int, match: re.Match[str]) -> tuple[DocstringBlock, int]:
        """Parse one reStructuredText field and any indented continuation lines."""
        block_end = self._continuation_end(start, end, text_layout.leading_width(match.group("indent")))
        field = match.group("field").lower()
        argument = (match.group("argument") or "").strip()
        first_description_line = self._reflow_line_from_text_span(start, match.start("description"), len(self.lines[start].text))
        description_fragments: list[DocstringTextFragment] = []
        reflow_runs: list[ReflowRegionRun] = []
        if first_description_line is not None and first_description_line.text:
            description_fragments.append(first_description_line)
        continuation_runs, following_description_block_kind = self._rest_field_description_reflow_runs(start + 1, block_end)
        description_fragments.extend(line for run in continuation_runs for line in run.lines)
        if first_description_line is not None and first_description_line.text:
            if continuation_runs and continuation_runs[0].start_line == start + 1:
                first_run = continuation_runs[0]
                reflow_runs.append(ReflowRegionRun(start_line=start, end_line=first_run.end_line, lines=(first_description_line, *first_run.lines)))
                reflow_runs.extend(continuation_runs[1:])
            else:
                reflow_runs.append(ReflowRegionRun(start_line=start, end_line=start + 1, lines=(first_description_line,)))
                reflow_runs.extend(continuation_runs)
        elif continuation_runs and continuation_runs[0].start_line == start + 1:
            first_run = continuation_runs[0]
            reflow_runs.append(ReflowRegionRun(start_line=start, end_line=first_run.end_line, lines=first_run.lines))
            reflow_runs.extend(continuation_runs[1:])
        else:
            reflow_runs.extend(continuation_runs)
        description_lines = [line.text for line in description_fragments]
        description = " ".join(description_lines).strip()
        issue_kind = _rest_field_arity_issue(field, argument)
        entry: DocstringEntry | None = None
        if issue_kind is None:
            kind, names, type_text = _rest_entry_metadata(field, argument)
            type_info = None
            if docstring_sections.is_rest_type_field(field) and description:
                inline_type_info = _type_info(start, self.lines[start].text, match.start("description"), match.end("description"))
                type_info = (
                    inline_type_info
                    if len(description_fragments) == 1 and description_fragments[0].line_index == start and inline_type_info is not None
                    else DocstringTypeInfo(text=description, slot=None)
                )
            elif kind is DocstringEntryKind.PARAMETER and type_text is not None and names and (raw_argument := match.group("argument")) is not None:
                name_start = raw_argument.rfind(names[0])
                if name_start > 0:
                    full_type = raw_argument[:name_start].rstrip(ascii_whitespace.SPACE_AND_TAB)
                    type_info = _type_info(start, self.lines[start].text, match.start("argument"), match.start("argument") + len(full_type))
            entry = DocstringEntry(
                kind=kind,
                names=names,
                name_slots=_rest_name_slots(start, match, names),
                type_info=type_info if type_info is not None else DocstringTypeInfo(text=type_text, slot=None) if type_text is not None else None,
                description=description,
                description_lines=tuple(description_fragments),
                start_line=start,
                end_line=block_end,
                following_description_block_kind=following_description_block_kind,
                field_name=field,
                field_argument=argument or None,
            )
            self.entries.append(entry)
        else:
            self._record_convention_entry_issue(ConventionEntryIssue(kind=issue_kind, start_line=start, field_name=field))
        prefix = self.lines[start].text[: match.start("description")]
        subsequent_indent = " " * len(prefix.expandtabs(self.settings.indent_width))
        if reflow_runs and reflow_runs[0].start_line == start and (first_description_line is None or not first_description_line.text) and not prefix.endswith((" ", "\t")):
            prefix = f"{prefix} "
            subsequent_indent = " " * len(prefix.expandtabs(self.settings.indent_width))
        for run in reflow_runs:
            run_indent = prefix if run.start_line == start else self.lines[run.start_line].text_indent
            run_subsequent_indent = subsequent_indent if run.start_line == start else run_indent
            self._add_reflow(DocstringBlockKind.REST_FIELD, run.start_line, run.end_line, lines=run.lines, initial_indent=run_indent, subsequent_indent=run_subsequent_indent)
        return DocstringBlock(DocstringBlockKind.REST_FIELD, start, block_end, entry=entry), block_end

    def _rest_field_description_reflow_runs(self, start: int, end: int) -> tuple[tuple[ReflowRegionRun, ...], DocstringBlockKind | None]:
        """Return reflowable runs and trailing protected structure from a reStructuredText field description body."""
        runs: list[ReflowRegionRun] = []
        run_start: int | None = None
        run_lines: list[DocstringTextFragment] = []
        following_description_block_kind: DocstringBlockKind | None = None
        index = start
        while index < end:
            protected = self._protected_block_kind_and_end(index, end)
            if protected is not None:
                protected_kind, protected_end = protected
                if run_start is not None and run_lines:
                    runs.append(ReflowRegionRun(start_line=run_start, end_line=index, lines=tuple(run_lines)))
                    run_start = None
                    run_lines = []
                if following_description_block_kind is None:
                    following_description_block_kind = protected_kind
                index = protected_end
                continue
            line = self._reflow_line_from_text_span(index, 0, len(self.lines[index].text))
            if line is not None and line.text:
                if run_start is None:
                    run_start = index
                    following_description_block_kind = None
                run_lines.append(line)
            index += 1
        if run_start is not None and run_lines:
            runs.append(ReflowRegionRun(start_line=run_start, end_line=end, lines=tuple(run_lines)))
        return tuple(runs), following_description_block_kind

    def _parse_list_item(self, start: int, end: int, match: re.Match[str]) -> tuple[DocstringBlock, int]:
        """Parse a Markdown-style list item and register its reflow region."""
        block_end = self._list_item_end(start, end, match)
        prefix = f"{match.group('indent')}{match.group('marker')} "
        first_line = self._reflow_line_from_text_span(start, match.start("text"), len(self.lines[start].text))
        lines = (() if first_line is None else (first_line,)) + self._stripped_reflow_lines(start + 1, block_end)
        self._add_reflow(DocstringBlockKind.LIST_ITEM, start, block_end, lines=tuple(lines), initial_indent=prefix, subsequent_indent=" " * len(prefix.expandtabs(self.settings.indent_width)))
        return DocstringBlock(DocstringBlockKind.LIST_ITEM, start, block_end), block_end

    def _parse_block_quote(self, start: int, end: int, match: re.Match[str]) -> tuple[DocstringBlock, int]:
        """Parse a block quote run and register its reflow region."""
        prefix = f"{match.group('indent')}{match.group('quote')}"
        block_end = self._block_quote_end(start, end, prefix)
        texts = tuple(line for line in (self._reflow_line_from_text_span(line, len(prefix), len(self.lines[line].text)) for line in range(start, block_end)) if line is not None)
        self._add_reflow(DocstringBlockKind.BLOCK_QUOTE, start, block_end, lines=tuple(texts), initial_indent=prefix, subsequent_indent=prefix)
        return DocstringBlock(DocstringBlockKind.BLOCK_QUOTE, start, block_end), block_end

    def _add_reflow(self, kind: DocstringBlockKind, start: int, end: int, *, lines: tuple[DocstringTextFragment, ...], initial_indent: str, subsequent_indent: str) -> None:
        """Register a non-empty safely reflowable region."""
        if not lines or not any(line.text for line in lines):
            return
        self.reflow_regions.append(
            ReflowRegion(
                kind=kind,
                start_line=start,
                end_line=end,
                start_offset=self.lines[start].start_offset,
                end_offset=self.lines[end - 1].end_offset,
                lines=lines,
                initial_indent=initial_indent,
                subsequent_indent=subsequent_indent,
            )
        )

    def _stripped_reflow_lines(self, start: int, end: int, *, skip_empty: bool = False) -> tuple[DocstringTextFragment, ...]:
        """Return stripped reflow lines for a logical line range."""
        lines: list[DocstringTextFragment] = []
        for index in range(start, end):
            line = self._reflow_line_from_text_span(index, 0, len(self.lines[index].text))
            if line is not None and (line.text or not skip_empty):
                lines.append(line)
        return tuple(lines)

    def _reflow_line_from_text_span(self, line_index: int, start_column: int, end_column: int) -> DocstringTextFragment | None:
        """Return a reflow line from a trimmed column span in evaluated text."""
        line = self.lines[line_index]
        full_start_offset = value_offset_for_text_column(line, start_column)
        full_end_offset = value_offset_for_text_column(line, end_column)
        while start_column < end_column and unicode_safety.is_layout_separator(line.text[start_column]):
            start_column += 1
        while end_column > start_column and unicode_safety.is_layout_separator(line.text[end_column - 1]):
            end_column -= 1
        if start_column > end_column:
            return None
        start_offset = value_offset_for_text_column(line, start_column)
        end_offset = value_offset_for_text_column(line, end_column)
        return DocstringTextFragment(
            text=line.text[start_column:end_column], line_index=line_index, full_start_offset=full_start_offset, full_end_offset=full_end_offset, start_offset=start_offset, end_offset=end_offset
        )

    def _fence_end(self, start: int, end: int, opening: str) -> int:
        """Return the end index for a fenced code block."""
        index = start + 1
        while index < end:
            match = inline_markup.FENCE_RE.match(self.lines[index].text)
            if match is not None and match.group("fence")[0] == opening[0] and len(match.group("fence")) >= len(opening) and not match.group("info").strip():
                return index + 1
            index += 1
        return end

    def _section_end(self, start: int, end: int, section_indent: int) -> int:
        """Return the first line after a convention section body."""
        index = start
        while index < end:
            if self._section_at(index, end, max_indent=section_indent) is not None:
                return index
            protected_end = self._protected_block_end(index, end)
            index = protected_end if protected_end is not None else index + 1
        return end

    def _protected_block_end(self, index: int, end: int) -> int | None:
        """Return the end of a protected structure starting at a line index."""
        protected = self._protected_block_kind_and_end(index, end)
        return None if protected is None else protected[1]

    def _protected_block_kind_and_end(self, index: int, end: int) -> tuple[DocstringBlockKind, int] | None:
        """Return the kind and end of a protected structure starting at a line index."""
        text = self.lines[index].text
        if self.settings.docstring_parse_code_fences and (fence := inline_markup.FENCE_RE.match(text)) is not None:
            return DocstringBlockKind.CODE_FENCE, self._fence_end(index, end, fence.group("fence"))
        if self.settings.docstring_parse_doctests and _is_doctest_prompt(text):
            block_end = index + 1
            while block_end < end and self.lines[block_end].text.strip():
                block_end += 1
            return DocstringBlockKind.DOCTEST, block_end
        if self.settings.docstring_parse_directives and (directive := _DIRECTIVE_RE.match(text)) is not None:
            return DocstringBlockKind.DIRECTIVE, self._indented_body_end(index, end, text_layout.leading_width(directive.group("indent")))
        if self.settings.docstring_parse_literal_blocks and text.rstrip().endswith("::") and self._has_indented_body(index, end):
            return DocstringBlockKind.LITERAL_BLOCK, self._indented_body_end(index, end, text_layout.leading_width(text))
        if self.settings.docstring_parse_tables and (table_end := self._table_end(index, end)) is not None:
            return DocstringBlockKind.TABLE, table_end
        if self.settings.docstring_parse_headings and self._is_heading(index, end):
            return DocstringBlockKind.HEADING, index + 2 if index + 1 < end and _is_adornment(self.lines[index + 1].text) else index + 1
        if self._parses_rest_fields() and (field_match := _REST_FIELD_RE.match(text)) is not None:
            return DocstringBlockKind.REST_FIELD, self._continuation_end(index, end, text_layout.leading_width(field_match.group("indent")))
        if self.settings.docstring_parse_list_items and (list_match := _LIST_RE.match(text)) is not None:
            return DocstringBlockKind.LIST_ITEM, self._list_item_end(index, end, list_match)
        if self.settings.docstring_parse_block_quotes and (quote_match := _BLOCK_QUOTE_RE.match(text)) is not None:
            prefix = f"{quote_match.group('indent')}{quote_match.group('quote')}"
            return DocstringBlockKind.BLOCK_QUOTE, self._block_quote_end(index, end, prefix)
        return None

    def _list_item_end(self, start: int, end: int, match: re.Match[str]) -> int:
        """Return the end index for a list item continuation block."""
        base_indent = text_layout.leading_width(match.group("indent"))
        block_end = start + 1
        while block_end < end:
            text = self.lines[block_end].text
            if not text.strip() or _LIST_RE.match(text) is not None or text_layout.leading_width(text) <= base_indent:
                break
            block_end += 1
        return block_end

    def _block_quote_end(self, start: int, end: int, prefix: str) -> int:
        """Return the end index for consecutive block quote lines with a shared prefix."""
        block_end = start + 1
        while block_end < end:
            next_match = _BLOCK_QUOTE_RE.match(self.lines[block_end].text)
            if next_match is None or f"{next_match.group('indent')}{next_match.group('quote')}" != prefix:
                break
            block_end += 1
        return block_end

    def _has_indented_body(self, index: int, end: int) -> bool:
        """Return whether the next non-blank line is more indented than the current line."""
        next_index = index + 1
        while next_index < end and not self.lines[next_index].text.strip():
            next_index += 1
        if next_index >= end:
            return False
        base_indent = text_layout.leading_width(self.lines[index].text)
        next_indent = text_layout.leading_width(self.lines[next_index].text)
        return next_indent > base_indent

    def _indented_body_end(self, start: int, end: int, base_indent: int) -> int:
        """Return the end index for an indented directive or literal-block body."""
        index = start + 1
        while index < end:
            text = self.lines[index].text
            indent = text_layout.leading_width(text)
            if text.strip() and indent <= base_indent:
                break
            index += 1
        return self._trim_trailing_blank_lines(start, index)

    def _trim_trailing_blank_lines(self, start: int, end: int) -> int:
        """Return an end index with trailing blank body lines excluded."""
        index = end
        while index > start + 1 and not self.lines[index - 1].text.strip():
            index -= 1
        return index

    def _entry_end(self, start: int, end: int, base_indent: int) -> int:
        """Return the end index for a convention entry body."""
        index = start + 1
        while index < end:
            text = self.lines[index].text
            if not text.strip() or text_layout.leading_width(text) <= base_indent or self._protected_block_end(index, end) is not None:
                break
            index += 1
        return index

    def _continuation_end(self, start: int, end: int, base_indent: int) -> int:
        """Return the end index for an indented continuation block."""
        index = start + 1
        while index < end:
            text = self.lines[index].text
            if not text.strip():
                break
            indent = text_layout.leading_width(text)
            if indent <= base_indent:
                break
            index += 1
        return index

    def _table_end(self, index: int, end: int) -> int | None:
        """Return the end index for a recognized Markdown or reST table."""
        text = self.lines[index].text
        if "|" in text and index + 1 < end and _MARKDOWN_TABLE_DELIMITER_RE.fullmatch(self.lines[index + 1].text) is not None:
            table_end = index + 2
            while table_end < end and "|" in self.lines[table_end].text:
                table_end += 1
            return table_end
        if _REST_GRID_BORDER_RE.fullmatch(text) is not None:
            table_end = index + 1
            while table_end < end and ("|" in self.lines[table_end].text or _REST_GRID_BORDER_RE.fullmatch(self.lines[table_end].text) is not None):
                table_end += 1
            return table_end
        if _REST_SIMPLE_BORDER_RE.fullmatch(text) is not None:
            table_end = index + 1
            while table_end < end and self.lines[table_end].text.strip():
                table_end += 1
            return table_end
        return None

    def _is_heading(self, index: int, end: int) -> bool:
        """Return whether a line starts an ATX or adornment-style heading."""
        return _ATX_HEADING_RE.match(self.lines[index].text) is not None or (index + 1 < end and bool(self.lines[index].text.strip()) and _is_adornment(self.lines[index + 1].text))


def _parse_docstring(
    value: str, *, settings: settings_check.CheckSettings, source_line_number: int | None, source_indent: int | None, malformed_entry_confidence: _MalformedEntryConfidence
) -> DocstringStructure:
    """Return semantic structure for an evaluated docstring value."""
    return _DocstringParser(value, settings=settings, source_line_number=source_line_number, source_indent=source_indent, malformed_entry_confidence=malformed_entry_confidence).parse()


def _value_lines(value: str, *, source_line_number: int | None, source_indent: int | None) -> tuple[DocstringValueLine, ...]:
    """Split an evaluated value into offset-bearing logical lines."""
    raw_lines: list[tuple[int, int, str]] = []
    start = 0
    while start < len(value):
        newline = re.search(r"\r\n|\r|\n", value[start:])
        end = len(value) if newline is None else start + newline.start()
        raw_lines.append((start, end, value[start:end]))
        if newline is None:
            start = len(value)
        else:
            start += newline.end()
    if not raw_lines:
        raw_lines.append((0, 0, ""))
    margin = source_indent if source_indent is not None else min((text_layout.leading_width(text) for _, _, text in raw_lines[1:] if text.strip()), default=0)
    lines: list[DocstringValueLine] = []
    for index, (line_start, line_end, raw_text) in enumerate(raw_lines):
        if index == 0:
            text_raw_start_column = len(raw_text) - len(raw_text.lstrip(ascii_whitespace.SPACE_AND_TAB))
            text_virtual_prefix_length = 0
            text = raw_text[text_raw_start_column:]
        else:
            text, text_raw_start_column, text_virtual_prefix_length = text_layout.strip_indent_with_mapping(raw_text, margin)
        lines.append(
            DocstringValueLine(
                index=index,
                start_offset=line_start,
                end_offset=line_end,
                raw_text=raw_text,
                text=text,
                raw_indent=raw_text[: len(raw_text) - len(raw_text.lstrip(ascii_whitespace.SPACE_AND_TAB))],
                text_indent=text[: len(text) - len(text.lstrip(ascii_whitespace.SPACE_AND_TAB))],
                text_raw_start_column=text_raw_start_column,
                text_virtual_prefix_length=text_virtual_prefix_length,
                source_line_number=None if source_line_number is None else source_line_number + index,
            )
        )
    return tuple(lines)


def _entry_kind(section_name: str) -> DocstringEntryKind:
    """Return the semantic entry kind for a convention section."""
    normalized = section_name.lower()
    if normalized in docstring_sections.PARAMETER_SECTION_NAMES:
        return DocstringEntryKind.PARAMETER
    if normalized in {"return", "returns"}:
        return DocstringEntryKind.RETURN
    if normalized in {"yield", "yields"}:
        return DocstringEntryKind.YIELD
    if normalized in {"raise", "raises"}:
        return DocstringEntryKind.EXCEPTION
    if normalized in {"warn", "warns"}:
        return DocstringEntryKind.WARNING
    if normalized in {"attribute", "attributes"}:
        return DocstringEntryKind.ATTRIBUTE
    if normalized in {"method", "methods"}:
        return DocstringEntryKind.METHOD
    return DocstringEntryKind.FIELD


def _rest_entry_kind(field: str) -> DocstringEntryKind:
    """Return the semantic entry kind for a reST field name."""
    metadata = docstring_sections.rest_field_metadata(field)
    if metadata is not None:
        return DocstringEntryKind(metadata[0].kind)
    return DocstringEntryKind.FIELD


def _rest_entry_metadata(field: str, argument: str) -> tuple[DocstringEntryKind, tuple[str, ...], str | None]:
    """Return semantic entry kind, names, and type text for a reST field."""
    kind = _rest_entry_kind(field)
    if not argument:
        return kind, (), None
    if kind is DocstringEntryKind.EXCEPTION:
        return kind, _exception_names(argument) or (), None
    if docstring_sections.is_rest_type_field(field):
        return kind, (argument,), None
    if kind is not DocstringEntryKind.PARAMETER:
        return kind, (argument,), None
    parts = argument.rsplit(None, 1)
    if len(parts) == 1:
        return kind, (argument,), None
    type_text, name = parts
    return kind, (name,), type_text


def _rest_name_slots(line_index: int, match: re.Match[str], names: tuple[str, ...]) -> tuple[DocstringNameSlot | None, ...]:
    """Return name slots aligned with a parsed reStructuredText field."""
    argument = match.group("argument")
    if argument is None:
        return (None,) * len(names)
    if len(names) == 1:
        name = names[0]
        name_start = argument.rfind(name)
        if name_start < 0:
            return (None,)
        start_column = match.start("argument") + name_start
        return (DocstringNameSlot(line_index=line_index, start_column=start_column, end_column=start_column + len(name)),)
    return _name_slots_from_text(line_index, argument, names, start_column=match.start("argument"))


def _name_slots_from_text(line_index: int, text: str, names: tuple[str, ...], *, start_column: int = 0) -> tuple[DocstringNameSlot | None, ...]:
    """Return sequential source spans for parsed names within parser-owned text."""
    slots: list[DocstringNameSlot | None] = []
    search_start = 0
    for name in names:
        name_start = text.find(name, search_start)
        if name_start < 0:
            slots.append(None)
            continue
        name_end = name_start + len(name)
        slots.append(DocstringNameSlot(line_index=line_index, start_column=start_column + name_start, end_column=start_column + name_end))
        search_start = name_end
    return tuple(slots)


def _entry_names(kind: DocstringEntryKind, text: str) -> tuple[str, ...] | None:
    """Return parsed entry names for a convention entry."""
    if is_exception_name_entry_kind(kind):
        return _exception_names(text)
    return tuple(part.strip() for part in text.split(","))


def _strict_numpy_names(text: str) -> tuple[str, ...] | None:
    """Return a strict comma-separated NumPy name list."""
    stripped = text.strip()
    if _NUMPY_NAME_LIST_RE.fullmatch(stripped) is None:
        return None
    names = tuple(part.strip() for part in stripped.split(","))
    return names if names and all(_ENTRY_NAME_RE.fullmatch(name) is not None for name in names) else None


def _is_missing_separator_type(text: str) -> bool:
    """Return whether text is a conservative type or quoted forward reference."""
    return type_expressions.is_type_like_text(text) or type_expressions.is_quoted_type_like_text(text)


def _is_numpy_exception_entry(text: str) -> bool:
    """Return whether text is a bare or colon-form NumPy exception entry."""
    match = _NUMPY_EXCEPTION_ENTRY_RE.match(text)
    return _exception_names(match.group("name") if match is not None else text.strip()) is not None


def _google_exception_missing_separator(text: str) -> tuple[tuple[str, ...], int] | None:
    """Return exception-like names and their head end before description text."""
    stripped = text.strip(ascii_whitespace.SPACE_AND_TAB)
    leading = len(text) - len(text.lstrip(ascii_whitespace.SPACE_AND_TAB))
    names: list[str] = []
    position = 0
    while True:
        if position < len(stripped) and stripped[position] == "`":
            closing = stripped.find("`", position + 1)
            if closing < 0:
                return None
            name = stripped[position + 1 : closing]
            if _EXCEPTION_NAME_RE.fullmatch(name) is None:
                return None
            position = closing + 1
        else:
            match = _EXCEPTION_NAME_RE.match(stripped, position)
            if match is None:
                return None
            name = match.group()
            position = match.end()
        names.append(name)
        after_whitespace = position
        while after_whitespace < len(stripped) and stripped[after_whitespace].isspace():
            after_whitespace += 1
        if after_whitespace < len(stripped) and stripped[after_whitespace] in {",", "|"}:
            position = after_whitespace + 1
            while position < len(stripped) and stripped[position].isspace():
                position += 1
            continue
        if after_whitespace == position or after_whitespace == len(stripped):
            return None
        return (tuple(names), leading + position) if all(_is_exception_like_name(name) for name in names) else None


def _exception_names(text: str) -> tuple[str, ...] | None:
    """Return validated exception names from a comma- or pipe-separated entry."""
    stripped = _strip_exception_code_span(text.strip())
    if not stripped:
        return None
    parts = _EXCEPTION_NAME_SEPARATOR_RE.split(stripped)
    names = tuple(_strip_exception_code_span(part.strip()) for part in parts)
    if not names or any(not _EXCEPTION_NAME_RE.fullmatch(name) for name in names):
        return None
    return names


def _is_exception_like_name(name: str) -> bool:
    """Return whether a qualified name has a conventional exception suffix."""
    return name.rpartition(".")[2].endswith(("Error", "Exception", "Warning"))


def _rest_field_arity_issue(field: str, argument: str) -> ConventionEntryIssueKind | None:
    """Return a malformed reStructuredText field arity issue."""
    metadata = docstring_sections.rest_field_metadata(field)
    if metadata is None:
        return None
    argument_policy = metadata[0].argument_policy
    if argument_policy is docstring_sections.RestFieldArgumentPolicy.REQUIRED and not argument:
        return ConventionEntryIssueKind.REST_MISSING_ARGUMENT
    if argument_policy is docstring_sections.RestFieldArgumentPolicy.FORBIDDEN and argument:
        return ConventionEntryIssueKind.REST_UNEXPECTED_ARGUMENT
    return None


def _entry_name_match_is_token(text: str, match: re.Match[str]) -> bool:
    """Return whether an entry-name match occupies one space-delimited token."""
    return (match.start() == 0 or text[match.start() - 1] in ascii_whitespace.SPACE_AND_TAB) and (match.end() == len(text) or text[match.end()] in ascii_whitespace.SPACE_AND_TAB)


def _strip_exception_code_span(text: str) -> str:
    """Return exception text without one surrounding inline-code span."""
    if len(text) >= 2 and text.startswith("`") and text.endswith("`") and "`" not in text[1:-1]:
        return text[1:-1].strip()
    return text


def _google_none_value_entry(kind: DocstringEntryKind, text: str, *, start: int) -> DocstringEntry | None:
    """Return a Google return/yield entry for bare None spellings."""
    if kind not in {DocstringEntryKind.RETURN, DocstringEntryKind.YIELD} or not text[:1].isspace() or text.strip() not in {"None", "None."}:
        return None
    return DocstringEntry(kind=kind, names=(), name_slots=(), type_info=DocstringTypeInfo(text="None", slot=None), description="", description_lines=(), start_line=start, end_line=start + 1)


def _is_adornment(text: str) -> bool:
    """Return whether text is a heading or section adornment line."""
    stripped = text.strip()
    return len(stripped) >= 3 and len(set(stripped)) == 1 and stripped[0] in "-=~`^:#*+"


def _is_doctest_prompt(text: str) -> bool:
    """Return whether text starts with a whitespace-delimited doctest prompt."""
    return text.lstrip().startswith(">>> ")


def is_same_line_closing_delimiter_prefix(docstring: DocstringInfo, line: DocstringValueLine) -> bool:
    """Return whether a value line prefixes same-line closing quotes.

    Args:
        docstring (DocstringInfo): Simple or suite docstring that owns the logical line.
        line (DocstringValueLine): Logical value line to compare against the docstring terminator position.

    Returns:
        True when the line is the final logical line of a non-empty docstring value without a trailing newline.
    """
    return line.index == len(docstring.structure.lines) - 1 and docstring.value != "" and not docstring_value_ends_with_newline(docstring)


def is_safely_mapped_simple_docstring(docstring: DocstringInfo, *, require_multiline: bool = False) -> bool:
    """Return whether a simple docstring is safely mapped by evaluated line.

    Args:
        docstring (DocstringInfo): Docstring candidate whose source mapping must be a LibCST simple string with mapped
            logical lines.
        require_multiline (bool): Whether single-line simple strings should be rejected for callers that only operate on
            multiline layouts.

    Returns:
        bool: Whether every parsed value line maps to concrete source and source-preserving edits can retain spelling.
    """
    return (
        docstring.kind is DocstringKind.SIMPLE
        and isinstance(docstring.node, cst.SimpleString)
        and (not require_multiline or len(docstring.physical_lines) > 1)
        and all(line.source_line_number is not None for line in docstring.structure.lines)
    )


def can_canonically_rewrite_simple_docstring(docstring: DocstringInfo, *, require_multiline: bool = False) -> bool:
    """Return whether a simple docstring permits canonical payload reconstruction.

    Args:
        docstring (DocstringInfo): Docstring candidate whose evaluated lines and Unicode policy must permit rewriting.
        require_multiline (bool): Whether single-line simple strings should be rejected.

    Returns:
        bool: Whether mapped source can be reconstructed without consuming suspicious Unicode.
    """
    return is_safely_mapped_simple_docstring(docstring, require_multiline=require_multiline) and not docstring.has_unicode_rewrite_barrier


def docstring_canonical_margin(docstring: DocstringInfo, *, context: RuleContext, source_lines: Sequence[str] | None = None) -> str:
    """Return the raw indentation margin for continuation and aligned blank lines.

    Args:
        docstring (DocstringInfo): Docstring whose opening source column determines the reusable margin.
        context (RuleContext): Rule context providing file source and indentation settings.
        source_lines (Sequence[str] | None): Optional alternate source text to use after a planned rewrite has been
            applied.

    Returns:
        Raw whitespace prefix that should be used for generated continuation lines in the docstring body.
    """
    lines = source_lines if source_lines is not None else context.source_lines
    source_line = lines[docstring.range.start.line - 1]
    line_indent = source_line[: len(source_line) - len(source_line.lstrip(ascii_whitespace.SPACE_AND_TAB))]
    if isinstance(docstring.statement, cst.SimpleStatementSuite):
        return f"{line_indent}{text_layout.indent_unit(context.settings)}"
    prefix = source_line[: docstring.range.start.column]
    return prefix if prefix.strip() == "" else line_indent


def planned_simple_docstring_line_change(docstring: DocstringInfo, *, raw_line_targets: tuple[str | None, ...]) -> rule_edits.PlannedSourceChange | None:
    """Return one whole-literal replacement for changed raw evaluated lines.

    Args:
        docstring (DocstringInfo): Simple docstring whose logical line bodies may be replaced.
        raw_line_targets (tuple[str | None, ...]): Target raw value text for each logical line, with None preserving the
            existing line.

    Returns:
        Planned replacement for the whole string literal, or None when no line changes or no safe source rendering is available.

    Raises:
        ValueError: Raised when the caller provides a target tuple that does not match the parsed logical line count.
    """
    if len(raw_line_targets) != len(docstring.structure.lines):
        raise ValueError("Raw line targets must match the docstring line count")
    replacements: list[rule_edits.PlannedTextReplacement] = []
    for line, target in zip(docstring.structure.lines, raw_line_targets, strict=True):
        line_number = line.source_line_number
        if target is not None and line_number is not None and line.raw_text != target:
            replacements.append(rule_edits.PlannedTextReplacement(start_offset=line.start_offset, end_offset=line.end_offset, text=target, line_numbers=(line_number,)))
    if not replacements:
        return None
    # Safe simple docstrings map evaluated line text back to source body text modulo newline spelling.
    value_lines = [target if target is not None else line.raw_text for line, target in zip(docstring.structure.lines, raw_line_targets, strict=True)]
    return planned_simple_docstring_source_change(docstring, replacements=tuple(replacements), value_lines=value_lines)


def planned_simple_docstring_source_change(
    docstring: DocstringInfo, *, replacements: tuple[rule_edits.PlannedTextReplacement, ...], value_lines: list[str], source_map: string_literals.SimpleStringSourceMap | None = None
) -> rule_edits.PlannedSourceChange | None:
    """Return one whole-literal replacement from evaluated-value replacements.

    Args:
        docstring (DocstringInfo): Simple docstring whose body source should be rebuilt from evaluated-value edits.
        replacements (tuple[rule_edits.PlannedTextReplacement, ...]): Evaluated-offset replacements that identify
            changed slices and affected source lines.
        value_lines (list[str]): Complete logical value lines after all replacements, used to verify that the rendered
            literal still evaluates correctly.
        source_map (string_literals.SimpleStringSourceMap | None): Optional precomputed lossless source map.

    Returns:
        Planned replacement for the whole string literal, or None when rendering would be unsafe or unchanged.
    """
    if not replacements:
        return None
    source_map = docstring.source_map if source_map is None else source_map
    if source_map is None or not isinstance(docstring.node, cst.SimpleString):
        return None
    value = join_docstring_value_lines(docstring, value_lines)
    body_source = source_map.body_source_with_replacements(tuple((replacement.start_offset, replacement.end_offset, replacement.text) for replacement in replacements))
    rendered = string_literals.render_simple_string_from_body_source(docstring.node.prefix, docstring.node.quote, body_source, expected_value=value)
    if rendered is None or rendered == docstring.source:
        return None
    return rule_edits.PlannedSourceChange(
        edit=rule_edits.SourceEdit(range=docstring.range, replacement=rendered),
        line_numbers=tuple(line_number for replacement in replacements for line_number in replacement.line_numbers),
        suppression_line_numbers=(),
    )


def planned_simple_docstring_text_change(
    docstring: DocstringInfo, *, context: RuleContext, replacement: rule_edits.PlannedTextReplacement, expected_value: str, expected_source: str | None = None, replacement_source: str | None = None
) -> rule_edits.PlannedSourceChange | None:
    """Return one source-slice replacement from an evaluated-value replacement.

    Args:
        docstring (DocstringInfo): Simple docstring whose source body should receive the replacement.
        context (RuleContext): Rule context providing source lines and cached offset bounds.
        replacement (rule_edits.PlannedTextReplacement): Evaluated-offset replacement to map into current source text.
        expected_value (str): Complete evaluated docstring value expected after applying the replacement.
        expected_source (str | None): Optional exact source spelling required for the replaced value slice.
        replacement_source (str | None): Optional source spelling that differs from the evaluated replacement text.

    Returns:
        Planned replacement for the mapped source slice, or None when the source mapping is unsafe.
    """
    line_bounds = line_bounds_for_context(context)
    source_map = docstring.source_map
    if source_map is None or replacement.start_offset < 0 or replacement.end_offset < replacement.start_offset or replacement.end_offset > len(source_map.value):
        return None
    if expected_source is not None and source_map.producing_source_for_value_slice(replacement.start_offset, replacement.end_offset) != expected_source:
        return None
    source_text = replacement.text if replacement_source is None else replacement_source
    replacement_body = source_map.body_source_with_replacements(((replacement.start_offset, replacement.end_offset, source_text),))
    if (
        not isinstance(docstring.node, cst.SimpleString)
        or string_literals.render_simple_string_from_body_source(docstring.node.prefix, docstring.node.quote, replacement_body, expected_value=expected_value) is None
    ):
        return None
    return rule_edits.PlannedSourceChange(
        edit=rule_edits.SourceEdit(
            range=simple_docstring_source_range(docstring, source_map=source_map, start_offset=replacement.start_offset, end_offset=replacement.end_offset, line_bounds=line_bounds),
            replacement=source_text,
        ),
        line_numbers=replacement.line_numbers,
        suppression_line_numbers=(),
    )


def line_bounds_for_context(context: RuleContext) -> source_text.LineBounds:
    """Return cached or derived source line bounds for a rule context.

    Args:
        context (RuleContext): Current source context whose lines should be mapped to absolute offsets.

    Returns:
        source_text.LineBounds: Absolute source offset bounds for each physical source line.
    """
    return context.line_bounds if context.line_bounds is not None else source_text.line_bounds_from_lines(context.source_lines)


def simple_docstring_source_range(
    docstring: DocstringInfo, *, source_map: string_literals.SimpleStringSourceMap, start_offset: int, end_offset: int, line_bounds: source_text.LineBounds
) -> cst_metadata.CodeRange:
    """Return the concrete source range for one evaluated-value slice.

    Args:
        docstring (DocstringInfo): Simple docstring that owns the mapped literal body.
        source_map (string_literals.SimpleStringSourceMap): Lossless map for the docstring body.
        start_offset (int): Evaluated offset where the slice starts.
        end_offset (int): Evaluated offset immediately after the slice.
        line_bounds (source_text.LineBounds): Absolute source bounds for each physical line.

    Returns:
        cst_metadata.CodeRange: Concrete source range matching the evaluated slice.

    Raises:
        TypeError: If the docstring is not a simple string.
    """
    if not isinstance(docstring.node, cst.SimpleString):
        raise TypeError("A simple docstring source range requires a simple string node")
    body_start = source_text.offset_for_position(docstring.range.start, line_bounds=line_bounds) + len(docstring.node.prefix) + len(docstring.node.quote)
    source_start = body_start + source_map.source_offset_for_value_offset(start_offset)
    source_end = source_start if start_offset == end_offset else body_start + source_map.source_offset_for_value_offset(end_offset, include_leading_zero_value_source=True)
    return cst_metadata.CodeRange(start=source_text.position_for_offset(source_start, line_bounds=line_bounds), end=source_text.position_for_offset(source_end, line_bounds=line_bounds))


def simple_docstring_replacement_is_source_safe(docstring: DocstringInfo, replacement: str) -> bool:
    """Return whether replacement source spelling is identical to its evaluated value.

    Args:
        docstring (DocstringInfo): Simple docstring whose quote delimiter constrains replacement spelling.
        replacement (str): Replacement text to insert into the literal source body.

    Returns:
        bool: Whether the replacement can be inserted as source text without changing its evaluated value.
    """
    if not isinstance(docstring.node, cst.SimpleString) or not replacement.isascii() or "\\" in replacement or "\r" in replacement or "\n" in replacement:
        return False
    return docstring.node.quote not in replacement


def planned_simple_docstring_output_change(
    docstring: DocstringInfo,
    *,
    context: RuleContext,
    output_lines: tuple[DocstringOutputLine, ...],
    line_numbers: tuple[int, ...],
    preserve_trailing_newline: bool | None = None,
    separator_fallback: DocstringOutputSeparatorFallback | None = None,
) -> rule_edits.PlannedSourceChange | None:
    """Return one whole-literal replacement from target output lines.

    Args:
        docstring (DocstringInfo): Simple docstring whose full literal source should be replaced.
        context (RuleContext): Rule context providing source line endings and string fragment mapping.
        output_lines (tuple[DocstringOutputLine, ...]): Render-ready line descriptors combining preserved source lines
            and synthesized text.
        line_numbers (tuple[int, ...]): Source lines that should be reported as affected by the resulting change.
        preserve_trailing_newline (bool | None): Optional override for whether the rendered docstring value keeps a
            final newline.
        separator_fallback (DocstringOutputSeparatorFallback | None): Optional strategy for adding boundary spaces when
            adjacent quote delimiters cannot be represented safely.

    Returns:
        Planned whole-literal source change, or None when the docstring is not safely renderable or the rendered source is unchanged.
    """
    if not isinstance(docstring.node, cst.SimpleString):
        return None
    source_map = docstring.source_map
    if source_map is None:
        return None
    keep_trailing_newline = docstring_value_ends_with_newline(docstring) if preserve_trailing_newline is None else preserve_trailing_newline
    body_source = _output_body_source(output_lines, source_map=source_map, line_ending=context.line_ending, preserve_trailing_newline=keep_trailing_newline)
    expected_value = _output_expected_value(output_lines, preserve_trailing_newline=keep_trailing_newline)
    rendered = _render_output_with_separator_fallback(docstring, body_source=body_source, expected_value=expected_value, separator_fallback=separator_fallback)
    if rendered is None or rendered == docstring.source:
        return None
    return rule_edits.PlannedSourceChange(edit=rule_edits.SourceEdit(range=docstring.range, replacement=rendered), line_numbers=line_numbers, suppression_line_numbers=())


def docstring_content_indexes(docstring: DocstringInfo) -> tuple[int, ...]:
    """Return logical line indexes containing non-space-tab text.

    Args:
        docstring (DocstringInfo): Parsed docstring whose logical value lines should be scanned.

    Returns:
        Zero-based logical line indexes that contain content other than spaces or tabs.
    """
    return tuple(line.index for line in docstring.structure.lines if line.text.strip(ascii_whitespace.SPACE_AND_TAB))


def docstring_value_line_numbers(lines: tuple[DocstringValueLine, ...]) -> tuple[int, ...]:
    """Return deduplicated source line numbers for changed logical lines.

    Args:
        lines (tuple[DocstringValueLine, ...]): Logical docstring lines that may map to physical source lines.

    Returns:
        Source line numbers for mapped logical lines, preserving first occurrence order and omitting unmapped lines.
    """
    return tuple(dict.fromkeys(line.source_line_number for line in lines if line.source_line_number is not None))


def docstring_physical_line_numbers(docstring: DocstringInfo) -> tuple[int, ...]:
    """Return physical source lines occupied by a docstring expression.

    Args:
        docstring (DocstringInfo): Docstring expression whose LibCST source range has already been collected.

    Returns:
        Physical source line numbers covered by the complete docstring literal expression.
    """
    return tuple(source_line.line_number for source_line in docstring.physical_lines)


def summary_first_line_targets(docstrings: tuple[DocstringInfo, ...]) -> tuple[SummaryLineTarget, ...]:
    """Return first non-adornment summary lines for parsed top-level summaries from all docstring owners.

    Args:
        docstrings (tuple[DocstringInfo, ...]): Docstrings whose first parsed summary block may produce a rule target.

    Returns:
        Summary targets pointing at the first content line in each top-level summary block.
    """
    targets: list[SummaryLineTarget] = []
    for docstring in docstrings:
        block = first_summary_block(docstring)
        if block is None:
            continue
        line = first_non_adornment_line(docstring, block.start_line, block.end_line)
        if line is not None:
            targets.append(SummaryLineTarget(docstring=docstring, block=block, line=line))
    return tuple(targets)


def summary_terminal_line_targets(docstrings: tuple[DocstringInfo, ...]) -> tuple[SummaryLineTarget, ...]:
    """Return final non-adornment summary lines for parsed top-level summaries.

    Args:
        docstrings (tuple[DocstringInfo, ...]): Docstrings whose first parsed summary block may produce a terminal-line
            target.

    Returns:
        Summary targets pointing at the final content line in each top-level summary block.
    """
    targets: list[SummaryLineTarget] = []
    for docstring in docstrings:
        block = first_summary_block(docstring)
        if block is None:
            continue
        line = final_non_adornment_line(docstring, block.start_line, block.end_line)
        if line is not None:
            targets.append(SummaryLineTarget(docstring=docstring, block=block, line=line))
    return tuple(targets)


def _entry_description_line_targets(docstrings: tuple[DocstringInfo, ...], *, first: bool) -> tuple[EntryDescriptionLineTarget, ...]:
    """Return source-mapped first or final entry-description fragments.

    Args:
        docstrings (tuple[DocstringInfo, ...]): Parsed docstrings whose semantic entries should be inspected.
        first (bool): Whether to target the first fragment instead of the final fragment.

    Returns:
        Entry description targets in docstring and source order.
    """
    targets: list[EntryDescriptionLineTarget] = []
    for docstring in docstrings:
        following_block_kinds = (
            {} if first else {block.entry.start_line: kind for block, kind in _blocks_with_following_nonblank_kind(docstring.structure.blocks, recursive=True) if block.entry is not None}
        )
        for entry in docstring.structure.entries:
            if entry.kind is DocstringEntryKind.FIELD or docstring_sections.is_rest_type_field(entry.field_name) or not entry.description:
                continue
            fragments = tuple(fragment for fragment in entry.description_lines if fragment.text.strip())
            if not fragments:
                continue
            following_kinds = () if first else tuple(kind for kind in (entry.following_description_block_kind, following_block_kinds.get(entry.start_line)) if kind is not None)
            targets.append(EntryDescriptionLineTarget(docstring=docstring, fragment=fragments[0] if first else fragments[-1], following_block_kinds=following_kinds))
    return tuple(targets)


def _blocks_with_following_nonblank_kind(blocks: tuple[DocstringBlock, ...], *, recursive: bool) -> Iterator[tuple[DocstringBlock, DocstringBlockKind]]:
    """Yield blocks paired with their next nonblank sibling kind.

    Args:
        blocks (tuple[DocstringBlock, ...]): Sibling blocks in source order.
        recursive (bool): Whether to inspect every nested sibling group.

    Yields:
        Blocks and the kind of their next nonblank sibling.
    """
    if recursive:
        for block in blocks:
            yield from _blocks_with_following_nonblank_kind(block.children, recursive=True)
    next_nonblank: DocstringBlock | None = None
    for block in reversed(blocks):
        if next_nonblank is not None:
            yield block, next_nonblank.kind
        if block.kind is not DocstringBlockKind.BLANK:
            next_nonblank = block


def first_summary_block(docstring: DocstringInfo) -> DocstringBlock | None:
    """Return the first non-blank block when it can be treated as a top-level summary.

    Args:
        docstring (DocstringInfo): Parsed docstring whose leading blocks should be inspected.

    Returns:
        First non-blank block when it is a summary block or a single standalone colon-ended line, otherwise None.
    """
    non_blank_blocks = tuple(block for block in docstring.structure.blocks if block.kind is not DocstringBlockKind.BLANK)
    if not non_blank_blocks:
        return None
    first_block = non_blank_blocks[0]
    if first_block.kind is DocstringBlockKind.SUMMARY:
        return first_block
    if first_block.kind is DocstringBlockKind.COLON_HEADER and len(non_blank_blocks) == 1:
        return first_block
    return None


def first_non_adornment_line(docstring: DocstringInfo, start: int, end: int) -> DocstringValueLine | None:
    """Return the first non-empty, non-adornment logical line in a summary block.

    Args:
        docstring (DocstringInfo): Docstring that owns the summary block range.
        start (int): Inclusive logical line index where the block begins.
        end (int): Exclusive logical line index where the block ends.

    Returns:
        First content line in the requested range, excluding blank and adornment-only lines.
    """
    for index in range(start, end):
        line = docstring.structure.lines[index]
        if line.text.strip(ascii_whitespace.SPACE_AND_TAB) and not is_adornment(line.text):
            return line
    return None


def final_non_adornment_line(docstring: DocstringInfo, start: int, end: int) -> DocstringValueLine | None:
    """Return the final non-empty, non-adornment logical line in a summary block.

    Args:
        docstring (DocstringInfo): Docstring that owns the summary block range.
        start (int): Inclusive logical line index where the block begins.
        end (int): Exclusive logical line index where the block ends.

    Returns:
        Final content line in the requested range, excluding blank and adornment-only lines.
    """
    for index in range(end - 1, start - 1, -1):
        line = docstring.structure.lines[index]
        if line.text.strip(ascii_whitespace.SPACE_AND_TAB) and not is_adornment(line.text):
            return line
    return None


def docstring_line_numbers(docstring: DocstringInfo, line: DocstringValueLine) -> tuple[int, ...]:
    """Return concrete source lines for a docstring value line.

    Args:
        docstring (DocstringInfo): Docstring whose physical range is used when the logical line lacks a direct source
            mapping.
        line (DocstringValueLine): Logical docstring line being reported by a rule.

    Returns:
        Direct logical line source numbers when available, otherwise the complete physical docstring range.
    """
    if line.source_line_number is not None:
        return docstring_value_line_numbers((line,))
    return docstring_physical_line_numbers(docstring)


def docstring_value_ends_with_newline(docstring: DocstringInfo) -> bool:
    """Return whether an evaluated docstring value ends with a newline.

    Args:
        docstring (DocstringInfo): Docstring whose evaluated Python string value should be checked.

    Returns:
        True when the value ends with any supported newline spelling.
    """
    return docstring.value.endswith(("\r\n", "\r", "\n"))


def _render_output_body_source(docstring: DocstringInfo, *, body_source: str, expected_value: str) -> str | None:
    """Render output body source using the docstring's original literal spelling."""
    if not isinstance(docstring.node, cst.SimpleString):
        return None
    return string_literals.render_simple_string_from_body_source(docstring.node.prefix, docstring.node.quote, body_source, expected_value=expected_value)


def _render_output_with_separator_fallback(docstring: DocstringInfo, *, body_source: str, expected_value: str, separator_fallback: DocstringOutputSeparatorFallback | None) -> str | None:
    """Render output source, applying separator fallback strategy when configured."""
    if separator_fallback is DocstringOutputSeparatorFallback.OPENING:
        return _opening_separator_rendered_output(docstring, body_source=body_source, expected_value=expected_value)
    if separator_fallback is DocstringOutputSeparatorFallback.CLOSING:
        return _closing_separator_rendered_output(docstring, body_source=body_source, expected_value=expected_value)
    if separator_fallback is DocstringOutputSeparatorFallback.BOTH:
        rendered = _render_output_body_source(docstring, body_source=body_source, expected_value=expected_value)
        if rendered is not None:
            return rendered
        fallback_body_source, fallback_expected_value = _separator_fallback_output(body_source, expected_value, separator_fallback=separator_fallback)
        return _render_output_body_source(docstring, body_source=fallback_body_source, expected_value=fallback_expected_value)
    return _render_output_body_source(docstring, body_source=body_source, expected_value=expected_value)


def render_docstring_output_with_separator_fallback(docstring: DocstringInfo, *, body_source: str, expected_value: str, separator_fallback: DocstringOutputSeparatorFallback | None) -> str | None:
    """Render output source, applying a configured separator fallback strategy.

    Args:
        docstring (DocstringInfo): Simple-string docstring whose original literal spelling should be reused.
        body_source (str): Desired literal body source.
        expected_value (str): Evaluated value expected from the rendered output.
        separator_fallback (DocstringOutputSeparatorFallback | None): Optional boundary separator strategy.

    Returns:
        str | None: Full rendered literal source, or None when the output cannot be represented safely.
    """
    return _render_output_with_separator_fallback(docstring, body_source=body_source, expected_value=expected_value, separator_fallback=separator_fallback)


def render_simple_docstring_body_with_separator_fallbacks(docstring: DocstringInfo, *, body_source: str, expected_value: str) -> str | None:
    """Render output source after trying value-preserving quote escapes and separator fallbacks.

    Args:
        docstring (DocstringInfo): Simple-string docstring whose quote style should be kept if possible.
        body_source (str): Desired literal body before escape or separator adjustments.
        expected_value (str): Desired evaluated value before separator fallbacks potentially add boundary spaces.

    Returns:
        First renderable full literal source from the candidate sequence, or None when every candidate is unsafe.
    """
    if not isinstance(docstring.node, cst.SimpleString):
        return None
    for candidate_body, candidate_value in simple_docstring_body_source_candidates(docstring.node, body_source, expected_value=expected_value):
        rendered = _render_output_body_source(docstring, body_source=candidate_body, expected_value=candidate_value)
        if rendered is not None:
            return rendered
    return None


def simple_docstring_body_source_candidates(node: cst.SimpleString, body_source: str, *, expected_value: str) -> Iterator[tuple[str, str]]:
    """Yield source-body candidates ordered by value preservation before separator fallback.

    Args:
        node (cst.SimpleString): Simple-string syntax node whose prefix and delimiter determine which escapes are legal.
        body_source (str): Desired literal body before trying quote escapes or separator spaces.
        expected_value (str): Evaluated value corresponding to the desired body source.

    Yields:
        Candidate body source and the evaluated value expected from rendering it.
    """
    seen: set[tuple[str, str]] = set()

    def candidate_once(candidate: tuple[str, str]) -> Iterator[tuple[str, str]]:
        """Yield a candidate pair only the first time it appears.

        Args:
            candidate (tuple[str, str]): Body-source and expected-value pair produced by an escape or separator
                strategy.

        Yields:
            The candidate pair when it has not already been emitted.
        """
        if candidate not in seen:
            seen.add(candidate)
            yield candidate

    escaped_opening = escaped_opening_quote_body_source(node, body_source)
    escaped_closing = escaped_closing_quote_body_source(node, body_source)
    if escaped_opening is not None:
        escaped_both = escaped_closing_quote_body_source(node, escaped_opening)
        if escaped_both is not None:
            yield from candidate_once((escaped_both, expected_value))
        yield from candidate_once((escaped_opening, expected_value))
    if escaped_closing is not None:
        escaped_closing_opening = escaped_opening_quote_body_source(node, escaped_closing)
        if escaped_closing_opening is not None:
            yield from candidate_once((escaped_closing_opening, expected_value))
        yield from candidate_once((escaped_closing, expected_value))
    yield from candidate_once((body_source, expected_value))
    yield from candidate_once(_separator_fallback_output(body_source, expected_value, separator_fallback=DocstringOutputSeparatorFallback.OPENING))
    yield from candidate_once(_separator_fallback_output(body_source, expected_value, separator_fallback=DocstringOutputSeparatorFallback.CLOSING))
    yield from candidate_once(_separator_fallback_output(body_source, expected_value, separator_fallback=DocstringOutputSeparatorFallback.BOTH))


def _opening_separator_rendered_output(docstring: DocstringInfo, *, body_source: str, expected_value: str) -> str | None:
    """Render output with opening quote separator precedence."""
    rendered = _render_output_body_source(docstring, body_source=body_source, expected_value=expected_value)
    if rendered is None:
        fallback_body_source, fallback_expected_value = _separator_fallback_output(body_source, expected_value, separator_fallback=DocstringOutputSeparatorFallback.OPENING)
        return _render_output_body_source(docstring, body_source=fallback_body_source, expected_value=fallback_expected_value)
    return _opening_quote_separator_output(docstring, body_source=body_source, expected_value=expected_value) or rendered


def _closing_separator_rendered_output(docstring: DocstringInfo, *, body_source: str, expected_value: str) -> str | None:
    """Render output with closing quote separator precedence."""
    rendered = _render_output_body_source(docstring, body_source=body_source, expected_value=expected_value)
    if rendered is not None:
        return rendered
    rendered = _closing_quote_separator_output(docstring, body_source=body_source, expected_value=expected_value)
    if rendered is not None:
        return rendered
    fallback_body_source, fallback_expected_value = _separator_fallback_output(body_source, expected_value, separator_fallback=DocstringOutputSeparatorFallback.CLOSING)
    return _render_output_body_source(docstring, body_source=fallback_body_source, expected_value=fallback_expected_value)


def _opening_quote_separator_output(docstring: DocstringInfo, *, body_source: str, expected_value: str) -> str | None:
    """Render an escaped leading quote to keep opening delimiter and content distinct."""
    if not isinstance(docstring.node, cst.SimpleString):
        return None
    escaped_body_source = escaped_opening_quote_body_source(docstring.node, body_source)
    if escaped_body_source is None:
        return None
    return _render_output_body_source(docstring, body_source=escaped_body_source, expected_value=expected_value)


def escaped_opening_quote_body_source(node: cst.SimpleString, body_source: str) -> str | None:
    """Return body source with a leading delimiter quote escaped where possible.

    Args:
        node (cst.SimpleString): Simple-string node whose raw prefix and delimiter control whether escaping is allowed.
        body_source (str): Literal body source that may start with the delimiter quote character.

    Returns:
        Body source with an inserted leading backslash escape, or None for raw strings and non-conflicting bodies.
    """
    if "r" in node.prefix.lower():
        return None
    quote_char = "'" if "'" in node.quote else '"'
    if not body_source.startswith(quote_char):
        return None
    return f"\\{body_source}"


def escaped_closing_quote_body_source(node: cst.SimpleString, body_source: str) -> str | None:
    """Return body source with trailing delimiter quotes escaped where possible.

    Args:
        node (cst.SimpleString): Simple-string node whose delimiter length limits how many trailing quotes may be
            escaped.
        body_source (str): Literal body source that may end with delimiter quote characters.

    Returns:
        Body source with safe trailing quote escapes, or None when raw-string semantics or the body shape prevent escaping.
    """
    if "r" in node.prefix.lower():
        return None
    quote_char = "'" if "'" in node.quote else '"'
    trailing_quotes = len(body_source) - len(body_source.rstrip(quote_char))
    if trailing_quotes <= 0:
        return None
    escape_count = min(trailing_quotes, len(node.quote) - 1)
    if escape_count <= 0:
        return None
    escaped_quotes = ("\\" + quote_char) * escape_count
    return f"{body_source[:-escape_count]}{escaped_quotes}"


def _closing_quote_separator_output(docstring: DocstringInfo, *, body_source: str, expected_value: str) -> str | None:
    """Render escaped trailing quotes to keep closing delimiter and content distinct."""
    if not isinstance(docstring.node, cst.SimpleString):
        return None
    escaped_body_source = escaped_closing_quote_body_source(docstring.node, body_source)
    if escaped_body_source is None:
        return None
    return _render_output_body_source(docstring, body_source=escaped_body_source, expected_value=expected_value)


def _separator_fallback_output(body_source: str, expected_value: str, *, separator_fallback: DocstringOutputSeparatorFallback) -> tuple[str, str]:
    """Return a one-space separator fallback body and value."""
    if separator_fallback is DocstringOutputSeparatorFallback.OPENING:
        return f" {body_source}", f" {expected_value}"
    if separator_fallback is DocstringOutputSeparatorFallback.CLOSING:
        return f"{body_source} ", f"{expected_value} "
    if separator_fallback is DocstringOutputSeparatorFallback.BOTH:
        return f" {body_source} ", f" {expected_value} "
    raise ValueError(f"Unsupported separator fallback: {separator_fallback!r}")


def _output_body_source(output_lines: tuple[DocstringOutputLine, ...], *, source_map: string_literals.SimpleStringSourceMap, line_ending: str, preserve_trailing_newline: bool) -> str:
    """Return replacement literal body source from output lines."""
    chunks: list[str] = []
    for index, output_line in enumerate(output_lines):
        if index:
            chunks.append(line_ending)
        if output_line.original is None:
            if output_line.source is None:
                raise ValueError("Synthesized output lines require source text")
            chunks.append(output_line.source)
        else:
            chunks.append(docstring_line_source(output_line.original, source_map=source_map, strip_docstring_margin=output_line.strip_docstring_margin))
    if preserve_trailing_newline:
        chunks.append(line_ending)
    return "".join(chunks)


def _output_expected_value(output_lines: tuple[DocstringOutputLine, ...], *, preserve_trailing_newline: bool) -> str:
    """Return replacement evaluated value from output lines."""
    chunks: list[str] = []
    for index, output_line in enumerate(output_lines):
        if index:
            chunks.append("\n")
        if output_line.original is None:
            if output_line.value is None:
                raise ValueError("Synthesized output lines require evaluated text")
            chunks.append(output_line.value)
        elif output_line.strip_docstring_margin:
            chunks.append(output_line.original.text)
        else:
            chunks.append(output_line.original.raw_text)
    if preserve_trailing_newline:
        chunks.append("\n")
    return "".join(chunks)


def docstring_output_expected_value(output_lines: tuple[DocstringOutputLine, ...], *, preserve_trailing_newline: bool) -> str:
    """Return replacement evaluated value from output lines.

    Args:
        output_lines (tuple[DocstringOutputLine, ...]): Render-ready line descriptors for the replacement body.
        preserve_trailing_newline (bool): Whether the output value should end with a final newline.

    Returns:
        str: Evaluated docstring value expected after rendering the output lines.
    """
    return _output_expected_value(output_lines, preserve_trailing_newline=preserve_trailing_newline)


def join_docstring_value_lines(docstring: DocstringInfo, lines: list[str]) -> str:
    """Join replacement logical lines with the original evaluated newline spellings.

    Args:
        docstring (DocstringInfo): Docstring whose evaluated value contains the separators between logical lines.
        lines (list[str]): Replacement logical line text in parsed line order.

    Returns:
        Full evaluated docstring value with caller-provided line text and original inter-line separators.
    """
    chunks: list[str] = []
    for index, (line_info, line) in enumerate(zip(docstring.structure.lines, lines, strict=True)):
        chunks.append(line)
        if index + 1 < len(lines):
            chunks.append(docstring.value[line_info.end_offset : docstring.structure.lines[index + 1].start_offset])
        else:
            chunks.append(docstring.value[line_info.end_offset :])
    return "".join(chunks)


def _docstring_source_indent(statement: cst.SimpleStatementLine | cst.SimpleStatementSuite, *, code_range: cst_metadata.CodeRange, source_lines: Sequence[str], indent_width: int) -> int | None:
    """Return the visual indentation margin for a simple docstring."""
    source_line = source_lines[code_range.start.line - 1]
    if isinstance(statement, cst.SimpleStatementLine) and source_line[: code_range.start.column].strip():
        return None
    source_indent = text_layout.leading_width(source_line)
    return source_indent + indent_width if isinstance(statement, cst.SimpleStatementSuite) else source_indent


@typing.overload
def value_offset_for_text_column(line: DocstringValueLine, column: int, *, require_source_text: typing.Literal[False] = False) -> int: ...


@typing.overload
def value_offset_for_text_column(line: DocstringValueLine, column: int, *, require_source_text: typing.Literal[True]) -> int | None: ...


def value_offset_for_text_column(line: DocstringValueLine, column: int, *, require_source_text: bool = False) -> int | None:
    """Return the evaluated-value offset for a line.text column.

    Args:
        line (DocstringValueLine): Logical docstring line whose visible text column should be translated.
        column (int): Zero-based column within the virtualized text field of the line.
        require_source_text (bool): Whether columns that exist only in virtual indentation should return None instead of
            clamping to the first source-backed character.

    Returns:
        Evaluated-value offset corresponding to the text column, or None when source-backed text is required but the column is outside the raw text span.
    """
    unclamped_raw_column = line.text_raw_start_column + column - line.text_virtual_prefix_length
    if require_source_text and (unclamped_raw_column < line.text_raw_start_column or unclamped_raw_column > len(line.raw_text)):
        return None
    raw_column = line.text_raw_start_column + max(column - line.text_virtual_prefix_length, 0)
    return line.start_offset + raw_column


def _qualified_name(parent: DefinitionInfo, name: str) -> str:
    """Return the qualified name for a child definition."""
    if parent.kind == DefinitionKind.MODULE:
        return name
    return f"{parent.qualified_name}.{name}"


def _docstring_sort_key(docstring: DocstringInfo) -> tuple[int, int]:
    """Return a source-order sort key for collected docstrings."""
    return docstring.range.start.line, docstring.range.start.column


def _docstring_info(
    expression: cst.Expr, statement: cst.SimpleStatementLine | cst.SimpleStatementSuite, *, owner: DocstringOwner, context: RuleCategoryContext, malformed_entry_confidence: _MalformedEntryConfidence
) -> DocstringInfo | None:
    """Return docstring metadata for a string expression."""
    node = expression.value
    if not isinstance(node, (cst.SimpleString, cst.ConcatenatedString)):
        return None
    value = node.evaluated_value
    if not isinstance(value, str):
        return None
    code_range = context.positions[node]
    source = source_text.source_for_range(code_range, source_lines=context.source_lines)
    physical_lines = _physical_lines(code_range, source)
    source_line_number = _simple_docstring_source_line_number(node, value=value, physical_lines=physical_lines, code_range=code_range) if isinstance(node, cst.SimpleString) else None
    return DocstringInfo(
        node=node,
        expression=expression,
        statement=statement,
        owner=owner,
        kind=DocstringKind.SIMPLE if isinstance(node, cst.SimpleString) else DocstringKind.CONCATENATED,
        range=code_range,
        source=source,
        value=value,
        physical_lines=physical_lines,
        value_lines=tuple(value.splitlines()),
        structure=_parse_docstring(
            value,
            settings=context.settings,
            source_line_number=source_line_number,
            source_indent=(
                _docstring_source_indent(statement, code_range=code_range, source_lines=context.source_lines, indent_width=context.settings.indent_width)
                if isinstance(node, cst.SimpleString)
                else None
            ),
            malformed_entry_confidence=malformed_entry_confidence,
        ),
    )


def _malformed_entry_inventories(*, definitions: tuple[DefinitionInfo, ...], attributes: tuple[AttributeInfo, ...]) -> tuple[Mapping[int, frozenset[str]], Mapping[int, frozenset[str]]]:
    """Return direct attribute and method names indexed by parent identity."""
    mutable_attribute_names: dict[int, set[str]] = {}
    for attribute in attributes:
        mutable_attribute_names.setdefault(id(attribute.parent), set()).update(attribute.targets)
    mutable_method_names: dict[int, set[str]] = {}
    for definition in definitions:
        if definition.kind is DefinitionKind.FUNCTION and definition.parent is not None and definition.parent.kind is DefinitionKind.CLASS:
            mutable_method_names.setdefault(id(definition.parent), set()).add(definition.name)
    return (
        MappingProxyType({parent_id: frozenset(names) for parent_id, names in mutable_attribute_names.items()}),
        MappingProxyType({parent_id: frozenset(names) for parent_id, names in mutable_method_names.items()}),
    )


def _malformed_entry_confidence(
    owner: DocstringOwner, *, attribute_names_by_parent_id: Mapping[int, frozenset[str]], method_names_by_parent_id: Mapping[int, frozenset[str]]
) -> _MalformedEntryConfidence:
    """Return owner names usable for high-confidence malformed entry detection."""
    if isinstance(owner, AttributeInfo):
        return _MalformedEntryConfidence(attribute_names=frozenset(owner.targets))
    parameter_names = frozenset(_parameter_names(owner.parameters)) if owner.kind is DefinitionKind.FUNCTION else frozenset()
    attribute_names = attribute_names_by_parent_id.get(id(owner), frozenset()) if owner.kind in {DefinitionKind.MODULE, DefinitionKind.CLASS} else frozenset()
    method_names = method_names_by_parent_id.get(id(owner), frozenset()) if owner.kind is DefinitionKind.CLASS else frozenset()
    return _MalformedEntryConfidence(parameter_names=parameter_names, attribute_names=attribute_names, method_names=method_names)


def _parameter_names(parameters: cst.Parameters | None) -> tuple[str, ...]:
    """Return normalized names from every parameter category."""
    if parameters is None:
        return ()
    raw_parameters = [*parameters.posonly_params, *parameters.params]
    if isinstance(parameters.star_arg, cst.Param):
        raw_parameters.append(parameters.star_arg)
    raw_parameters.extend(parameters.kwonly_params)
    if isinstance(parameters.star_kwarg, cst.Param):
        raw_parameters.append(parameters.star_kwarg)
    return tuple(parameter.name.value for parameter in raw_parameters)


def _attribute_info(statement: cst.BaseSmallStatement, owner: DefinitionInfo, *, context: RuleCategoryContext) -> AttributeInfo | None:
    """Return attribute inventory metadata for supported assignment statements."""
    if not isinstance(statement, (cst.Assign, cst.AnnAssign)):
        return None
    parent = _attribute_parent(owner)
    if parent is None:
        return None
    targets = _assignment_targets(statement, owner, context=context)
    if not targets:
        return None
    names = tuple(target.name for target in targets)
    target_line_numbers = tuple(target.line_numbers for target in targets)
    qualified_names = tuple(_qualified_name(parent, target) for target in names)
    return AttributeInfo(
        node=statement,
        kind=DefinitionKind.ATTRIBUTE,
        name=", ".join(names),
        qualified_name=", ".join(qualified_names),
        parent=parent,
        targets=names,
        line_numbers=tuple(dict.fromkeys(line_number for line_numbers in target_line_numbers for line_number in line_numbers)),
        target_line_numbers=target_line_numbers,
        instance=owner.kind is DefinitionKind.FUNCTION,
    )


def _attribute_parent(owner: DefinitionInfo) -> DefinitionInfo | None:
    """Return the API parent for attributes documented in an owner body."""
    if owner.kind in {DefinitionKind.MODULE, DefinitionKind.CLASS}:
        return owner
    if owner.kind is DefinitionKind.FUNCTION and owner.name == "__init__" and owner.parent is not None and owner.parent.kind is DefinitionKind.CLASS:
        return owner.parent
    return None


def _assignment_targets(statement: cst.Assign | cst.AnnAssign, owner: DefinitionInfo, *, context: RuleCategoryContext) -> tuple[_AttributeTarget, ...]:
    """Return supported attribute targets for an assignment."""
    if isinstance(statement, cst.Assign):
        return tuple(attribute_target for target in statement.targets for attribute_target in _target_attributes(target.target, owner, context=context))
    attribute_target = _target_attribute(statement.target, owner, context=context)
    return (attribute_target,) if attribute_target is not None else ()


def _target_attributes(target: cst.BaseAssignTargetExpression, owner: DefinitionInfo, *, context: RuleCategoryContext) -> tuple[_AttributeTarget, ...]:
    """Return supported attributes from one assignment target."""
    if isinstance(target, cst.Tuple):
        attributes: list[_AttributeTarget] = []
        for element in target.elements:
            attributes.extend(_target_attributes(typing.cast("cst.BaseAssignTargetExpression", element.value), owner, context=context))
        return tuple(attributes)
    attribute_target = _target_attribute(target, owner, context=context)
    return (attribute_target,) if attribute_target is not None else ()


def _target_attribute(target: cst.BaseAssignTargetExpression, owner: DefinitionInfo, *, context: RuleCategoryContext) -> _AttributeTarget | None:
    """Return a supported attribute target."""
    if owner.kind in {DefinitionKind.MODULE, DefinitionKind.CLASS} and isinstance(target, cst.Name):
        return _AttributeTarget(name=target.value, line_numbers=_target_line_numbers(target, context=context))
    if owner.kind is DefinitionKind.FUNCTION and isinstance(target, cst.Attribute) and isinstance(target.value, cst.Name) and target.value.value == "self" and isinstance(target.attr, cst.Name):
        return _AttributeTarget(name=target.attr.value, line_numbers=_target_line_numbers(target.attr, context=context))
    return None


def _target_line_numbers(target: cst.CSTNode, *, context: RuleCategoryContext) -> tuple[int, ...]:
    """Return the source line for an attribute target."""
    return _node_line_numbers(target, context=context)


def _node_line_numbers(node: cst.CSTNode, *, context: RuleCategoryContext) -> tuple[int, ...]:
    """Return the one-based start line for a CST node with a safe fallback."""
    position = context.positions.get(node)
    return (1,) if position is None else (position.start.line,)


def _is_none_expression(expression: cst.BaseExpression) -> bool:
    """Return whether an expression is the literal `None` name."""
    return isinstance(expression, cst.Name) and expression.value == "None"


def _first_expression(body: cst.Module | cst.BaseSuite) -> tuple[cst.Expr, cst.SimpleStatementLine | cst.SimpleStatementSuite] | None:
    """Return the first expression statement in a definition body."""
    if isinstance(body, cst.SimpleStatementSuite):
        if body.body and isinstance(body.body[0], cst.Expr):
            return body.body[0], body
        return None

    statements = body.body
    if not statements or not isinstance(statements[0], cst.SimpleStatementLine):
        return None
    statement = statements[0]
    if statement.body and isinstance(statement.body[0], cst.Expr):
        return statement.body[0], statement
    return None


def _simple_docstring_source_line_number(node: cst.SimpleString, *, value: str, physical_lines: tuple[DocstringLine, ...], code_range: cst_metadata.CodeRange) -> int | None:
    """Return the first source line when evaluated lines map unambiguously."""
    if not string_literals.simple_string_has_direct_line_mapping(node, value=value):
        return None
    logical_line_count = len(_value_lines(value, source_line_number=None, source_indent=None))
    has_separate_trailing_closing_delimiter = value.endswith(("\r\n", "\r", "\n")) and len(physical_lines) == logical_line_count + 1 and physical_lines[-1].source.strip() == node.quote
    if len(physical_lines) != logical_line_count and not has_separate_trailing_closing_delimiter:
        return None
    return code_range.start.line


def _physical_lines(code_range: cst_metadata.CodeRange, source: str) -> tuple[DocstringLine, ...]:
    """Split exact docstring source into physical source-line records."""
    lines = re.split(r"\r\n|\r|\n", source)
    return tuple(
        DocstringLine(
            line_number=code_range.start.line + index,
            start_column=code_range.start.column if index == 0 else 0,
            end_column=code_range.end.column if index == len(lines) - 1 else (code_range.start.column + len(line) if index == 0 else len(line)),
            source=line,
        )
        for index, line in enumerate(lines)
    )
