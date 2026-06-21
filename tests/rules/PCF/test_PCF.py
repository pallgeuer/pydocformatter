import typing

import libcst as cst
import libcst.metadata as cst_metadata
import pytest

import pydocformatter.formatter as formatter
import pydocformatter.rules.definition_helpers.source_text as source_text
import pydocformatter.rules_selection as rules_selection
from pydocformatter.cli.settings_check import CheckSettings
from pydocformatter.rules.definition import RuleCategoryContext, RuleContext
from pydocformatter.rules.definitions.PCF.PCF import PCF, CommentKind, CommentPlacement, available_comment_width, render_comment


def category_context(source: str) -> RuleCategoryContext:
    module = cst.parse_module(source)
    metadata_wrapper = cst_metadata.MetadataWrapper(module, unsafe_skip_copy=True)
    return RuleCategoryContext(
        path="example.py",
        settings=CheckSettings(),
        module=module,
        metadata_wrapper=metadata_wrapper,
        positions=metadata_wrapper.resolve(cst_metadata.PositionProvider),
        line_ending="\r\n" if "\r\n" in source else "\n",
        source=source,
        source_lines=tuple(source_text.source_lines(source)),
    )


def rule_context(context: RuleCategoryContext, data: object | None) -> RuleContext:
    return RuleContext(
        path=context.path,
        settings=context.settings,
        module=context.module,
        metadata_wrapper=context.metadata_wrapper,
        positions=context.positions,
        line_ending=context.line_ending,
        source=context.source,
        source_lines=context.source_lines,
        category_data=data,
        effectively_fixable=True,
    )


def parent_metadata_resolves_for_format(source: str, *, settings: CheckSettings, monkeypatch: pytest.MonkeyPatch, fix: bool = False) -> tuple[int, formatter.FormatterResult]:
    resolves = 0
    original_resolve = cst_metadata.MetadataWrapper.resolve

    def count_parent_resolve(wrapper: cst_metadata.MetadataWrapper, provider: object) -> object:
        nonlocal resolves
        if provider is cst_metadata.ParentNodeProvider:
            resolves += 1
        return typing.cast("typing.Any", original_resolve)(wrapper, provider)

    monkeypatch.setattr(cst_metadata.MetadataWrapper, "resolve", count_parent_resolve)
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=fix)
    return resolves, result


def module_visit_counter(monkeypatch: pytest.MonkeyPatch) -> typing.Callable[[], int]:
    visits = 0
    original_visit = cst.Module.visit

    def count_visit(module: cst.Module, visitor: cst.CSTVisitor) -> object:
        nonlocal visits
        visits += 1
        return original_visit(module, visitor)

    monkeypatch.setattr(cst.Module, "visit", count_visit)

    return lambda: visits


def test_prepare_classifies_comments_and_groups_only_eligible_standalone_blocks() -> None:
    source = "#!/usr/bin/env python\n# -*- coding: utf-8 -*-\n# first\n# second\n#\n# third\ndef f():\n    # inner first\n    # inner second\n    value = 1  # trailing\n# type: ignore\n# noqa\n"
    data = PCF.prepare(category_context(source))
    assert tuple(comment.text for comment in data.comments) == (
        "#!/usr/bin/env python",
        "# -*- coding: utf-8 -*-",
        "# first",
        "# second",
        "#",
        "# third",
        "# inner first",
        "# inner second",
        "# trailing",
        "# type: ignore",
        "# noqa",
    )
    assert tuple(comment.kind for comment in data.comments) == (
        CommentKind.SHEBANG,
        CommentKind.ENCODING_COOKIE,
        CommentKind.REGULAR,
        CommentKind.REGULAR,
        CommentKind.REGULAR,
        CommentKind.REGULAR,
        CommentKind.REGULAR,
        CommentKind.REGULAR,
        CommentKind.REGULAR,
        CommentKind.TYPE_DIRECTIVE,
        CommentKind.TOOL_DIRECTIVE,
    )
    assert tuple(comment.placement for comment in data.comments) == (CommentPlacement.STANDALONE,) * 8 + (CommentPlacement.TRAILING, CommentPlacement.STANDALONE, CommentPlacement.STANDALONE)
    assert tuple(comment.indent for comment in data.comments) == ("", "", "", "", "", "", "    ", "    ", "    ", "", "")
    assert tuple(tuple(comment.text for comment in run.comments) for run in data.standalone_runs) == (("# first", "# second"), ("# third",), ("# inner first", "# inner second"))
    assert tuple(run.indent for run in data.standalone_runs) == ("", "", "    ")
    assert tuple(comment.text for comment in data.trailing_comments) == ("# trailing",)
    assert data.comments[2].raw_content == " first"
    assert data.comments[2].body == "first"
    assert data.source_for(data.standalone_runs[0].range) == "# first\n# second"


