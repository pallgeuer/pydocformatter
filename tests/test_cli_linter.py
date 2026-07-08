# Standard library imports
import json
import unittest
import contextlib
import unittest.mock
from io import StringIO

# Third-party imports
import pytest

# First-party imports
import pydocformatter.cli.main as pydocfmt_cli


class TestCLILinter(unittest.TestCase):
    def test_pydocfmt_linter_prints_linter_table(self) -> None:
        stdout = StringIO()
        argv = ["pydocfmt", "linter"]
        with unittest.mock.patch("sys.argv", argv), contextlib.redirect_stdout(stdout):
            exit_code = pydocfmt_cli.main()

        assert exit_code == 0
        assert stdout.getvalue() == "PCF pydocformatter comment formatting\nPDF pydocformatter docstring formatting\n"

    def test_pydocfmt_linter_prints_linter_json(self) -> None:
        stdout = StringIO()
        argv = ["pydocfmt", "linter", "--output-format", "json"]
        with unittest.mock.patch("sys.argv", argv), contextlib.redirect_stdout(stdout):
            exit_code = pydocfmt_cli.main()

        output = json.loads(stdout.getvalue())
        assert exit_code == 0
        assert output == [
            {"prefix": "PCF", "name": "pydocformatter comment formatting", "url": "https://github.com/pallgeuer/pydocformatter"},
            {"prefix": "PDF", "name": "pydocformatter docstring formatting", "url": "https://github.com/pallgeuer/pydocformatter"},
        ]

    def test_pydocfmt_linter_rejects_invalid_output_format(self) -> None:
        stderr = StringIO()
        argv = ["pydocfmt", "linter", "--output-format", "yaml"]
        with unittest.mock.patch("sys.argv", argv), contextlib.redirect_stderr(stderr), pytest.raises(SystemExit) as cm:
            pydocfmt_cli.main()

        assert cm.value.code == 2
        assert "invalid choice: 'yaml'" in stderr.getvalue()

    def test_pydocfmt_linter_help_and_help_linter_print_linter_help(self) -> None:
        for argv in (["pydocfmt", "linter", "--help"], ["pydocfmt", "help", "linter"]):
            stdout = StringIO()
            with unittest.mock.patch("sys.argv", argv), contextlib.redirect_stdout(stdout):
                if argv[-1] == "--help":
                    with pytest.raises(SystemExit) as cm:
                        pydocfmt_cli.main()
                    assert cm.value.code == 0
                else:
                    exit_code = pydocfmt_cli.main()
                    assert exit_code == 0
            assert "Usage: pydocfmt linter" in stdout.getvalue()
            assert "--output-format {text,json}" in stdout.getvalue()

    def test_pydocfmt_help_lists_linter_command(self) -> None:
        stdout = StringIO()
        argv = ["pydocfmt", "--help"]
        with unittest.mock.patch("sys.argv", argv), contextlib.redirect_stdout(stdout), pytest.raises(SystemExit) as cm:
            pydocfmt_cli.main()

        assert cm.value.code == 0
        assert "linter" in stdout.getvalue()


if __name__ == "__main__":
    unittest.main()
