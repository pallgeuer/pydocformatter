"""Settings schema for `pydocfmt check`.

Attributes:
    DEFAULT_EXCLUDE (tuple[str, ...]): Directory names excluded from recursive file discovery unless a caller extends or
        replaces file-selection settings.
    DEFAULT_INCLUDE (tuple[str, ...]): Default filename patterns considered Python source during directory traversal.
    DEFAULT_RULE_SELECT (tuple[str, ...]): Initial broad rule selector used when users do not provide an explicit
        `select` setting.
    DEFAULT_RULE_FIXABLE (tuple[str, ...]): Initial broad fixability selector used when users do not restrict automatic
        fixes.
    DEFAULT_REQUIRE_EXPLICIT (tuple[str, ...]): Rules that broad selectors skip so projects must opt into certain checks
        deliberately.
    DEFAULT_DOCSTRING_FORBIDDEN_FUNCTION_DECORATORS (tuple[str, ...]): Function decorators whose definitions should not
        have docstrings.
    DEFAULT_DOCSTRING_OPTIONAL_FUNCTION_DECORATORS (tuple[str, ...]): Function decorators whose definitions may omit
        docstrings.
    DEFAULT_DOCSTRING_PROPERTY_DECORATORS (tuple[str, ...]): Function decorators whose definitions should be treated as
        properties.
    PARALLELISM_CONSTRAINT_MESSAGE (str): Shared validation text for the worker-count setting accepted by the check
        command.
    SETTINGS_SCHEMA (SettingsSchema[CheckSettings]): Complete `pydocfmt check` schema used for config loading, CLI
        option generation, validation, and settings display.
"""

import dataclasses
import enum
from typing import Any, TypedDict, cast

import pydocformatter.settings as settings_core
from pydocformatter.rules.codes import ALL_RULE_SELECTOR_TAG
from pydocformatter.settings import MultiStringMap, PerFileSettingsMap, SettingDefinition, SettingsSchema, StringList
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

