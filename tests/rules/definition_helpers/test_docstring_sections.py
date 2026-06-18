import pydocformatter.rules.definition_helpers.docstring_sections as docstring_sections
from pydocformatter.cli.settings_check import DocstringConvention


def test_convention_parses_sections_only_for_named_section_conventions() -> None:
    assert docstring_sections.convention_parses_sections(DocstringConvention.GOOGLE)
    assert docstring_sections.convention_parses_sections(DocstringConvention.NUMPY)
    assert not docstring_sections.convention_parses_sections(DocstringConvention.REST)
    assert not docstring_sections.convention_parses_sections(DocstringConvention.PEP257)


def test_canonical_section_name_uses_convention_specific_names() -> None:
    assert docstring_sections.canonical_section_name(DocstringConvention.GOOGLE, "keyword args") == "Keyword Args"
    assert docstring_sections.canonical_section_name(DocstringConvention.NUMPY, "other parameters") == "Other Parameters"
    assert docstring_sections.canonical_section_name(DocstringConvention.GOOGLE, "other parameters") is None


def test_section_order_rank_uses_convention_specific_ordering() -> None:
    assert docstring_sections.section_order_rank(DocstringConvention.GOOGLE, "Args") == 0
    assert docstring_sections.section_order_rank(DocstringConvention.NUMPY, "Returns") == 3
    assert docstring_sections.section_order_rank(DocstringConvention.GOOGLE, "Examples") is None


def test_repeated_section_key_normalizes_aliases() -> None:
    assert docstring_sections.repeated_section_key(DocstringConvention.GOOGLE, "Arguments") == "args"
    assert docstring_sections.repeated_section_key(DocstringConvention.NUMPY, "Other Params") == "other parameters"
    assert docstring_sections.repeated_section_key(DocstringConvention.REST, "param") == "param"
