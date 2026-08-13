"""Settings schema for `pydocfmt check`.

Attributes:
    DEFAULT_EXCLUDE (tuple[str, ...]): Directory names excluded from recursive file discovery unless a caller extends or
        replaces file-selection settings.
    DEFAULT_INCLUDE (tuple[str, ...]): Default filename patterns considered Python or Markdown source during directory
        traversal.
    DEFAULT_RULE_SELECT (tuple[str, ...]): Initial broad rule selector used when users do not provide an explicit
        `select` setting.
    DEFAULT_RULE_FIXABLE (tuple[str, ...]): Initial broad fixability selector used when users do not restrict automatic
        fixes.
    DEFAULT_REQUIRE_EXPLICIT (tuple[str, ...]): Rules that broad selectors skip so projects must opt into certain checks
        deliberately.
    DEFAULT_DOCSTRING_FORBIDDEN_FUNCTION_DECORATORS (tuple[str, ...]): Function decorators whose definitions should not
        have docstrings.
    DEFAULT_DOCSTRING_CLASS_ATTRIBUTE_NO_TYPE_BASE_CLASSES (tuple[str, ...]): Class base names whose attribute entries
        should not include docstring types.
    DEFAULT_DOCSTRING_OPTIONAL_FUNCTION_DECORATORS (tuple[str, ...]): Function decorators whose definitions may omit
        docstrings.
    DEFAULT_DOCSTRING_PLACEHOLDER_MARKERS (tuple[str, ...]): Whole-docstring marker labels recognized as placeholders by
        default.
    DEFAULT_DOCSTRING_PROPERTY_DECORATORS (tuple[str, ...]): Function decorators whose definitions should be treated as
        properties.
    DEFAULT_COMMENT_TASK_MARKERS (tuple[str, ...]): Task marker labels recognized by default in comments.
    PARALLELISM_CONSTRAINT_MESSAGE (str): Shared validation text for the worker-count setting accepted by the check
        command.
    BUILTIN_EXTENSION_LANGUAGES (dict[str, SourceLanguage]): Fixed extension-to-language assignments.
    SETTINGS_SCHEMA (SettingsSchema[CheckSettings]): Complete `pydocfmt check` schema used for config loading, CLI
        option generation, validation, and settings display.
    CHECK_SETTING_DEFINITIONS (tuple[CheckSettingDefinition, ...]): Check setting metadata with co-located clean-proof
        identity roles.
    DIRECT_ANALYSIS_DEFINITIONS (tuple[SettingDefinition[Any], ...]): Schema-ordered setting definitions whose effective
        values determine clean analysis.
"""

# Standard library imports
import re
import enum
import typing
import pathlib
import dataclasses
from typing import Any, TypedDict

# First-party imports
import pydocformatter.settings as settings_core
from pydocformatter.rules.codes import ALL_RULE_SELECTOR_TAG
from pydocformatter.rules.models import SourceContext
from pydocformatter.settings import MultiStringMap, PerFileSettingsMap, SettingCLIValueKind, SettingDefinition, SettingsSchema, StringList, StringMap
from pydocformatter.utils.globs import BaseRelativeGlobMatcher


DEFAULT_EXCLUDE = (
    ".bzr",
    ".direnv",
    ".eggs",
    ".git",
    ".git-rewrite",
    ".hg",
    ".mypy_cache",
    ".nox",
    ".pants.d",
    ".pydocfmt_cache",
    ".pytype",
    ".ruff_cache",
    ".svn",
    ".tox",
    ".venv",
    "__pypackages__",
    "_build",
    "buck-out",
    "dist",
    "node_modules",
    "venv",
)

DEFAULT_INCLUDE = ("*.py", "*.pyi", "*.pyw", "*.md")
DEFAULT_RULE_SELECT = (ALL_RULE_SELECTOR_TAG,)
DEFAULT_RULE_FIXABLE = (ALL_RULE_SELECTOR_TAG,)
DEFAULT_REQUIRE_EXPLICIT = (
    "PCF200",
    "PCF102",
    "PCF103",
    "PDF003",
    "PDF516",
    "PDF517",
    "PDF518",
    "PDF519",
    "PDF520",
    "PDF521",
    "PDF522",
    "PDF524",
    "PDF601",
    "PDF603",
    "PDF605",
    "PDF607",
    "PDF609",
    "PDF611",
    "PDF612",
    "PDF613",
    "PDF615",
)
DEFAULT_DOCSTRING_FORBIDDEN_FUNCTION_DECORATORS = ("typing.overload", "typing_extensions.overload")
DEFAULT_DOCSTRING_CLASS_ATTRIBUTE_NO_TYPE_BASE_CLASSES = ("enum.Enum", "enum.IntEnum", "enum.StrEnum", "enum.Flag", "enum.IntFlag", "enum.ReprEnum")
DEFAULT_DOCSTRING_OPTIONAL_FUNCTION_DECORATORS = ("typing.override", "typing_extensions.override")
DEFAULT_DOCSTRING_PLACEHOLDER_MARKERS = ("TODO", "TBD", "FIXME", "pass", "XXX", "HACK", "NotImplemented", "...")
DEFAULT_DOCSTRING_PROPERTY_DECORATORS = ("builtins.property", "enum.property", "functools.cached_property", "abc.abstractproperty", "types.DynamicClassAttribute")
DEFAULT_COMMENT_TASK_MARKERS = ("TODO", "FIXME", "XXX", "HACK", "BUG", "DEBUG", "NOTE", "OPTIMIZE", "REVIEW")
PARALLELISM_CONSTRAINT_MESSAGE = "must be 0, a fractional value greater than 0 and less than 1, or a whole number greater than or equal to 1"
_MAX_DOCUMENTED_STRING_LIST_DEFAULT_LENGTH = 50
_PLACEHOLDER_MARKER_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")
_TASK_MARKER_RE = re.compile(r"^[A-Z][A-Z0-9_-]*$")
_EXTENSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
_validate_non_negative_float = settings_core.validate_float(min_value=0)


class SourceLanguage(enum.StrEnum):
    """Supported source languages selected from filename extensions.

    Attributes:
        PYTHON: Parse a complete Python source or fragment directly.
        MARKDOWN: Extract and process supported fenced Python blocks from Markdown.
    """

    PYTHON = "python"
    MARKDOWN = "markdown"


BUILTIN_EXTENSION_LANGUAGES = {"py": SourceLanguage.PYTHON, "pyi": SourceLanguage.PYTHON, "pyw": SourceLanguage.PYTHON, "md": SourceLanguage.MARKDOWN}


class IndentStyle(enum.StrEnum):
    """Indentation styles for generated and normalized docstring indentation.

    Attributes:
        SPACE: Use spaces for generated and normalized docstring indentation.
        TAB: Use tabs for generated docstring indentation.
    """

    SPACE = "space"
    TAB = "tab"


class LineEnding(enum.StrEnum):
    """Line ending modes for rewritten files.

    Attributes:
        AUTO: Preserve the first detected line ending in each file, defaulting to LF.
        LF: Rewrite generated lines with LF endings.
        CR_LF: Rewrite generated lines with CRLF endings.
        NATIVE: Rewrite generated lines with the platform-native line ending.
    """

    AUTO = "auto"
    LF = "lf"
    CR_LF = "cr-lf"
    NATIVE = "native"


class DocstringConvention(enum.StrEnum):
    """Conventions used to parse semantic docstring sections.

    Attributes:
        NONE: Disable convention-specific section parsing.
        PEP257: Apply generic PEP 257 style checks without semantic sections.
        GOOGLE: Parse Google-style section headers and entries.
        NUMPY: Parse NumPy-style section headers, underlines, and entries.
        REST: Parse reStructuredText field lists.
    """

    NONE = "none"
    PEP257 = "pep257"
    GOOGLE = "google"
    NUMPY = "numpy"
    REST = "rest"


class DocstringBlankLineStyle(enum.StrEnum):
    """Whitespace styles for blank docstring lines.

    Attributes:
        BLANK: Normalize blank docstring lines to empty lines.
        ALIGNED: Preserve indentation on blank lines so they align with surrounding content.
    """

    BLANK = "blank"
    ALIGNED = "aligned"


class DocstringMissingDocumentation(enum.StrEnum):
    """Activation policies for missing documentation diagnostics.

    Attributes:
        HAS_SECTION: Check only docstrings that already contain a relevant documentation section.
        NON_SUMMARY_DOCSTRINGS: Check docstrings with content beyond a single summary line.
        ALL_DOCSTRINGS: Check every eligible function docstring.
    """

    HAS_SECTION = "has-section"
    NON_SUMMARY_DOCSTRINGS = "non-summary-docstrings"
    ALL_DOCSTRINGS = "all-docstrings"


