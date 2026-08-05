"""Repository-wide pytest configuration.

Attributes:
    pytest_plugins (tuple[str, ...]): Explicit shared isolation plugin loaded before pytest session setup.
"""

# Third-party imports
import pytest

# First-party imports
from tests import assertion_rewriting


pytest_plugins = ("la_dev_codex_plugins.pytest_isolation.plugin",)

pytest.register_assert_rewrite(*assertion_rewriting.ASSERT_REWRITE_MODULES)


def pytest_la_dev_cwd_isolation_shared_policy(config: pytest.Config) -> dict[str, dict[str, str]]:
    """Return the project-specific shared CWD isolation policy.

    Args:
        config (pytest.Config): Active pytest configuration; the static project policy does not inspect it.

    Returns:
        Neutral boundary and guarded-CWD poison files for the shared isolation plugin.
    """
    del config
    return {"boundary_files": {"pyproject.toml": '[tool.pydocfmt]\ncache-dir = "tmp/.pydocfmt_cache"\n'}, "poison_files": {"pyproject.toml": "[tool.pydocfmt\n"}}
