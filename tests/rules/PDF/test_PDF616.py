import pydocformatter.formatter as formatter
import pydocformatter.rules_selection as rules_selection
from pydocformatter.cli.settings_check import CheckSettings


def format_source(source: str, *, settings: CheckSettings | None = None, fix: bool = True) -> formatter.FormatterResult:
    """Format source with PDF616 selected by default."""
    resolved_settings = CheckSettings(select=("PDF616",)) if settings is None else settings
    return formatter.format_source(source, "example.py", settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=fix)


def assert_findings(source: str, *, expected: tuple[tuple[str, tuple[int, ...], str], ...], settings: CheckSettings | None = None, fix: bool = True) -> formatter.FormatterResult:
    """Assert PDF616 findings for source."""
    result = format_source(source, settings=settings, fix=fix)

    assert tuple((finding.rule.code.tag, finding.line_numbers, finding.message) for finding in result.unfixed_findings) == expected
    assert result.new_source == source
    assert not result.fixed_findings
    assert result.errors == ()
    return result


def test_default_overload_decorators_should_not_have_docstrings() -> None:
    source = '@typing.overload\ndef parse(value: int):\n    """Parse int."""\n    pass\n\n@typing.overload()\ndef parse(value: str):\n    """Parse str."""\n    pass\n\n@typing_extensions.overload\ndef parse(value: bytes):\n    """Parse bytes."""\n    pass\n\n@project.overload\ndef parse(value: object):\n    """Parse project."""\n    pass\n\ndef parse(value):\n    """Parse."""\n    pass\n'

    assert_findings(
        source,
        expected=(
            ("PDF616", (3,), "Function decorated with '@typing.overload' should not have a docstring"),
            ("PDF616", (8,), "Function decorated with '@typing.overload' should not have a docstring"),
            ("PDF616", (13,), "Function decorated with '@typing_extensions.overload' should not have a docstring"),
        ),
    )


def test_configured_forbidden_function_decorators_are_exact_names() -> None:
    source = '@project.overload()\ndef parse(value: int):\n    """Project overload."""\n    pass\n\n@overload\ndef standard(value: int):\n    """Standard overload."""\n    pass\n'
    settings = CheckSettings(select=("PDF616",), docstring_forbidden_function_decorators=("project.overload",))

    assert_findings(source, settings=settings, expected=(("PDF616", (3,), "Function decorated with '@project.overload' should not have a docstring"),))


def test_absent_docstrings_are_not_reported() -> None:
    source = "@overload\ndef parse(value: int):\n    pass\n"

    assert_findings(source, expected=())


def test_existing_forbidden_docstrings_remain_visible_to_other_rules() -> None:
    source = '@typing.overload\ndef parse(value: int):\n    """Parse int"""\n    pass\n'
    settings = CheckSettings(select=("PDF300", "PDF616"))

    result = assert_findings(
        source,
        settings=settings,
        fix=False,
        expected=(
            ("PDF300", (3,), "Docstring summary should end with a period"),
            ("PDF616", (3,), "Function decorated with '@typing.overload' should not have a docstring"),
        ),
    )

    assert result.new_source == source


def test_function_shapes_with_forbidden_docstrings_are_reported() -> None:
    source = 'class Client:\n    """Client."""\n\n    @typing.overload\n    def connect(self, value: int):\n        """Connect int."""\n        pass\n\n    @typing.overload\n    async def fetch(self, value: int):\n        """Fetch int."""\n        pass\n\n    @typing_extensions.overload\n    def __str__(self):\n        """Format client."""\n        return "client"\n\n    @typing.overload\n    def __init__(self, value: int):\n        """Initialize int."""\n        self.value = value\n\n\ndef outer():\n    """Outer."""\n\n    @typing.overload\n    def inner(value: int):\n        """Inner int."""\n        return value\n'

    assert_findings(
        source,
        expected=(
            ("PDF616", (6,), "Function decorated with '@typing.overload' should not have a docstring"),
            ("PDF616", (11,), "Function decorated with '@typing.overload' should not have a docstring"),
            ("PDF616", (16,), "Function decorated with '@typing_extensions.overload' should not have a docstring"),
            ("PDF616", (21,), "Function decorated with '@typing.overload' should not have a docstring"),
            ("PDF616", (30,), "Function decorated with '@typing.overload' should not have a docstring"),
        ),
    )


def test_non_function_dynamic_and_non_exact_decorators_are_not_reported() -> None:
    source = '@overload\nclass Client:\n    """Client."""\n\nclass Container:\n    """Container."""\n\n    @decorator_factory(overload)\n    def generated(self):\n        """Generated."""\n        pass\n\n    @(lambda method: method)\n    def dynamic(self):\n        """Dynamic."""\n        pass\n\n    @typing().overload\n    def dynamic_receiver(self):\n        """Dynamic receiver."""\n        pass\n\n    @typing.overload.extra\n    def extended(self):\n        """Extended."""\n        pass\n'

    assert_findings(source, expected=())


def test_multiline_and_compact_docstring_targets_use_docstring_physical_lines() -> None:
    source = '@typing.overload\ndef compact(): """Compact."""\n\n@typing.overload\ndef multiline():\n    """Summary.\n\n    Details.\n    """\n    pass\n'

    assert_findings(
        source,
        expected=(
            ("PDF616", (2,), "Function decorated with '@typing.overload' should not have a docstring"),
            ("PDF616", (6, 7, 8, 9), "Function decorated with '@typing.overload' should not have a docstring"),
        ),
    )


