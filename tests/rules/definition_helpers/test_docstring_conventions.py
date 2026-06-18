import pydocformatter.rules.definition_helpers.docstring_conventions as docstring_conventions
from pydocformatter.cli.settings_check import DocstringConvention


def test_ignored_conventions_except_keeps_only_allowed_conventions_enabled() -> None:
    assert docstring_conventions.ignored_conventions_except(DocstringConvention.GOOGLE, DocstringConvention.NUMPY) == (
        DocstringConvention.NONE,
        DocstringConvention.REST,
        DocstringConvention.PEP257,
    )
