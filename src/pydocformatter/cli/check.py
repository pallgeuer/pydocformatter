from __future__ import annotations

import argparse
import contextlib
import dataclasses
import os
import sys
import tomllib
import typing
from collections import defaultdict
from collections.abc import Iterator

import pydocformatter.config as config
import pydocformatter.file_selection as file_selection
import pydocformatter.formatter as formatter
import pydocformatter.formatters.pydocfmt as pydocfmt
import pydocformatter.utils.diagnostics as diagnostics
from pydocformatter.formatter import FormatterResult, Rule, RuleFinding

LEGACY_CHECK_RULE = Rule(
    rule_code="000",
    rule_name="legacy-formatting-needed",
    message="Needs formatting",
    fixable=True,
)


def add_parser(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    settings: config.FormatterSettings,
    formatter_class: type[argparse.HelpFormatter],
) -> argparse.ArgumentParser:
    """Add the check subcommand parser."""
    parser = subparsers.add_parser(
        "check",
        description="Check and optionally fix Python docstrings and comments.",
        help="Check and optionally fix Python docstrings and comments",
        formatter_class=formatter_class,
    )
    add_arguments(parser, settings)
    parser.set_defaults(func=run)
    return parser


def add_arguments(
    parser: argparse.ArgumentParser,
    settings: config.FormatterSettings,
) -> None:
    """Add CLI arguments for the check subcommand."""
    arguments = parser.add_argument_group("Arguments")
    arguments.add_argument(
        "files",
        nargs="*",
        default=None,
        metavar="PATH",
        help="Python files or directories to check, or '-' to read from stdin (default: current directory).",
    )

    options = parser.add_argument_group("Options")
    options.add_argument(
        "--fix",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Apply fixes instead of only checking for needed changes.",
    )
    options.add_argument(
        "--output-format",
        choices=("grouped",),
        default=None,
        help=f"Output format for experimental rule findings (default: {settings.output_format}).",
    )
    options.add_argument(
        "-o",
        "--output-file",
        default=None,
        metavar="FILE",
        help="Specify file to write diagnostics and show output to (default: stdout).",
    )
    options.add_argument(
        "--show-files",
        action="store_true",
        help="Show file-selection decisions without checking or fixing files.",
    )
    options.add_argument(
        "--show-settings",
        action="store_true",
        help="Show resolved settings without checking or fixing files.",
    )
    options.add_argument(
        "--experimental",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=f"Use the experimental rule-based formatter implementation (default: {_enabled_label(settings.experimental)}).",
    )

    formatting = parser.add_argument_group("Formatting")
    formatting.add_argument(
        "--line-length",
        type=int,
        default=None,
        metavar="LENGTH",
        help=f"Maximum line length for docstrings and comments (default: {settings.line_length}).",
    )
    formatting.add_argument(
        "--line-ending",
        choices=("auto", "lf", "cr-lf", "native"),
        default=None,
        help=f"Line ending to use when rewriting files (default: {settings.line_ending}).",
    )
    formatting.add_argument(
        "--indent-style",
        choices=("space", "tab"),
        default=None,
        help=f"Indentation style for generated docstring sections (default: {settings.indent_style}).",
    )
    formatting.add_argument(
        "--indent-width",
        type=int,
        default=None,
        metavar="WIDTH",
        help=f"Indentation width for generated docstring sections (default: {settings.indent_width}).",
    )

    rule_selection = parser.add_argument_group("Rule selection")
    rule_selection.add_argument(
        "--select",
        action="append",
        default=None,
        metavar="RULE",
        help="Comma-separated rule selector(s) to enable.",
    )
    rule_selection.add_argument(
        "--ignore",
        action="append",
        default=None,
        metavar="RULE",
        help="Comma-separated rule selector(s) to ignore.",
    )
    rule_selection.add_argument(
        "--extend-select",
        action="append",
        default=None,
        metavar="RULE",
        help="Comma-separated additional rule selector(s) to enable.",
    )
    rule_selection.add_argument(
        "--per-file-ignores",
        action="append",
        default=None,
        metavar="TOML",
        help="TOML inline table mapping file patterns to ignored rule selectors.",
    )
    rule_selection.add_argument(
        "--extend-per-file-ignores",
        action="append",
        default=None,
        metavar="TOML",
        help="TOML inline table mapping file patterns to additional ignored rule selectors.",
    )
    rule_selection.add_argument(
        "--fixable",
        action="append",
        default=None,
        metavar="RULE",
        help="Comma-separated rule selector(s) eligible for automatic fixes.",
    )
    rule_selection.add_argument(
        "--unfixable",
        action="append",
        default=None,
        metavar="RULE",
        help="Comma-separated rule selector(s) ineligible for automatic fixes.",
    )
    rule_selection.add_argument(
        "--extend-fixable",
        action="append",
        default=None,
        metavar="RULE",
        help="Comma-separated additional rule selector(s) eligible for automatic fixes.",
    )

    file_selection_group = parser.add_argument_group("File selection")
    file_selection_group.add_argument(
        "--include",
        action="append",
        default=None,
        metavar="GLOB",
        help="Comma-separated glob pattern(s) for files to include.",
    )
    file_selection_group.add_argument(
        "--extend-include",
        action="append",
        default=None,
        metavar="GLOB",
        help="Comma-separated additional glob pattern(s) for files to include.",
    )
    file_selection_group.add_argument(
        "--exclude",
        action="append",
        default=None,
        metavar="GLOB",
        help="Comma-separated glob pattern(s) for files or directories to exclude.",
    )
    file_selection_group.add_argument(
        "--extend-exclude",
        action="append",
        default=None,
        metavar="GLOB",
        help="Comma-separated additional glob pattern(s) for files or directories to exclude.",
    )
    file_selection_group.add_argument(
        "--respect-gitignore",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=f"Respect .gitignore when discovering files (default: {_enabled_label(settings.respect_gitignore)}).",
    )
    file_selection_group.add_argument(
        "--force-exclude",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=f"Apply include/exclude/gitignore rules even to files passed explicitly (default: {_enabled_label(settings.force_exclude)}).",
    )

    miscellaneous = parser.add_argument_group("Miscellaneous")
    miscellaneous.add_argument(
        "--stdin-filename",
        default=None,
        metavar="FILENAME",
        help="The name of the file when passing it through stdin.",
    )
    exit_options = miscellaneous.add_mutually_exclusive_group()
    exit_options.add_argument(
        "-e",
        "--exit-zero",
        action="store_true",
        help='Exit with status code "0", even upon detecting formatting violations.',
    )
    exit_options.add_argument(
        "--exit-non-zero-on-fix",
        action="store_true",
        help="Exit with a non-zero status code if any files were modified via fix, even if no formatting violations remain.",
    )

    config.add_global_arguments(parser, dest_prefix="command")


