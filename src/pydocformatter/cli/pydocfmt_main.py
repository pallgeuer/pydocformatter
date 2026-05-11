import argparse
import sys
import tomllib
from collections import defaultdict

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


def main() -> int:
    """Run the pydocfmt command-line entry point."""
    parser = argparse.ArgumentParser(description="Format Python docstrings and comments.")
    add_arguments(parser, config.FormatterSettings())
    args = parser.parse_args()

    settings = load_settings(args)
    if settings is None:
        return 2

    try:
        selection = file_selection.select_files(args.files, settings)
    except file_selection.FileSelectionError as error:
        print(f"pydocfmt: file selection error: {error}", file=sys.stderr)
        return 2
    if args.show_files:
        print_file_selection_decisions(selection.decisions)
        return 0

    if settings.experimental:
        results = format_files_exp(selection.accepted_paths, settings, args.check)
    else:
        results = format_files(selection.accepted_paths, settings, args.check)

    print_results(results, settings)
    needs_changes = any(result.findings for result in results)
    return 1 if args.check and needs_changes else 0


def add_arguments(
    parser: argparse.ArgumentParser,
    settings: config.FormatterSettings,
) -> None:
    """Add CLI arguments for pydocfmt."""
    parser.add_argument(
        "files",
        nargs="*",
        default=["."],
        help="Python files to format (default: current directory).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if files are formatted correctly without modifying them.",
    )
    parser.add_argument(
        "--show-files",
        action="store_true",
        help="Show file-selection decisions without formatting files.",
    )
    parser.add_argument(
        "--line-length",
        type=int,
        default=None,
        help=f"Maximum line length for docstrings and comments (default: {settings.line_length}).",
    )
    parser.add_argument(
        "--line-ending",
        choices=("auto", "lf", "cr-lf", "native"),
        default=None,
        help=f"Line ending to use when rewriting files (default: {settings.line_ending}).",
    )
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
        "--respect-gitignore",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=f"Respect .gitignore when discovering files (default: {_enabled_label(settings.respect_gitignore)}).",
    )
    parser.add_argument(
        "--force-exclude",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=f"Apply include/exclude/gitignore rules even to files passed explicitly (default: {_enabled_label(settings.force_exclude)}).",
    )
    parser.add_argument(
        "--experimental",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=f"Use the experimental rule-based formatter implementation (default: {_enabled_label(settings.experimental)}).",
    )
    parser.add_argument(
        "--output-format",
        choices=("grouped",),
        default=None,
        help=f"Output format for experimental rule findings (default: {settings.output_format}).",
    )
    parser.add_argument(
        "--select",
        action="append",
        default=None,
        metavar="RULE",
        nargs="+",
        help="Rule selector(s) to enable.",
    )
    parser.add_argument(
        "--extend-select",
        action="append",
        default=None,
        metavar="RULE",
        nargs="+",
        help="Additional rule selector(s) to enable.",
    )
    parser.add_argument(
        "--ignore",
        action="append",
        default=None,
        metavar="RULE",
        nargs="+",
        help="Rule selector(s) to ignore.",
    )
    parser.add_argument(
        "--fixable",
        action="append",
        default=None,
        metavar="RULE",
        nargs="+",
        help="Rule selector(s) eligible for automatic fixes.",
    )
    parser.add_argument(
        "--extend-fixable",
        action="append",
        default=None,
        metavar="RULE",
        nargs="+",
        help="Additional rule selector(s) eligible for automatic fixes.",
    )
    parser.add_argument(
        "--unfixable",
        action="append",
        default=None,
        metavar="RULE",
        nargs="+",
        help="Rule selector(s) ineligible for automatic fixes.",
    )
    parser.add_argument(
        "--per-file-ignores",
        action="append",
        default=None,
        metavar="TOML",
        help="TOML inline table mapping file patterns to ignored rule selectors.",
    )
    parser.add_argument(
        "--extend-per-file-ignores",
        action="append",
        default=None,
        metavar="TOML",
        help="TOML inline table mapping file patterns to additional ignored rule selectors.",
    )


def load_settings(args: argparse.Namespace) -> config.FormatterSettings | None:
    """Load settings with command-line overrides, returning None on failure."""
    try:
        overrides = _settings_overrides_from_args(args)
        return config.load_config(overrides)
    except config.ConfigError as error:
        print(f"pydocfmt: configuration error: {error}", file=sys.stderr)
        return None
    except tomllib.TOMLDecodeError as error:
        print(
            f"pydocfmt: configuration error: invalid TOML inline table: {error}",
            file=sys.stderr,
        )
        return None


