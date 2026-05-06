from pydocformatter.cli.common import run_formatter
from pydocformatter.formatters.pycommentfmt import format_comments


def main() -> None:
    """Main entry point for the script."""
    run_formatter(
        tool_name="pycommentfmt",
        description="Format Python comments.",
        line_length_subject="comments",
        format_file=format_comments,
    )