def run(args: argparse.Namespace) -> int:
    """Run the check subcommand."""
    if args.show_files and args.show_settings:
        print("pydocfmt check: argument error: --show-files and --show-settings cannot be used together", file=sys.stderr)
        return 2
    if args.stdin_filename is not None and (args.show_files or args.show_settings):
        option = "--show-files" if args.show_files else "--show-settings"
        print(f"pydocfmt check: argument error: the argument '{option}' cannot be used with '--stdin-filename <FILENAME>'", file=sys.stderr)
        return 2

    settings = load_settings(args)
    if settings is None:
        return 2

    try:
        if args.show_settings:
            with output_stream(args.output_file) as output:
                print_settings(settings, output=output)
            return 0

        stdin_mode = _uses_stdin(args)
        if stdin_mode:
            with output_stream(args.output_file) as output:
                if args.show_files:
                    return 0
                return run_stdin(args, settings, output=output)

        files = typing.cast(list[str], args.files) if args.files else ["."]
        try:
            selection = file_selection.select_files(files, settings)
        except file_selection.FileSelectionError as error:
            print(f"pydocfmt check: file selection error: {error}", file=sys.stderr)
            return 2

        if args.show_files:
            with output_stream(args.output_file) as output:
                print_file_selection_decisions(selection.decisions, output=output)
            return 0

        if settings.experimental:
            results = format_files_exp(selection.accepted_paths, settings, fix=args.fix)
        else:
            results = format_files(selection.accepted_paths, settings, fix=args.fix, output=None, collect_diagnostics=args.output_file is not None)

        with output_stream(args.output_file) as output:
            print_results(results, settings, output=output)

        has_findings = any(result.findings for result in results)
        modified = any(result.modified for result in results)
        if args.exit_zero:
            return 0
        if has_findings:
            return 1
        if args.fix and args.exit_non_zero_on_fix and modified:
            return 1
        return 0
    except OSError as error:
        print(f"pydocfmt check: output error: {error}", file=sys.stderr)
        return 2


