# First-party imports
from pydocformatter.cli.settings_check import DocstringConvention
from pydocformatter.rules.definition_helpers import docstring_conventions


def test_ignored_conventions_except_keeps_only_allowed_conventions_enabled() -> None:
    assert docstring_conventions.ignored_conventions_except(DocstringConvention.GOOGLE, DocstringConvention.NUMPY) == (DocstringConvention.NONE, DocstringConvention.PEP257, DocstringConvention.REST)
