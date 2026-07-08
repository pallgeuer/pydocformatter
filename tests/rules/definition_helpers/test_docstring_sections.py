# First-party imports
from pydocformatter.cli.settings_check import DocstringConvention
from pydocformatter.rules.definition_helpers import docstring_sections


def test_convention_parses_sections_only_for_named_section_conventions() -> None:
    assert docstring_sections.convention_parses_sections(DocstringConvention.GOOGLE)
    assert docstring_sections.convention_parses_sections(DocstringConvention.NUMPY)
    assert not docstring_sections.convention_parses_sections(DocstringConvention.REST)
    assert not docstring_sections.convention_parses_sections(DocstringConvention.PEP257)


def test_canonical_section_name_uses_convention_specific_names() -> None:
    assert docstring_sections.canonical_section_name(DocstringConvention.GOOGLE, "arg") == "Arg"
    assert docstring_sections.canonical_section_name(DocstringConvention.GOOGLE, "keyword args") == "Keyword Args"
    assert docstring_sections.canonical_section_name(DocstringConvention.GOOGLE, "method") == "Method"
    assert docstring_sections.canonical_section_name(DocstringConvention.NUMPY, "other parameters") == "Other Parameters"
    assert docstring_sections.canonical_section_name(DocstringConvention.NUMPY, "parameter") == "Parameter"
    assert docstring_sections.canonical_section_name(DocstringConvention.NUMPY, "receive") == "Receive"
    assert docstring_sections.canonical_section_name(DocstringConvention.GOOGLE, "other parameters") is None


def test_plural_section_name_uses_convention_specific_names() -> None:
    assert docstring_sections.plural_section_name(DocstringConvention.GOOGLE, "Arg") == "Args"
    assert docstring_sections.plural_section_name(DocstringConvention.GOOGLE, "Keyword Argument") == "Keyword Arguments"
    assert docstring_sections.plural_section_name(DocstringConvention.GOOGLE, "Warn") == "Warns"
    assert docstring_sections.plural_section_name(DocstringConvention.NUMPY, "Other Param") == "Other Params"
    assert docstring_sections.plural_section_name(DocstringConvention.NUMPY, "Receive") == "Receives"


def test_term_normalized_section_name_uses_convention_specific_names() -> None:
    assert docstring_sections.term_normalized_section_name(DocstringConvention.GOOGLE, "Arguments") == "Args"
    assert docstring_sections.term_normalized_section_name(DocstringConvention.GOOGLE, "Keyword Arguments") == "Keyword Args"
    assert docstring_sections.term_normalized_section_name(DocstringConvention.GOOGLE, "Warns") is None
    assert docstring_sections.term_normalized_section_name(DocstringConvention.GOOGLE, "Warnings") is None
    assert docstring_sections.term_normalized_section_name(DocstringConvention.NUMPY, "Other Params") == "Other Parameters"


def test_section_order_rank_uses_convention_specific_ordering() -> None:
    assert docstring_sections.section_order_rank(DocstringConvention.GOOGLE, "Arg") == 0
    assert docstring_sections.section_order_rank(DocstringConvention.GOOGLE, "Args") == 0
    assert docstring_sections.section_order_rank(DocstringConvention.GOOGLE, "Warn") == 2
    assert docstring_sections.section_order_rank(DocstringConvention.NUMPY, "Parameter") == 2
    assert docstring_sections.section_order_rank(DocstringConvention.NUMPY, "Returns") == 3
    assert docstring_sections.section_order_rank(DocstringConvention.GOOGLE, "Examples") is None


def test_repeated_section_key_normalizes_aliases() -> None:
    assert docstring_sections.repeated_section_key(DocstringConvention.GOOGLE, "Arg") == "args"
    assert docstring_sections.repeated_section_key(DocstringConvention.GOOGLE, "Arguments") == "args"
    assert docstring_sections.repeated_section_key(DocstringConvention.GOOGLE, "Raise") == "raises"
    assert docstring_sections.repeated_section_key(DocstringConvention.GOOGLE, "Warn") == "warns"
    assert docstring_sections.repeated_section_key(DocstringConvention.NUMPY, "Parameter") == "parameters"
    assert docstring_sections.repeated_section_key(DocstringConvention.NUMPY, "Other Params") == "other parameters"
    assert docstring_sections.repeated_section_key(DocstringConvention.NUMPY, "Other Param") == "other parameters"
    assert docstring_sections.repeated_section_key(DocstringConvention.NUMPY, "Warning") == "warnings"
    assert docstring_sections.repeated_section_key(DocstringConvention.NUMPY, "Warn") == "warns"
    assert docstring_sections.repeated_section_key(DocstringConvention.REST, "param") == "param"
