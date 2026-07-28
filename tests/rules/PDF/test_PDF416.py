"""Tests for PDF416 type-spelling-normalization."""

# Third-party imports
import pytest

# First-party imports
import tests.rules.PDF.helpers as pdf_helpers
from pydocformatter import rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringConvention
from pydocformatter.rules.definition_helpers import type_expressions
from pydocformatter.rules.definitions.PDF.PDF004_docstring_suspicious_unicode import PDF004DocstringSuspiciousUnicode
from pydocformatter.rules.definitions.PDF.PDF416_type_spelling_normalization import PDF416TypeSpellingNormalization


format_source = pdf_helpers.formatter_for("PDF416")


def test_metadata() -> None:
    """Expose the stable sometimes-fixable rule identity."""
    assert PDF416TypeSpellingNormalization.meta.name == "type-spelling-normalization"
    assert PDF416TypeSpellingNormalization.meta.message == "Docstring type spelling should be normalized"
    assert PDF416TypeSpellingNormalization.meta.stable_since == "1.1.0"


def test_normalizes_combined_google_type_spelling_defects() -> None:
    """Apply the conservative period, grouping, and none pipeline."""
    source = 'def lookup(key):\n    """Look up a value.\n\n    Args:\n        key (((str))): Lookup key.\n\n    Returns:\n        ((none)).: No matching value.\n    """\n'
    result = format_source(source)

    assert result.new_source == 'def lookup(key):\n    """Look up a value.\n\n    Args:\n        key (str): Lookup key.\n\n    Returns:\n        None: No matching value.\n    """\n'
    assert result.fixed_findings[PDF416TypeSpellingNormalization.meta] == 1
    assert not result.unfixed_findings
    assert not format_source(result.new_source).modified


def test_normalizes_parentheses_with_ascii_inner_padding_in_one_pass() -> None:
    """Trim only ASCII space and tab after removing each redundant parenthesis layer."""
    source = 'def lookup(key):\n    """Look up a value.\n\n    Args:\n        key ((( int ))): Lookup key.\n\n    Returns:\n        (( none )): No matching value.\n    """\n'
    result = format_source(source)

    assert result.new_source == source.replace("(( int ))", "int").replace("(( none ))", "None")
    assert result.fixed_findings[PDF416TypeSpellingNormalization.meta] == 1
    assert not format_source(result.new_source).modified


def test_preserves_outer_type_slot_whitespace_for_pdf409() -> None:
    """Replace only the semantic spelling span."""
    source = 'def lookup(key):\n    """Look up a value.\n\n    Args:\n        key ( ((str)). ): Lookup key.\n    """\n'
    result = format_source(source)

    assert result.new_source == source.replace("((str)).", "str")
    assert "key ( str )" in result.new_source


def test_removes_space_exposed_before_trailing_period() -> None:
    """Remove spaces that become trailing only after period removal."""
    source = 'def lookup(key):\n    """Look up a value.\n\n    Args:\n        key (list[int] .): Lookup key.\n    """\n'
    result = format_source(source)

    assert result.new_source == source.replace("list[int] .", "list[int]")
    assert result.fixed_findings[PDF416TypeSpellingNormalization.meta] == 1
    assert not format_source(result.new_source).modified


def test_preserves_accepted_bare_google_none_period() -> None:
    """Keep the parser's special bare None spelling unchanged."""
    source = 'def lookup():\n    """Look up a value.\n\n    Returns:\n        None.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_normalizes_numpy_types_and_legacy_method_type() -> None:
    """Normalize NumPy bare, named, and legacy method type slots."""
    source = 'class Client:\n    """Client.\n\n    Attributes\n    ----------\n    timeout : ((float)).\n        Timeout.\n\n    Methods\n    -------\n    connect(value: none)\n        Connect.\n    close : ((Callable[[], None])).\n        Close.\n    """\n'
    settings = CheckSettings(select=("PDF416",), docstring_convention=DocstringConvention.NUMPY)
    result = format_source(source, settings=settings)

    assert result.new_source == source.replace("((float)).", "float").replace("((Callable[[], None])).", "Callable[[], None]")
    assert "connect(value: none)" in result.new_source
    assert result.fixed_findings[PDF416TypeSpellingNormalization.meta] == 1


def test_normalizes_google_fallback_method_type_spelling() -> None:
    """Normalize type spelling on starred method entries that are not opaque signatures."""
    source = 'class Client:\n    """Client.\n\n    Methods:\n        *args (((str))): Describe the fallback entry.\n    """\n'
    result = format_source(source)

    assert result.new_source == source.replace("((str))", "str")
    assert result.fixed_findings[PDF416TypeSpellingNormalization.meta] == 1
    assert not format_source(result.new_source).modified


def test_leaves_multiline_rest_type_spelling_unchanged_without_a_source_slot() -> None:
    """Analyze continued type semantics without partially rewriting one line."""
    source = 'def lookup() -> None:\n    """Look up a value.\n\n    :returns: Result.\n    :rtype:\n        ((none)).\n    """\n'
    settings = CheckSettings(select=("PDF416",), docstring_convention=DocstringConvention.REST)
    result = format_source(source, settings=settings)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


