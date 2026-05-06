from pydocformatter.cli.common import run_formatter
from pydocformatter.formatters.pydocfmt import format_docstrings


def main() -> None:
    """Main entry point for the script."""
    run_formatter(
        tool_name="pydocfmt",
        description="Format Python docstrings.",
        line_length_subject="docstrings",
        format_file=format_docstrings,
    )
