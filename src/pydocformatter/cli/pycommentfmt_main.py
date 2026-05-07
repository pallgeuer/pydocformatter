from pydocformatter.cli.common import run_formatter
from pydocformatter.config import FormatterSettings
from pydocformatter.formatters.pycommentfmt import format_comments


def _format_comments(path: str, settings: FormatterSettings, check: bool) -> bool:
    """Format one path using resolved pycommentfmt settings."""
    return format_comments(path, settings.line_length, check)


def main() -> None:
    """Run the pycommentfmt command-line entry point.

    Returns:
        None: The command runs the shared formatter CLI and may terminate the process
            through `run_formatter`.
    """
    run_formatter(
        tool_name="pycommentfmt",
        description="Format Python comments.",
        line_length_subject="comments",
        format_file=_format_comments,
    )
