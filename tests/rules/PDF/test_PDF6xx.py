import pathlib

import pydocformatter.formatter as formatter
import pydocformatter.rules_selection as rules_selection
from pydocformatter.cli.settings_check import CheckSettings, DocstringMissingDocumentation


def format_source(source: str, *, select: tuple[str, ...], path: str = "example.py", settings: CheckSettings | None = None) -> formatter.FormatterResult:
    """Format source with selected PDF6xx rules."""
    resolved_settings = CheckSettings(select=select) if settings is None else settings
    return formatter.format_source(source, path, settings=resolved_settings, rule_selection=rules_selection.select_rules(resolved_settings), fix=True)


def assert_findings(
    source: str, *, select: tuple[str, ...], expected: tuple[tuple[str, tuple[int, ...], str], ...], path: str = "example.py", settings: CheckSettings | None = None
) -> formatter.FormatterResult:
    """Assert PDF6xx findings for source."""
    result = format_source(source, select=select, path=path, settings=settings)

    assert result.new_source == source
    assert not result.fixed_findings
    assert result.errors == ()
    assert tuple((finding.rule.code.tag, finding.line_numbers, finding.message) for finding in result.unfixed_findings) == expected
    return result


def test_package_and_module_rules_use_path_shape_and_privacy() -> None:
    source = "VALUE = 1\n"

    assert_findings(source, select=("PDF600",), path="package/__init__.py", expected=(("PDF600", (1,), "Public package is missing docstring"),))
    assert_findings(source, select=("PDF601",), path="_package/__init__.py", expected=(("PDF601", (1,), "Private package is missing docstring"),))
    assert_findings(source, select=("PDF600",), path="package/__init__.pyi", expected=(("PDF600", (1,), "Public package is missing docstring"),))
    assert_findings(source, select=("PDF601",), path="_package/__init__.pyi", expected=(("PDF601", (1,), "Private package is missing docstring"),))
    assert_findings(source, select=("PDF602",), path="package/public.py", expected=(("PDF602", (1,), "Public module is missing docstring"),))
    assert_findings(source, select=("PDF603",), path="package/_private.py", expected=(("PDF603", (1,), "Private module is missing docstring"),))
    assert_findings(source, select=("PDF600", "PDF602"), path="package/public.py", expected=(("PDF602", (1,), "Public module is missing docstring"),))
    assert_findings(source, select=("PDF600", "PDF602"), path="package/__init__.py", expected=(("PDF600", (1,), "Public package is missing docstring"),))


def test_existing_package_path_privacy_uses_import_package_suffix(tmp_path: pathlib.Path) -> None:
    source = "VALUE = 1\n"
    workspace = tmp_path / "_workspace"
    package = workspace / "package"
    private_package = package / "_internal"
    private_stub_package = workspace / "_stub"
    private_package.mkdir(parents=True)
    private_stub_package.mkdir()
    (package / "__init__.py").write_text(source, encoding="utf-8")
    (package / "public.py").write_text(source, encoding="utf-8")
    (private_package / "__init__.py").write_text(source, encoding="utf-8")
    (private_package / "public.py").write_text(source, encoding="utf-8")
    (private_stub_package / "__init__.pyi").write_text(source, encoding="utf-8")
    (private_stub_package / "public.pyi").write_text(source, encoding="utf-8")

    assert_findings(source, select=("PDF600", "PDF601"), path=str(package / "__init__.py"), expected=(("PDF600", (1,), "Public package is missing docstring"),))
    assert_findings(source, select=("PDF602", "PDF603"), path=str(package / "public.py"), expected=(("PDF602", (1,), "Public module is missing docstring"),))
    assert_findings(source, select=("PDF600", "PDF601"), path=str(private_package / "__init__.py"), expected=(("PDF601", (1,), "Private package is missing docstring"),))
    assert_findings(source, select=("PDF602", "PDF603"), path=str(private_package / "public.py"), expected=(("PDF603", (1,), "Private module is missing docstring"),))
    assert_findings(source, select=("PDF600", "PDF601"), path=str(private_stub_package / "__init__.pyi"), expected=(("PDF601", (1,), "Private package is missing docstring"),))
    assert_findings(source, select=("PDF602", "PDF603"), path=str(private_stub_package / "public.pyi"), expected=(("PDF603", (1,), "Private module is missing docstring"),))


