# Contributing to pydocformatter

Thank you for your interest in contributing to pydocformatter! We welcome contributions from everyone and are grateful for every pull request, bug report, and feature suggestion.

## Code of conduct

This project adheres to a code of conduct that we expect all contributors to follow. Please be respectful and constructive in all interactions.

## Getting started

### Prerequisites

- Python 3.11 or higher
- [uv](https://docs.astral.sh/uv/)
- Git
- A GitHub account

### Types of contributions

We welcome several types of contributions:

- **Bug Reports:** Help us identify and fix issues
- **Feature Requests:** Suggest new functionality
- **Documentation:** Improve or add documentation
- **Code:** Fix bugs or implement features
- **Tests:** Add or improve test coverage
- **Examples:** Provide usage examples

## Development setup

### 1. Fork and clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR-USERNAME/pydocformatter.git
cd pydocformatter
```

### 2. Set up development environment

```bash
uv sync --group dev
```

### 3. Set up pre-commit hooks

```bash
# Install pre-commit hooks
uv run pre-commit install

# Test the hooks (this will use the local development version)
uv run pre-commit run --all-files
```

**Note:** During development, the pre-commit hooks use the local version of pydocformatter. External users will use the published version from the repository.

**Dependency pinning note:**
- All dependencies in `dependency-groups.test` and `dependency-groups.dev` in `pyproject.toml` must use exact pins (`name==version`).
- The `pre-commit`, `ruff`, and `ty` dependencies in `dependency-groups.dev` must stay pinned because local hooks run them from the locked project environment.

### 4. Verify installation

```bash
# Test the CLI tools
uv run pydocfmt --help
uv run pydocfmt check --help

# Run tests
uv run pytest -q
```

Pytest uses project-default multiprocessing through pytest-xdist. Add `-n 0` when a serial run is needed for debugging or a focused run avoids worker startup overhead.

## Making changes

### 1. Create a branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b bugfix/issue-description
```

### Branch naming convention

- **Features:** `feature/description-of-feature`
- **Bug fixes:** `bugfix/issue-description`
- **Documentation:** `docs/what-you-are-documenting`
- **Tests:** `test/what-you-are-testing`

### 2. Make your changes

#### For bug fixes:
1. Write a test that reproduces the bug
2. Fix the bug
3. Ensure the test passes
4. Update documentation if needed

#### For new features:
1. Discuss the feature in an issue first (for major changes)
2. Write tests for the new functionality
3. Implement the feature
4. Update documentation
5. Add examples if applicable

### 3. Code guidelines

#### Python code style
- Follow PEP 8
- Use type hints for all function parameters and return values
- Write docstrings for all public functions and classes
- Keep functions focused and small
- Use descriptive variable and function names

#### Documentation style
- Use Google-style docstrings
- Include examples in docstrings when helpful
- Keep line length to 88 characters
- Use proper Markdown formatting

## Testing

### Running tests

```bash
# Run all tests
uv run pytest -q

# Run tests with coverage
uv run pytest -q --cov=pydocformatter --cov-report=html

# Run specific test file
uv run pytest -q tests/test_pydocfmt.py

# Run tests serially for debugging or focused-run speed
uv run pytest -n 0 -q
```

### Writing tests

- Write tests for all new functionality
- Include edge cases and error conditions
- Use descriptive test method names
- Follow the existing test patterns

#### Test file structure
```python
from pydocformatter.your_module import your_function  # noqa


def test_normal_case() -> None:
    """Test the normal expected behavior."""
    input_data = "test input"
    expected = "expected output"

    result = your_function(input_data)

    assert result == expected


def test_edge_case() -> None:
    """Test edge cases."""
```

## Documentation site

The public documentation site is generated with Zensical. Use `uv` for all docs commands:

```bash
uv run python tools/docs/generate_zensical.py
uv run zensical build --strict -f zensical.generated.toml
uv run zensical serve -f zensical.generated.toml
```

Use the focused generator test while iterating:

```bash
uv run pytest -n 0 tests/test_docs_generation.py
```

The docs dependency tree must stay free of MkDocs, Material for MkDocs, mkdocstrings, mkdocs-redirects, ProperDocs, and MkDocs plugin packages.

After the docs workflow is merged and pushed, GitHub Pages may need repository settings configured manually:

1. Open the GitHub repository settings.
2. In Pages, set Build and deployment to GitHub Actions.
3. In Actions, General, keep workflow permissions at read-only repository contents because the docs workflow declares granular `pages: write` and `id-token: write` permissions.
4. Push the branch and let the docs workflow deploy.
5. Open `https://pallgeuer.github.io/pydocformatter/`.

## Code style

We use several tools to maintain code quality (also via automated pre-commit checks):

### Automated formatting
- **Ruff:** Code formatting
- **pydocfmt:** Docstring and comment formatting (our own tool)

### Code quality
- **Ruff:** Code linting
- **pydocfmt:** Docstring and comment checking (our own tool)
- **ty:** Type checking

### Running style checks

```bash
# Lint and format code
uv run ruff check --fix
uv run pydocfmt check --fix
uv run ruff format

# Check linter and formatter findings without making changes
uv run ruff check
uv run pydocfmt check
uv run ruff format --check

# Type checking
uv run ty check

# Run the full local hook suite (includes the above)
uv run pre-commit run --all-files
```

## Submitting changes

### 1. Before submitting

- [ ] All tests pass
- [ ] Code follows style guidelines
- [ ] Documentation is updated
- [ ] Commit messages are clear and descriptive
- [ ] Changes are focused and atomic

### 2. Commit message format

Use clear, descriptive commit messages:

```
type: short description (50 chars or less)

Longer description if needed. Explain what and why, not how.
Include any breaking changes or important notes.

Fixes #123
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

### 3. Pull request process

1. **Push your branch** to your fork
2. **Create a Pull Request** on GitHub
3. **Fill out the PR template** completely
4. **Wait for review** and address feedback
5. **Ensure CI passes** on all checks

#### Pull request title format
```
[Type] Brief description of changes

Examples:
[Feature] Add support for NumPy-style docstrings
[Bugfix] Fix comment wrapping edge case with special characters
[Docs] Update installation instructions
```

#### Pull request description template
```markdown
## Description
Brief description of changes and motivation.

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing
- [ ] New tests added for new functionality
- [ ] All existing tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Comments added for complex code
- [ ] No new warnings introduced

## Related Issues
Fixes #(issue number)
```

### 4. Review process

- **All PRs require review** before merging
- **Address feedback promptly** and professionally
- **Keep discussions focused** on the code
- **Be open to suggestions** and alternative approaches

## Release process

### Versioning

We follow [Semantic Versioning](https://semver.org/):
- **MAJOR:** Breaking changes
- **MINOR:** New features (backward compatible)
- **PATCH:** Bug fixes (backward compatible)

### Release steps (for maintainers)

Follow the detailed [release checklist](RELEASE.md). At a high level:

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create release PR
4. After merge, tag the release
5. Create GitHub release
6. Publish to PyPI

## Development tips

### Debugging
- Use `uv run python -m pdb` for debugging
- Add print statements or logging for complex issues
- Test with various Python files to ensure compatibility

### Performance
- Consider performance impact for large files
- Profile code when making optimization changes
- Keep memory usage reasonable

### Compatibility
- Test with different Python versions (3.11+)
- Ensure cross-platform compatibility (Windows, macOS, Linux)
- Consider edge cases in file handling

## Getting help

### Communication channels
- **GitHub Issues:** Bug reports and feature requests
- **GitHub Discussions:** General questions and ideas
- **Pull Request Comments:** Code-specific discussions

### Asking good questions
1. **Search existing issues** first
2. **Provide minimal reproducible examples**
3. **Include environment details** (Python version, OS, etc.)
4. **Be specific** about expected vs. actual behavior

### Useful resources
- [Python Style Guide (PEP 8)](https://pep8.org/)
- [Google Style Docstrings](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)
- [Semantic Versioning](https://semver.org/)
- [Keep a Changelog](https://keepachangelog.com/)

---

### Need help?
- Read the [README](README.md)
- [Report a bug](https://github.com/pallgeuer/pydocformatter/issues/new)
- [Request a feature](https://github.com/pallgeuer/pydocformatter/issues/new)
- [Start a discussion](https://github.com/pallgeuer/pydocformatter/discussions)
