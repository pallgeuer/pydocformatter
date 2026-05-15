import dataclasses
import enum
from typing import Any, TypedDict

import pydocformatter.config as config
import pydocformatter.rules as rules

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
DEFAULT_RULE_SELECT = (rules.ALL_RULE_CODE,)
DEFAULT_RULE_FIXABLE = (rules.ALL_RULE_CODE,)


class IndentStyle(enum.StrEnum):
    """Indentation styles for generated docstring sections."""

    SPACE = "space"
    TAB = "tab"


class LineEnding(enum.StrEnum):
    """Line ending modes for rewritten files."""

    AUTO = "auto"
    LF = "lf"
    CR_LF = "cr-lf"
    NATIVE = "native"


class OutputFormat(enum.StrEnum):
    """Output formats for rule findings."""

    GROUPED = "grouped"


@dataclasses.dataclass(frozen=True)
class CheckSettings:
    """Resolved formatter settings for pydocformatter.

    Attributes:
        output_format (OutputFormat): Output format used for rule findings.
        experimental (bool): Whether to use the experimental rule-based formatter implementation.
        line_length (int): Maximum line length used when wrapping docstrings or comments.
        line_ending (LineEnding): Line ending used when rewriting files.
        indent_style (IndentStyle): Indentation style used for generated docstring section indentation.
        indent_width (int): Number of spaces per generated docstring indentation level, or the visual width of a tab.
        select (config.StringList): Base selected pydocformatter rule selectors.
        ignore (config.StringList): Rule selectors to ignore.
        extend_select (config.StringList): Additional selected rule selectors.
        per_file_ignores (config.MultiStringMap): File-pattern-specific ignored selectors.
        extend_per_file_ignores (config.MultiStringMap): Additional file-specific ignores.
        fixable (config.StringList): Rule selectors eligible for automatic fixes.
        unfixable (config.StringList): Rule selectors ineligible for automatic fixes.
        extend_fixable (config.StringList): Additional fixable rule selectors.
        include (config.StringList): Base glob patterns that identify format-eligible files.
        extend_include (config.StringList): Additional include glob patterns appended to `include`.
        exclude (config.StringList): Base glob patterns for files or directories to ignore.
        extend_exclude (config.StringList): Additional exclude glob patterns appended to `exclude`.
        respect_gitignore (bool): Whether discovered files are filtered through `.gitignore`.
        force_exclude (bool): Whether include, exclude, and gitignore rules apply to explicitly passed paths.
    """

    output_format: OutputFormat = OutputFormat.GROUPED
    experimental: bool = False
    line_length: int = 88
    line_ending: LineEnding = LineEnding.AUTO
    indent_style: IndentStyle = IndentStyle.SPACE
    indent_width: int = 4
    select: config.StringList = DEFAULT_RULE_SELECT
    ignore: config.StringList = ()
    extend_select: config.StringList = ()
    per_file_ignores: config.MultiStringMap = ()
    extend_per_file_ignores: config.MultiStringMap = ()
    fixable: config.StringList = DEFAULT_RULE_FIXABLE
    unfixable: config.StringList = ()
    extend_fixable: config.StringList = ()
    include: config.StringList = DEFAULT_INCLUDE
    extend_include: config.StringList = ()
    exclude: config.StringList = DEFAULT_EXCLUDE
    extend_exclude: config.StringList = ()
    respect_gitignore: bool = True
    force_exclude: bool = False

    @property
    def include_patterns(self) -> tuple[str, ...]:
        """Return the final include patterns used by file selection."""
        return self.include + self.extend_include

    @property
    def exclude_patterns(self) -> tuple[str, ...]:
        """Return the final exclude patterns used by file selection."""
        return self.exclude + self.extend_exclude


class CheckSettingsOverrides(TypedDict, total=False):
    """Formatter settings supplied by one precedence layer."""

    output_format: OutputFormat
    experimental: bool
    line_length: int
    line_ending: LineEnding
    indent_style: IndentStyle
    indent_width: int
    select: config.StringList
    ignore: config.StringList
    extend_select: config.StringList
    per_file_ignores: config.MultiStringMap
    extend_per_file_ignores: config.MultiStringMap
    fixable: config.StringList
    unfixable: config.StringList
    extend_fixable: config.StringList
    include: config.StringList
    extend_include: config.StringList
    exclude: config.StringList
    extend_exclude: config.StringList
    respect_gitignore: bool
    force_exclude: bool


