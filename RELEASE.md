# Release checklist for pydocformatter

## Pre-release validation

### Code quality
- [x] All tests pass with project-default pytest-xdist multiprocessing (`uv run pytest -q`)
- [x] Package builds successfully (`uv build`)
- [x] No linting errors (`uv run ruff check`, `uv run pydocfmt check`, `uv run ruff format --check`, `uv run ty check`)
- [x] Pre-commit hooks pass (`uv run pre-commit run --all-files`)

### Documentation
- [x] [README](README.md) is comprehensive and up-to-date
- [x] [Changelog](CHANGELOG.md) is complete for new version
- [x] [Release checklist](RELEASE.md) is up-to-date with current uv-based commands
- [x] [Contributing](CONTRIBUTING.md) provides clear guidelines
- [x] Generated Zensical documentation builds successfully (`uv run python tools/docs/generate_zensical.py`, `uv run zensical build --strict -f zensical.generated.toml`)
- [x] All docstrings are properly formatted

### Project configuration
- [x] pyproject.toml has complete metadata
- [x] Version number is correct
- [x] License information is accurate
- [x] Entry points are configured correctly
- [x] Dependencies are minimal and correct

### GitHub setup
- [x] .pre-commit-hooks.yaml for external consumption
- [x] Pull request template
- [x] GitHub Actions workflows

## Release process

Set the release version once and use it consistently in the commands below:

```bash
VERSION=1.0.0
```

### Step 1: Final validation
```bash
# Run tests one more time with project-default pytest-xdist multiprocessing
uv run pytest -q

# Check linting, formatting, and types
uv run ruff check
uv run pydocfmt check
uv run ruff format --check
uv run ty check

# Build documentation site
uv run python tools/docs/generate_zensical.py
uv run zensical build --strict -f zensical.generated.toml

# Run pre-commit hooks
uv run pre-commit run --all-files

# Test build
uv build

# Test CLI tools
uv run pydocfmt --help
uv run pydocfmt check --help

# Test functionality
uv run python -c "
import tempfile
from pathlib import Path

with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
    f.write('def test(): \"\"\"Test function.\"\"\"')
    fname = f.name
import subprocess
subprocess.run(['uv', 'run', 'pydocfmt', 'check', '--fix', fname], check=True)
print(Path(fname).read_text())
"
```

### Step 2: Commit and push final changes
```bash
# Stage all changes
git add .

# Final commit
git commit -m "feat: prepare for v${VERSION} release"

# Push to main
git push origin main
```

### Step 3: Create GitHub release
1. Go to <https://github.com/pallgeuer/pydocformatter/releases>
2. Click "Create a new release"
3. Tag: `v${VERSION}`
4. Title: `pydocformatter v${VERSION} release`
5. Description: Use the content from CHANGELOG.md for this release. For the next release, move the current `Unreleased` entries under the new version heading before tagging.
6. Upload built packages: `dist/pydocformatter-${VERSION}.tar.gz` and `dist/pydocformatter-${VERSION}-py3-none-any.whl`
7. Click "Publish release"

### Step 4: Publish to PyPI
```bash
rm -rf dist/*
uv build
uv publish --token pypi-...           # <-- Option A
UV_PUBLISH_TOKEN=pypi-... uv publish  # <-- Option B
```

### Step 5: Post-release tasks
- [ ] Update README badges if needed
- [ ] Announce on social media/relevant communities
- [ ] Monitor for issues and feedback
- [ ] Plan next release features

## Release artifacts

The following files will be created and distributed:

1. **Source Distribution:** `pydocformatter-${VERSION}.tar.gz`
2. **Wheel Distribution:** `pydocformatter-${VERSION}-py3-none-any.whl`
3. **GitHub Release:** With release notes and assets
4. **PyPI Package:** Available via `pip install pydocformatter`

## Post-release validation

After release, verify:

1. **PyPI installation:**
   ```bash
   pip install pydocformatter
   pydocfmt --help
   pydocfmt check --help
   ```

2. **Pre-commit hook usage:**
   ```yaml
   repos:
     - repo: https://github.com/pallgeuer/pydocformatter
       rev: v1.0.0
       hooks:
         - id: pydocfmt-fix
   ```

3. **GitHub features:**
   - [ ] Actions run successfully
   - [ ] Pre-commit hooks work for external users

## Success criteria

**Release is successful when:**
- Package installs cleanly from PyPI
- CLI tools work correctly
- Pre-commit hooks are usable by external projects
- Documentation is accessible and helpful
- No critical bugs reported in first 24 hours

## Support channels

After release, users can get help via:
- GitHub Issues: Bug reports and feature requests
- GitHub Discussions: Questions and community support