@pytest.mark.parametrize("type_text", ["int.", "Widget.", "Nothing."])
def test_normalizes_every_parsed_bare_numpy_type_slot(type_text: str) -> None:
    """Trust NumPy parsing for simple bare return type identifiers."""
    source = f'def lookup():\n    """Look up a value.\n\n    Returns\n    -------\n    {type_text}\n    """\n'
    settings = CheckSettings(select=("PDF416",), docstring_convention=DocstringConvention.NUMPY)
    result = format_source(source, settings=settings)

    assert result.new_source == source.replace(type_text, type_text.removesuffix("."))
    assert result.fixed_findings[PDF416TypeSpellingNormalization.meta] == 1


def test_normalizes_rest_inline_companion_and_orphan_types() -> None:
    """Normalize every parsed reST type slot independently of pairing."""
    source = 'def lookup(key):\n    """Look up a value.\n\n    :param ((str)). key: Lookup key.\n    :type key: none.\n    :rtype: "Value".\n    :ytype orphan: ((Iterator[str]))\n    :returns: list[str]. in prose.\n    """\n'
    settings = CheckSettings(select=("PDF416",), docstring_convention=DocstringConvention.REST)
    result = format_source(source, settings=settings)

    assert result.new_source == source.replace("((str)).", "str").replace(":type key: none.", ":type key: None").replace('"Value".', '"Value"').replace("((Iterator[str]))", "Iterator[str]")
    assert ":returns: list[str]. in prose." in result.new_source
    assert result.fixed_findings[PDF416TypeSpellingNormalization.meta] == 1


@pytest.mark.parametrize(("convention", "body"), [(DocstringConvention.NUMPY, "Returns\n    -------\n    None.\n        No matching value."), (DocstringConvention.REST, ":rtype: None.")])
def test_normalizes_none_period_outside_google_bare_entries(convention: DocstringConvention, body: str) -> None:
    """Restrict the accepted bare-None-period exception to Google syntax."""
    source = f'def lookup():\n    """Look up a value.\n\n    {body}\n    """\n'
    settings = CheckSettings(select=("PDF416",), docstring_convention=convention)
    result = format_source(source, settings=settings)
    expected = source.replace("None.", "None")

    assert result.new_source == expected
    assert result.fixed_findings[PDF416TypeSpellingNormalization.meta] == 1
    assert not format_source(expected, settings=settings).modified


@pytest.mark.parametrize("type_text", ["Optional[List[str]]", "Factory()", "int, str", "[int]", "NONE", "NoneType", "((none.))", '("Value")'])
def test_leaves_unsupported_or_out_of_scope_spelling_unchanged(type_text: str) -> None:
    """Avoid broader typing policy and unsupported cleanup."""
    source = f'def lookup(key):\n    """Look up a value.\n\n    Args:\n        key ({type_text}): Lookup key.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


@pytest.mark.parametrize(
    ("convention", "body"),
    [
        (DocstringConvention.GOOGLE, "Args:\n        key (\\f((none)).\\f): Lookup key."),
        (DocstringConvention.NUMPY, "Returns\n    -------\n    \\v((none)).\\v"),
        (DocstringConvention.REST, ":rtype: \\f((none)).\\f"),
    ],
)
def test_leaves_suspicious_control_bounded_types_to_pdf004(convention: DocstringConvention, body: str) -> None:
    """Avoid normalizing type slots that contain suspicious control characters."""
    source = f'def lookup(key=None):\n    """Look up a value.\n\n    {body}\n    """\n'
    settings = CheckSettings(select=("PDF004", "PDF416"), docstring_convention=convention)
    result = format_source(source, settings=settings)

    assert result.new_source == source
    assert PDF416TypeSpellingNormalization.meta not in result.fixed_findings
    assert tuple(finding.rule for finding in result.unfixed_findings) == (PDF004DocstringSuspiciousUnicode.meta,)


def test_reuses_cached_type_spelling_normalization_for_repeated_text(monkeypatch: pytest.MonkeyPatch) -> None:
    """Normalize each distinct parsed type spelling once per analyzed file."""
    calls: list[str] = []
    original_normalizer = type_expressions.normalized_type_spelling_text

    def counting_normalizer(text: str) -> str | None:
        calls.append(text)
        return original_normalizer(text)

    monkeypatch.setattr(type_expressions, "normalized_type_spelling_text", counting_normalizer)
    source = (
        'def first():\n    """Look up a value.\n\n    Returns:\n        ((none)).: No matching value.\n    """\n\n\n'
        'def second():\n    """Look up another value.\n\n    Returns:\n        ((none)).: No matching value.\n    """\n'
    )
    result = format_source(source, fix=False)

    assert tuple(finding.rule for finding in result.unfixed_findings) == (PDF416TypeSpellingNormalization.meta,) * 2
    assert calls == ["((none))."]


