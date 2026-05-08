import pydocformatter.cli.common as cli_common
import pydocformatter.formatters.pydocfmt as pydocfmt


def main() -> int:
    """Run the pydocfmt command-line entry point."""
    return cli_common.run_formatter(
        tool_name="pydocfmt",
        description="Format Python docstrings.",
        line_length_subject="docstrings",
        format_file=pydocfmt.format_docstrings,
    )