def test_existing_docstrings_satisfy_package_and_module_rules() -> None:
    source = '"""Documented."""\n\nVALUE = 1\n'

    assert_findings(source, select=("PDF600", "PDF601", "PDF602", "PDF603"), path="package/__init__.py", expected=())
    assert_findings(source, select=("PDF600", "PDF601", "PDF602", "PDF603"), path="package/public.py", expected=())


def test_compact_suite_docstrings_satisfy_owner_rules() -> None:
    source = '"""Module."""\n\nclass Client: """Client."""\n\ndef build(): """Build."""\n\nclass Container:\n    """Container."""\n\n    class Nested: """Nested."""\n\n    def method(self): """Method."""\n\n    def __str__(self): """String."""\n\n    def __init__(self): """Initialize."""\n'

    assert_findings(source, select=("PDF600", "PDF602", "PDF604", "PDF606", "PDF608", "PDF610", "PDF612", "PDF614"), expected=())


def test_class_nested_class_function_method_dunder_and_init_rules_are_separate() -> None:
    source = '"""Module."""\n\nclass Client:\n    """Client."""\n\n    class Response:\n        pass\n\n    def connect(self):\n        pass\n\n    def __str__(self):\n        return "client"\n\n    def __init__(self):\n        pass\n\n\ndef build():\n    pass\n'

    assert_findings(source, select=("PDF606",), expected=(("PDF606", (6,), "Public nested class 'Client.Response' is missing docstring"),))
    assert_findings(source, select=("PDF608",), expected=(("PDF608", (19,), "Public function 'build' is missing docstring"),))
    assert_findings(source, select=("PDF610",), expected=(("PDF610", (9,), "Public method 'Client.connect' is missing docstring"),))
    assert_findings(source, select=("PDF612",), expected=(("PDF612", (12,), "Public dunder method 'Client.__str__' is missing docstring"),))
    assert_findings(source, select=("PDF614",), expected=(("PDF614", (15,), "Public __init__ method 'Client.__init__' is missing docstring"),))


def test_async_definitions_are_classified_like_regular_definitions() -> None:
    source = '"""Module."""\n\nasync def build():\n    pass\n\nclass Client:\n    """Client."""\n\n    async def connect(self):\n        pass\n\n    async def __aenter__(self):\n        return self\n'

    assert_findings(source, select=("PDF608",), expected=(("PDF608", (3,), "Public function 'build' is missing docstring"),))
    assert_findings(source, select=("PDF610",), expected=(("PDF610", (9,), "Public method 'Client.connect' is missing docstring"),))
    assert_findings(source, select=("PDF612",), expected=(("PDF612", (12,), "Public dunder method 'Client.__aenter__' is missing docstring"),))


def test_private_rules_include_private_names_and_private_containing_scopes() -> None:
    source = '"""Module."""\n\nclass _Client:\n    class Response:\n        pass\n\n    def connect(self):\n        pass\n\n    def __str__(self):\n        return "client"\n\n    def __init__(self):\n        pass\n\n\ndef _build():\n    pass\n'

    assert_findings(source, select=("PDF605",), expected=(("PDF605", (3,), "Private class '_Client' is missing docstring"),))
    assert_findings(source, select=("PDF607",), expected=(("PDF607", (4,), "Private nested class '_Client.Response' is missing docstring"),))
    assert_findings(source, select=("PDF609",), expected=(("PDF609", (17,), "Private function '_build' is missing docstring"),))
    assert_findings(source, select=("PDF611",), expected=(("PDF611", (7,), "Private method '_Client.connect' is missing docstring"),))
    assert_findings(source, select=("PDF613",), expected=(("PDF613", (10,), "Private dunder method '_Client.__str__' is missing docstring"),))
    assert_findings(source, select=("PDF615",), expected=(("PDF615", (13,), "Private __init__ method '_Client.__init__' is missing docstring"),))