def test_fixes_escaped_simple_source_and_preserves_crlf() -> None:
    """Reuse source-safe simple-string reconstruction."""
    source = 'def lookup(key):\r\n    """Look up a value.\r\n\r\n    Args:\r\n        key (((\\x73tr)).): Lookup key.\r\n    """\r\n'
    result = format_source(source)

    assert result.new_source == source.replace("((\\x73tr)).", "str")
    assert "\r\n" in result.new_source
    assert result.fixed_findings[PDF416TypeSpellingNormalization.meta] == 1


def test_reports_concatenated_type_slot_without_fixing() -> None:
    """Report unsafe concatenated source mappings."""
    source = 'def lookup(key):\n    ("Look up a value.\\n\\n"\n     "Args:\\n"\n     "    key (((str))): Lookup key.")\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert tuple(finding.rule for finding in result.unfixed_findings) == (PDF416TypeSpellingNormalization.meta,)
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2, 3, 4),)


def test_fixes_safe_docstring_while_reporting_unsafe_peer() -> None:
    """Keep fixability independent across separately mapped docstrings."""
    source = (
        'def first(key):\n    ("Look up a value.\\n\\n"\n     "Args:\\n"\n     "    key (((str))): Lookup key.")\n\n\n'
        'def second():\n    """Look up a value.\n\n    Returns:\n        none.: No matching value.\n    """\n'
    )
    result = format_source(source)

    assert result.new_source == source.replace("none.", "None")
    assert result.fixed_findings[PDF416TypeSpellingNormalization.meta] == 1
    assert tuple(finding.rule for finding in result.unfixed_findings) == (PDF416TypeSpellingNormalization.meta,)
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((2, 3, 4),)
    assert tuple(finding.fixable for finding in result.unfixed_findings) == (False,)


def test_local_suppression_before_docstring_suppresses_all_findings() -> None:
    """Honor complete-expression PDF suppression."""
    source = 'def lookup(key):\n    # pydocfmt: ignore[PDF416]\n    """Look up a value.\n\n    Args:\n        key (((str))): Lookup key.\n    """\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_concatenated_docstring_component_suppresses_unsafe_finding() -> None:
    """Honor complete-expression suppression for an otherwise unfixable mapping."""
    source = 'def lookup(key):\n    ("Look up a value.\\n\\n"  # pydocfmt: ignore[PDF416]\n     "Args:\\n"\n     "    key (((str))): Lookup key.")\n'
    result = format_source(source)

    assert result.new_source == source
    assert not result.fixed_findings
    assert not result.unfixed_findings


def test_literal_block_parsing_setting_controls_type_spelling_normalization() -> None:
    """Normalize convention-looking examples only when literal protection is disabled."""
    source = 'def lookup():\n    """Look up a value.\n\n    Returns:\n        Example::\n\n            (((int))).: Example value.\n    """\n'
    unprotected_settings = CheckSettings(select=("PDF416",), docstring_convention=DocstringConvention.GOOGLE, docstring_parse_literal_blocks=False)
    protected = format_source(source)
    unprotected = format_source(source, settings=unprotected_settings)

    assert protected.new_source == source
    assert not protected.fixed_findings
    assert unprotected.new_source == source.replace("(((int))).", "int")
    assert unprotected.fixed_findings[PDF416TypeSpellingNormalization.meta] == 1
    assert not format_source(unprotected.new_source, settings=unprotected_settings).modified


def test_converges_with_spacing_and_annotation_mismatch_rules() -> None:
    """Normalize spelling before later type comparison remains authoritative."""
    source = 'def lookup(key: list[str]) -> None:\n    """Look up a value.\n\n    Args:\n        key (((list[ str ]))).: Lookup key.\n\n    Returns:\n        none.: No matching value.\n    """\n'
    settings = CheckSettings(select=("PDF411", "PDF416", "PDF703", "PDF707"), docstring_convention=DocstringConvention.GOOGLE)
    result = format_source(source, settings=settings)

    assert result.new_source == source.replace("((list[ str ])).", "list[str]").replace("none.", "None")
    assert result.fixed_findings[PDF416TypeSpellingNormalization.meta] == 1
    assert not result.unfixed_findings
    assert not format_source(result.new_source, settings=settings).modified


def test_broad_selection_and_unparsed_convention_effects() -> None:
    """Enable parsed conventions and disable unparsed conventions."""
    for convention in (DocstringConvention.GOOGLE, DocstringConvention.NUMPY, DocstringConvention.REST):
        selection = rules_selection.select_rules(CheckSettings(select=("PDF4",), docstring_convention=convention))
        assert "PDF416" in {rule.rule.code.tag for rule in selection.rules}
    for convention in (DocstringConvention.NONE, DocstringConvention.PEP257):
        selection = rules_selection.select_rules(CheckSettings(select=("PDF4",), docstring_convention=convention))
        assert "PDF416" not in {rule.rule.code.tag for rule in selection.rules}
        exact_selection = rules_selection.select_rules(CheckSettings(select=("PDF416",), docstring_convention=convention))
        assert "PDF416" not in {rule.rule.code.tag for rule in exact_selection.rules}