def run_stdin(args: argparse.Namespace, settings: config.FormatterSettings, *, output: typing.TextIO | None) -> int:
    """Run the check subcommand against stdin."""
    _warn_about_ignored_stdin_paths(args)
    display_path = args.stdin_filename if args.stdin_filename is not None else "-"
    source = sys.stdin.read()
    if settings.experimental:
        formatted_source, result = formatter.format_source_exp(source, display_path, settings, fix=args.fix)
        results = [result]
    else:
        source_result = pydocfmt.format_source(source, settings, fix=args.fix)
        if args.fix:
            result = FormatterResult(path=display_path, modified=source_result.modified, findings=())
        elif source_result.modified:
            result = FormatterResult(
                path=display_path,
                modified=False,
                findings=(RuleFinding(rule=LEGACY_CHECK_RULE, line_numbers=(0,)),),
                diagnostic_messages=pydocfmt.source_diagnostic_messages(display_path, source_result),
            )
        else:
            result = FormatterResult(path=display_path, modified=False, findings=())
        formatted_source = source_result.source
        results = [result]

    print_results(results, settings, output=output)
    if args.fix:
        sys.stdout.write(formatted_source)
    has_findings = any(result.findings for result in results)
    modified = any(result.modified for result in results)
    if args.exit_zero:
        return 0
    if has_findings:
        return 1
    if args.fix and args.exit_non_zero_on_fix and modified:
        return 1
    return 0


@contextlib.contextmanager
def output_stream(output_file: str | None) -> Iterator[typing.TextIO | None]:
    """Yield the configured diagnostics output stream."""
    if output_file is None:
        yield None
        return

    parent = os.path.dirname(output_file)
    if parent:
        try:
            os.mkdir(parent)
        except FileExistsError:
            pass
    with open(output_file, "w", encoding="utf-8", newline="") as file:
        yield file


def _uses_stdin(args: argparse.Namespace) -> bool:
    """Return whether parsed arguments request stdin input."""
    return args.stdin_filename is not None or (args.files is not None and "-" in args.files)


def _warn_about_ignored_stdin_paths(args: argparse.Namespace) -> None:
    """Warn when stdin mode ignores explicitly supplied file paths."""
    if args.files is None:
        return
    ignored_paths = [path for path in args.files if path != "-"]
    for path in ignored_paths:
        print(f"warning: Ignoring file {path} in favor of standard input.", file=sys.stderr)


def load_settings(args: argparse.Namespace) -> config.FormatterSettings | None:
    """Load settings with command-line overrides, returning None on failure."""
    try:
        overrides = _settings_overrides_from_args(args)
        return config.load_config(
            overrides,
            config_options=_config_options_from_args(args),
            isolated=_isolated_from_args(args),
        )
    except config.ConfigError as error:
        print(f"pydocfmt check: configuration error: {error}", file=sys.stderr)
        return None
    except tomllib.TOMLDecodeError as error:
        print(f"pydocfmt check: configuration error: invalid TOML inline table: {error}", file=sys.stderr)
        return None


def print_file_selection_decisions(decisions: tuple[file_selection.FileDecision, ...], *, output: typing.TextIO | None) -> None:
    """Print file-selection decisions."""
    for decision in decisions:
        if decision.accepted:
            print(f"{decision.path} INCLUDED", file=output)
        else:
            print(f"{decision.path} IGNORED: {decision.message}", file=output)


