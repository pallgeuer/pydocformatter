# Standard library imports
import dataclasses

# Third-party imports
import pytest

# First-party imports
import tests.rules.PDF.helpers as pdf_helpers
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definitions.PDF.PDF000_docstring_literal_normalization import PDF000DocstringLiteralNormalization
from pydocformatter.rules.definitions.PDF.PDF202_empty_docstring import PDF202EmptyDocstring
from pydocformatter.rules.definitions.PDF.PDF203_summary_too_long import PDF203SummaryTooLong
from pydocformatter.rules.definitions.PDF.PDF212_missing_summary import PDF212MissingSummary
from tests import rule_helpers


contexts = pdf_helpers.contexts_for("PDF212")
format_source = pdf_helpers.formatter_for("PDF212")


@pytest.mark.parametrize(
    ("source", "settings", "expected_lines"),
    [
        ('def function(value):\n    """Args:\n        value: Description.\n    """\n', CheckSettings(select=("PDF212",), docstring_convention=DocstringConvention.GOOGLE), (2, 3, 4)),
        (
            'def function(value):\n    """Parameters\n    ----------\n    value : int\n        Description.\n    """\n',
            CheckSettings(select=("PDF212",), docstring_convention=DocstringConvention.NUMPY),
            (2, 3, 4, 5, 6),
        ),
        ('def function(value):\n    """:param value: Description.\n    :returns: Result.\n    """\n', CheckSettings(select=("PDF212",), docstring_convention=DocstringConvention.REST), (2, 3, 4)),
        ('def function():\n    """- first\n    - second\n    """\n', CheckSettings(select=("PDF212",)), (2, 3, 4)),
        ('def function():\n    """# Heading\n    """\n', CheckSettings(select=("PDF212",)), (2, 3)),
        ('def function():\n    """>>> call()\n    """\n', CheckSettings(select=("PDF212",)), (2, 3)),
        ('def function():\n    """```python\n    call()\n    ```\n    """\n', CheckSettings(select=("PDF212",)), (2, 3, 4, 5)),
        ('def function():\n    """> quoted\n    """\n', CheckSettings(select=("PDF212",)), (2, 3)),
        ('def function():\n    """| A | B |\n    | --- | --- |\n    | 1 | 2 |\n    """\n', CheckSettings(select=("PDF212",)), (2, 3, 4, 5)),
        ('def function():\n    """.. note::\n        Body.\n    """\n', CheckSettings(select=("PDF212",)), (2, 3, 4)),
        ('def function():\n    """Example::\n\n        call()\n    """\n', CheckSettings(select=("PDF212",)), (2, 3, 4, 5)),
        ('def function():\n    """\n        indented\n        verbatim\n    """\n', CheckSettings(select=("PDF212",)), (2, 3, 4, 5)),
    ],
)
def test_reports_leading_convention_and_generic_structures(source: str, settings: CheckSettings, expected_lines: tuple[int, ...]) -> None:
    result = format_source(source, settings=settings)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == (expected_lines,)
    assert tuple(finding.message for finding in result.unfixed_findings) == ("Docstring is missing a summary",)
    assert not result.unfixed_findings[0].fixable


def test_reports_once_when_later_prose_follows_multiple_leading_structures() -> None:
    source = 'def function():\n    """- first\n    - second\n\n    Return the choices.\n\n    > Detail.\n    """\n'
    result = format_source(source)

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2, 3, 4, 5, 6, 7, 8),)


def test_ignores_leading_and_trailing_blank_blocks_when_deciding_summary_presence() -> None:
    source = 'def summary():\n    """\n    Summary.\n    """\n\ndef section(value):\n    """\n    Args:\n        value: Description.\n    """\n\ndef compact_label():\n    """\n    Result:\n    """\n'
    result = format_source(source, settings=CheckSettings(select=("PDF212",), docstring_convention=DocstringConvention.GOOGLE))

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((7, 8, 9, 10),)


@pytest.mark.parametrize(
    "source",
    [
        'def function():\n    """Summary."""\n',
        'def function():\n    """Summary line\n    continuation line.\n    """\n',
        'def function():\n    """Summary.\n\n    Body.\n    """\n',
        'def function():\n    """Result:"""\n',
        'def function():\n    """   """\n',
        "def function():\n    pass\n",
        'def function():\n    """Summary."""\n    """Args:\n        ignored: Additional string.\n    """\n',
    ],
)
def test_skips_present_empty_absent_and_ignored_summaries(source: str) -> None:
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_colon_header_with_following_content_is_not_a_summary() -> None:
    source = 'def function():\n    """Accepted values:\n    fast and safe.\n    """\n'
    result = format_source(source)

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2, 3, 4),)