def test_prepare_skips_module_visit_when_source_has_no_hash(monkeypatch: pytest.MonkeyPatch) -> None:
    context = category_context("value = 1\n")
    visits = module_visit_counter(monkeypatch)

    data = PCF.prepare(context)

    assert visits() == 0
    assert data.source_lines is context.source_lines
    assert data.comments == ()
    assert data.standalone_runs == ()
    assert data.trailing_comments == ()


def test_prepare_keeps_conservative_visit_when_hash_appears_inside_string(monkeypatch: pytest.MonkeyPatch) -> None:
    context = category_context('value = "# not a comment"\n')
    visits = module_visit_counter(monkeypatch)

    data = PCF.prepare(context)

    assert visits() == 1
    assert data.comments == ()
    assert data.standalone_runs == ()
    assert data.trailing_comments == ()


def test_prepare_preserves_comment_order_with_crlf_source() -> None:
    data = PCF.prepare(category_context("# first\r\nvalue = 1  # second\r\n"))
    assert tuple((comment.text, comment.range.start.line) for comment in data.comments) == (("# first", 1), ("# second", 2))


def test_second_line_encoding_text_after_code_is_regular_comment() -> None:
    data = PCF.prepare(category_context('value = """first\u2028second"""\n# coding: utf-8\n'))
    assert data.comments[0].kind == CommentKind.REGULAR
    assert data.comments[0].range.start.line == 2


def test_require_data_validates_category_data_type() -> None:
    context = category_context("# comment\n")
    data = PCF.prepare(context)
    assert PCF.require_data(rule_context(context, data)) is data
    with pytest.raises(TypeError, match="require PCFCategoryData"):
        PCF.require_data(rule_context(context, None))


@pytest.mark.parametrize(
    ("source", "expected_kinds"),
    (
        ("#!/usr/bin/python\n# coding=utf-8\n", (CommentKind.SHEBANG, CommentKind.ENCODING_COOKIE)),
        ("# ordinary first line\n# CoDiNg: latin-1\n", (CommentKind.REGULAR, CommentKind.REGULAR)),
        ("\n# coding: utf-8\n", (CommentKind.ENCODING_COOKIE,)),
        ("value = 1\n# coding: utf-8\n", (CommentKind.REGULAR,)),
        ("\n\n# coding: utf-8\n", (CommentKind.REGULAR,)),
        (" #!/usr/bin/python\n", (CommentKind.SHEBANG,)),
    ),
)
def test_prepare_classifies_shebang_and_encoding_cookie_boundaries(source: str, expected_kinds: tuple[CommentKind, ...]) -> None:
    data = PCF.prepare(category_context(source))
    assert tuple(comment.kind for comment in data.comments) == expected_kinds


@pytest.mark.parametrize(
    "directive",
    (
        "# type: ignore",
        "# TYPE : ignore",
        "#noqa",
        "# NOSEC reason",
        "# nosemgrep",
        "# pylint: disable=x",
        "# PYRIGHT: ignore",
        "# mypy: ignore-errors",
        "# ruff: noqa",
        "# flake8: noqa",
        "# fmt: off",
        "# isort: skip",
        "# pragma: no cover",
    ),
)
def test_prepare_protects_type_and_tool_directives_case_insensitively(directive: str) -> None:
    data = PCF.prepare(category_context(f"value = 1  {directive}\n"))
    assert data.comments[0].kind in (CommentKind.TYPE_DIRECTIVE, CommentKind.TOOL_DIRECTIVE)


@pytest.mark.parametrize("comment", ("# typewriter: prose", "# noqaish prose", "# nosecurity prose", "# formatted prose", "# isotope prose", "# pragmatic prose"))
def test_prepare_does_not_overclassify_directive_prefixes(comment: str) -> None:
    data = PCF.prepare(category_context(f"value = 1  {comment}\n"))
    assert data.comments[0].kind == CommentKind.REGULAR


@pytest.mark.parametrize(
    ("text", "raw_content", "body", "content", "is_empty", "is_hash_only"),
    (
        ("#", "", "", "", True, True),
        ("# \t", " \t", "\t", "", True, True),
        ("### \t", "## \t", "## \t", "##", False, True),
        ("## heading ", "# heading ", "# heading ", "# heading", False, False),
    ),
)
def test_comment_info_content_views(text: str, raw_content: str, body: str, content: str, is_empty: bool, is_hash_only: bool) -> None:
    comment = PCF.prepare(category_context(f"{text}\n")).comments[0]
    assert (comment.raw_content, comment.body, comment.content, comment.is_empty, comment.is_hash_only) == (raw_content, body, content, is_empty, is_hash_only)


