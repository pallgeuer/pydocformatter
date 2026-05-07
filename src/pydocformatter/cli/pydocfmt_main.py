from pydocformatter.cli.common import run_formatter
from pydocformatter.config import FormatterSettings
from pydocformatter.formatters.pydocfmt import format_docstrings


def _format_docstrings(path: str, settings: FormatterSettings, check: bool) -> bool:
    """Format one path using resolved pydocfmt settings."""
    return format_docstrings(
        path,
        settings.line_length,
        check,
        indent_style=settings.indent_style,
        indent_width=settings.indent_width,
    )


def main() -> None:
    """Run the pydocfmt command-line entry point.

    Returns:
        None: The command runs the shared formatter CLI and may terminate the process
            through `run_formatter`.
    """
    run_formatter(
        tool_name="pydocfmt",
        description="Format Python docstrings.",
        line_length_subject="docstrings",
        format_file=_format_docstrings,
    )