_MARKDOWN_LANGUAGE_DEFAULTS: tuple[tuple[str, object], ...] = (("source_context", SourceContext.FRAGMENT), ("docstring_missing_documentation", DocstringMissingDocumentation.HAS_SECTION))


class CommentTaskMarkerMode(enum.StrEnum):
    """Treatment modes for recognized comment task markers.

    Attributes:
        NONE: Treat task markers like ordinary comment text.
        NO_WRAP: Normalize recognized task marker units without wrapping their payloads.
        HANGING: Reflow recognized task marker units with hanging continuation indentation.
    """

    NONE = "none"
    NO_WRAP = "no-wrap"
    HANGING = "hanging"


class OutputFormat(enum.StrEnum):
    """Output formats for rule findings.

    Attributes:
        GROUPED: Group diagnostics by file.
    """

    GROUPED = "grouped"


@dataclasses.dataclass(frozen=True)
class CheckSettings:
    """Resolved formatter settings for pydocformatter.

    Attributes:
        output_format (OutputFormat): Output format used for rule findings.
        cache (bool): Whether persistent clean-proof caching is enabled.
        cache_dir (str): Project-relative or source-base-relative persistent cache directory.
        line_length (int): Maximum line length used when wrapping docstrings or comments.
        url_aware_wrapping (bool): Whether destination-bearing tokens activate balanced line selection.
        line_ending (LineEnding): Line ending used when rewriting files.
        indent_style (IndentStyle): Indentation style used for generated and normalized docstring indentation.
        indent_width (int): Number of spaces per generated docstring indentation level, or the visual width of a tab.
        parallelism (float): Number or ratio of logical CPU cores to use for internal file-level parallelism.
        source_context (SourceContext): Whether analyzed Python is a complete module or a standalone fragment.
        docstring_convention (DocstringConvention): Convention used to parse semantic docstring sections.
        docstring_blank_line_style (DocstringBlankLineStyle): Whitespace style used by PDF103 for blank docstring lines.
        docstring_blank_line_after_last_section (bool): Whether PDF108, PDF200, and PDF201 preserve one blank line after
            the last convention section.
        docstring_missing_documentation (DocstringMissingDocumentation): When missing-documentation rules report missing
            documentation.
        docstring_missing_documentation_public_only (bool): Whether broad missing-documentation checks are limited to
            public API definitions.
        docstring_require_init_attribute_documentation (bool): Whether class missing-attribute checks require `self.*`
            attributes assigned in `__init__`.
        docstring_include_assertion_errors (bool): Whether `assert` statements contribute possible `AssertionError`
            occurrences to exception-documentation checks.
        docstring_class_attribute_no_type_base_classes (StringList): Direct class base names whose class attribute
            docstring entries should not include types for PDF713.
        docstring_forbidden_function_decorators (StringList): Exact function decorator names whose definitions should
            not have docstrings.
        docstring_optional_function_decorators (StringList): Exact function decorator names whose definitions may omit
            docstrings.
        docstring_placeholder_markers (StringList): Exact whole-docstring marker labels recognized as placeholders.
        docstring_property_decorators (StringList): Exact function decorator names whose definitions should be treated
            as properties.
        docstring_parse_list_items (bool): Whether list items are parsed as distinct docstring structures.
        docstring_parse_headings (bool): Whether Markdown and reStructuredText headings are parsed.
        docstring_parse_doctests (bool): Whether doctest regions are parsed and protected.
        docstring_parse_code_fences (bool): Whether Markdown fenced code blocks are parsed and protected.
        docstring_parse_block_quotes (bool): Whether Markdown block quotes are parsed as distinct structures.
        docstring_parse_tables (bool): Whether Markdown and reStructuredText tables are parsed and protected.
        docstring_parse_directives (bool): Whether reStructuredText directives and their bodies are parsed.
        docstring_parse_literal_blocks (bool): Whether reStructuredText literal blocks are parsed and protected.
        comment_join_standalone_lines (bool): Whether consecutive standalone prose comment lines are joined before
            wrapping.
        comment_format_list_items (bool): Whether standalone comment list items are detected and reflowed.
        comment_task_marker_mode (CommentTaskMarkerMode): How recognized task-marker comments are treated.
        comment_task_markers (StringList): Exact uppercase task-marker labels recognized before a colon.
        comment_preserve_headings (bool): Whether detected Markdown and reStructuredText comment headings are preserved.
        comment_preserve_doctests (bool): Whether standalone doctest comment regions are preserved.
        comment_preserve_code_fences (bool): Whether fenced code regions in standalone comments are preserved.
        comment_format_block_quotes (bool): Whether Markdown block quotes in standalone comments are detected and
            reflowed.
        comment_preserve_tables (bool): Whether detected Markdown and reStructuredText comment tables are preserved.
        comment_preserve_directives (bool): Whether reStructuredText directives and their indented bodies are preserved.
        comment_trailing_extraction_syntax_aware (bool): Whether trailing-comment extraction avoids syntax-sensitive
            positions.
        comment_trailing_extraction_content_aware (bool): Whether trailing-comment extraction avoids content that is
            unsafe to reinterpret as a standalone comment.
        comment_detect_code (bool): Whether the indentation and leading-keyword heuristic protects standalone comment
            runs.
        comment_detect_statements (bool): Whether parseable Python statements protect standalone comment runs.
        comment_detect_expressions (bool): Whether nontrivial Python expressions protect standalone comment runs.
        select (StringList): Base selected pydocformatter rule selectors.
        ignore (StringList): Rule selectors to ignore.
        extend_select (StringList): Additional selected rule selectors.
        require_explicit (StringList): Rule selectors that require exact rule-code or rule-name selection.
        per_file_ignores (MultiStringMap): File-pattern-specific ignored selectors.
        extend_per_file_ignores (MultiStringMap): Additional file-specific ignores.
        per_file_settings (PerFileSettingsMap): File-pattern-specific formatter setting overrides.
        fixable (StringList): Rule selectors eligible for automatic fixes.
        unfixable (StringList): Rule selectors ineligible for automatic fixes.
        extend_fixable (StringList): Additional fixable rule selectors.
        extension (StringMap): Custom filename extensions mapped to supported source languages.
        include (StringList): Base glob patterns that identify format-eligible files.
        extend_include (StringList): Additional include glob patterns appended to `include`.
        exclude (StringList): Base glob patterns for files or directories to ignore.
        extend_exclude (StringList): Additional exclude glob patterns appended to `exclude`.
        respect_gitignore (bool): Whether discovered files are filtered through `.gitignore`.
        force_exclude (bool): Whether exclude rules apply to explicitly passed paths.
    """

    output_format: OutputFormat = OutputFormat.GROUPED
    cache: bool = True
    cache_dir: str = ".pydocfmt_cache"
    line_length: int = 88
    url_aware_wrapping: bool = True
    line_ending: LineEnding = LineEnding.AUTO
    indent_style: IndentStyle = IndentStyle.SPACE
    indent_width: int = 4
    parallelism: float = 0.0
    source_context: SourceContext = SourceContext.MODULE
    docstring_convention: DocstringConvention = DocstringConvention.PEP257
    docstring_blank_line_style: DocstringBlankLineStyle = DocstringBlankLineStyle.BLANK
    docstring_blank_line_after_last_section: bool = False
    docstring_missing_documentation: DocstringMissingDocumentation = DocstringMissingDocumentation.HAS_SECTION
    docstring_missing_documentation_public_only: bool = True
    docstring_require_init_attribute_documentation: bool = False
    docstring_include_assertion_errors: bool = False
    docstring_class_attribute_no_type_base_classes: StringList = DEFAULT_DOCSTRING_CLASS_ATTRIBUTE_NO_TYPE_BASE_CLASSES
    docstring_forbidden_function_decorators: StringList = DEFAULT_DOCSTRING_FORBIDDEN_FUNCTION_DECORATORS
    docstring_optional_function_decorators: StringList = DEFAULT_DOCSTRING_OPTIONAL_FUNCTION_DECORATORS
    docstring_placeholder_markers: StringList = DEFAULT_DOCSTRING_PLACEHOLDER_MARKERS
    docstring_property_decorators: StringList = DEFAULT_DOCSTRING_PROPERTY_DECORATORS
    docstring_parse_list_items: bool = True
    docstring_parse_headings: bool = True
    docstring_parse_doctests: bool = True
    docstring_parse_code_fences: bool = True
    docstring_parse_block_quotes: bool = True
    docstring_parse_tables: bool = True
    docstring_parse_directives: bool = True
    docstring_parse_literal_blocks: bool = True
    comment_join_standalone_lines: bool = False
    comment_format_list_items: bool = True
    comment_task_marker_mode: CommentTaskMarkerMode = CommentTaskMarkerMode.NO_WRAP
    comment_task_markers: StringList = DEFAULT_COMMENT_TASK_MARKERS
    comment_preserve_headings: bool = True
    comment_preserve_doctests: bool = True
    comment_preserve_code_fences: bool = True
    comment_format_block_quotes: bool = True
    comment_preserve_tables: bool = True
    comment_preserve_directives: bool = True
    comment_trailing_extraction_syntax_aware: bool = True
    comment_trailing_extraction_content_aware: bool = True
    comment_detect_code: bool = False
    comment_detect_statements: bool = True
    comment_detect_expressions: bool = False
    select: StringList = DEFAULT_RULE_SELECT
    ignore: StringList = ()
    extend_select: StringList = ()
    require_explicit: StringList = DEFAULT_REQUIRE_EXPLICIT
    per_file_ignores: MultiStringMap = ()
    extend_per_file_ignores: MultiStringMap = ()
    per_file_settings: PerFileSettingsMap = ()
    fixable: StringList = DEFAULT_RULE_FIXABLE
    unfixable: StringList = ()
    extend_fixable: StringList = ()
    extension: StringMap = ()
    include: StringList = DEFAULT_INCLUDE
    extend_include: StringList = ()
    exclude: StringList = DEFAULT_EXCLUDE
    extend_exclude: StringList = ()
    respect_gitignore: bool = True
    force_exclude: bool = False

    @property
    def include_patterns(self) -> tuple[str, ...]:
        """Final include patterns used by file selection.

        Returns:
            tuple[str, ...]: Base include patterns followed by extension include patterns.
        """
        return self.include + self.extend_include

    @property
    def exclude_patterns(self) -> tuple[str, ...]:
        """Final exclude patterns used by file selection.

        Returns:
            tuple[str, ...]: Base exclude patterns followed by extension exclude patterns.
        """
        return self.exclude + self.extend_exclude