def test_private_module_path_makes_otherwise_public_definitions_private() -> None:
    source = '"""Module."""\n\nclass Client:\n    class Response:\n        pass\n\n    def connect(self):\n        pass\n\n    def __str__(self):\n        return "client"\n\n    def __init__(self):\n        pass\n\n\ndef build():\n    pass\n'

    assert_findings(source, select=("PDF604", "PDF606", "PDF608", "PDF610", "PDF612", "PDF614"), path="package/_private.py", expected=())
    assert_findings(
        source,
        select=("PDF605", "PDF607", "PDF609", "PDF611", "PDF613", "PDF615"),
        path="package/_private.py",
        expected=(
            ("PDF605", (3,), "Private class 'Client' is missing docstring"),
            ("PDF607", (4,), "Private nested class 'Client.Response' is missing docstring"),
            ("PDF609", (17,), "Private function 'build' is missing docstring"),
            ("PDF611", (7,), "Private method 'Client.connect' is missing docstring"),
            ("PDF613", (10,), "Private dunder method 'Client.__str__' is missing docstring"),
            ("PDF615", (13,), "Private __init__ method 'Client.__init__' is missing docstring"),
        ),
    )


def test_deeply_nested_classes_use_full_public_and_private_ancestor_chain() -> None:
    source = '"""Module."""\n\nclass Outer:\n    """Outer."""\n\n    class Middle:\n        class Leaf:\n            pass\n\nclass PublicOuter:\n    """Public outer."""\n\n    class _PrivateMiddle:\n        class Leaf:\n            pass\n'

    assert_findings(
        source,
        select=("PDF606",),
        expected=(("PDF606", (6,), "Public nested class 'Outer.Middle' is missing docstring"), ("PDF606", (7,), "Public nested class 'Outer.Middle.Leaf' is missing docstring")),
    )
    assert_findings(
        source,
        select=("PDF607",),
        expected=(
            ("PDF607", (13,), "Private nested class 'PublicOuter._PrivateMiddle' is missing docstring"),
            ("PDF607", (14,), "Private nested class 'PublicOuter._PrivateMiddle.Leaf' is missing docstring"),
        ),
    )


def test_top_level_class_and_function_rules_ignore_local_definitions() -> None:
    source = '"""Module."""\n\nclass Client:\n    pass\n\n\ndef build():\n    class Local:\n        pass\n\n    def inner():\n        pass\n'

    assert_findings(source, select=("PDF604",), expected=(("PDF604", (3,), "Public class 'Client' is missing docstring"),))
    assert_findings(source, select=("PDF608",), expected=(("PDF608", (7,), "Public function 'build' is missing docstring"),))
    assert_findings(source, select=("PDF604", "PDF608"), expected=(("PDF604", (3,), "Public class 'Client' is missing docstring"), ("PDF608", (7,), "Public function 'build' is missing docstring")))


def test_method_rules_ignore_local_classes_and_functions_inside_methods() -> None:
    source = '"""Module."""\n\nclass Client:\n    """Client."""\n\n    def method(self):\n        class Local:\n            pass\n\n        def inner():\n            pass\n'

    assert_findings(source, select=("PDF604", "PDF606", "PDF608"), expected=())
    assert_findings(source, select=("PDF610",), expected=(("PDF610", (6,), "Public method 'Client.method' is missing docstring"),))


def test_member_rules_ignore_classes_local_to_functions() -> None:
    source = '"""Module."""\n\ndef factory():\n    class Local:\n        class Nested:\n            pass\n\n        def method(self):\n            pass\n\n        def __str__(self):\n            return "local"\n\n        def __init__(self):\n            pass\n\n    class _PrivateLocal:\n        class Nested:\n            pass\n\n        def method(self):\n            pass\n\n        def __str__(self):\n            return "local"\n\n        def __init__(self):\n            pass\n'

    assert_findings(source, select=("PDF606", "PDF607", "PDF610", "PDF611", "PDF612", "PDF613", "PDF614", "PDF615"), expected=())


