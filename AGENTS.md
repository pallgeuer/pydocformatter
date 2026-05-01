# AGENTS.md

## Rules

- Use `uv` for `.venv` management and all Python execution.
- Never run `uv` with a custom/temporary cache dir (e.g. `UV_CACHE_DIR` or `--cache-dir`); if cache-related `uv` failures occur then abort and notify the user.
- `.venv` has no `pip`; use `uv pip`, `uv tree`, or similar.