class CheckSettingsOverrides(TypedDict, total=False):
    """Formatter settings supplied by one precedence layer.

    Attributes:
        output_format (OutputFormat): Output format used for rule findings.
        cache (bool): Whether persistent clean-proof caching is enabled.
        cache_dir (str): Project-relative or source-base-relative persistent cache directory.
        line_length (int): Maximum line length used when wrapping docstrings or comments.
        url_aware_wrapping (bool): Whether destination-bearing tokens activate balanced line selection.
        line_ending (LineEnding): Line ending used when rewriting files.
        indent_style (IndentStyle): Indentation style used for generated and normalized docstring indentation.
        indent_width (int): Number of spaces per generated docstring indentation level, or the visual width of a tab.
        parallelism (float): Number or ratio of logical CPU cores to use for internal file-level parallelism.
        source_context (SourceContext): Whether analyzed Python is a complete module or a standalone fragment.
        docstring_convention (DocstringConvention): Convention used to parse semantic docstring sections.
        docstring_blank_line_style (DocstringBlankLineStyle): Whitespace style used by PDF103 for blank docstring lines.
        docstring_blank_line_after_last_section (bool): Whether PDF108, PDF200, and PDF201 preserve one blank line after
            the last convention section.
        docstring_missing_documentation (DocstringMissingDocumentation): When missing-documentation rules report missing
            documentation.
        docstring_missing_documentation_public_only (bool): Whether broad missing-documentation checks are limited to
            public API definitions.
        docstring_require_init_attribute_documentation (bool): Whether class missing-attribute checks require `self.*`
            attributes assigned in `__init__`.
        docstring_include_assertion_errors (bool): Whether `assert` statements contribute possible `AssertionError`
            occurrences to exception-documentation checks.
        docstring_class_attribute_no_type_base_classes (StringList): Direct class base names whose class attribute
            docstring entries should not include types for PDF713.
        docstring_forbidden_function_decorators (StringList): Exact function decorator names whose definitions should
            not have docstrings.
        docstring_optional_function_decorators (StringList): Exact function decorator names whose definitions may omit
            docstrings.
        docstring_placeholder_markers (StringList): Exact whole-docstring marker labels recognized as placeholders.
        docstring_property_decorators (StringList): Exact function decorator names whose definitions should be treated
            as properties.
        docstring_parse_list_items (bool): Whether list items are parsed as distinct docstring structures.
        docstring_parse_headings (bool): Whether Markdown and reStructuredText headings are parsed.
        docstring_parse_doctests (bool): Whether doctest regions are parsed and protected.
        docstring_parse_code_fences (bool): Whether Markdown fenced code blocks are parsed and protected.
        docstring_parse_block_quotes (bool): Whether Markdown block quotes are parsed as distinct structures.
        docstring_parse_tables (bool): Whether Markdown and reStructuredText tables are parsed and protected.
        docstring_parse_directives (bool): Whether reStructuredText directives and their bodies are parsed.
        docstring_parse_literal_blocks (bool): Whether reStructuredText literal blocks are parsed and protected.
        comment_join_standalone_lines (bool): Whether consecutive standalone prose comment lines are joined before
            wrapping.
        comment_format_list_items (bool): Whether standalone comment list items are detected and reflowed.
        comment_task_marker_mode (CommentTaskMarkerMode): How recognized task-marker comments are treated.
        comment_task_markers (StringList): Exact uppercase task-marker labels recognized before a colon.
        comment_preserve_headings (bool): Whether detected Markdown and reStructuredText comment headings are preserved.
        comment_preserve_doctests (bool): Whether standalone doctest comment regions are preserved.
        comment_preserve_code_fences (bool): Whether fenced code regions in standalone comments are preserved.
        comment_format_block_quotes (bool): Whether Markdown block quotes in standalone comments are detected and
            reflowed.
        comment_preserve_tables (bool): Whether detected Markdown and reStructuredText comment tables are preserved.
        comment_preserve_directives (bool): Whether reStructuredText directives and their indented bodies are preserved.
        comment_trailing_extraction_syntax_aware (bool): Whether trailing-comment extraction avoids syntax-sensitive
            positions.
        comment_trailing_extraction_content_aware (bool): Whether trailing-comment extraction avoids content that is
            unsafe to reinterpret as a standalone comment.
        comment_detect_code (bool): Whether the indentation and leading-keyword heuristic protects standalone comment
            runs.
        comment_detect_statements (bool): Whether parseable Python statements protect standalone comment runs.
        comment_detect_expressions (bool): Whether nontrivial Python expressions protect standalone comment runs.
        select (StringList): Base selected pydocformatter rule selectors.
        ignore (StringList): Rule selectors to ignore.
        extend_select (StringList): Additional selected rule selectors.
        require_explicit (StringList): Rule selectors that require exact rule-code or rule-name selection.
        per_file_ignores (MultiStringMap): File-pattern-specific ignored selectors.
        extend_per_file_ignores (MultiStringMap): Additional file-specific ignores.
        per_file_settings (PerFileSettingsMap): File-pattern-specific formatter setting overrides.
        fixable (StringList): Rule selectors eligible for automatic fixes.
        unfixable (StringList): Rule selectors ineligible for automatic fixes.
        extend_fixable (StringList): Additional fixable rule selectors.
        extension (StringMap): Custom filename extensions mapped to supported source languages.
        include (StringList): Base glob patterns that identify format-eligible files.
        extend_include (StringList): Additional include glob patterns appended to `include`.
        exclude (StringList): Base glob patterns for files or directories to ignore.
        extend_exclude (StringList): Additional exclude glob patterns appended to `exclude`.
        respect_gitignore (bool): Whether discovered files are filtered through `.gitignore`.
        force_exclude (bool): Whether exclude rules apply to explicitly passed paths.
    """

    output_format: OutputFormat
    cache: bool
    cache_dir: str
    line_length: int
    url_aware_wrapping: bool
    line_ending: LineEnding
    indent_style: IndentStyle
    indent_width: int
    parallelism: float
    source_context: SourceContext
    docstring_convention: DocstringConvention
    docstring_blank_line_style: DocstringBlankLineStyle
    docstring_blank_line_after_last_section: bool
    docstring_missing_documentation: DocstringMissingDocumentation
    docstring_missing_documentation_public_only: bool
    docstring_require_init_attribute_documentation: bool
    docstring_include_assertion_errors: bool
    docstring_class_attribute_no_type_base_classes: StringList
    docstring_forbidden_function_decorators: StringList
    docstring_optional_function_decorators: StringList
    docstring_placeholder_markers: StringList
    docstring_property_decorators: StringList
    docstring_parse_list_items: bool
    docstring_parse_headings: bool
    docstring_parse_doctests: bool
    docstring_parse_code_fences: bool
    docstring_parse_block_quotes: bool
    docstring_parse_tables: bool
    docstring_parse_directives: bool
    docstring_parse_literal_blocks: bool
    comment_join_standalone_lines: bool
    comment_format_list_items: bool
    comment_task_marker_mode: CommentTaskMarkerMode
    comment_task_markers: StringList
    comment_preserve_headings: bool
    comment_preserve_doctests: bool
    comment_preserve_code_fences: bool
    comment_format_block_quotes: bool
    comment_preserve_tables: bool
    comment_preserve_directives: bool
    comment_trailing_extraction_syntax_aware: bool
    comment_trailing_extraction_content_aware: bool
    comment_detect_code: bool
    comment_detect_statements: bool
    comment_detect_expressions: bool
    select: StringList
    ignore: StringList
    extend_select: StringList
    require_explicit: StringList
    per_file_ignores: MultiStringMap
    extend_per_file_ignores: MultiStringMap
    per_file_settings: PerFileSettingsMap
    fixable: StringList
    unfixable: StringList
    extend_fixable: StringList
    extension: StringMap
    include: StringList
    extend_include: StringList
    exclude: StringList
    extend_exclude: StringList
    respect_gitignore: bool
    force_exclude: bool