def test_non_initial_string_literals_do_not_satisfy_owner_docstring_rules() -> None:
    source = 'VALUE = 1\n"""Module attribute."""\n\nclass Client:\n    VALUE = 1\n    """Class attribute."""\n\n    def method(self):\n        value = 1\n        """Local string."""\n'

    assert_findings(
        source,
        select=("PDF602", "PDF604", "PDF610"),
        expected=(
            ("PDF602", (1,), "Public module is missing docstring"),
            ("PDF604", (4,), "Public class 'Client' is missing docstring"),
            ("PDF610", (8,), "Public method 'Client.method' is missing docstring"),
        ),
    )


def test_decorated_definitions_report_definition_line_and_ignore_decorator_line_suppression() -> None:
    source = '"""Module."""\n\n@decorator  # pydocfmt: ignore[PDF604]\nclass Client:\n    pass\n\nclass Container:\n    """Container."""\n\n    @decorator  # pydocfmt: ignore[PDF610]\n    def method(self):\n        pass\n'

    assert_findings(
        source,
        select=("PDF604", "PDF610"),
        expected=(("PDF604", (4,), "Public class 'Client' is missing docstring"), ("PDF610", (11,), "Public method 'Container.method' is missing docstring")),
    )


def test_decorated_regular_methods_still_require_docstrings() -> None:
    source = '"""Module."""\n\nclass Client:\n    """Client."""\n\n    @property\n    def url(self):\n        return "https://example.com"\n\n    @classmethod\n    def from_config(cls):\n        return cls()\n\n    @staticmethod\n    def parse(value):\n        return value\n'

    assert_findings(
        source,
        select=("PDF610",),
        expected=(
            ("PDF610", (7,), "Public method 'Client.url' is missing docstring"),
            ("PDF610", (11,), "Public method 'Client.from_config' is missing docstring"),
            ("PDF610", (15,), "Public method 'Client.parse' is missing docstring"),
        ),
    )


def test_override_methods_are_not_required_to_repeat_inherited_documentation() -> None:
    source = '"""Module."""\n\nclass Client:\n    """Client."""\n\n    @typing.override\n    def connect(self):\n        pass\n\n    @typing_extensions.override()\n    def close(self):\n        pass\n\n    @override\n    def flush(self):\n        pass\n\n    def send(self):\n        pass\n'

    assert_findings(source, select=("PDF610",), expected=(("PDF610", (18,), "Public method 'Client.send' is missing docstring"),))


def test_optional_function_decorators_apply_to_all_function_owner_rules() -> None:
    source = '"""Module."""\n\n@typing.override\ndef build():\n    pass\n\n@typing_extensions.override()\ndef _build():\n    pass\n\nclass Client:\n    """Client."""\n\n    @override\n    def connect(self):\n        pass\n\n    @typing.override\n    def __str__(self):\n        return "client"\n\n    @typing_extensions.override()\n    def __init__(self):\n        pass\n\nclass _Private:\n    """Private."""\n\n    @override\n    def connect(self):\n        pass\n\n    @typing.override\n    def __str__(self):\n        return "private"\n\n    @typing_extensions.override()\n    def __init__(self):\n        pass\n'

    assert_findings(source, select=("PDF608", "PDF609", "PDF610", "PDF611", "PDF612", "PDF613", "PDF614", "PDF615"), expected=())


def test_forbidden_function_decorators_also_make_owner_docstrings_optional() -> None:
    source = (
        '"""Module."""\n\n@typing.overload\ndef build(value: int) -> int:\n    pass\n\nclass Client:\n    """Client."""\n\n    @overload()\n    def connect(self, value: int) -> int:\n        pass\n'
    )

    assert_findings(source, select=("PDF608", "PDF610"), expected=())


def test_configured_optional_function_decorators_are_exact_names() -> None:
    source = '"""Module."""\n\n@project.optional\ndef configured():\n    pass\n\n@optional\ndef unconfigured():\n    pass\n\nclass Client:\n    """Client."""\n\n    @project.optional()\n    def configured(self):\n        pass\n\n    @project.other\n    def unconfigured(self):\n        pass\n'
    settings = CheckSettings(select=("PDF608", "PDF610"), docstring_optional_function_decorators=("project.optional",), docstring_forbidden_function_decorators=())

    assert_findings(
        source,
        select=("PDF608", "PDF610"),
        settings=settings,
        expected=(
            ("PDF608", (8,), "Public function 'unconfigured' is missing docstring"),
            ("PDF610", (19,), "Public method 'Client.unconfigured' is missing docstring"),
        ),
    )