DEFAULT_INCLUDE = ("*.py", "*.pyi", "*.pyw")
DEFAULT_RULE_SELECT = (ALL_RULE_SELECTOR_TAG,)
DEFAULT_RULE_FIXABLE = (ALL_RULE_SELECTOR_TAG,)
DEFAULT_REQUIRE_EXPLICIT = ("PCF005", "PDF003", "PDF601", "PDF603", "PDF605", "PDF607", "PDF609", "PDF611", "PDF612", "PDF613", "PDF615")
DEFAULT_DOCSTRING_FORBIDDEN_FUNCTION_DECORATORS = ("overload", "typing.overload", "typing_extensions.overload")
DEFAULT_DOCSTRING_OPTIONAL_FUNCTION_DECORATORS = ("override", "typing.override", "typing_extensions.override")
DEFAULT_DOCSTRING_PROPERTY_DECORATORS = ("property", "builtins.property", "enum.property", "functools.cached_property", "abc.abstractproperty", "types.DynamicClassAttribute")
PARALLELISM_CONSTRAINT_MESSAGE = "must be 0, a fractional value greater than 0 and less than 1, or a whole number greater than or equal to 1"
_validate_non_negative_float = settings_core.validate_float(min_value=0)


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
        line_length (int): Maximum line length used when wrapping docstrings or comments.
        url_aware_wrapping (bool): Whether wrapping balances prose around unbroken URL tokens.
        line_ending (LineEnding): Line ending used when rewriting files.
        indent_style (IndentStyle): Indentation style used for generated and normalized docstring indentation.
        indent_width (int): Number of spaces per generated docstring indentation level, or the visual width of a tab.
        parallelism (float): Number or ratio of logical CPU cores to use for internal file-level parallelism.
        docstring_convention (DocstringConvention): Convention used to parse semantic docstring sections.
        docstring_blank_line_style (DocstringBlankLineStyle): Whitespace style used by PDF103 for blank docstring lines.
        docstring_blank_line_after_last_section (bool): Whether PDF200 and PDF201 keep one blank line after the last
            convention section.
        docstring_missing_documentation (DocstringMissingDocumentation): When missing-documentation rules report missing
            documentation.
        docstring_missing_documentation_public_only (bool): Whether broad missing-documentation checks are limited to
            public API definitions.
        docstring_require_init_attribute_documentation (bool): Whether class missing-attribute checks require `self.*`
            attributes assigned in `__init__`.
        docstring_forbidden_function_decorators (StringList): Exact function decorator names whose definitions should
            not have docstrings.
        docstring_optional_function_decorators (StringList): Exact function decorator names whose definitions may omit
            docstrings.
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
        comment_format_task_markers (bool): Whether task-marker comments are detected and reflowed with hanging
            indentation.
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
        require_explicit (StringList): Rule selectors that require exact rule-code selection.
        per_file_ignores (MultiStringMap): File-pattern-specific ignored selectors.
        extend_per_file_ignores (MultiStringMap): Additional file-specific ignores.
        per_file_settings (PerFileSettingsMap): File-pattern-specific formatter setting overrides.
        fixable (StringList): Rule selectors eligible for automatic fixes.
        unfixable (StringList): Rule selectors ineligible for automatic fixes.
        extend_fixable (StringList): Additional fixable rule selectors.
        include (StringList): Base glob patterns that identify format-eligible files.
        extend_include (StringList): Additional include glob patterns appended to `include`.
        exclude (StringList): Base glob patterns for files or directories to ignore.
        extend_exclude (StringList): Additional exclude glob patterns appended to `exclude`.
        respect_gitignore (bool): Whether discovered files are filtered through `.gitignore`.
        force_exclude (bool): Whether exclude rules apply to explicitly passed paths.
    """

    output_format: OutputFormat = OutputFormat.GROUPED
    line_length: int = 88
    url_aware_wrapping: bool = True
    line_ending: LineEnding = LineEnding.AUTO
    indent_style: IndentStyle = IndentStyle.SPACE
    indent_width: int = 4
    parallelism: float = 0.0
    docstring_convention: DocstringConvention = DocstringConvention.PEP257
    docstring_blank_line_style: DocstringBlankLineStyle = DocstringBlankLineStyle.BLANK
    docstring_blank_line_after_last_section: bool = False
    docstring_missing_documentation: DocstringMissingDocumentation = DocstringMissingDocumentation.HAS_SECTION
    docstring_missing_documentation_public_only: bool = True
    docstring_require_init_attribute_documentation: bool = False
    docstring_forbidden_function_decorators: StringList = DEFAULT_DOCSTRING_FORBIDDEN_FUNCTION_DECORATORS
    docstring_optional_function_decorators: StringList = DEFAULT_DOCSTRING_OPTIONAL_FUNCTION_DECORATORS
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
    comment_format_task_markers: bool = True
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
        line_length (int): Maximum line length used when wrapping docstrings or comments.
        url_aware_wrapping (bool): Whether wrapping balances prose around unbroken URL tokens.
        line_ending (LineEnding): Line ending used when rewriting files.
        indent_style (IndentStyle): Indentation style used for generated and normalized docstring indentation.
        indent_width (int): Number of spaces per generated docstring indentation level, or the visual width of a tab.
        parallelism (float): Number or ratio of logical CPU cores to use for internal file-level parallelism.
        docstring_convention (DocstringConvention): Convention used to parse semantic docstring sections.
        docstring_blank_line_style (DocstringBlankLineStyle): Whitespace style used by PDF103 for blank docstring lines.
        docstring_blank_line_after_last_section (bool): Whether PDF200 and PDF201 keep one blank line after the last
            convention section.
        docstring_missing_documentation (DocstringMissingDocumentation): When missing-documentation rules report missing
            documentation.
        docstring_missing_documentation_public_only (bool): Whether broad missing-documentation checks are limited to
            public API definitions.
        docstring_require_init_attribute_documentation (bool): Whether class missing-attribute checks require `self.*`
            attributes assigned in `__init__`.
        docstring_forbidden_function_decorators (StringList): Exact function decorator names whose definitions should
            not have docstrings.
        docstring_optional_function_decorators (StringList): Exact function decorator names whose definitions may omit
            docstrings.
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
        comment_format_task_markers (bool): Whether task-marker comments are detected and reflowed with hanging
            indentation.
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
        require_explicit (StringList): Rule selectors that require exact rule-code selection.
        per_file_ignores (MultiStringMap): File-pattern-specific ignored selectors.
        extend_per_file_ignores (MultiStringMap): Additional file-specific ignores.
        per_file_settings (PerFileSettingsMap): File-pattern-specific formatter setting overrides.
        fixable (StringList): Rule selectors eligible for automatic fixes.
        unfixable (StringList): Rule selectors ineligible for automatic fixes.
        extend_fixable (StringList): Additional fixable rule selectors.
        include (StringList): Base glob patterns that identify format-eligible files.
        extend_include (StringList): Additional include glob patterns appended to `include`.
        exclude (StringList): Base glob patterns for files or directories to ignore.
        extend_exclude (StringList): Additional exclude glob patterns appended to `exclude`.
        respect_gitignore (bool): Whether discovered files are filtered through `.gitignore`.
        force_exclude (bool): Whether exclude rules apply to explicitly passed paths.
    """

    output_format: OutputFormat
    line_length: int
    url_aware_wrapping: bool
    line_ending: LineEnding
    indent_style: IndentStyle
    indent_width: int
    parallelism: float
    docstring_convention: DocstringConvention
    docstring_blank_line_style: DocstringBlankLineStyle
    docstring_blank_line_after_last_section: bool
    docstring_missing_documentation: DocstringMissingDocumentation
    docstring_missing_documentation_public_only: bool
    docstring_require_init_attribute_documentation: bool
    docstring_forbidden_function_decorators: StringList
    docstring_optional_function_decorators: StringList
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
    comment_format_task_markers: bool
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
    parallelism = _validate_non_negative_float(value, context)
    if parallelism > 1 and not parallelism.is_integer():
        raise settings_core.SettingsError(f"{context} {PARALLELISM_CONSTRAINT_MESSAGE}")
    return parallelism


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
        items = value
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
            raw_update_items: dict[str, object] = dict(raw_updates)
        elif isinstance(raw_updates, dict):
            raw_update_items = raw_updates
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
    """Return a settings profile after applying matching per-file formatter settings.

    Args:
        profile (settings_core.SettingsProfile[CheckSettings]): Base settings profile resolved for file and rule
            selection.
        path (str): Display or filesystem path used to match per-file setting patterns.

    Returns:
        settings_core.SettingsProfile[CheckSettings]: Effective formatter settings profile for `path`, or the original
            profile when no override applies.
    """
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
        settings=dataclasses.replace(profile.settings, **cast(Any, updates)),
        field_bases=field_bases,
        field_priorities=field_priorities,
    )