class SettingsGroup(enum.StrEnum):
    """Check settings groups used for ordered CLI/help presentation.

    Attributes:
        RUN: Whole-run settings for output and parallel execution.
        FORMATTING: Formatting behavior settings.
        DOCSTRING_FORMATTING: Docstring semantic parsing settings.
        COMMENT_FORMATTING: Comment formatting settings.
        RULE_SELECTION: Rule selection settings.
        FILE_SELECTION: File discovery and filtering settings.
        CONFIGURATION: Settings that affect how other settings are resolved.
    """

    RUN = "Run"
    FORMATTING = "Formatting"
    DOCSTRING_FORMATTING = "Docstring formatting"
    COMMENT_FORMATTING = "Comment formatting"
    RULE_SELECTION = "Rule selection"
    FILE_SELECTION = "File selection"
    CONFIGURATION = "Configuration"


class CacheIdentityRole(enum.StrEnum):
    """Roles of resolved setting fields in persistent clean-proof identity.

    A configuration-relative path must not use the ordinary direct-value role until a canonical semantic-path encoding
    has been designed for its source-base and relocation semantics.

    Attributes:
        DIRECT_ANALYSIS_VALUE: Include the effective value after path-specific configuration is applied.
        FINAL_RULE_CODES: Exclude the raw value after it is represented by successfully resolved final rule codes.
        CLEAN_PROOF_IRRELEVANT: Exclude a value that cannot change whether existing source bytes are finding-free.
        DISCOVERY_ONLY: Exclude a value after file selection has completed.
        APPLIED_CONFIGURATION: Exclude raw configuration after its matching effective values are applied.
    """

    DIRECT_ANALYSIS_VALUE = "direct-analysis-value"
    FINAL_RULE_CODES = "final-rule-codes"
    CLEAN_PROOF_IRRELEVANT = "clean-proof-irrelevant"
    DISCOVERY_ONLY = "discovery-only"
    APPLIED_CONFIGURATION = "applied-configuration"


@dataclasses.dataclass(frozen=True, init=False)
class CheckSettingDefinition(SettingDefinition[Any]):
    """Check setting metadata with its intentional persistent-cache role.

    Attributes:
        cache_identity_role (CacheIdentityRole): How the resolved setting participates in clean-proof identity.
    """

    cache_identity_role: CacheIdentityRole

    def __init__(self, *, cache_identity_role: CacheIdentityRole, **definition: Any) -> None:
        """Initialize generic setting metadata and its required cache identity role.

        Args:
            cache_identity_role (CacheIdentityRole): Intentional persistent-cache role for this setting.
            **definition (Any): Keyword arguments forwarded to the generic setting definition.
        """
        super().__init__(**definition)
        object.__setattr__(self, "cache_identity_role", cache_identity_role)


def validate_parallelism(value: object, context: str) -> float:
    """Validate a file-level parallelism setting.

    Args:
        value (object): Raw parallelism value from configuration or the CLI.
        context (str): User-facing setting label included in validation errors.

    Returns:
        float: Normalized non-negative value accepted by worker-count resolution.

    Raises:
        settings_core.SettingsError: If the value is negative, non-numeric, fractional above one, or otherwise invalid.
    """
    parallelism: float = _validate_non_negative_float(value, context)
    if parallelism > 1 and parallelism % 1 != 0:
        raise settings_core.SettingsError(f"{context} {PARALLELISM_CONSTRAINT_MESSAGE}")
    return parallelism


def validate_comment_task_markers(value: object, context: str) -> StringList:
    """Validate configured comment task marker labels.

    Args:
        value (object): Raw marker-list value from configuration or the CLI.
        context (str): User-facing setting label included in validation errors.

    Returns:
        StringList: Validated marker labels in configured order.

    Raises:
        settings_core.SettingsError: If the value is not a string list, contains duplicate labels, or contains labels
            outside the allowed uppercase marker syntax.
    """
    markers = settings_core.validate_string_list(value, context)
    seen: set[str] = set()
    duplicates: set[str] = set()
    for marker in markers:
        if marker in seen:
            duplicates.add(marker)
        seen.add(marker)
    sorted_duplicates = sorted(duplicates)
    if sorted_duplicates:
        raise settings_core.SettingsError(f"{context} must not contain duplicate markers: {', '.join(sorted_duplicates)}")
    invalid = [marker for marker in markers if _TASK_MARKER_RE.fullmatch(marker) is None]
    if invalid:
        raise settings_core.SettingsError(f"{context} entries must match [A-Z][A-Z0-9_-]*: {', '.join(invalid)}")
    return markers


def validate_docstring_placeholder_markers(value: object, context: str) -> StringList:
    """Validate configured whole-docstring placeholder markers.

    Args:
        value (object): Raw marker-list value from configuration or the CLI.
        context (str): User-facing setting label included in validation errors.

    Returns:
        StringList: Validated marker labels in configured order and spelling.

    Raises:
        settings_core.SettingsError: If the value is not a string list, contains ASCII case-insensitive duplicates, or
            contains an unsupported marker.
    """
    markers = settings_core.validate_string_list(value, context)
    invalid = [marker for marker in markers if marker != "..." and _PLACEHOLDER_MARKER_RE.fullmatch(marker) is None]
    if invalid:
        raise settings_core.SettingsError(f"{context} entries must be '...' or match [A-Za-z][A-Za-z0-9_-]*: {', '.join(invalid)}")
    seen: set[str] = set()
    duplicates: set[str] = set()
    for marker in markers:
        normalized = marker.upper()
        if normalized in seen:
            duplicates.add(marker)
        seen.add(normalized)
    sorted_duplicates = sorted(duplicates, key=lambda marker: (marker.upper(), marker))
    if sorted_duplicates:
        raise settings_core.SettingsError(f"{context} must not contain ASCII case-insensitive duplicate markers: {', '.join(sorted_duplicates)}")
    return markers


def validate_extension_map(value: object, context: str) -> StringMap:
    """Validate and normalize custom extension-to-language assignments.

    Args:
        value (object): Raw table or ordered key/value pairs from one configuration layer.
        context (str): User-facing setting label included in validation errors.

    Returns:
        StringMap: Normalized assignments sorted by extension.

    Raises:
        settings_core.SettingsError: If the mapping shape, extension syntax, language, or uniqueness is invalid.
    """
    if isinstance(value, tuple):
        for item in value:
            if not isinstance(item, tuple) or len(item) != 2:
                raise settings_core.SettingsError(f"{context} entries must be two-item extension/language pairs")
        items = typing.cast("tuple[tuple[object, object], ...]", value)
    elif isinstance(value, dict):
        items = tuple(value.items())
    else:
        raise settings_core.SettingsError(f"{context} must be a table mapping extensions to source languages")

    entries: dict[str, str] = {}
    for raw_extension, raw_language in items:
        if not isinstance(raw_extension, str):
            raise settings_core.SettingsError(f"{context} keys must be strings")
        extension = raw_extension.removeprefix(".")
        if _EXTENSION_RE.fullmatch(extension) is None:
            raise settings_core.SettingsError(f"{context} key {raw_extension!r} must contain one simple filename extension matching [A-Za-z0-9][A-Za-z0-9_-]*")
        normalized = extension.lower()
        if normalized in BUILTIN_EXTENSION_LANGUAGES:
            raise settings_core.SettingsError(f"{context} must not configure built-in extension {raw_extension!r}")
        if normalized in entries:
            raise settings_core.SettingsError(f"{context} contains duplicate extension {raw_extension!r} after normalization")
        if not isinstance(raw_language, str):
            raise settings_core.SettingsError(f"{context}.{raw_extension} must be a string source language")
        try:
            language = SourceLanguage(raw_language)
        except ValueError as error:
            raise settings_core.SettingsError(f"{context}.{raw_extension} must be one of {{'python', 'markdown'}}") from error
        entries[normalized] = language.value
    return tuple(sorted(entries.items()))