def test_dynamic_and_similarly_named_decorators_do_not_skip_method_documentation() -> None:
    source = '"""Module."""\n\n@typing().override\ndef build():\n    pass\n\nclass Client:\n    """Client."""\n\n    @decorator_factory(override)\n    def generated(self):\n        pass\n\n    @(lambda method: method)\n    def dynamic(self):\n        pass\n\n    @typing().override\n    def dynamic_receiver(self):\n        pass\n\n    @project.override\n    def project_override(self):\n        pass\n\n    @project.overridden\n    def similarly_named(self):\n        pass\n'

    assert_findings(
        source,
        select=("PDF608", "PDF610"),
        expected=(
            ("PDF608", (4,), "Public function 'build' is missing docstring"),
            ("PDF610", (11,), "Public method 'Client.generated' is missing docstring"),
            ("PDF610", (15,), "Public method 'Client.dynamic' is missing docstring"),
            ("PDF610", (19,), "Public method 'Client.dynamic_receiver' is missing docstring"),
            ("PDF610", (23,), "Public method 'Client.project_override' is missing docstring"),
            ("PDF610", (27,), "Public method 'Client.similarly_named' is missing docstring"),
        ),
    )


def test_dunder_classification_requires_both_leading_and_trailing_double_underscores() -> None:
    source = '"""Module."""\n\nclass Client:\n    """Client."""\n\n    def __helper(self):\n        pass\n\n    def helper__(self):\n        pass\n\n    def __call__(self):\n        pass\n'

    assert_findings(source, select=("PDF610",), expected=(("PDF610", (9,), "Public method 'Client.helper__' is missing docstring"),))
    assert_findings(source, select=("PDF611",), expected=(("PDF611", (6,), "Private method 'Client.__helper' is missing docstring"),))
    assert_findings(source, select=("PDF612",), expected=(("PDF612", (12,), "Public dunder method 'Client.__call__' is missing docstring"),))


def test_broad_selection_includes_public_non_dunder_rules_only() -> None:
    source = '"""Module."""\n\nclass Client:\n    """Client."""\n\n    def __str__(self):\n        return "client"\n\n    def __init__(self):\n        pass\n\nclass _Private:\n    def __init__(self):\n        pass\n'

    result = format_source(source, select=("PDF",))

    assert "PDF614" in tuple(finding.rule.code.tag for finding in result.unfixed_findings)
    assert "PDF612" not in tuple(finding.rule.code.tag for finding in result.unfixed_findings)
    assert "PDF615" not in tuple(finding.rule.code.tag for finding in result.unfixed_findings)


def test_missing_documentation_settings_do_not_change_owner_public_private_split() -> None:
    source = '"""Module."""\n\nclass _Client:\n    pass\n'
    settings = CheckSettings(
        select=("PDF604", "PDF605"),
        docstring_missing_documentation=DocstringMissingDocumentation.ALL_DOCSTRINGS,
        docstring_missing_documentation_public_only=False,
    )
    result = formatter.format_source(source, "example.py", settings=settings, rule_selection=rules_selection.select_rules(settings), fix=True)

    assert tuple((finding.rule.code.tag, finding.line_numbers, finding.message) for finding in result.unfixed_findings) == (("PDF605", (3,), "Private class '_Client' is missing docstring"),)


def test_suppression_on_definition_line_suppresses_missing_docstring() -> None:
    source = '"""Module."""\n\nclass Client:  # pydocfmt: ignore[PDF604]\n    pass\n'

    assert_findings(source, select=("PDF604",), expected=())


def test_file_suppression_suppresses_missing_module_docstring() -> None:
    source = "# pydocfmt: file-ignore[PDF602]\nVALUE = 1\n"

    assert_findings(source, select=("PDF602",), expected=())