def _definitions_by_key() -> dict[str, SettingDefinition[Any]]:
    """Return TOML setting definitions keyed by public configuration key."""
    return {definition.key: definition for definition in SETTINGS_SCHEMA.definitions if definition.available_in_toml}


def _per_file_settings_allowed_fields() -> frozenset[str]:
    """Return settings fields that may be overridden for matching files."""
    behavior_groups = {
        SettingsGroup.FORMATTING,
        SettingsGroup.DOCSTRING_FORMATTING,
        SettingsGroup.COMMENT_FORMATTING,
    }
    setting_effect_fields = _rule_setting_effect_fields()
    return frozenset(
        definition.field for definition in SETTINGS_SCHEMA.definitions if definition.available_in_toml and definition.group in behavior_groups and definition.field not in setting_effect_fields
    )


def _rule_setting_effect_fields() -> frozenset[str]:
    """Return settings fields referenced by rule selection effects."""
    import pydocformatter.rules.collection as rule_collection

    return frozenset(setting_effects.setting for rule_class in rule_collection.RULE_COLLECTION.rules for setting_effects in rule_class.meta.setting_effects)


def _per_file_settings_pattern_matches(pattern: str, path: str, *, base_path: str) -> bool:
    """Return whether a per-file setting pattern applies to a path."""
    negated = pattern.startswith("!")
    pattern_body = pattern[1:] if negated else pattern
    matcher = BaseRelativeGlobMatcher.compile((pattern_body,), base_path=base_path, match_parent_segments_for_bare=False)
    matched = matcher.matches(path)
    return not matched if negated else matched


