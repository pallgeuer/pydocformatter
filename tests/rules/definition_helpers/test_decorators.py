import libcst as cst

import pydocformatter.rules.definition_helpers.decorators as decorators


def test_decorator_qualified_name_unwraps_calls_and_attributes() -> None:
    assert decorators.decorator_qualified_name(cst.parse_expression("package.decorator()")) == "package.decorator"
    assert decorators.decorator_qualified_name(cst.parse_expression("decorator")) == "decorator"


def test_decorator_qualified_name_returns_none_for_dynamic_expression() -> None:
    assert decorators.decorator_qualified_name(cst.parse_expression("factory()[0]")) is None
