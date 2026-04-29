# Release Checklist for pydocformatter

## Pre-Release Validation

### Code Quality
- [x] All tests pass (`python -m unittest discover -s tests -v`)
- [x] Package builds successfully (`python -m build`)
- [x] No linting errors (black, isort, pycommentfmt, pydocfmt, mypy)
- [x] Pre-commit hooks pass

### Documentation
- [x] README.md is comprehensive and up-to-date
- [x] CHANGELOG.md is complete for new version
- [x] CONTRIBUTING.md provides clear guidelines
- [x] All docstrings are properly formatted

### Project Configuration
- [x] pyproject.toml has complete metadata
- [x] Version number is correct
- [x] License information is accurate
- [x] Entry points are configured correctly
- [x] Dependencies are minimal and correct

### GitHub Setup
- [x] .pre-commit-hooks.yaml for external consumption
- [x] Pull request template
- [x] Dependabot configuration
- [x] GitHub Actions workflows
- [x] Issue templates (optional for initial release)

## Release Process

### Step 1: Final Validation
```bash
# Run tests one more time
python -m unittest discover -s tests -v

# Test build
python -m build

# Test installation from built package
pip install dist/pydocformatter-0.2.0-py3-none-any.whl

# Test CLI tools
pydocfmt --help
pycommentfmt --help

# Test functionality
echo 'def test(): """Test function."""' | python -c "
import tempfile
with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
    f.write('def test(): \"\"\"Test function.\"\"\"')
    fname = f.name
import subprocess
subprocess.run(['pydocfmt', fname])
with open(fname) as f: print(f.read())
"
```

### Step 2: Commit and Push Final Changes
```bash
# Stage all changes
git add .

# Final commit
git commit -m "feat: prepare for v0.2.0 release

- Complete project documentation
- Add comprehensive release infrastructure
- Ready for initial public release"

# Push to main
git push origin main
```

### Step 3: Create GitHub Release
1. Go to https://github.com/pallgeuer/pydocformatter/releases
2. Click "Create a new release"
3. Tag: `v0.2.0`
4. Title: `pydocformatter v0.2.0 release`
5. Description: Use the content from CHANGELOG.md for v0.2.0
6. Upload built packages: `dist/pydocformatter-0.2.0.tar.gz` and `dist/pydocformatter-0.2.0-py3-none-any.whl`
7. Click "Publish release"

### Step 4: Publish to PyPI
```bash
# Install twine for uploading
pip install twine

# Upload to Test PyPI first (optional but recommended)
python -m twine upload --repository testpypi dist/*

# Test installation from Test PyPI
pip install --index-url https://test.pypi.org/simple/ pydocformatter

# If everything works, upload to real PyPI
python -m twine upload dist/*
```

### Step 5: Post-Release Tasks
- [ ] Update README badges if needed
- [ ] Announce on social media/relevant communities
- [ ] Monitor for issues and feedback
- [ ] Plan next release features

## Release Artifacts

The following files will be created and distributed:

1. **Source Distribution**: `pydocformatter-0.2.0.tar.gz`
2. **Wheel Distribution**: `pydocformatter-0.2.0-py3-none-any.whl`
3. **GitHub Release**: With release notes and assets
4. **PyPI Package**: Available via `pip install pydocformatter`

## Post-Release Validation

After release, verify:

1. **PyPI Installation**:
   ```bash
   pip install pydocformatter
   pydocfmt --version
   pycommentfmt --version
   ```

2. **Pre-commit Hook Usage**:
   ```yaml
   repos:
     - repo: https://github.com/pallgeuer/pydocformatter
       rev: v0.2.0
       hooks:
         - id: pydocfmt
         - id: pycommentfmt
   ```

3. **GitHub Features**:
   - [ ] Dependabot is active
   - [ ] Actions run successfully
   - [ ] Pre-commit hooks work for external users

## Success Criteria

**Release is successful when**:
- Package installs cleanly from PyPI
- CLI tools work correctly
- Pre-commit hooks are usable by external projects
- Documentation is accessible and helpful
- No critical bugs reported in first 24 hours

## Support Channels

After release, users can get help via:
- GitHub Issues: Bug reports and feature requests
- GitHub Discussions: Questions and community support

---

## Quick Release Commands

For convenience, here are the key commands:

```bash
# Final validation
python -m unittest discover -s tests -v
python -m build

# Release
git add .
git commit -m "feat: prepare for v0.2.0 release"
git push origin main

# Tag and upload (after GitHub release)
python -m twine upload dist/*
```