def print_file_selection_decisions(decisions: tuple[file_selection.FileDecision, ...]) -> None:
    """Print file-selection decisions."""
    for decision in decisions:
        if decision.accepted:
            print(f"{decision.path} included")
        else:
            print(f"{decision.path} ignored: {decision.message}")


def format_files_exp(
    paths: tuple[str, ...],
    settings: config.FormatterSettings,
    check: bool,
) -> list[FormatterResult]:
    """Format files with the experimental formatter path."""
    results: list[FormatterResult] = []
    for path in _deduplicated_paths(paths):
        try:
            results.append(formatter.format_file_exp(path, settings, check))
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
    check: bool,
) -> list[FormatterResult]:
    """Format files with the legacy formatter path."""
    results: list[FormatterResult] = []
    for path in _deduplicated_paths(paths):
        try:
            modified_or_needs_formatting = pydocfmt.format_file(path, settings, check)
        except UnicodeDecodeError as error:
            print(f"{path} ignored WARNING: failed to decode as UTF-8 ({error})")
            continue
        except OSError as error:
            print(f"{path} ignored WARNING: failed to read or write file ({error})")
            continue
        if check and modified_or_needs_formatting:
            finding = RuleFinding(rule=LEGACY_CHECK_RULE, line_numbers=(0,))
            results.append(FormatterResult(path=path, modified=False, findings=(finding,)))
        else:
            results.append(FormatterResult(path=path, modified=modified_or_needs_formatting, findings=()))
    return results


def print_results(results: list[FormatterResult], settings: config.FormatterSettings) -> None:
    """Print formatter results in the configured output format."""
    if settings.output_format == "grouped":
        print_results_grouped(results)
        return
    raise AssertionError(f"unknown output format: {settings.output_format}")


def print_results_grouped(results: list[FormatterResult]) -> None:
    """Print remaining findings grouped by file."""
    total_findings = sum(len(result.findings) for result in results)
    if total_findings == 0:
        return

    for result in results:
        if not result.findings:
            continue
        print(f"{result.path}:")
        for finding in _group_findings(result.findings):
            print(f"  {_format_grouped_finding(finding)}")
        print()

    fixable_findings = sum(1 for result in results for finding in result.findings if finding.fixable)
    print(f"Found {total_findings} errors ({fixable_findings} fixable).")


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


def _deduplicated_paths(paths: tuple[str, ...]) -> tuple[str, ...]:
    """Return paths with duplicate physical targets removed while preserving display paths."""
    seen: set[str] = set()
    result: list[str] = []
    for path in paths:
        key = formatter.path_identity_key(path)
        if key in seen:
            continue
        seen.add(key)
        result.append(path)
    return tuple(result)


def _settings_overrides_from_args(args: argparse.Namespace) -> config.SettingsOverrides:
    """Build settings overrides from parsed command-line arguments."""
    return config.SettingsOverrides(
        line_length=args.line_length,
        line_ending=args.line_ending,
        indent_style=args.indent_style,
        indent_width=args.indent_width,
        include=_flatten_option_groups(args.include),
        extend_include=_flatten_option_groups(args.extend_include),
        exclude=_flatten_option_groups(args.exclude),
        extend_exclude=_flatten_option_groups(args.extend_exclude),
        respect_gitignore=args.respect_gitignore,
        force_exclude=args.force_exclude,
        experimental=args.experimental,
        output_format=args.output_format,
        select=_flatten_option_groups(args.select),
        extend_select=_flatten_option_groups(args.extend_select),
        ignore=_flatten_option_groups(args.ignore),
        fixable=_flatten_option_groups(args.fixable),
        extend_fixable=_flatten_option_groups(args.extend_fixable),
        unfixable=_flatten_option_groups(args.unfixable),
        per_file_ignores=_parse_per_file_options(args.per_file_ignores),
        extend_per_file_ignores=_parse_per_file_options(args.extend_per_file_ignores),
    )


def _flatten_option_groups(groups: list[list[str]] | None) -> tuple[str, ...] | None:
    """Flatten repeated CLI option groups while preserving an omitted option as None."""
    if groups is None:
        return None
    return tuple(value for group in groups for value in group)


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


def _enabled_label(value: bool) -> str:
    """Return a human-readable enabled state."""
    return "enabled" if value else "disabled"