def source_language_for_path(path: str, extension: StringMap) -> SourceLanguage | None:
    """Return the source language assigned to a path, if any.

    Args:
        path (str): Display or filesystem path whose final suffix selects its language.
        extension (StringMap): Normalized custom extension assignments.

    Returns:
        SourceLanguage | None: Built-in or configured source language, Python for bare stdin, or None when unmapped.
    """
    if path == "-":
        return SourceLanguage.PYTHON
    suffix = pathlib.PurePath(path).suffix
    if not suffix:
        return None
    normalized = suffix[1:].lower()
    builtin = BUILTIN_EXTENSION_LANGUAGES.get(normalized)
    if builtin is not None:
        return builtin
    return next((SourceLanguage(language) for configured_extension, language in extension if configured_extension == normalized), None)


def unknown_source_language_error(path: str) -> str:
    """Return the operational error for a selected path without a language mapping.

    Args:
        path (str): Selected display path whose suffix has no language assignment.

    Returns:
        str: Actionable per-file language-assignment error.
    """
    suffix = pathlib.PurePath(path).suffix
    extension = suffix or "<none>"
    return f"Cannot determine the source language for {path}: extension {extension!r} is not built in or mapped by the extension setting"


def validate_per_file_settings(value: object, context: str) -> PerFileSettingsMap:
    """Validate and return per-file formatter setting overrides.

    Args:
        value (object): Raw per-file settings table from TOML or normalized internal overrides.
        context (str): User-facing setting label included in validation errors.

    Returns:
        PerFileSettingsMap: Ordered pattern-to-setting mapping with validated public setting keys and values.

    Raises:
        settings_core.SettingsError: If the mapping shape, pattern, setting key, setting value, or per-file eligibility
            is invalid.
    """
    if isinstance(value, tuple):
        items = typing.cast("tuple[tuple[object, object], ...]", value)
    elif isinstance(value, dict):
        items = tuple(value.items())
    else:
        raise settings_core.SettingsError(f"{context} must be a table mapping strings to setting tables")

    definitions_by_key = _definitions_by_key()
    allowed_fields = _per_file_settings_allowed_fields()
    entries: list[tuple[str, tuple[tuple[str, object], ...]]] = []
    for pattern, raw_updates in items:
        if not isinstance(pattern, str):
            raise settings_core.SettingsError(f"{context} keys must be strings")
        if not pattern:
            raise settings_core.SettingsError(f"{context} keys must not be empty")
        if isinstance(raw_updates, tuple):
            raw_update_items: dict[str, object] = {}
            for raw_key, raw_value in typing.cast("tuple[tuple[object, object], ...]", raw_updates):
                if not isinstance(raw_key, str):
                    raise settings_core.SettingsError(f"{context}.{pattern} keys must be strings")
                raw_update_items[raw_key] = raw_value
        elif isinstance(raw_updates, dict):
            raw_update_items = typing.cast("dict[str, object]", raw_updates)
        else:
            raise settings_core.SettingsError(f"{context}.{pattern} must be a table mapping setting keys to values")
        flattened_updates = settings_core._flatten_prefixed_toml_setting_tables(raw_update_items, prefixes=("docstring", "comment"), context=f"{context}.{pattern}")
        if not flattened_updates:
            raise settings_core.SettingsError(f"{context}.{pattern} must not be empty")
        unknown_keys = [key for key in flattened_updates if key not in definitions_by_key]
        if unknown_keys:
            unknown_keys.sort()
            raise settings_core.SettingsError(f"{context}.{pattern} contains unknown setting(s): {', '.join(unknown_keys)}")

        updates: list[tuple[str, object]] = []
        for key, raw_value in flattened_updates.items():
            definition = definitions_by_key[key]
            if definition.field not in allowed_fields:
                raise settings_core.SettingsError(f"{context}.{pattern}.{key} cannot be configured in per-file-settings")
            updates.append((key, definition.validator(raw_value, f"{context}.{pattern}.{key}")))
        entries.append((pattern, tuple(updates)))
    return tuple(entries)


def effective_profile_for_path(profile: settings_core.SettingsProfile[CheckSettings], path: str) -> settings_core.SettingsProfile[CheckSettings]:
    """Return a settings profile after applying language and per-file settings.

    Args:
        profile (settings_core.SettingsProfile[CheckSettings]): Base settings profile resolved for file and rule
            selection.
        path (str): Display or filesystem path used to match per-file setting patterns.

    Returns:
        settings_core.SettingsProfile[CheckSettings]: Effective formatter settings profile for `path`, or the original
            profile when no language or per-file override applies.
    """
    source_language = source_language_for_path(path, profile.settings.extension)
    language_updates = {field: value for field, value in language_default_updates(source_language) if profile.priority_for_field(field) <= settings_core.CONFIG_FILE_SOURCE_PRIORITY}
    if language_updates:
        profile = dataclasses.replace(profile, settings=dataclasses.replace(profile.settings, **typing.cast("Any", language_updates)))

    if not profile.settings.per_file_settings:
        return profile

    definitions_by_key = _definitions_by_key()
    per_file_settings_priority = profile.priority_for_field("per_file_settings")
    per_file_settings_base = profile.base_for_field("per_file_settings")
    updates: dict[str, object] = {}
    for pattern, pattern_updates in profile.settings.per_file_settings:
        if not _per_file_settings_pattern_matches(pattern, path, base_path=per_file_settings_base):
            continue
        for key, value in pattern_updates:
            field = definitions_by_key[key].field
            if per_file_settings_priority >= profile.priority_for_field(field):
                updates[field] = value

    if not updates:
        return profile

    field_bases = dict(profile.field_bases)
    field_priorities = dict(profile.field_priorities)
    for field in updates:
        field_bases[field] = per_file_settings_base
        field_priorities[field] = per_file_settings_priority
    return settings_core.SettingsProfile(
        settings=dataclasses.replace(profile.settings, **typing.cast("Any", updates)), field_bases=field_bases, field_priorities=field_priorities, project_root=profile.project_root
    )


def language_default_updates(source_language: SourceLanguage | None) -> tuple[tuple[str, object], ...]:
    """Return automatic setting updates for a resolved source language.

    Args:
        source_language (SourceLanguage | None): Resolved source language, or None for an unmapped path.

    Returns:
        tuple[tuple[str, object], ...]: Field/value updates in stable settings order.
    """
    return _MARKDOWN_LANGUAGE_DEFAULTS if source_language is SourceLanguage.MARKDOWN else ()


def apply_language_defaults(settings: CheckSettings, source_language: SourceLanguage | None) -> CheckSettings:
    """Apply automatic language defaults directly to resolved settings.

    Args:
        settings (CheckSettings): Settings supplied to a direct formatting API.
        source_language (SourceLanguage | None): Resolved source language, or None for an unmapped path.

    Returns:
        CheckSettings: Settings with language defaults applied.
    """
    updates = dict(language_default_updates(source_language))
    return dataclasses.replace(settings, **typing.cast("Any", updates)) if updates else settings


def analysis_settings_identity(profile: settings_core.SettingsProfile[CheckSettings], *, source_language: SourceLanguage = SourceLanguage.PYTHON) -> tuple[tuple[str, object], ...]:
    """Return effective setting names and values that determine clean analysis.

    Args:
        profile (settings_core.SettingsProfile[CheckSettings]): Effective profile after matching per-file settings are
            applied.
        source_language (SourceLanguage): Resolved language used to interpret the selected source.

    Returns:
        tuple[tuple[str, object], ...]: Schema-ordered direct-analysis setting names and normalized effective values.
    """
    return (("source_language", source_language), *(tuple((definition.field, getattr(profile.settings, definition.field)) for definition in DIRECT_ANALYSIS_DEFINITIONS)))