def print_settings(settings: config.FormatterSettings, *, output: typing.TextIO | None) -> None:
    """Print resolved settings in a stable TOML-like form."""
    print("[tool.pydocfmt]", file=output)
    for field in dataclasses.fields(config.FormatterSettings):
        key = field.name.replace("_", "-")
        value = getattr(settings, field.name)
        if field.name in {"per_file_ignores", "extend_per_file_ignores"}:
            print(f"{key} = {_format_rule_selector_map(value)}", file=output)
        elif isinstance(value, tuple):
            print(f"{key} = {_format_string_list(value)}", file=output)
        elif isinstance(value, str):
            print(f'{key} = "{value}"', file=output)
        elif isinstance(value, bool):
            print(f"{key} = {str(value).lower()}", file=output)
        else:
            print(f"{key} = {value}", file=output)


def format_files_exp(
    paths: tuple[str, ...],
    settings: config.FormatterSettings,
    fix: bool,
) -> list[FormatterResult]:
    """Format files with the experimental formatter path."""
    results: list[FormatterResult] = []
    for path in paths:
        try:
            results.append(formatter.format_file_exp(path, settings, fix=fix))
        except UnicodeDecodeError as error:
            print(f"{path} ignored WARNING: failed to decode as UTF-8 ({error})")
            continue
        except OSError as error:
            print(f"{path} ignored WARNING: failed to read or write file ({error})")
            continue
    return results


def format_files(
    paths: tuple[str, ...],
    settings: config.FormatterSettings,
    fix: bool,
    *,
    output: typing.TextIO | None,
    collect_diagnostics: bool = False,
) -> list[FormatterResult]:
    """Format files with the legacy formatter path."""
    results: list[FormatterResult] = []
    for path in paths:
        try:
            if collect_diagnostics:
                source_result = pydocfmt.format_file_source(path, settings, fix=fix)
                modified_or_needs_formatting = source_result.modified
                diagnostic_messages = pydocfmt.source_diagnostic_messages(path, source_result) if not fix else ()
            else:
                modified_or_needs_formatting = pydocfmt.format_file(path, settings, fix=fix, output=output)
                diagnostic_messages = ()
        except UnicodeDecodeError as error:
            print(f"{path} ignored WARNING: failed to decode as UTF-8 ({error})")
            continue
        except OSError as error:
            print(f"{path} ignored WARNING: failed to read or write file ({error})")
            continue
        if not fix and modified_or_needs_formatting:
            finding = RuleFinding(rule=LEGACY_CHECK_RULE, line_numbers=(0,))
            results.append(FormatterResult(path=path, modified=False, findings=(finding,), diagnostic_messages=diagnostic_messages))
        else:
            results.append(FormatterResult(path=path, modified=modified_or_needs_formatting, findings=()))
    return results


def print_results(results: list[FormatterResult], settings: config.FormatterSettings, *, output: typing.TextIO | None) -> None:
    """Print formatter results in the configured output format."""
    if settings.output_format == "grouped":
        print_results_grouped(results, output=output)
        return
    raise AssertionError(f"unknown output format: {settings.output_format}")


def print_results_grouped(results: list[FormatterResult], *, output: typing.TextIO | None) -> None:
    """Print remaining findings grouped by file."""
    total_findings = sum(len(result.findings) for result in results)
    total_diagnostic_messages = sum(len(result.diagnostic_messages) for result in results)
    if total_findings == 0 and total_diagnostic_messages == 0:
        return

    for result in results:
        for message in result.diagnostic_messages:
            print(message, file=output)
    if total_findings == 0:
        return

    for result in results:
        if not result.findings:
            continue
        print(f"{result.path}:", file=output)
        for finding in _group_findings(result.findings):
            print(f"  {_format_grouped_finding(finding)}", file=output)
        print(file=output)

    fixable_findings = sum(1 for result in results for finding in result.findings if finding.fixable)
    print(f"Found {total_findings} errors ({fixable_findings} fixable).", file=output)


def _group_findings(findings: tuple[RuleFinding, ...]) -> tuple[RuleFinding, ...]:
    """Group same-rule findings while preserving first-seen order."""
    grouped_lines: defaultdict[formatter.RuleFindingKey, set[int]] = defaultdict(set)
    exemplars: dict[formatter.RuleFindingKey, RuleFinding] = {}
    for finding in findings:
        key = finding.grouping_key
        exemplars.setdefault(key, finding)
        grouped_lines[key].update(finding.line_numbers)

    return tuple(exemplars[key].with_line_numbers(tuple(sorted(line_numbers))) for key, line_numbers in grouped_lines.items())