def test_prepare_splits_standalone_runs_at_code_blank_lines_protected_comments_hash_separators_and_indent_changes() -> None:
    source = "# first\nvalue = 1\n# second\n\n# third\n# noqa\n# fourth\n###\n# fifth\nif value:\n    # sixth\n    pass\n# seventh\n"
    data = PCF.prepare(category_context(source))
    assert tuple(tuple(comment.text for comment in run.comments) for run in data.standalone_runs) == (
        ("# first",),
        ("# second",),
        ("# third",),
        ("# fourth",),
        ("# fifth",),
        ("# sixth",),
        ("# seventh",),
    )


def test_source_for_handles_multiline_ranges_and_preserves_mixed_endings() -> None:
    data = PCF.prepare(category_context("# first\r\n# second\n# third"))
    code_range = cst_metadata.CodeRange(start=data.comments[0].range.start, end=data.comments[-1].range.end)
    assert data.source_for(code_range) == "# first\r\n# second\n# third"


def test_comment_rendering_and_width_helpers_cover_tabs_tiny_widths_and_empty_content() -> None:
    assert available_comment_width("\t", line_length=12, tab_width=4, prefix="> ") == 4
    assert render_comment("", indent="    ") == "    #"


def test_prepare_ignores_hashes_inside_all_string_literal_forms() -> None:
    source = "plain = '# not a comment'\nraw = r\"# still not a comment\"\nformatted = f'# {plain}'\nmultiline = '''# also not a comment'''\n# actual comment\n"
    data = PCF.prepare(category_context(source))
    assert tuple(comment.text for comment in data.comments) == ("# actual comment",)


def test_prepare_classifies_comments_in_parenthesized_decorator_and_compound_statement_positions() -> None:
    source = "@decorator  # decorator trailing\ndef function(\n    value,  # argument trailing\n):\n    if value:  # header trailing\n        # body standalone\n        return (\n            value  # expression trailing\n        )\ntry:  # try star trailing\n    pass\nexcept* Error:  # except star trailing\n    pass\nif enabled: pass  # one-line trailing\n"
    data = PCF.prepare(category_context(source))
    assert tuple((comment.text, comment.placement, comment.indent, comment.syntax_sensitive) for comment in data.comments) == (
        ("# decorator trailing", CommentPlacement.TRAILING, "", True),
        ("# argument trailing", CommentPlacement.TRAILING, "    ", True),
        ("# header trailing", CommentPlacement.TRAILING, "    ", True),
        ("# body standalone", CommentPlacement.STANDALONE, "        ", False),
        ("# expression trailing", CommentPlacement.TRAILING, "            ", True),
        ("# try star trailing", CommentPlacement.TRAILING, "", True),
        ("# except star trailing", CommentPlacement.TRAILING, "", True),
        ("# one-line trailing", CommentPlacement.TRAILING, "", True),
    )


def test_pcf001_does_not_resolve_parent_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = CheckSettings(select=("PCF001",), line_length=24)

    resolves, result = parent_metadata_resolves_for_format("#standalone words that should wrap\n", settings=settings, monkeypatch=monkeypatch)

    assert resolves == 0
    assert tuple(finding.rule.code.tag for finding in result.unfixed_findings) == ("PCF001",)


def test_pcf004_resolves_parent_metadata_for_overlong_syntax_sensitive_comment(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = CheckSettings(select=("PCF004",), line_length=32)

    resolves, result = parent_metadata_resolves_for_format("if enabled:  # explanation long enough to move above the header\n    pass\n", settings=settings, monkeypatch=monkeypatch)

    assert resolves == 1
    assert not result.unfixed_findings


def test_pcf004_does_not_resolve_parent_metadata_when_syntax_awareness_is_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = CheckSettings(select=("PCF004",), line_length=32, comment_trailing_extraction_syntax_aware=False)

    resolves, result = parent_metadata_resolves_for_format("if enabled:  # explanation long enough to move above the header\n    pass\n", settings=settings, monkeypatch=monkeypatch)

    assert resolves == 0
    assert tuple(finding.line_numbers for finding in result.unfixed_findings) == ((1,),)


def test_pcf004_does_not_resolve_parent_metadata_for_short_trailing_comment(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = CheckSettings(select=("PCF004",), line_length=88)

    resolves, result = parent_metadata_resolves_for_format("if enabled:  # short\n    pass\n", settings=settings, monkeypatch=monkeypatch)

    assert resolves == 0
    assert not result.unfixed_findings