def test_checks_primary_and_supported_attached_attribute_docstrings() -> None:
    source = (
        '"""Notes:\n    Module details.\n"""\n\n'
        'module_value = 1\n"""Notes:\n    Module value details.\n"""\n\n'
        'class Client:\n    """Notes:\n        Class details.\n    """\n\n'
        '    class_value = 1\n    """Notes:\n        Class value details.\n    """\n\n'
        '    class Nested:\n        """Notes:\n            Nested details.\n        """\n\n'
        '    def __init__(self):\n        """Notes:\n            Initializer details.\n        """\n        self.instance_value = 1\n        """Notes:\n            Instance value details.\n        """\n\n'
        '    @property\n    def value(self):\n        """Notes:\n            Property details.\n        """\n\n'
        '    def __str__(self):\n        """Notes:\n            Dunder details.\n        """\n\n'
        'def function():\n    """Notes:\n        Function details.\n    """\n\n'
        'def outer():\n    """Outer."""\n\n    def nested():\n        """Notes:\n            Nested function details.\n        """\n'
    )
    result = format_source(source, settings=CheckSettings(select=("PDF212",), docstring_convention=DocstringConvention.GOOGLE))

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == (
        (1, 2, 3),
        (6, 7, 8),
        (11, 12, 13),
        (16, 17, 18),
        (21, 22, 23),
        (26, 27, 28),
        (30, 31, 32),
        (36, 37, 38),
        (41, 42, 43),
        (46, 47, 48),
        (54, 55, 56),
    )
    assert all(finding.rule == PDF212MissingSummary.meta for finding in result.unfixed_findings)


def test_reports_once_for_multi_target_attribute_docstring_and_ignores_unsupported_attachment_locations() -> None:
    source = (
        'left = right = 1\n"""Notes:\n    Shared details.\n"""\n\n'
        'class Client:\n    def __init__(self):\n        local = 1\n        """Notes:\n            Ignored local details.\n        """\n        self.supported = 1\n        """Notes:\n            Supported details.\n        """\n\n'
        '    def method(self):\n        self.late = 1\n        """Notes:\n            Ignored non-initializer details.\n        """\n'
    )
    result = format_source(source, settings=CheckSettings(select=("PDF212",), docstring_convention=DocstringConvention.GOOGLE))

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2, 3, 4), (13, 14, 15))


def test_reports_distinct_same_line_attached_docstrings_without_deduplicating_findings() -> None:
    source = 'first = 1; """Notes:"""; second = 2; """Notes:"""\n'
    result = format_source(source, settings=CheckSettings(select=("PDF212",), docstring_convention=DocstringConvention.GOOGLE))

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((1,), (1,))


@pytest.mark.parametrize(
    ("source", "expected_lines"),
    [
        ('def function():\n    """Args:\n        value: Description.\n"""\n', (2, 3, 4)),
        ('def function():\n    r"""Args:\n        value: Description.\n    """\n', (2, 3, 4)),
        ("def function():\n    '''Args:\n        value: Description.\n    '''\n", (2, 3, 4)),
        ('def function():\n    """Args:\\n    value: Description."""\n', (2,)),
        ('def function():\n    ("Args:\\n"\n     # Interstitial comment.\n     "    value: Description.")\n', (2, 3, 4)),
        ('def function():\n    (\n        "Args:\\n"\n        "    value: Description."\n    )\n', (3, 4)),
    ],
)
def test_targets_complete_physical_string_expression(source: str, expected_lines: tuple[int, ...]) -> None:
    result = format_source(source, settings=CheckSettings(select=("PDF212",), docstring_convention=DocstringConvention.GOOGLE))

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == (expected_lines,)


def test_preserves_crlf_and_reports_the_same_physical_lines() -> None:
    source = 'def function():\r\n    """Args:\r\n        value: Description.\r\n    """\r\n'
    result = format_source(source, settings=CheckSettings(select=("PDF212",), docstring_convention=DocstringConvention.GOOGLE))

    assert result.new_source == source
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2, 3, 4),)


@pytest.mark.parametrize(
    ("source", "convention", "missing"),
    [
        ('def function(value):\n    """:param value: Description."""\n', DocstringConvention.REST, True),
        ('def function(value):\n    """:param value: Description."""\n', DocstringConvention.PEP257, False),
        ('def function(value):\n    """:param value missing terminator"""\n', DocstringConvention.REST, True),
        ('def function(value):\n    """Args:\n        value: Description.\n    """\n', DocstringConvention.PEP257, True),
        ('def function(value):\n    """Parameters\n    ----------\n    value : int\n        Description.\n    """\n', DocstringConvention.GOOGLE, True),
        ('def function(value):\n    """Args\n        value: Description.\n    """\n', DocstringConvention.GOOGLE, True),
    ],
)
def test_convention_specific_malformed_and_generic_fallback_classification(source: str, convention: DocstringConvention, missing: bool) -> None:
    result = format_source(source, settings=CheckSettings(select=("PDF212",), docstring_convention=convention))

    assert bool(result.unfixed_findings) is missing


@pytest.mark.parametrize("convention", tuple(DocstringConvention))
def test_generic_missing_summary_is_enabled_under_every_convention(convention: DocstringConvention) -> None:
    source = 'def function():\n    """- item"""\n'
    result = format_source(source, settings=CheckSettings(select=("PDF212",), docstring_convention=convention))

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2,),)