def validate_rule_selectors(values: dict[str, Any], context: str) -> None:
    """Validate rule selectors against the known rule scope."""
    selector_values = [(definition, selector) for definition in RULE_SELECTOR_DEFINITIONS for selector in values.get(definition.field, ())]
    selector_values.extend((definition, selector) for definition in RULE_SELECTOR_MAP_DEFINITIONS for _, selectors in values.get(definition.field, ()) for selector in selectors)
    for definition, selector in selector_values:
        if not rules.selector_matches_known_rule(selector):
            raise config.ConfigError(f"{context}.{definition.key} contains unknown selector: {selector}")


def post_validate(values: dict[str, Any], context: str) -> None:
    """Validate check settings after field-level validation."""
    validate_rule_selectors(values, context)


class SettingsGroup(enum.StrEnum):
    """Check settings groups used for ordered CLI/help presentation."""

    FORMATTING = "Formatting"
    RULE_SELECTION = "Rule selection"
    FILE_SELECTION = "File selection"


SETTINGS_SCHEMA = config.SettingsSchema(
    settings_type=CheckSettings,
    overrides_type=CheckSettingsOverrides,
    group_type=SettingsGroup,
    table_path=("tool", "pydocfmt"),
    definitions=(
        config.SettingDefinition(
            field="output_format",
            type=OutputFormat,
            group=SettingsGroup.FORMATTING,
            help="Output format for experimental rule findings.",
            documentation='Output format for rule findings; currently only "grouped" is supported.',
        ),
        config.SettingDefinition(
            field="experimental",
            type=bool,
            group=SettingsGroup.FORMATTING,
            help="Use the experimental rule-based formatter implementation.",
        ),
        config.SettingDefinition(
            field="line_length",
            type=int,
            group=SettingsGroup.FORMATTING,
            cli=config.SettingCLIDefinition(metavar="LENGTH"),
            help="Maximum line length for docstrings and comments.",
            validator=config.validate_int(min_value=1, max_value=320),
        ),
        config.SettingDefinition(
            field="line_ending",
            type=LineEnding,
            group=SettingsGroup.FORMATTING,
            help="Line ending to use when rewriting files.",
            documentation='Line ending to use when rewriting files; one of "auto", "lf", "cr-lf", or "native".',
        ),
        config.SettingDefinition(
            field="indent_style",
            type=IndentStyle,
            group=SettingsGroup.FORMATTING,
            help="Indentation style for generated docstring sections.",
            documentation='Generated docstring section indentation style; one of "space" or "tab".',
        ),
        config.SettingDefinition(
            field="indent_width",
            type=int,
            group=SettingsGroup.FORMATTING,
            cli=config.SettingCLIDefinition(metavar="WIDTH"),
            help="Indentation width for generated docstring sections.",
            documentation="Generated docstring section indentation width.",
            validator=config.validate_int(min_value=1, max_value=255),
        ),
        config.SettingDefinition(
            field="select",
            type=config.StringList,
            group=SettingsGroup.RULE_SELECTION,
            cli=config.SettingCLIDefinition(metavar="RULE"),
            help="Comma-separated rule selector(s) to enable.",
            documentation='Rule selectors to enable; defaults to ["ALL"].',
            validator=config.validate_non_empty_string_list,
        ),
        config.SettingDefinition(
            field="ignore",
            type=config.StringList,
            group=SettingsGroup.RULE_SELECTION,
            cli=config.SettingCLIDefinition(metavar="RULE"),
            help="Comma-separated rule selector(s) to ignore.",
            documentation="Rule selectors to ignore.",
            validator=config.validate_non_empty_string_list,
        ),
        config.SettingDefinition(
            field="extend_select",
            type=config.StringList,
            group=SettingsGroup.RULE_SELECTION,
            cli=config.SettingCLIDefinition(metavar="RULE"),
            help="Comma-separated additional rule selector(s) to enable.",
            documentation="Additional rule selectors to enable.",
            validator=config.validate_non_empty_string_list,
        ),
        config.SettingDefinition(
            field="per_file_ignores",
            type=config.MultiStringMap,
            group=SettingsGroup.RULE_SELECTION,
            cli=config.SettingCLIDefinition(metavar="RULE_TOML"),
            help="TOML inline table mapping file patterns to ignored rule selectors.",
            documentation="File-pattern-specific ignored rule selectors.",
        ),
        config.SettingDefinition(
            field="extend_per_file_ignores",
            type=config.MultiStringMap,
            group=SettingsGroup.RULE_SELECTION,
            cli=config.SettingCLIDefinition(metavar="RULE_TOML"),
            help="TOML inline table mapping file patterns to additional ignored rule selectors.",
            documentation="Additional file-pattern-specific ignored rule selectors.",
        ),
        config.SettingDefinition(
            field="fixable",
            type=config.StringList,
            group=SettingsGroup.RULE_SELECTION,
            cli=config.SettingCLIDefinition(metavar="RULE"),
            help="Comma-separated rule selector(s) eligible for automatic fixes.",
            documentation='Rule selectors eligible for automatic fixes; defaults to ["ALL"].',
            validator=config.validate_non_empty_string_list,
        ),
        config.SettingDefinition(
            field="unfixable",
            type=config.StringList,
            group=SettingsGroup.RULE_SELECTION,
            cli=config.SettingCLIDefinition(metavar="RULE"),
            help="Comma-separated rule selector(s) ineligible for automatic fixes.",
            documentation="Rule selectors ineligible for automatic fixes.",
            validator=config.validate_non_empty_string_list,
        ),
        config.SettingDefinition(
            field="extend_fixable",
            type=config.StringList,
            group=SettingsGroup.RULE_SELECTION,
            cli=config.SettingCLIDefinition(metavar="RULE"),
            help="Comma-separated additional rule selector(s) eligible for automatic fixes.",
            documentation="Additional rule selectors eligible for automatic fixes.",
            validator=config.validate_non_empty_string_list,
        ),
        config.SettingDefinition(
            field="include",
            type=config.StringList,
            group=SettingsGroup.FILE_SELECTION,
            cli=config.SettingCLIDefinition(metavar="GLOB"),
            help="Comma-separated glob pattern(s) for files to include.",
            documentation="Glob patterns for files to include.",
            validator=config.validate_non_empty_string_list,
        ),
        config.SettingDefinition(
            field="extend_include",
            type=config.StringList,
            group=SettingsGroup.FILE_SELECTION,
            cli=config.SettingCLIDefinition(metavar="GLOB"),
            help="Comma-separated additional glob pattern(s) for files to include.",
            documentation="Additional include glob patterns.",
            validator=config.validate_non_empty_string_list,
        ),
        config.SettingDefinition(
            field="exclude",
            type=config.StringList,
            group=SettingsGroup.FILE_SELECTION,
            cli=config.SettingCLIDefinition(metavar="GLOB"),
            help="Comma-separated glob pattern(s) for files or directories to exclude.",
            documentation="Glob patterns for files/directories to exclude.",
            validator=config.validate_non_empty_string_list,
        ),
        config.SettingDefinition(
            field="extend_exclude",
            type=config.StringList,
            group=SettingsGroup.FILE_SELECTION,
            cli=config.SettingCLIDefinition(metavar="GLOB"),
            help="Comma-separated additional glob pattern(s) for files or directories to exclude.",
            documentation="Additional exclude glob patterns.",
            validator=config.validate_non_empty_string_list,
        ),
        config.SettingDefinition(
            field="respect_gitignore",
            type=bool,
            group=SettingsGroup.FILE_SELECTION,
            help="Respect .gitignore when discovering files.",
        ),
        config.SettingDefinition(
            field="force_exclude",
            type=bool,
            group=SettingsGroup.FILE_SELECTION,
            help="Apply include/exclude/gitignore rules even to files passed explicitly.",
        ),
    ),
    post_validate=post_validate,
)

RULE_SELECTOR_DEFINITIONS = frozenset(
    definition
    for definition in SETTINGS_SCHEMA.definitions
    if definition.group == SettingsGroup.RULE_SELECTION and definition.cli is not None and definition.cli.metavar == "RULE" and definition.cli.value_kind == config.SettingCLIValueKind.COMMA_LIST
)
RULE_SELECTOR_MAP_DEFINITIONS = frozenset(
    definition
    for definition in SETTINGS_SCHEMA.definitions
    if definition.group == SettingsGroup.RULE_SELECTION and definition.cli is not None and definition.cli.metavar == "RULE_TOML" and definition.cli.value_kind == config.SettingCLIValueKind.TOML_MAP
)