def _definitions_by_key() -> dict[str, SettingDefinition[Any]]:
    """Return TOML setting definitions keyed by public configuration key."""
    return {definition.key: definition for definition in SETTINGS_SCHEMA.definitions if definition.available_in_toml}


def _per_file_settings_allowed_fields() -> frozenset[str]:
    """Return settings fields that may be overridden for matching files."""
    behavior_groups = {SettingsGroup.FORMATTING, SettingsGroup.DOCSTRING_FORMATTING, SettingsGroup.COMMENT_FORMATTING}
    setting_effect_fields = _rule_setting_effect_fields()
    return frozenset(
        definition.field for definition in SETTINGS_SCHEMA.definitions if definition.available_in_toml and definition.group in behavior_groups and definition.field not in setting_effect_fields
    )


def _rule_setting_effect_fields() -> frozenset[str]:
    """Return settings fields referenced by rule selection effects."""
    # First-party imports
    import pydocformatter.rules.collection as rule_collection  # ruff: ignore[import-outside-top-level]

    return frozenset(setting_effects.setting for rule_class in rule_collection.RULE_COLLECTION.rules for setting_effects in rule_class.meta.setting_effects)


def _per_file_settings_pattern_matches(pattern: str, path: str, *, base_path: str) -> bool:
    """Return whether a per-file setting pattern applies to a path."""
    negated = pattern.startswith("!")
    pattern_body = pattern[1:] if negated else pattern
    matcher = BaseRelativeGlobMatcher.compile((pattern_body,), base_path=base_path, match_parent_segments_for_bare=False)
    matched = matcher.matches(path)
    return not matched if negated else matched


def _setting_default_text(field: str, value_type: Any) -> str | None:
    """Return a concise TOML-formatted default value for a settings field."""
    default_text = settings_core.format_value(getattr(CheckSettings(), field), value_type)
    return _documented_default_text(default_text, value_type)


def _documented_default_text(default_text: str, value_type: Any) -> str | None:
    """Return a default value only when it is short enough for prose."""
    if value_type is StringList and len(default_text) > _MAX_DOCUMENTED_STRING_LIST_DEFAULT_LENGTH:
        return None
    return default_text


def _setting_default_clause(field: str, value_type: Any) -> str:
    """Return a concise prose clause describing a settings field default."""
    default_text = _setting_default_text(field, value_type)
    if default_text is None:
        return "has a default value"
    return f"defaults to {default_text}"