SETTINGS_SCHEMA = SettingsSchema(
    settings_type=CheckSettings,
    overrides_type=CheckSettingsOverrides,
    group_type=SettingsGroup,
    definitions=(
        SettingDefinition(
            field="output_format",
            value_type=OutputFormat,
            group=SettingsGroup.RUN,
            help="Output format for rule findings.",
            documentation='Output format for rule findings; currently only "grouped" is supported.',
        ),
        SettingDefinition(
            field="line_length",
            value_type=int,
            group=SettingsGroup.FORMATTING,
            help="Maximum line length for docstrings and comments.",
            validator=settings_core.validate_int(min_value=1, max_value=320),
            cli={"metavar": "LENGTH"},
        ),
        SettingDefinition(
            field="url_aware_wrapping",
            value_type=bool,
            group=SettingsGroup.FORMATTING,
            help="Balance wrapping around URL tokens without splitting URLs.",
            documentation="Whether comment and docstring wrapping should balance surrounding prose around URL tokens without splitting URLs.",
        ),
        SettingDefinition(
            field="line_ending",
            value_type=LineEnding,
            group=SettingsGroup.FORMATTING,
            help="Line ending to use when rewriting files.",
            documentation='Line ending to use when rewriting files; one of "auto", "lf", "cr-lf", or "native".',
        ),
        SettingDefinition(
            field="indent_style",
            value_type=IndentStyle,
            group=SettingsGroup.FORMATTING,
            help="Indentation style for generated and normalized docstring indentation.",
            documentation='Generated and normalized docstring indentation style; one of "space" or "tab".',
        ),
        SettingDefinition(
            field="indent_width",
            value_type=int,
            group=SettingsGroup.FORMATTING,
            help="Indentation width for generated docstring indentation and measurement.",
            validator=settings_core.validate_int(min_value=1, max_value=255),
            cli={"metavar": "WIDTH"},
            documentation="Generated docstring indentation width and tab expansion width used when measuring docstrings and comments.",
        ),
        SettingDefinition(
            field="parallelism",
            value_type=float,
            group=SettingsGroup.RUN,
            help="Number or ratio of logical CPU cores to use for file-level parallelism.",
            validator=validate_parallelism,
            cli={"metavar": "JOBS"},
            documentation="File-level parallelism. Use 0 for all logical CPU cores subject to platform process-pool limits, a whole number greater than or equal to 1 for an exact worker count, or a fractional value greater than 0 and less than 1 for that ratio of logical CPU cores. Small file sets may be slower with parallelism due to process startup overhead.",
            example="parallelism = 0.0",
        ),
        SettingDefinition(
            field="docstring_convention",
            value_type=DocstringConvention,
            group=SettingsGroup.DOCSTRING_FORMATTING,
            help="Convention used to parse semantic docstring sections.",
            documentation='Docstring convention; one of "none", "pep257", "google", "numpy", or "rest".',
        ),
        SettingDefinition(
            field="docstring_blank_line_style",
            value_type=DocstringBlankLineStyle,
            group=SettingsGroup.DOCSTRING_FORMATTING,
            help="Whitespace style for blank docstring lines.",
            documentation='Blank docstring line whitespace style used by PDF103; one of "blank" or "aligned".',
        ),
        SettingDefinition(
            field="docstring_blank_line_after_last_section",
            value_type=bool,
            group=SettingsGroup.DOCSTRING_FORMATTING,
            help="Keep one blank line after the last docstring section.",
            documentation="Whether PDF200 and PDF201 keep one blank line after the last recognized Google or NumPy docstring section.",
        ),
        SettingDefinition(
            field="docstring_missing_documentation",
            value_type=DocstringMissingDocumentation,
            group=SettingsGroup.DOCSTRING_FORMATTING,
            help="When missing-documentation rules report missing documentation.",
            documentation='When missing-documentation rules report missing documentation; one of "has-section", "non-summary-docstrings", or "all-docstrings".',
        ),
        SettingDefinition(
            field="docstring_missing_documentation_public_only",
            value_type=bool,
            group=SettingsGroup.DOCSTRING_FORMATTING,
            help="Limit broad missing-documentation checks to public API definitions.",
            documentation="Whether broad missing-documentation checks only apply to public API definitions; explicit relevant documentation is always checked for consistency.",
        ),
        SettingDefinition(
            field="docstring_require_init_attribute_documentation",
            value_type=bool,
            group=SettingsGroup.DOCSTRING_FORMATTING,
            help="Require documented `__init__` instance attributes.",
            documentation="Whether class missing-attribute documentation rules require supported `self.*` attributes assigned in `__init__`; extraneous class-attribute documentation checks always treat those attributes as present.",
        ),
        SettingDefinition(
            field="docstring_forbidden_function_decorators",
            value_type=StringList,
            group=SettingsGroup.DOCSTRING_FORMATTING,
            help="Exact function decorator names whose definitions should not have docstrings.",
            validator=settings_core.validate_non_empty_string_list,
            cli={"metavar": "DECORATOR"},
            documentation="Exact function decorator names whose definitions should not have docstrings. Calls are unwrapped before matching, so `@typing.overload()` matches `typing.overload`; import aliases and project-qualified names require explicit configuration.",
            example='docstring-forbidden-function-decorators = ["overload", "typing.overload", "typing_extensions.overload"]',
        ),
        SettingDefinition(
            field="docstring_optional_function_decorators",
            value_type=StringList,
            group=SettingsGroup.DOCSTRING_FORMATTING,
            help="Exact function decorator names whose definitions may omit docstrings.",
            validator=settings_core.validate_non_empty_string_list,
            cli={"metavar": "DECORATOR"},
            documentation="Exact function decorator names whose definitions may omit docstrings. Calls are unwrapped before matching, so `@typing.override()` matches `typing.override`; import aliases and project-qualified names require explicit configuration.",
            example='docstring-optional-function-decorators = ["override", "typing.override", "typing_extensions.override"]',
        ),
        SettingDefinition(
            field="docstring_property_decorators",
            value_type=StringList,
            group=SettingsGroup.DOCSTRING_FORMATTING,
            help="Exact function decorator names whose definitions should be treated as properties.",
            validator=settings_core.validate_non_empty_string_list,
            cli={"metavar": "DECORATOR"},
            documentation="Exact function decorator names whose definitions should be treated as properties for property-specific summary checks. Calls are unwrapped before matching, so `@functools.cached_property()` matches `functools.cached_property`; import aliases and project-qualified names require explicit configuration.",
            example='docstring-property-decorators = ["property", "functools.cached_property", "project.Property"]',
        ),
        SettingDefinition(
            field="docstring_parse_list_items",
            value_type=bool,
            group=SettingsGroup.DOCSTRING_FORMATTING,
            help="Parse docstring list items as distinct structures.",
        ),
        SettingDefinition(
            field="docstring_parse_headings",
            value_type=bool,
            group=SettingsGroup.DOCSTRING_FORMATTING,
            help="Parse Markdown and reStructuredText docstring headings.",
        ),
        SettingDefinition(
            field="docstring_parse_doctests",
            value_type=bool,
            group=SettingsGroup.DOCSTRING_FORMATTING,
            help="Parse and protect doctest regions in docstrings.",
        ),
        SettingDefinition(
            field="docstring_parse_code_fences",
            value_type=bool,
            group=SettingsGroup.DOCSTRING_FORMATTING,
            help="Parse and protect fenced code blocks in docstrings.",
        ),
        SettingDefinition(
            field="docstring_parse_block_quotes",
            value_type=bool,
            group=SettingsGroup.DOCSTRING_FORMATTING,
            help="Parse Markdown block quotes in docstrings.",
        ),
        SettingDefinition(
            field="docstring_parse_tables",
            value_type=bool,
            group=SettingsGroup.DOCSTRING_FORMATTING,
            help="Parse and protect Markdown and reStructuredText tables in docstrings.",
        ),
        SettingDefinition(
            field="docstring_parse_directives",
            value_type=bool,
            group=SettingsGroup.DOCSTRING_FORMATTING,
            help="Parse reStructuredText directives and their bodies in docstrings.",
        ),
        SettingDefinition(
            field="docstring_parse_literal_blocks",
            value_type=bool,
            group=SettingsGroup.DOCSTRING_FORMATTING,
            help="Parse and protect reStructuredText literal blocks in docstrings.",
        ),
        SettingDefinition(
            field="comment_join_standalone_lines",
            value_type=bool,
            group=SettingsGroup.COMMENT_FORMATTING,
            help="Join consecutive standalone prose comment lines before wrapping.",
        ),
        SettingDefinition(
            field="comment_format_list_items",
            value_type=bool,
            group=SettingsGroup.COMMENT_FORMATTING,
            help="Detect and reflow standalone comment list items with hanging indentation.",
        ),
        SettingDefinition(
            field="comment_format_task_markers",
            value_type=bool,
            group=SettingsGroup.COMMENT_FORMATTING,
            help="Detect and reflow task-marker comments with hanging indentation.",
        ),
        SettingDefinition(
            field="comment_preserve_headings",
            value_type=bool,
            group=SettingsGroup.COMMENT_FORMATTING,
            help="Preserve detected Markdown and reStructuredText comment headings.",
        ),
        SettingDefinition(
            field="comment_preserve_doctests",
            value_type=bool,
            group=SettingsGroup.COMMENT_FORMATTING,
            help="Preserve standalone doctest comment regions.",
        ),
        SettingDefinition(
            field="comment_preserve_code_fences",
            value_type=bool,
            group=SettingsGroup.COMMENT_FORMATTING,
            help="Preserve fenced code regions in standalone comments.",
        ),
        SettingDefinition(
            field="comment_format_block_quotes",
            value_type=bool,
            group=SettingsGroup.COMMENT_FORMATTING,
            help="Detect and reflow Markdown block quotes in standalone comments.",
        ),
        SettingDefinition(
            field="comment_preserve_tables",
            value_type=bool,
            group=SettingsGroup.COMMENT_FORMATTING,
            help="Preserve detected Markdown and reStructuredText comment tables.",
        ),
        SettingDefinition(
            field="comment_preserve_directives",
            value_type=bool,
            group=SettingsGroup.COMMENT_FORMATTING,
            help="Preserve reStructuredText directives and their indented bodies.",
        ),
        SettingDefinition(
            field="comment_trailing_extraction_syntax_aware",
            value_type=bool,
            group=SettingsGroup.COMMENT_FORMATTING,
            help="Avoid extracting trailing comments from syntax-sensitive positions.",
            documentation="Whether overlong trailing-comment extraction avoids decorators, compound statement headers, arguments, and parenthesized or continuation contexts.",
        ),
        SettingDefinition(
            field="comment_trailing_extraction_content_aware",
            value_type=bool,
            group=SettingsGroup.COMMENT_FORMATTING,
            help="Avoid extracting trailing comments with unsafe standalone content.",
            documentation="Whether overlong trailing-comment extraction avoids content that enabled standalone comment structure and code detectors, or the content-aware operator heuristic, would make unsafe to reinterpret as a standalone comment.",
        ),
        SettingDefinition(
            field="comment_detect_code",
            value_type=bool,
            group=SettingsGroup.COMMENT_FORMATTING,
            help="Protect standalone runs matching the indentation and leading-keyword heuristic.",
        ),
        SettingDefinition(
            field="comment_detect_statements",
            value_type=bool,
            group=SettingsGroup.COMMENT_FORMATTING,
            help="Protect standalone runs containing parseable Python statements.",
        ),
        SettingDefinition(
            field="comment_detect_expressions",
            value_type=bool,
            group=SettingsGroup.COMMENT_FORMATTING,
            help="Protect standalone runs containing nontrivial Python expressions.",
        ),
        SettingDefinition(
            field="select",
            value_type=StringList,
            group=SettingsGroup.RULE_SELECTION,
            help="Comma-separated rule selector(s) to enable.",
            validator=settings_core.validate_non_empty_string_list,
            cli={"metavar": "RULE"},
            documentation='Rule selectors to enable; defaults to ["ALL"].',
        ),
        SettingDefinition(
            field="ignore",
            value_type=StringList,
            group=SettingsGroup.RULE_SELECTION,
            help="Comma-separated rule selector(s) to ignore.",
            validator=settings_core.validate_non_empty_string_list,
            cli={"metavar": "RULE"},
            documentation="Rule selectors to ignore.",
        ),
        SettingDefinition(
            field="extend_select",
            value_type=StringList,
            group=SettingsGroup.RULE_SELECTION,
            help="Comma-separated additional rule selector(s) to enable.",
            validator=settings_core.validate_non_empty_string_list,
            cli={"metavar": "RULE"},
            documentation="Additional rule selectors to enable.",
        ),
        SettingDefinition(
            field="require_explicit",
            value_type=StringList,
            group=SettingsGroup.RULE_SELECTION,
            help="Comma-separated rule selector(s) that require exact rule-code selection.",
            validator=settings_core.validate_non_empty_string_list,
            cli={"metavar": "RULE"},
            documentation='Rule selectors that broad rule selectors do not enable unless an exact rule-code selector also participates; defaults to ["PCF005", "PDF003", "PDF601", "PDF603", "PDF605", "PDF607", "PDF609", "PDF611", "PDF612", "PDF613", "PDF615"].',
        ),
        SettingDefinition(
            field="per_file_ignores",
            value_type=MultiStringMap,
            group=SettingsGroup.RULE_SELECTION,
            help="TOML inline table mapping file patterns to ignored rule selectors.",
            cli={"metavar": "RULE_TOML"},
            documentation="File-pattern-specific ignored rule selectors.",
        ),
        SettingDefinition(
            field="extend_per_file_ignores",
            value_type=MultiStringMap,
            group=SettingsGroup.RULE_SELECTION,
            help="TOML inline table mapping file patterns to additional ignored rule selectors.",
            cli={"metavar": "RULE_TOML"},
            documentation="Additional file-pattern-specific ignored rule selectors.",
        ),
        SettingDefinition(
            field="per_file_settings",
            value_type=PerFileSettingsMap,
            group=SettingsGroup.CONFIGURATION,
            help="TOML table mapping file patterns to formatter setting overrides.",
            available_in_cli=False,
            validator=validate_per_file_settings,
            documentation="File-pattern-specific formatter setting overrides. Rule-selection, file-selection, run-level, and rule-selection-effect settings cannot be overridden per file.",
            example='[tool.pydocfmt.per-file-settings]\n"tests/**/*.py" = { docstring-missing-documentation = "has-section" }',
        ),
        SettingDefinition(
            field="fixable",
            value_type=StringList,
            group=SettingsGroup.RULE_SELECTION,
            help="Comma-separated rule selector(s) eligible for automatic fixes.",
            validator=settings_core.validate_non_empty_string_list,
            cli={"metavar": "RULE"},
            documentation='Rule selectors eligible for automatic fixes; defaults to ["ALL"].',
        ),
        SettingDefinition(
            field="unfixable",
            value_type=StringList,
            group=SettingsGroup.RULE_SELECTION,
            help="Comma-separated rule selector(s) ineligible for automatic fixes.",
            validator=settings_core.validate_non_empty_string_list,
            cli={"metavar": "RULE"},
            documentation="Rule selectors ineligible for automatic fixes.",
        ),
        SettingDefinition(
            field="extend_fixable",
            value_type=StringList,
            group=SettingsGroup.RULE_SELECTION,
            help="Comma-separated additional rule selector(s) eligible for automatic fixes.",
            validator=settings_core.validate_non_empty_string_list,
            cli={"metavar": "RULE"},
            documentation="Additional rule selectors eligible for automatic fixes.",
        ),
        SettingDefinition(
            field="include",
            value_type=StringList,
            group=SettingsGroup.FILE_SELECTION,
            help="Comma-separated glob pattern(s) for files to include.",
            validator=settings_core.validate_non_empty_string_list,
            cli={"metavar": "GLOB"},
            documentation="Glob patterns for files to include.",
        ),
        SettingDefinition(
            field="extend_include",
            value_type=StringList,
            group=SettingsGroup.FILE_SELECTION,
            help="Comma-separated additional glob pattern(s) for files to include.",
            validator=settings_core.validate_non_empty_string_list,
            cli={"metavar": "GLOB"},
            documentation="Additional include glob patterns.",
        ),
        SettingDefinition(
            field="exclude",
            value_type=StringList,
            group=SettingsGroup.FILE_SELECTION,
            help="Comma-separated glob pattern(s) for files or directories to exclude.",
            validator=settings_core.validate_non_empty_string_list,
            cli={"metavar": "GLOB"},
            documentation="Glob patterns for files/directories to exclude.",
        ),
        SettingDefinition(
            field="extend_exclude",
            value_type=StringList,
            group=SettingsGroup.FILE_SELECTION,
            help="Comma-separated additional glob pattern(s) for files or directories to exclude.",
            validator=settings_core.validate_non_empty_string_list,
            cli={"metavar": "GLOB"},
            documentation="Additional exclude glob patterns.",
        ),
        SettingDefinition(
            field="respect_gitignore",
            value_type=bool,
            group=SettingsGroup.FILE_SELECTION,
            help="Respect .gitignore when discovering files.",
        ),
        SettingDefinition(
            field="force_exclude",
            value_type=bool,
            group=SettingsGroup.FILE_SELECTION,
            help="Apply exclude rules even to files passed explicitly.",
        ),
    ),
    table_path=("tool", "pydocfmt"),
)