def test_empty_forbidden_decorator_setting_disables_rule() -> None:
    source = '@overload\ndef parse(value: int):\n    """Parse int."""\n    pass\n'
    settings = CheckSettings(select=("PDF616",), docstring_forbidden_function_decorators=())

    assert_findings(source, settings=settings, expected=())


def test_broad_pdf_selection_includes_forbidden_function_docstrings() -> None:
    source = '"""Module."""\n\n@typing.overload\ndef parse(value: int):\n    """Parse int."""\n    pass\n'
    settings = CheckSettings(select=("PDF",))

    assert_findings(source, settings=settings, expected=(("PDF616", (5,), "Function decorated with '@typing.overload' should not have a docstring"),))


def test_optional_decorators_do_not_trigger_forbidden_docstring_rule() -> None:
    source = '@override\ndef parse(value: int):\n    """Parse int."""\n    pass\n\n@project.shared\ndef shared(value: int):\n    """Shared."""\n    pass\n'
    settings = CheckSettings(
        select=("PDF616",),
        docstring_forbidden_function_decorators=("project.shared",),
        docstring_optional_function_decorators=("override", "project.shared"),
    )

    assert_findings(source, settings=settings, expected=(("PDF616", (8,), "Function decorated with '@project.shared' should not have a docstring"),))


def test_first_matching_forbidden_decorator_controls_message() -> None:
    source = '@typing.overload\n@overload\ndef parse(value: int):\n    """Parse int."""\n    pass\n\n@decorator\n@typing_extensions.overload\ndef build(value: int):\n    """Build int."""\n    pass\n'

    assert_findings(
        source,
        expected=(
            ("PDF616", (4,), "Function decorated with '@typing.overload' should not have a docstring"),
            ("PDF616", (10,), "Function decorated with '@typing_extensions.overload' should not have a docstring"),
        ),
    )


def test_suppression_targets_docstring_lines_not_decorator_or_definition_lines() -> None:
    source = '@typing.overload  # pydocfmt: ignore[PDF616]\ndef decorator_suppressed(value: int):\n    """Decorator directive does not suppress."""\n    pass\n\n@typing.overload\ndef definition_suppressed(value: int):  # pydocfmt: ignore[PDF616]\n    """Definition directive does not suppress."""\n    pass\n\n@typing.overload\ndef docstring_suppressed(value: int):\n    """Docstring directive suppresses."""  # pydocfmt: ignore[PDF616]\n    pass\n'

    assert_findings(
        source,
        expected=(
            ("PDF616", (3,), "Function decorated with '@typing.overload' should not have a docstring"),
            ("PDF616", (8,), "Function decorated with '@typing.overload' should not have a docstring"),
        ),
    )


def test_preceding_directive_suppresses_multiline_forbidden_docstring() -> None:
    source = '@typing.overload\ndef parse(value: int):\n    # pydocfmt: ignore[PDF616]\n    """Parse int.\n\n    Details.\n    """\n    pass\n'

    assert_findings(source, expected=())


def test_import_alias_decorator_names_match_qualified_configuration() -> None:
    source = 'import typing as t\n\n@t.overload\ndef parse(value: int):\n    """Parse int."""\n    pass\n'

    assert_findings(source, expected=(("PDF616", (5,), "Function decorated with '@t.overload' should not have a docstring"),))
    assert_findings(
        source,
        settings=CheckSettings(select=("PDF616",), docstring_forbidden_function_decorators=("t.overload",)),
        expected=(("PDF616", (5,), "Function decorated with '@t.overload' should not have a docstring"),),
    )


def test_called_import_alias_decorator_names_match_qualified_configuration() -> None:
    source = 'from typing import overload as ov\n\n@ov()\ndef parse(value: int):\n    """Parse int."""\n    pass\n'

    assert_findings(source, expected=(("PDF616", (5,), "Function decorated with '@ov' should not have a docstring"),))


def test_unqualified_decorator_configuration_is_syntactic_only() -> None:
    source = 'from typing import overload as ov\n\n@ov\ndef parse(value: int):\n    """Parse int."""\n    pass\n\n@overload\ndef build(value: int):\n    """Build int."""\n    pass\n'
    settings = CheckSettings(select=("PDF616",), docstring_forbidden_function_decorators=("overload",))

    assert_findings(source, settings=settings, expected=(("PDF616", (10,), "Function decorated with '@overload' should not have a docstring"),))


def test_shadowed_import_alias_decorator_does_not_match_qualified_configuration() -> None:
    source = 'from typing import overload as ov\nov = decorator\n\n@ov\ndef parse(value: int):\n    """Parse int."""\n    pass\n'

    assert_findings(source, expected=())


def test_shadowed_dotted_decorator_does_not_match_qualified_configuration() -> None:
    source = 'class Typing:\n    overload = object()\n\ntyping = Typing()\n\n@typing.overload\ndef parse(value: int):\n    """Parse int."""\n    pass\n'

    assert_findings(source, expected=())


def test_source_decorator_order_controls_message_not_setting_order() -> None:
    source = '@project.second\n@project.first\ndef parse(value: int):\n    """Parse int."""\n    pass\n'
    settings = CheckSettings(select=("PDF616",), docstring_forbidden_function_decorators=("project.first", "project.second"))

    assert_findings(source, settings=settings, expected=(("PDF616", (4,), "Function decorated with '@project.second' should not have a docstring"),))


def test_concatenated_forbidden_docstring_targets_all_physical_string_lines() -> None:
    source = '@typing.overload\ndef parse(value: int):\n    (\n        "Parse "\n        "int."\n    )\n    pass\n'

    assert_findings(source, expected=(("PDF616", (4, 5), "Function decorated with '@typing.overload' should not have a docstring"),))
