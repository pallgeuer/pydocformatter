import contextlib
import re
import tempfile
import textwrap
import unittest
from io import StringIO
from pathlib import Path

import pydocformatter.formatters.google_docstrings as google_docstrings
import pydocformatter.formatters.pydocfmt as pydocfmt
from pydocformatter.config import FormatterSettings


class TestPyDocFmt(unittest.TestCase):
    def _format_and_check(self, source: str, expected: str, line_length: int = 88, indent: str = "") -> None:
        formatted = google_docstrings.reflow(source.strip(), line_length, indent)

        self.assertEqual("".join(formatted).strip(), expected.strip())

    def test_single_line_docstring(self) -> None:
        source = """Short summary."""
        expected = '''    """Short summary."""'''
        self._format_and_check(source, expected)

    def test_summary_and_description(self) -> None:
        doc = """Short summary.

A longer description follows this, explaining more details
about what the function does."""
        expected = textwrap.dedent("""\
            \"\"\"Short summary.

            A longer description follows this, explaining more details about what the function does.
            \"\"\"
        """)
        self._format_and_check(doc, expected)

    def test_description_with_multiple_paragraphs(self) -> None:
        doc = """Short summary.

This is the first paragraph of the description.

This is the second paragraph with more explanation."""
        expected = textwrap.dedent("""\
            \"\"\"Short summary.

            This is the first paragraph of the description.

            This is the second paragraph with more explanation.
            \"\"\"
        """)
        self._format_and_check(doc, expected)

    def test_description_with_list(self) -> None:
        doc = """Does something.
        
Here are the parameters:
- foo: does foo
- bar: does bar"""
        expected = textwrap.dedent("""\
            \"\"\"Does something.
                                   
            Here are the parameters:
            - foo: does foo
            - bar: does bar
            \"\"\"
        """)
        self._format_and_check(doc, expected)

    def test_description_with_multiple_lists(self) -> None:
        doc = """Does something.

Here are the parameters:
- foo: does foo
- bar: does bar

Here are some more parameters:
- baz: does baz
- qux: does qux"""
        expected = textwrap.dedent("""\
            \"\"\"Does something.

            Here are the parameters:
            - foo: does foo
            - bar: does bar

            Here are some more parameters:
            - baz: does baz
            - qux: does qux
            \"\"\"
        """)
        self._format_and_check(doc, expected)

    def test_args_section(self) -> None:
        doc = """Does something.

Args:
    foo (str): the foo param which is very long and needs to be wrapped to fit within the line length limit.
    bar: the bar param."""
        expected = textwrap.dedent("""\
            \"\"\"Does something.
                                   
            Args:
                foo (str): the foo param which is very long and needs to be wrapped to fit within
                    the line length limit.
                bar: the bar param.
            \"\"\"
        """)
        self._format_and_check(doc, expected)

    def test_args_section_with_two_space_indent_width(self) -> None:
        doc = """Does something.

Args:
    foo (str): the foo param which is very long and needs to be wrapped to fit within the line length limit."""
        expected = textwrap.dedent("""\
            \"\"\"Does something.
            
            Args:
              foo (str): the foo param which is very long and needs to be wrapped to fit
                within the line length limit.
            \"\"\"
        """)
        formatted = google_docstrings.reflow(doc.strip(), 78, "", indent_style="space", indent_width=2)

        self.assertEqual("".join(formatted).strip(), expected.strip())

    def test_args_section_with_tab_indent_style(self) -> None:
        doc = """Does something.

Args:
    foo (str): the foo param which is very long and needs to be wrapped to fit within the line length limit."""
        expected = textwrap.dedent("""\
            \"\"\"Does something.
            
            Args:
            \tfoo (str): the foo param which is very long and needs to be wrapped to fit
            \t\twithin the line length limit.
            \"\"\"
        """)
        formatted = google_docstrings.reflow(doc.strip(), 78, "", indent_style="tab", indent_width=4)

        self.assertEqual("".join(formatted).strip(), expected.strip())

    def test_tab_line_length_uses_non_standard_indent_width(self) -> None:
        doc = """Does.

Args:
    foo: one two three four five six seven"""
        expected = textwrap.dedent("""\
            \"\"\"Does.
            
            Args:
            \tfoo: one two three
            \t\tfour five six seven
            \"\"\"
        """)
        formatted = google_docstrings.reflow(doc.strip(), 24, "", indent_style="tab", indent_width=2)

        self.assertEqual("".join(formatted).strip(), expected.strip())
        for line in formatted:
            visual_width = sum(2 if char == "\t" else 1 for char in line.rstrip("\n"))
            self.assertLessEqual(visual_width, 24)

    def test_tab_indent_preserves_space_base_indent(self) -> None:
        doc = """Does something.

Args:
    foo: a parameter that should be normalized."""
        expected = '    """Does something.\n' "\n    Args:\n    \tfoo: a parameter that should be normalized.\n" '    """'
        formatted = google_docstrings.reflow(doc.strip(), 88, "    ", indent_style="tab", indent_width=4)

        self.assertEqual("".join(formatted).strip(), expected.strip())

    def test_description_preserves_single_base_indent(self) -> None:
        doc = """Does something.

This description should keep exactly one base indentation level after wrapping."""
        expected = '    """Does something.\n' "\n    This description should keep exactly one base indentation level after\n    wrapping.\n" '    """'
        formatted = google_docstrings.reflow(doc.strip(), 76, "    ")

        self.assertEqual("".join(formatted).strip(), expected.strip())

    def test_returns_section(self) -> None:
        doc = """Returns a result.
        
Returns:
    int: the computed result which is very long and needs to be wrapped to fit within the line length limit."""
        expected = textwrap.dedent("""\
            \"\"\"Returns a result.

            Returns:
                int: the computed result which is very long and needs to be wrapped to fit within
                    the line length limit.
            \"\"\"
        """)
        self._format_and_check(doc, expected)

    def test_yields_section(self) -> None:
        doc = """Yields output.

Yields:
    str: a line of output text that should be wrapped if it's too long to fit within the line length limit."""
        expected = textwrap.dedent("""\
            \"\"\"Yields output.
            
            Yields:
                str: a line of output text that should be wrapped if it's too long to fit within the
                    line length limit.
            \"\"\"
        """)
        self._format_and_check(doc, expected)

    def test_raises_section(self) -> None:
        doc = """Raises things.
    
Raises:
    ValueError: if input is invalid.
    TypeError: if the type is wrong."""
        expected = textwrap.dedent("""\
            \"\"\"Raises things.
            
            Raises:
                `ValueError`: if input is invalid.
                `TypeError`: if the type is wrong.
            \"\"\"
        """)
        self._format_and_check(doc, expected)

    def test_examples_section_fenced(self) -> None:
        doc = """Gives an example.

Examples:
    ```
    x = 1
    print(x)
    ```"""
        expected = textwrap.dedent("""\
            \"\"\"Gives an example.
            
            Examples:
                ```
                x = 1
                print(x)
                ```
            \"\"\"
        """)
        self._format_and_check(doc, expected)

    def test_examples_section_unfenced(self) -> None:
        doc = """Gives an example.

Examples:
    x = 1
    print(x)
"""
        expected = textwrap.dedent("""\
            \"\"\"Gives an example.

            Examples:
                ```
                x = 1
                print(x)
                ```
            \"\"\"
        """)
        self._format_and_check(doc, expected)

    def test_examples_section_with_code_block(self) -> None:
        doc = """Gives an example.

Examples:
    def example_function():
        pass
    example_function()"""
        expected = textwrap.dedent("""\
            \"\"\"Gives an example.

            Examples:
                ```
                def example_function():
                    pass
                example_function()
                ```
            \"\"\"
        """)
        self._format_and_check(doc, expected)

    def test_full_docstring_all_section(self) -> None:
        doc = """Format a section with parameters.

This function handles multiple Google style docstring sections including Args, Returns, Raises, and Examples.

Acceptable formats include:
- `param (type) : description`
- `param: description`

Args:
    param1 (int): a parameter that should be documented and wrapped as needed.
    param2: another one.

Returns:
    bool: True if successful, False otherwise.

Raises:
    ValueError: if the input is invalid.

Examples:
    result = run()
    print(result)"""
        expected = textwrap.dedent("""\
            \"\"\"Format a section with parameters.

            This function handles multiple Google style docstring sections including Args, Returns,
            Raises, and Examples.

            Acceptable formats include:
            - `param (type) : description`
            - `param: description`

            Args:
                param1 (int): a parameter that should be documented and wrapped as needed.
                param2: another one.

            Returns:
                bool: True if successful, False otherwise.

            Raises:
                `ValueError`: if the input is invalid.

            Examples:
                ```
                result = run()
                print(result)
                ```
            \"\"\"
        """)
        self._format_and_check(doc, expected)

    def test_check_mode_flags_unformatted_file(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".py", delete=False) as tf:
            tf.write('def foo():\n    """Does something.\n\nArgs:\n    x (int): some parameter.\n    """\n    pass\n')
            tf.flush()
            path = tf.name

        needs_fixing = pydocfmt.format_docstrings(path, FormatterSettings(line_length=72), check=True)
        Path(path).unlink()
        self.assertTrue(needs_fixing, "The docstring should need formatting.")

    def test_check_mode_flags_formatted_file(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".py", delete=False) as tf:
            tf.write('def foo():\n    """Does something.\n\n    Args:\n        x (int): some parameter.\n    """\n    pass\n')
            tf.flush()
            path = tf.name

        needs_fixing = pydocfmt.format_docstrings(path, FormatterSettings(line_length=72), check=True)
        Path(path).unlink()
        self.assertFalse(needs_fixing, "The docstring should not need formatting.")

    def test_no_op_on_formatted_files(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".py", delete=False) as tf:
            tf.write('def foo():\n    """Does something.\n\n    Args:\n        x (int): some parameter.\n    """\n    pass\n')
            tf.flush()
            path = tf.name

        modified = pydocfmt.format_docstrings(path, FormatterSettings(line_length=72), check=False)
        Path(path).unlink()
        self.assertFalse(modified, "The file should not be modified if already formatted.")

    def test_check_mode_reports_single_line_location(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".py", delete=False) as tf:
            tf.write('def foo():\n    """This is a very long single-line docstring that should be reflowed by the formatter due to line length."""\n    pass\n')
            tf.flush()
            path = tf.name

        output = StringIO()
        with contextlib.redirect_stdout(output):
            needs_fixing = pydocfmt.format_docstrings(path, FormatterSettings(line_length=72), check=True)
        Path(path).unlink()

        self.assertTrue(needs_fixing, "The docstring should need formatting.")
        self.assertRegex(
            output.getvalue().strip(),
            rf"^{re.escape(path)}: Needs docstring formatting on line 2$",
        )

    def test_check_mode_reports_compressed_ranges(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".py", delete=False) as tf:
            tf.write(
                'def foo():\n    """Does something.\n\nArgs:\n    x (int): some parameter.\n    """\n    pass\n\n\n'
                'def bar():\n    """Another long summary that should be wrapped because it is intentionally too long for the selected line length."""\n    pass\n'
            )
            tf.flush()
            path = tf.name

        output = StringIO()
        with contextlib.redirect_stdout(output):
            needs_fixing = pydocfmt.format_docstrings(path, FormatterSettings(line_length=72), check=True)
        Path(path).unlink()

        self.assertTrue(needs_fixing, "Docstrings should need formatting.")
        self.assertRegex(
            output.getvalue().strip(),
            rf"^{re.escape(path)}: Needs docstring formatting on lines 2-6, 11$",
        )


if __name__ == "__main__":
    unittest.main()
