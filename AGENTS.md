# AGENTS.md

## Rules

- Always use `uv` to manage `.venv` and to run all Python code.
- Never run `uv` with a custom or temporary cache dir (e.g. via UV_CACHE_DIR or --cache-dir). If `uv` fails for cache-related reasons then abort and notify the user.
- `.venv` does not have pip: Instead use `uv pip`, `uv tree`, or similar.
