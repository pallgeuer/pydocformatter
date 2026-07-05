import libcst as cst

import pydocformatter.rules.definition_helpers.decorators as decorators
from pydocformatter.cli.settings_check import CheckSettings


def test_decorator_qualified_name_unwraps_calls_and_attributes() -> None:
    assert decorators.decorator_qualified_name(cst.parse_expression("package.decorator()")) == "package.decorator"
    assert decorators.decorator_qualified_name(cst.parse_expression("package.decorator.extra")) == "package.decorator.extra"
    assert decorators.decorator_qualified_name(cst.parse_expression("decorator")) == "decorator"


def test_decorator_qualified_name_returns_none_for_dynamic_expression() -> None:
    assert decorators.decorator_qualified_name(cst.parse_expression("factory().decorator")) is None
    assert decorators.decorator_qualified_name(cst.parse_expression("typing().overload")) is None
    assert decorators.decorator_qualified_name(cst.parse_expression("factory()[0]")) is None


def test_is_property_decorator_name_uses_exact_configured_names_and_accessor_suffixes() -> None:
    settings = CheckSettings(docstring_property_decorators=("property", "project.Property"))

    assert decorators.is_property_decorator_name("property", settings=settings)
    assert decorators.is_property_decorator_name("project.Property", settings=settings)
    assert decorators.is_property_decorator_name("value.getter", settings=settings)
    assert decorators.is_property_decorator_name("value.setter", settings=settings)
    assert decorators.is_property_decorator_name("value.deleter", settings=settings)
    assert not decorators.is_property_decorator_name("project.property", settings=settings)
    assert not decorators.is_property_decorator_name("project.Property.extra", settings=settings)
    assert not decorators.is_property_decorator_name("getter", settings=settings)
