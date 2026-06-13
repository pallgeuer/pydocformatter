import dataclasses
import enum
from typing import TypedDict

import pydocformatter.settings as settings_core
from pydocformatter.rules.codes import ALL_RULE_SELECTOR_TAG
from pydocformatter.settings import MultiStringMap, SettingDefinition, SettingsSchema, StringList

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


class IndentStyle(enum.StrEnum):
    """Indentation styles for generated docstring sections.

    Attributes:
        SPACE (IndentStyle): Use spaces for generated section indentation.
        TAB (IndentStyle): Use tabs for generated section indentation.
    """

    SPACE = "space"
    TAB = "tab"


class LineEnding(enum.StrEnum):
    """Line ending modes for rewritten files.

    Attributes:
        AUTO (LineEnding): Preserve the first detected line ending in each file, defaulting to LF.
        LF (LineEnding): Rewrite generated lines with LF endings.
        CR_LF (LineEnding): Rewrite generated lines with CRLF endings.
        NATIVE (LineEnding): Rewrite generated lines with the platform-native line ending.
    """

    AUTO = "auto"
    LF = "lf"
    CR_LF = "cr-lf"
    NATIVE = "native"


class DocstringConvention(enum.StrEnum):
    """Conventions used to parse semantic docstring sections."""

    NONE = "none"
    GOOGLE = "google"
    NUMPY = "numpy"
    PEP257 = "pep257"


class DocstringBlankLineStyle(enum.StrEnum):
    """Whitespace styles for blank docstring lines."""

    BLANK = "blank"
    ALIGNED = "aligned"


class OutputFormat(enum.StrEnum):
    """Output formats for rule findings.

    Attributes:
        GROUPED (OutputFormat): Group diagnostics by file.
    """

    GROUPED = "grouped"