@pytest.mark.parametrize(
    ("source", "changes", "missing"),
    [
        ('def function():\n    """- item"""\n', {"docstring_parse_list_items": False}, False),
        ('def function():\n    """# Heading"""\n', {"docstring_parse_headings": False}, False),
        ('def function():\n    """```python\n    call()\n    ```"""\n', {"docstring_parse_code_fences": False}, False),
        ('def function():\n    """> quote"""\n', {"docstring_parse_block_quotes": False}, False),
        ('def function():\n    """| A | B |\n    | --- | --- |\n    | 1 | 2 |"""\n', {"docstring_parse_tables": False}, False),
        ('def function():\n    """>>> call()"""\n', {"docstring_parse_doctests": False}, True),
        ('def function():\n    """>>> call()"""\n', {"docstring_parse_doctests": False, "docstring_parse_block_quotes": False}, False),
        ('def function():\n    """.. note::\n        Body."""\n', {"docstring_parse_directives": False}, True),
        ('def function():\n    """.. note::"""\n', {}, True),
        ('def function():\n    """.. note::"""\n', {"docstring_parse_directives": False}, False),
        ('def function():\n    """.. versionadded: 1.0"""\n', {}, True),
        ('def function():\n    """.. versionadded: 1.0"""\n', {"docstring_parse_directives": False}, False),
        ('def function():\n    """Example::\n\n        call()"""\n', {"docstring_parse_literal_blocks": False}, True),
    ],
)
def test_parser_setting_fallthrough_uses_the_prepared_block_tree(source: str, changes: dict[str, bool], missing: bool) -> None:
    settings = dataclasses.replace(CheckSettings(select=("PDF212",)), **changes)
    result = format_source(source, settings=settings)

    assert bool(result.unfixed_findings) is missing


def test_empty_missing_and_multiline_summary_rules_remain_disjoint() -> None:
    source = 'def empty():\n    """   """\n\n\ndef missing():\n    """- item"""\n\n\ndef multiline():\n    """Summary line\n    continuation line."""\n'
    settings = CheckSettings(select=("PDF202", "PDF203", "PDF212"))
    result = format_source(source, settings=settings)

    assert tuple((finding.rule, finding.line_numbers) for finding in result.unfixed_findings) == (
        (PDF202EmptyDocstring.meta, (2,)),
        (PDF203SummaryTooLong.meta, (10, 11)),
        (PDF212MissingSummary.meta, (6,)),
    )


def test_reports_final_reparsed_lines_after_literal_normalization_expands_a_compact_suite() -> None:
    source = 'def function(value): ("Args:\\n" "    value: Description.")\n'
    settings = CheckSettings(select=("PDF000", "PDF212"), docstring_convention=DocstringConvention.GOOGLE)
    result = format_source(source, settings=settings)

    assert result.new_source == 'def function(value): ("""Args:\n    value: Description.""")\n'
    assert result.fixed_findings[PDF000DocstringLiteralNormalization.meta] == 1
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((1, 2),)


def test_local_component_and_closing_line_suppressions_cover_the_whole_docstring() -> None:
    local_source = 'def local():\n    # pydocfmt: ignore[PDF212]\n    """Args:\n        value: Description.\n    """\n'
    component_source = 'def component():\n    ("Args:\\n"  # noqa: PDF212\n     "    value: Description.")\n'
    closing_source = 'def closing():\n    """Args:\n        value: Description.\n    """  # noqa: PDF212\n'

    assert not format_source(local_source).unfixed_findings
    assert not format_source(component_source).unfixed_findings
    assert not format_source(closing_source).unfixed_findings


def test_interstitial_suppression_does_not_cover_a_concatenated_docstring() -> None:
    source = 'def function():\n    ("Args:\\n"\n     # noqa: PDF212\n     "    value: Description.")\n'
    result = format_source(source, settings=CheckSettings(select=("PCF006", "PDF212")))

    assert tuple((finding.rule.code.tag, finding.line_numbers) for finding in result.unfixed_findings) == (("PDF212", (2, 3, 4)), ("PCF006", (3,)))


def test_compact_suite_docstrings_are_checked_on_their_single_physical_line() -> None:
    source = 'def function(): """Args:"""; return None\n\n\nclass Client: """Attributes:"""\n'
    result = format_source(source, settings=CheckSettings(select=("PDF212",), docstring_convention=DocstringConvention.GOOGLE))

    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((1,), (4,))


@pytest.mark.parametrize("selector", ["PDF212", "PDF2", "PDF", "ALL"])
def test_broad_and_exact_selectors_enable_rule(selector: str) -> None:
    source = 'def function(value):\n    """Args:\n        value: Description.\n    """\n'
    result = format_source(source, settings=CheckSettings(select=(selector,), docstring_convention=DocstringConvention.GOOGLE), fix=False)

    assert PDF212MissingSummary.meta in {finding.rule for finding in result.unfixed_findings}


def test_direct_rule_hook_returns_valid_diagnostic() -> None:
    source = 'def function():\n    """- item"""\n'
    _, context = contexts(source)
    findings = rule_helpers.rule_findings(PDF212MissingSummary, context)

    assert tuple(finding.line_numbers for finding in findings) == ((2,),)