SETTINGS_SCHEMA = SettingsSchema(
    settings_type=CheckSettings,
    overrides_type=CheckSettingsOverrides,
    group_type=SettingsGroup,
    definitions=(
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.CLEAN_PROOF_IRRELEVANT,
            field="output_format",
            value_type=OutputFormat,
            group=SettingsGroup.RUN,
            help="Output format for rule findings.",
            documentation='Output format for rule findings; currently only "grouped" is supported.',
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.CLEAN_PROOF_IRRELEVANT,
            field="cache",
            value_type=bool,
            group=SettingsGroup.RUN,
            help="Use persistent clean-proof caching.",
            documentation="Whether selected disk files may reuse and populate persistent clean proofs. Disable this for diagnostics or when a cache location is not trusted.",
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.CLEAN_PROOF_IRRELEVANT,
            field="cache_dir",
            value_type=str,
            group=SettingsGroup.RUN,
            help="Cache directory to create; its immediate parent must exist.",
            validator=settings_core.validate_non_empty_path,
            cli={"metavar": "PATH"},
            documentation="Persistent cache directory. The default is relative to the auto-discovered project configuration root, while explicitly configured values follow their normal setting source base. pydocformatter may create this directory, but it does not create missing ancestor directories; the immediate parent must already be a directory.",
            example='cache-dir = ".pydocfmt_cache"',
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.DIRECT_ANALYSIS_VALUE,
            field="line_length",
            value_type=int,
            group=SettingsGroup.FORMATTING,
            help="Maximum line length for docstrings and comments.",
            validator=settings_core.validate_int(min_value=1, max_value=320),
            cli={"metavar": "LENGTH"},
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.DIRECT_ANALYSIS_VALUE,
            field="url_aware_wrapping",
            value_type=bool,
            group=SettingsGroup.FORMATTING,
            help="Balance wrapping around destination-bearing tokens.",
            documentation="Whether comment and docstring wrapping should balance line selection around destination-bearing tokens; recognized inline markup remains atomic regardless.",
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.DIRECT_ANALYSIS_VALUE,
            field="line_ending",
            value_type=LineEnding,
            group=SettingsGroup.FORMATTING,
            help="Line ending to use when rewriting files.",
            documentation='Line ending to use when rewriting files; one of "auto", "lf", "cr-lf", or "native".',
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.DIRECT_ANALYSIS_VALUE,
            field="indent_style",
            value_type=IndentStyle,
            group=SettingsGroup.FORMATTING,
            help="Indentation style for generated and normalized docstring indentation.",
            documentation='Generated and normalized docstring indentation style; one of "space" or "tab".',
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.DIRECT_ANALYSIS_VALUE,
            field="indent_width",
            value_type=int,
            group=SettingsGroup.FORMATTING,
            help="Indentation width for generated docstring indentation and measurement.",
            validator=settings_core.validate_int(min_value=1, max_value=255),
            cli={"metavar": "WIDTH"},
            documentation="Generated docstring indentation width and tab expansion width used when measuring docstrings and comments.",
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.CLEAN_PROOF_IRRELEVANT,
            field="parallelism",
            value_type=float,
            group=SettingsGroup.RUN,
            help="Number or ratio of logical CPU cores to use for file-level parallelism.",
            validator=validate_parallelism,
            cli={"metavar": "JOBS"},
            documentation="File-level parallelism. Use 0 for all logical CPU cores subject to platform process-pool limits, a whole number greater than or equal to 1 for an exact worker count, or a fractional value greater than 0 and less than 1 for that ratio of logical CPU cores. Small file sets may be slower with parallelism due to process startup overhead.",
            example="parallelism = 0.0",
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.DIRECT_ANALYSIS_VALUE,
            field="source_context",
            value_type=SourceContext,
            group=SettingsGroup.FORMATTING,
            help="Treat source as a complete module or standalone fragment.",
            documentation='Source semantics; use "module" for complete importable Python modules or "fragment" for examples that do not represent a complete module or callable API. Sources assigned to Markdown default to "fragment" after ordinary project configuration; matching per-file settings and inline, command-line, or in-process overrides can opt them into "module".',
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.DIRECT_ANALYSIS_VALUE,
            field="docstring_convention",
            value_type=DocstringConvention,
            group=SettingsGroup.DOCSTRING_FORMATTING,
            help="Convention used to parse semantic docstring sections.",
            documentation='Docstring convention; one of "none", "pep257", "google", "numpy", or "rest".',
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.DIRECT_ANALYSIS_VALUE,
            field="docstring_blank_line_style",
            value_type=DocstringBlankLineStyle,
            group=SettingsGroup.DOCSTRING_FORMATTING,
            help="Whitespace style for blank docstring lines.",
            documentation='Blank docstring line whitespace style used by PDF103; one of "blank" or "aligned".',
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.DIRECT_ANALYSIS_VALUE,
            field="docstring_blank_line_after_last_section",
            value_type=bool,
            group=SettingsGroup.DOCSTRING_FORMATTING,
            help="Keep one blank line after the last docstring section.",
            documentation="Whether PDF108, PDF200, and PDF201 preserve one blank line after the last recognized Google or NumPy docstring section.",
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.DIRECT_ANALYSIS_VALUE,
            field="docstring_missing_documentation",
            value_type=DocstringMissingDocumentation,
            group=SettingsGroup.DOCSTRING_FORMATTING,
            help="When missing-documentation rules report missing documentation.",
            documentation='When missing-documentation rules report missing documentation; one of "has-section", "non-summary-docstrings", or "all-docstrings". Sources assigned to Markdown default to "has-section" after ordinary project configuration; matching per-file settings and inline, command-line, or in-process overrides can select another policy.',
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.DIRECT_ANALYSIS_VALUE,
            field="docstring_missing_documentation_public_only",
            value_type=bool,
            group=SettingsGroup.DOCSTRING_FORMATTING,
            help="Limit broad missing-documentation checks to public API definitions.",
            documentation="Whether broad missing-documentation checks only apply to public API definitions; explicit relevant documentation is always checked for consistency.",
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.DIRECT_ANALYSIS_VALUE,
            field="docstring_require_init_attribute_documentation",
            value_type=bool,
            group=SettingsGroup.DOCSTRING_FORMATTING,
            help="Require documented `__init__` instance attributes.",
            documentation="Whether class missing-attribute documentation rules require supported `self.*` attributes assigned in `__init__`; extraneous class-attribute documentation checks always treat those attributes as present.",
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.DIRECT_ANALYSIS_VALUE,
            field="docstring_include_assertion_errors",
            value_type=bool,
            group=SettingsGroup.DOCSTRING_FORMATTING,
            help="Treat `assert` statements as possible `AssertionError` occurrences.",
            documentation="Whether PDF506 and PDF507 treat every syntactic `assert` statement as a possible `AssertionError`. Assertions can be removed by optimized Python execution, so this option is disabled by default.",
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.DIRECT_ANALYSIS_VALUE,
            field="docstring_class_attribute_no_type_base_classes",
            value_type=StringList,
            group=SettingsGroup.DOCSTRING_FORMATTING,
            help="Direct class base names whose attribute docstring entries should not include types.",
            validator=settings_core.validate_string_list,
            cli={"metavar": "BASE"},
            documentation="Direct class base names whose class attribute docstring entries should not include types for PDF713. Dotted names also match direct import aliases resolved statically by LibCST; unqualified names are syntactic-only, and transitive inheritance is not resolved.",
            example='docstring-class-attribute-no-type-base-classes = ["enum.Enum"]',
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.DIRECT_ANALYSIS_VALUE,
            field="docstring_forbidden_function_decorators",
            value_type=StringList,
            group=SettingsGroup.DOCSTRING_FORMATTING,
            help="Function decorator names whose definitions should not have docstrings.",
            validator=settings_core.validate_non_empty_string_list,
            cli={"metavar": "DECORATOR"},
            documentation="Function decorator names whose definitions should not have docstrings. Calls are unwrapped before matching, and dotted names also match import aliases resolved statically by LibCST; unqualified names are syntactic-only.",
            example='docstring-forbidden-function-decorators = ["typing.overload", "typing_extensions.overload"]',
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.DIRECT_ANALYSIS_VALUE,
            field="docstring_optional_function_decorators",
            value_type=StringList,
            group=SettingsGroup.DOCSTRING_FORMATTING,
            help="Function decorator names whose definitions may omit docstrings.",
            validator=settings_core.validate_non_empty_string_list,
            cli={"metavar": "DECORATOR"},
            documentation="Function decorator names whose definitions may omit docstrings. Calls are unwrapped before matching, and dotted names also match import aliases resolved statically by LibCST; unqualified names are syntactic-only.",
            example='docstring-optional-function-decorators = ["typing.override", "typing_extensions.override"]',
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.DIRECT_ANALYSIS_VALUE,
            field="docstring_placeholder_markers",
            value_type=StringList,
            group=SettingsGroup.DOCSTRING_FORMATTING,
            help="Whole-docstring marker labels recognized as placeholders.",
            validator=validate_docstring_placeholder_markers,
            cli={"metavar": "MARKER"},
            documentation=f"Whole-docstring placeholder markers recognized by PDF213 after ASCII case-insensitive label matching and narrow terminal-punctuation normalization; {_setting_default_clause('docstring_placeholder_markers', StringList)}. Use an empty list to suppress placeholder findings without changing rule selection.",
            example='docstring-placeholder-markers = ["TODO", "NotImplemented", "..."]',
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.DIRECT_ANALYSIS_VALUE,
            field="docstring_property_decorators",
            value_type=StringList,
            group=SettingsGroup.DOCSTRING_FORMATTING,
            help="Function decorator names whose definitions should be treated as properties.",
            validator=settings_core.validate_non_empty_string_list,
            cli={"metavar": "DECORATOR"},
            documentation="Function decorator names whose definitions should be treated as properties for property-specific summary checks. Calls are unwrapped before matching, and dotted names also match import aliases and builtins resolved statically by LibCST; unqualified names are syntactic-only.",
            example='docstring-property-decorators = ["builtins.property", "functools.cached_property", "project.Property"]',
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.DIRECT_ANALYSIS_VALUE,
            field="docstring_parse_list_items",
            value_type=bool,
            group=SettingsGroup.DOCSTRING_FORMATTING,
            help="Parse docstring list items as distinct structures.",
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.DIRECT_ANALYSIS_VALUE,
            field="docstring_parse_headings",
            value_type=bool,
            group=SettingsGroup.DOCSTRING_FORMATTING,
            help="Parse Markdown and reStructuredText docstring headings.",
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.DIRECT_ANALYSIS_VALUE,
            field="docstring_parse_doctests",
            value_type=bool,
            group=SettingsGroup.DOCSTRING_FORMATTING,
            help="Parse and protect doctest regions in docstrings.",
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.DIRECT_ANALYSIS_VALUE,
            field="docstring_parse_code_fences",
            value_type=bool,
            group=SettingsGroup.DOCSTRING_FORMATTING,
            help="Parse and protect fenced code blocks in docstrings.",
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.DIRECT_ANALYSIS_VALUE,
            field="docstring_parse_block_quotes",
            value_type=bool,
            group=SettingsGroup.DOCSTRING_FORMATTING,
            help="Parse Markdown block quotes in docstrings.",
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.DIRECT_ANALYSIS_VALUE,
            field="docstring_parse_tables",
            value_type=bool,
            group=SettingsGroup.DOCSTRING_FORMATTING,
            help="Parse and protect Markdown and reStructuredText tables in docstrings.",
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.DIRECT_ANALYSIS_VALUE,
            field="docstring_parse_directives",
            value_type=bool,
            group=SettingsGroup.DOCSTRING_FORMATTING,
            help="Parse reStructuredText directives and their bodies in docstrings.",
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.DIRECT_ANALYSIS_VALUE,
            field="docstring_parse_literal_blocks",
            value_type=bool,
            group=SettingsGroup.DOCSTRING_FORMATTING,
            help="Parse and protect reStructuredText literal blocks in docstrings.",
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.DIRECT_ANALYSIS_VALUE,
            field="comment_join_standalone_lines",
            value_type=bool,
            group=SettingsGroup.COMMENT_FORMATTING,
            help="Join consecutive standalone prose comment lines before wrapping.",
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.DIRECT_ANALYSIS_VALUE,
            field="comment_format_list_items",
            value_type=bool,
            group=SettingsGroup.COMMENT_FORMATTING,
            help="Detect and reflow standalone comment list items with hanging indentation.",
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.DIRECT_ANALYSIS_VALUE,
            field="comment_task_marker_mode",
            value_type=CommentTaskMarkerMode,
            group=SettingsGroup.COMMENT_FORMATTING,
            help="Treatment for recognized task-marker comments.",
            documentation='Treatment for recognized task-marker comments; one of "none", "no-wrap", or "hanging".',
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.DIRECT_ANALYSIS_VALUE,
            field="comment_task_markers",
            value_type=StringList,
            group=SettingsGroup.COMMENT_FORMATTING,
            help="Task marker labels recognized before a colon.",
            validator=validate_comment_task_markers,
            cli={"metavar": "MARKER"},
            documentation=f"Exact uppercase task marker labels recognized before a colon; {_setting_default_clause('comment_task_markers', StringList)}. Use an empty list to disable recognition.",
            example='comment-task-markers = ["TODO", "FIXME", "BUG"]',
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.DIRECT_ANALYSIS_VALUE,
            field="comment_preserve_headings",
            value_type=bool,
            group=SettingsGroup.COMMENT_FORMATTING,
            help="Preserve detected Markdown and reStructuredText comment headings.",
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.DIRECT_ANALYSIS_VALUE,
            field="comment_preserve_doctests",
            value_type=bool,
            group=SettingsGroup.COMMENT_FORMATTING,
            help="Preserve standalone doctest comment regions.",
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.DIRECT_ANALYSIS_VALUE,
            field="comment_preserve_code_fences",
            value_type=bool,
            group=SettingsGroup.COMMENT_FORMATTING,
            help="Preserve fenced code regions in standalone comments.",
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.DIRECT_ANALYSIS_VALUE,
            field="comment_format_block_quotes",
            value_type=bool,
            group=SettingsGroup.COMMENT_FORMATTING,
            help="Detect and reflow Markdown block quotes in standalone comments.",
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.DIRECT_ANALYSIS_VALUE,
            field="comment_preserve_tables",
            value_type=bool,
            group=SettingsGroup.COMMENT_FORMATTING,
            help="Preserve detected Markdown and reStructuredText comment tables.",
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.DIRECT_ANALYSIS_VALUE,
            field="comment_preserve_directives",
            value_type=bool,
            group=SettingsGroup.COMMENT_FORMATTING,
            help="Preserve reStructuredText directives and their indented bodies.",
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.DIRECT_ANALYSIS_VALUE,
            field="comment_trailing_extraction_syntax_aware",
            value_type=bool,
            group=SettingsGroup.COMMENT_FORMATTING,
            help="Avoid extracting trailing comments from syntax-sensitive positions.",
            documentation="Whether overlong trailing-comment extraction avoids decorators, compound statement headers, arguments, and parenthesized or continuation contexts.",
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.DIRECT_ANALYSIS_VALUE,
            field="comment_trailing_extraction_content_aware",
            value_type=bool,
            group=SettingsGroup.COMMENT_FORMATTING,
            help="Avoid extracting trailing comments with unsafe standalone content.",
            documentation="Whether overlong trailing-comment extraction avoids content that enabled standalone comment structure and code detectors, or the content-aware operator heuristic, would make unsafe to reinterpret as a standalone comment.",
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.DIRECT_ANALYSIS_VALUE,
            field="comment_detect_code",
            value_type=bool,
            group=SettingsGroup.COMMENT_FORMATTING,
            help="Protect standalone runs matching the indentation and leading-keyword heuristic.",
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.DIRECT_ANALYSIS_VALUE,
            field="comment_detect_statements",
            value_type=bool,
            group=SettingsGroup.COMMENT_FORMATTING,
            help="Protect standalone runs containing parseable Python statements.",
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.DIRECT_ANALYSIS_VALUE,
            field="comment_detect_expressions",
            value_type=bool,
            group=SettingsGroup.COMMENT_FORMATTING,
            help="Protect standalone runs containing nontrivial Python expressions.",
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.FINAL_RULE_CODES,
            field="select",
            value_type=StringList,
            group=SettingsGroup.RULE_SELECTION,
            help="Comma-separated rule selector(s) to enable.",
            validator=settings_core.validate_non_empty_string_list,
            cli={"metavar": "RULE"},
            documentation=f"Rule selectors to enable; {_setting_default_clause('select', StringList)}.",
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.FINAL_RULE_CODES,
            field="ignore",
            value_type=StringList,
            group=SettingsGroup.RULE_SELECTION,
            help="Comma-separated rule selector(s) to ignore.",
            validator=settings_core.validate_non_empty_string_list,
            cli={"metavar": "RULE"},
            documentation="Rule selectors to ignore.",
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.FINAL_RULE_CODES,
            field="extend_select",
            value_type=StringList,
            group=SettingsGroup.RULE_SELECTION,
            help="Comma-separated additional rule selector(s) to enable.",
            validator=settings_core.validate_non_empty_string_list,
            cli={"metavar": "RULE"},
            documentation="Additional rule selectors to enable.",
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.FINAL_RULE_CODES,
            field="require_explicit",
            value_type=StringList,
            group=SettingsGroup.RULE_SELECTION,
            help="Comma-separated rule selector(s) that require exact rule-code or rule-name selection.",
            validator=settings_core.validate_non_empty_string_list,
            cli={"metavar": "RULE"},
            documentation=f"Rule selectors that broad rule selectors do not enable unless an exact rule-code or rule-name selector also participates; {_setting_default_clause('require_explicit', StringList)}.",
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.FINAL_RULE_CODES,
            field="per_file_ignores",
            value_type=MultiStringMap,
            group=SettingsGroup.RULE_SELECTION,
            help="TOML inline table mapping file patterns to ignored rule selectors.",
            cli={"metavar": "RULE_TOML"},
            documentation="File-pattern-specific ignored rule selectors.",
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.FINAL_RULE_CODES,
            field="extend_per_file_ignores",
            value_type=MultiStringMap,
            group=SettingsGroup.RULE_SELECTION,
            help="TOML inline table mapping file patterns to additional ignored rule selectors.",
            cli={"metavar": "RULE_TOML"},
            documentation="Additional file-pattern-specific ignored rule selectors.",
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.APPLIED_CONFIGURATION,
            field="per_file_settings",
            value_type=PerFileSettingsMap,
            group=SettingsGroup.CONFIGURATION,
            help="TOML table mapping file patterns to formatter setting overrides.",
            available_in_cli=False,
            validator=validate_per_file_settings,
            documentation="File-pattern-specific formatter setting overrides. Rule-selection, file-selection, run-level, and rule-selection-effect settings cannot be overridden per file.",
            example='[tool.pydocfmt.per-file-settings]\n"tests/**/*.py" = { docstring-missing-documentation = "has-section" }',
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.CLEAN_PROOF_IRRELEVANT,
            field="fixable",
            value_type=StringList,
            group=SettingsGroup.RULE_SELECTION,
            help="Comma-separated rule selector(s) eligible for automatic fixes.",
            validator=settings_core.validate_non_empty_string_list,
            cli={"metavar": "RULE"},
            documentation=f"Rule selectors eligible for automatic fixes; {_setting_default_clause('fixable', StringList)}.",
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.CLEAN_PROOF_IRRELEVANT,
            field="unfixable",
            value_type=StringList,
            group=SettingsGroup.RULE_SELECTION,
            help="Comma-separated rule selector(s) ineligible for automatic fixes.",
            validator=settings_core.validate_non_empty_string_list,
            cli={"metavar": "RULE"},
            documentation="Rule selectors ineligible for automatic fixes.",
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.CLEAN_PROOF_IRRELEVANT,
            field="extend_fixable",
            value_type=StringList,
            group=SettingsGroup.RULE_SELECTION,
            help="Comma-separated additional rule selector(s) eligible for automatic fixes.",
            validator=settings_core.validate_non_empty_string_list,
            cli={"metavar": "RULE"},
            documentation="Additional rule selectors eligible for automatic fixes.",
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.APPLIED_CONFIGURATION,
            field="extension",
            value_type=StringMap,
            group=SettingsGroup.FILE_SELECTION,
            help="Map a custom filename extension to a source language.",
            validator=validate_extension_map,
            cli={"action": "append", "metavar": "EXT:LANGUAGE", "value_kind": SettingCLIValueKind.EXTENSION_MAP, "show_default": False},
            documentation='Custom filename extensions mapped to "python" or "markdown". Extension keys are ASCII case-insensitive and may have one leading dot. This setting assigns languages but does not add files to directory discovery.',
            example='[tool.pydocfmt.extension]\nrpy = "python"\nmdx = "markdown"',
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.DISCOVERY_ONLY,
            field="include",
            value_type=StringList,
            group=SettingsGroup.FILE_SELECTION,
            help="Comma-separated glob pattern(s) for files to include.",
            validator=settings_core.validate_non_empty_string_list,
            cli={"metavar": "GLOB"},
            documentation="Glob patterns for files to include.",
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.DISCOVERY_ONLY,
            field="extend_include",
            value_type=StringList,
            group=SettingsGroup.FILE_SELECTION,
            help="Comma-separated additional glob pattern(s) for files to include.",
            validator=settings_core.validate_non_empty_string_list,
            cli={"metavar": "GLOB"},
            documentation="Additional include glob patterns.",
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.DISCOVERY_ONLY,
            field="exclude",
            value_type=StringList,
            group=SettingsGroup.FILE_SELECTION,
            help="Comma-separated glob pattern(s) for files or directories to exclude.",
            validator=settings_core.validate_non_empty_string_list,
            cli={"metavar": "GLOB"},
            documentation="Glob patterns for files/directories to exclude.",
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.DISCOVERY_ONLY,
            field="extend_exclude",
            value_type=StringList,
            group=SettingsGroup.FILE_SELECTION,
            help="Comma-separated additional glob pattern(s) for files or directories to exclude.",
            validator=settings_core.validate_non_empty_string_list,
            cli={"metavar": "GLOB"},
            documentation="Additional exclude glob patterns.",
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.DISCOVERY_ONLY, field="respect_gitignore", value_type=bool, group=SettingsGroup.FILE_SELECTION, help="Respect .gitignore when discovering files."
        ),
        CheckSettingDefinition(
            cache_identity_role=CacheIdentityRole.DISCOVERY_ONLY,
            field="force_exclude",
            value_type=bool,
            group=SettingsGroup.FILE_SELECTION,
            help="Apply exclude rules even to files passed explicitly.",
        ),
    ),
    table_path=("tool", "pydocfmt"),
)

CHECK_SETTING_DEFINITIONS = tuple(typing.cast("CheckSettingDefinition", definition) for definition in SETTINGS_SCHEMA.definitions)
DIRECT_ANALYSIS_DEFINITIONS = tuple(definition for definition in CHECK_SETTING_DEFINITIONS if definition.cache_identity_role is CacheIdentityRole.DIRECT_ANALYSIS_VALUE)
