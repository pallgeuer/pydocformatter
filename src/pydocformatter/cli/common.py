import argparse
import sys
from collections.abc import Callable

from pydocformatter.config import (
    ConfigError,
    FormatterSettings,
    SettingsOverrides,
    ToolName,
    apply_cli_overrides,
    load_config,
)
from pydocformatter.file_selection import FileDecision, select_files

FormatFile = Callable[[str, FormatterSettings, bool], bool]


def load_settings_or_exit(tool_name: ToolName) -> FormatterSettings:
    """Load pyproject settings or exit with a command-line error.

    Args:
        tool_name (ToolName): Formatter tool whose configuration should be loaded.

    Returns:
        FormatterSettings: Resolved settings for the requested tool.

    Raises:
        `SystemExit`: If configuration loading fails.
    """
    try:
        return load_config(tool_name)
    except ConfigError as error:
        print(f"{tool_name}: configuration error: {error}", file=sys.stderr)
        raise SystemExit(2) from error


def add_common_arguments(
    parser: argparse.ArgumentParser,
    settings: FormatterSettings,
    *,
    tool_name: ToolName,
    line_length_subject: str,
) -> None:
    """Add CLI arguments for one pydocformatter tool.

    Most arguments are shared by both tools. `pydocfmt` additionally receives docstring
    indentation options that `pycommentfmt` does not accept.

    Args:
        parser (argparse.ArgumentParser): Parser to mutate.
        settings (FormatterSettings): Settings used for displaying default values in
            help text.
        tool_name (ToolName): Formatter tool whose arguments should be added.
        line_length_subject (str): Human-readable subject controlled by `--line-length`,
            such as `docstrings` or `comments`.

    Returns:
        None: The parser is modified in place.
    """
    parser.add_argument(
        "files",
        nargs="*",
        default=["."],
        help="Python files to format (default: current directory).",
    )
    parser.add_argument(
        "--line-length",
        type=int,
        default=None,
        help=f"Maximum line length for {line_length_subject} (default: {settings.line_length}).",
    )
    if tool_name == "pydocfmt":
        parser.add_argument(
            "--indent-style",
            choices=("space", "tab"),
            default=None,
            help=f"Indentation style for generated docstring sections (default: {settings.indent_style}).",
        )
        parser.add_argument(
            "--indent-width",
            type=int,
            default=None,
            help=f"Indentation width for generated docstring sections (default: {settings.indent_width}).",
        )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if files are formatted correctly without modifying them.",
    )
    parser.add_argument(
        "--include",
        action="append",
        default=None,
        metavar="GLOB",
        nargs="+",
        help="Glob pattern(s) for files to include.",
    )
    parser.add_argument(
        "--extend-include",
        action="append",
        default=None,
        metavar="GLOB",
        nargs="+",
        help="Additional glob pattern(s) for files to include.",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=None,
        metavar="GLOB",
        nargs="+",
        help="Glob pattern(s) for files to exclude.",
    )
    parser.add_argument(
        "--extend-exclude",
        action="append",
        default=None,
        metavar="GLOB",
        nargs="+",
        help="Additional glob pattern(s) for files to exclude.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Emit messages about included and ignored files.",
    )
    parser.add_argument(
        "--respect-gitignore",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=(
            "Respect .gitignore when discovering files "
            f"(default: {_enabled_label(settings.respect_gitignore)})."
        ),
    )
    parser.add_argument(
        "--force-exclude",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Apply include/exclude/gitignore rules even to files passed explicitly.",
    )


def resolve_cli_settings(
    parser: argparse.ArgumentParser,
    settings: FormatterSettings,
    args: argparse.Namespace,
) -> FormatterSettings:
    """Apply parsed command-line settings to resolved config settings.

    Args:
        parser (argparse.ArgumentParser): Parser used to report argument validation
            errors.
        settings (FormatterSettings): Settings resolved before CLI overrides.
        args (argparse.Namespace): Parsed arguments containing optional override values.

    Returns:
        FormatterSettings: Settings with command-line overrides applied.
    """
    overrides = SettingsOverrides(
        line_length=args.line_length,
        indent_style=getattr(args, "indent_style", None),
        indent_width=getattr(args, "indent_width", None),
        respect_gitignore=args.respect_gitignore,
        force_exclude=args.force_exclude,
        include=_flatten_option_groups(args.include),
        extend_include=_flatten_option_groups(args.extend_include),
        exclude=_flatten_option_groups(args.exclude),
        extend_exclude=_flatten_option_groups(args.extend_exclude),
    )
    try:
        return apply_cli_overrides(settings, overrides)
    except ConfigError as error:
        parser.error(str(error))


def run_formatter(
    *,
    tool_name: ToolName,
    description: str,
    line_length_subject: str,
    format_file: FormatFile,
) -> None:
    """Run a formatter CLI with shared argument and file-selection behavior.

    Args:
        tool_name (ToolName): Formatter tool name used for configuration lookup and
            diagnostics.
        description (str): Argument parser description.
        line_length_subject (str): Human-readable subject controlled by `--line-length`.
        format_file (FormatFile): Callable that formats or checks one file and reports
            whether it changed or would change.

    Returns:
        None: The function processes files and may terminate the process in check mode
            when changes are needed.

    Raises:
        `SystemExit`: If argument parsing fails, configuration is invalid, or check mode
            detects required formatting changes.
    """
    parser = argparse.ArgumentParser(description=description)
    add_common_arguments(
        parser,
        FormatterSettings(),
        tool_name=tool_name,
        line_length_subject=line_length_subject,
    )
    args = parser.parse_args()

    configured_settings = load_settings_or_exit(tool_name)
    settings = resolve_cli_settings(parser, configured_settings, args)

    selection = select_files(args.files, settings)
    if args.verbose:
        print_verbose_decisions(selection.decisions)

    modified = False
    for path in selection.accepted_files:
        try:
            changed = format_file(path, settings, args.check)
        except UnicodeDecodeError as error:
            print(f"{path} ignored WARNING: failed to decode as UTF-8 ({error})")
            continue
        except OSError as error:
            print(f"{path} ignored WARNING: failed to read or write file ({error})")
            continue
        if changed:
            modified = True

    if args.check and modified:
        sys.exit(1)


def print_verbose_decisions(decisions: tuple[FileDecision, ...]) -> None:
    """Print file-selection decisions in verbose mode.

    Args:
        decisions (tuple[FileDecision, ...]): Decisions to emit in their original
            evaluation order.

    Returns:
        None: Messages are written to standard output.
    """
    for decision in decisions:
        if decision.accepted:
            print(f"{decision.path} included")
        else:
            print(f"{decision.path} ignored: {decision.message}")


def _flatten_option_groups(groups: list[list[str]] | None) -> tuple[str, ...] | None:
    """Flatten repeated CLI option groups while preserving an omitted option as None."""
    if groups is None:
        return None
    return tuple(value for group in groups for value in group)


def _enabled_label(value: bool) -> str:
    """Return a human-readable enabled state for help text."""
    return "enabled" if value else "disabled"