@dataclasses.dataclass(frozen=True)
class CheckSettings:
    """Resolved formatter settings for pydocformatter.

    Attributes:
        output_format (OutputFormat): Output format used for rule findings.
        legacy (bool): Whether to use the legacy formatter implementation.
        line_length (int): Maximum line length used when wrapping docstrings or comments.
        line_ending (LineEnding): Line ending used when rewriting files.
        indent_style (IndentStyle): Indentation style used for generated docstring section indentation.
        indent_width (int): Number of spaces per generated docstring indentation level, or the visual width of a tab.
        docstring_convention (DocstringConvention): Convention used to parse semantic docstring sections.
        docstring_blank_line_style (DocstringBlankLineStyle): Whitespace style used by PDF004 for blank docstring lines.
        docstring_blank_line_after_last_section (bool): Whether PDF100 and PDF101 keep one blank line after the last
            convention section.
        docstring_parse_list_items (bool): Whether list items are parsed as distinct docstring structures.
        docstring_parse_headings (bool): Whether Markdown and reStructuredText headings are parsed.
        docstring_parse_doctests (bool): Whether doctest regions are parsed and protected.
        docstring_parse_code_fences (bool): Whether Markdown fenced code blocks are parsed and protected.
        docstring_parse_block_quotes (bool): Whether Markdown block quotes are parsed as distinct structures.
        docstring_parse_tables (bool): Whether Markdown and reStructuredText tables are parsed and protected.
        docstring_parse_directives (bool): Whether reStructuredText directives and their bodies are parsed.
        docstring_parse_literal_blocks (bool): Whether reStructuredText literal blocks are parsed and protected.
        docstring_parse_sphinx_fields (bool): Whether Sphinx fields are parsed into semantic entries.
        comment_join_standalone_lines (bool): Whether consecutive standalone prose comment lines are joined before
            wrapping.
        comment_format_list_items (bool): Whether standalone comment list items are detected and reflowed.
        comment_preserve_headings (bool): Whether detected Markdown and reStructuredText comment headings are preserved.
        comment_preserve_doctests (bool): Whether standalone doctest comment regions are preserved.
        comment_preserve_code_fences (bool): Whether fenced code regions in standalone comments are preserved.
        comment_format_block_quotes (bool): Whether Markdown block quotes in standalone comments are detected and
            reflowed.
        comment_preserve_tables (bool): Whether detected Markdown and reStructuredText comment tables are preserved.
        comment_preserve_directives (bool): Whether reStructuredText directives and their indented bodies are preserved.
        comment_detect_code (bool): Whether the indentation and leading-keyword heuristic protects standalone comment
            runs.
        comment_detect_statements (bool): Whether parseable Python statements protect standalone comment runs.
        comment_detect_expressions (bool): Whether nontrivial Python expressions protect standalone comment runs.
        select (StringList): Base selected pydocformatter rule selectors.
        ignore (StringList): Rule selectors to ignore.
        extend_select (StringList): Additional selected rule selectors.
        per_file_ignores (MultiStringMap): File-pattern-specific ignored selectors.
        extend_per_file_ignores (MultiStringMap): Additional file-specific ignores.
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
    legacy: bool = False
    line_length: int = 88
    line_ending: LineEnding = LineEnding.AUTO
    indent_style: IndentStyle = IndentStyle.SPACE
    indent_width: int = 4
    docstring_convention: DocstringConvention = DocstringConvention.NONE
    docstring_blank_line_style: DocstringBlankLineStyle = DocstringBlankLineStyle.BLANK
    docstring_blank_line_after_last_section: bool = False
    docstring_parse_list_items: bool = True
    docstring_parse_headings: bool = True
    docstring_parse_doctests: bool = True
    docstring_parse_code_fences: bool = True
    docstring_parse_block_quotes: bool = True
    docstring_parse_tables: bool = True
    docstring_parse_directives: bool = True
    docstring_parse_literal_blocks: bool = True
    docstring_parse_sphinx_fields: bool = True
    comment_join_standalone_lines: bool = False
    comment_format_list_items: bool = True
    comment_preserve_headings: bool = True
    comment_preserve_doctests: bool = True
    comment_preserve_code_fences: bool = True
    comment_format_block_quotes: bool = True
    comment_preserve_tables: bool = True
    comment_preserve_directives: bool = True
    comment_detect_code: bool = False
    comment_detect_statements: bool = True
    comment_detect_expressions: bool = False
    select: StringList = DEFAULT_RULE_SELECT
    ignore: StringList = ()
    extend_select: StringList = ()
    per_file_ignores: MultiStringMap = ()
    extend_per_file_ignores: MultiStringMap = ()
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
        """Return the final include patterns used by file selection.

        Returns:
            tuple[str, ...]: Base include patterns followed by extension include patterns.
        """
        return self.include + self.extend_include

    @property
    def exclude_patterns(self) -> tuple[str, ...]:
        """Return the final exclude patterns used by file selection.

        Returns:
            tuple[str, ...]: Base exclude patterns followed by extension exclude patterns.
        """
        return self.exclude + self.extend_exclude


class CheckSettingsOverrides(TypedDict, total=False):
    """Formatter settings supplied by one precedence layer.

    Attributes:
        output_format (OutputFormat): Output format used for rule findings.
        legacy (bool): Whether to use the legacy formatter implementation.
        line_length (int): Maximum line length used when wrapping docstrings or comments.
        line_ending (LineEnding): Line ending used when rewriting files.
        indent_style (IndentStyle): Indentation style used for generated docstring section indentation.
        indent_width (int): Number of spaces per generated docstring indentation level, or the visual width of a tab.
        docstring_convention (DocstringConvention): Convention used to parse semantic docstring sections.
        docstring_blank_line_style (DocstringBlankLineStyle): Whitespace style used by PDF004 for blank docstring lines.
        docstring_blank_line_after_last_section (bool): Whether PDF100 and PDF101 keep one blank line after the last
            convention section.
        docstring_parse_list_items (bool): Whether list items are parsed as distinct docstring structures.
        docstring_parse_headings (bool): Whether Markdown and reStructuredText headings are parsed.
        docstring_parse_doctests (bool): Whether doctest regions are parsed and protected.
        docstring_parse_code_fences (bool): Whether Markdown fenced code blocks are parsed and protected.
        docstring_parse_block_quotes (bool): Whether Markdown block quotes are parsed as distinct structures.
        docstring_parse_tables (bool): Whether Markdown and reStructuredText tables are parsed and protected.
        docstring_parse_directives (bool): Whether reStructuredText directives and their bodies are parsed.
        docstring_parse_literal_blocks (bool): Whether reStructuredText literal blocks are parsed and protected.
        docstring_parse_sphinx_fields (bool): Whether Sphinx fields are parsed into semantic entries.
        comment_join_standalone_lines (bool): Whether consecutive standalone prose comment lines are joined before
            wrapping.
        comment_format_list_items (bool): Whether standalone comment list items are detected and reflowed.
        comment_preserve_headings (bool): Whether detected Markdown and reStructuredText comment headings are preserved.
        comment_preserve_doctests (bool): Whether standalone doctest comment regions are preserved.
        comment_preserve_code_fences (bool): Whether fenced code regions in standalone comments are preserved.
        comment_format_block_quotes (bool): Whether Markdown block quotes in standalone comments are detected and
            reflowed.
        comment_preserve_tables (bool): Whether detected Markdown and reStructuredText comment tables are preserved.
        comment_preserve_directives (bool): Whether reStructuredText directives and their indented bodies are preserved.
        comment_detect_code (bool): Whether the indentation and leading-keyword heuristic protects standalone comment
            runs.
        comment_detect_statements (bool): Whether parseable Python statements protect standalone comment runs.
        comment_detect_expressions (bool): Whether nontrivial Python expressions protect standalone comment runs.
        select (StringList): Base selected pydocformatter rule selectors.
        ignore (StringList): Rule selectors to ignore.
        extend_select (StringList): Additional selected rule selectors.
        per_file_ignores (MultiStringMap): File-pattern-specific ignored selectors.
        extend_per_file_ignores (MultiStringMap): Additional file-specific ignores.
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
    legacy: bool
    line_length: int
    line_ending: LineEnding
    indent_style: IndentStyle
    indent_width: int
    docstring_convention: DocstringConvention
    docstring_blank_line_style: DocstringBlankLineStyle
    docstring_blank_line_after_last_section: bool
    docstring_parse_list_items: bool
    docstring_parse_headings: bool
    docstring_parse_doctests: bool
    docstring_parse_code_fences: bool
    docstring_parse_block_quotes: bool
    docstring_parse_tables: bool
    docstring_parse_directives: bool
    docstring_parse_literal_blocks: bool
    docstring_parse_sphinx_fields: bool
    comment_join_standalone_lines: bool
    comment_format_list_items: bool
    comment_preserve_headings: bool
    comment_preserve_doctests: bool
    comment_preserve_code_fences: bool
    comment_format_block_quotes: bool
    comment_preserve_tables: bool
    comment_preserve_directives: bool
    comment_detect_code: bool
    comment_detect_statements: bool
    comment_detect_expressions: bool
    select: StringList
    ignore: StringList
    extend_select: StringList
    per_file_ignores: MultiStringMap
    extend_per_file_ignores: MultiStringMap
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
        FORMATTING (SettingsGroup): Formatting behavior settings.
        DOCSTRING_FORMATTING (SettingsGroup): Docstring semantic parsing settings.
        COMMENT_FORMATTING (SettingsGroup): Comment formatting settings.
        RULE_SELECTION (SettingsGroup): Rule selection settings.
        FILE_SELECTION (SettingsGroup): File discovery and filtering settings.
    """

    FORMATTING = "Formatting"
    DOCSTRING_FORMATTING = "Docstring formatting"
    COMMENT_FORMATTING = "Comment formatting"
    RULE_SELECTION = "Rule selection"
    FILE_SELECTION = "File selection"


SETTINGS_SCHEMA = SettingsSchema(
    settings_type=CheckSettings,
    overrides_type=CheckSettingsOverrides,
    group_type=SettingsGroup,
    definitions=(
        SettingDefinition(
            field="output_format",
            value_type=OutputFormat,
            group=SettingsGroup.FORMATTING,
            help="Output format for rule findings.",
            documentation='Output format for rule findings; currently only "grouped" is supported.',
        ),
        SettingDefinition(
            field="legacy",
            value_type=bool,
            group=SettingsGroup.FORMATTING,
            help="Use the legacy formatter implementation.",
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
            help="Indentation style for generated docstring sections.",
            documentation='Generated docstring section indentation style; one of "space" or "tab".',
        ),
        SettingDefinition(
            field="indent_width",
            value_type=int,
            group=SettingsGroup.FORMATTING,
            help="Indentation width for generated docstring sections.",
            validator=settings_core.validate_int(min_value=1, max_value=255),
            cli={"metavar": "WIDTH"},
            documentation="Generated docstring section indentation width and tab expansion width used when measuring comments.",
        ),
        SettingDefinition(
            field="docstring_convention",
            value_type=DocstringConvention,
            group=SettingsGroup.DOCSTRING_FORMATTING,
            help="Convention used to parse semantic docstring sections.",
            documentation='Docstring convention; one of "none", "google", "numpy", or "pep257".',
        ),
        SettingDefinition(
            field="docstring_blank_line_style",
            value_type=DocstringBlankLineStyle,
            group=SettingsGroup.DOCSTRING_FORMATTING,
            help="Whitespace style for blank docstring lines.",
            documentation='Blank docstring line whitespace style used by PDF004; one of "blank" or "aligned".',
        ),
        SettingDefinition(
            field="docstring_blank_line_after_last_section",
            value_type=bool,
            group=SettingsGroup.DOCSTRING_FORMATTING,
            help="Keep one blank line after the last docstring section.",
            documentation="Whether PDF100 and PDF101 keep one blank line after the last recognized Google or NumPy docstring section.",
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
            field="docstring_parse_sphinx_fields",
            value_type=bool,
            group=SettingsGroup.DOCSTRING_FORMATTING,
            help="Parse Sphinx docstring fields into semantic entries.",
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