def _format_grouped_finding(finding: RuleFinding) -> str:
    """Format one grouped finding line."""
    label = "Lines" if len(finding.line_numbers) != 1 else "Line"
    ranges = diagnostics.format_line_ranges(list(finding.line_numbers))
    fixable = "*" if finding.fixable else ""
    message = finding.message
    message_end = "" if message.endswith((".", "!", "?")) else "."
    return f"{finding.rule.rule_code}{fixable} {message}{message_end} {label} {ranges}"


def _settings_overrides_from_args(args: argparse.Namespace) -> config.SettingsOverrides:
    """Build settings overrides from parsed command-line arguments."""
    return config.SettingsOverrides(
        output_format=args.output_format,
        experimental=args.experimental,
        line_length=args.line_length,
        line_ending=args.line_ending,
        indent_style=args.indent_style,
        indent_width=args.indent_width,
        select=_parse_comma_option_groups(args.select),
        ignore=_parse_comma_option_groups(args.ignore),
        extend_select=_parse_comma_option_groups(args.extend_select),
        per_file_ignores=_parse_per_file_options(args.per_file_ignores),
        extend_per_file_ignores=_parse_per_file_options(args.extend_per_file_ignores),
        fixable=_parse_comma_option_groups(args.fixable),
        unfixable=_parse_comma_option_groups(args.unfixable),
        extend_fixable=_parse_comma_option_groups(args.extend_fixable),
        include=_parse_comma_option_groups(args.include),
        extend_include=_parse_comma_option_groups(args.extend_include),
        exclude=_parse_comma_option_groups(args.exclude),
        extend_exclude=_parse_comma_option_groups(args.extend_exclude),
        respect_gitignore=args.respect_gitignore,
        force_exclude=args.force_exclude,
    )


def _config_options_from_args(args: argparse.Namespace) -> tuple[str, ...]:
    """Return --config values from the top-level and subcommand parsers."""
    options = []
    for name in ("global_config", "command_config"):
        value = getattr(args, name, None)
        if value is not None:
            options.extend(value)
    return tuple(options)


def _isolated_from_args(args: argparse.Namespace) -> bool:
    """Return whether any parser position specified --isolated."""
    return bool(getattr(args, "global_isolated", False) or getattr(args, "command_isolated", False))


def _parse_comma_option_groups(groups: list[str] | None) -> tuple[str, ...] | None:
    """Parse repeated comma-separated CLI option groups while preserving omitted options as None."""
    if groups is None:
        return None
    return tuple(value.strip() for group in groups for value in group.split(","))


def _parse_per_file_options(groups: list[str] | None) -> config.RuleSelectorMap | None:
    """Parse repeated TOML inline per-file ignore maps from CLI options."""
    if groups is None:
        return None

    merged: dict[str, tuple[str, ...]] = {}
    for group in groups:
        parsed = tomllib.loads(f"value = {group}")
        value = parsed["value"]
        if not isinstance(value, dict):
            raise config.ConfigError("per-file ignore CLI value must be a TOML table")
        for pattern, selectors in value.items():
            if not isinstance(pattern, str):
                raise config.ConfigError("per-file ignore CLI patterns must be strings")
            if not isinstance(selectors, (list, tuple)) or not all(isinstance(selector, str) for selector in selectors):
                raise config.ConfigError("per-file ignore CLI selectors must be lists of strings")
            merged[pattern] = tuple(selectors)
    result: config.RuleSelectorMap = tuple((pattern, selectors) for pattern, selectors in merged.items())
    return result


def _format_rule_selector_map(value: config.RuleSelectorMap) -> str:
    """Format a rule selector mapping as a TOML inline table."""
    entries = [f'"{pattern}" = {_format_string_list(selectors)}' for pattern, selectors in value]
    return "{" + ", ".join(entries) + "}"


def _format_string_list(values: tuple[str, ...]) -> str:
    """Format string values as a TOML list."""
    return "[" + ", ".join(f'"{value}"' for value in values) + "]"


def _enabled_label(value: bool) -> str:
    """Return a human-readable enabled state."""
    return "enabled" if value else "disabled"
