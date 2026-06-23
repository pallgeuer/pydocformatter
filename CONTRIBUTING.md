# Contributing to pydocformatter

Thank you for your interest in contributing to pydocformatter! We welcome contributions from everyone and are grateful for every pull request, bug report, and feature suggestion.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Code Style](#code-style)
- [Submitting Changes](#submitting-changes)
- [Release Process](#release-process)
- [Getting Help](#getting-help)

## Code of Conduct

This project adheres to a code of conduct that we expect all contributors to follow. Please be respectful and constructive in all interactions.

## Getting Started

### Prerequisites

- Python 3.11 or higher
- [uv](https://docs.astral.sh/uv/)
- Git
- A GitHub account

### Types of Contributions

We welcome several types of contributions:

- **Bug Reports:** Help us identify and fix issues
- **Feature Requests:** Suggest new functionality
- **Documentation:** Improve or add documentation
- **Code:** Fix bugs or implement features
- **Tests:** Add or improve test coverage
- **Examples:** Provide usage examples

## Development Setup

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR-USERNAME/pydocformatter.git
cd pydocformatter
```

### 2. Set Up Development Environment

```bash
uv sync --group dev
```

### 3. Set Up Pre-commit Hooks

```bash
# Install pre-commit hooks
uv run pre-commit install

# Test the hooks (this will use the local development version)
uv run pre-commit run --all-files
```

**Note:** During development, the pre-commit hooks use the local version of pydocformatter. External users will use the published version from the repository.

**Dependency pinning note:**
- All dependencies in `dependency-groups.test` and `dependency-groups.dev` in `pyproject.toml` must use exact pins (`name==version`).
- The `black`, `isort`, and `mypy` versions in `dependency-groups.dev` must exactly match the corresponding `rev` values in `.pre-commit-config.yaml` (ignoring an optional `v` prefix).

### 4. Verify Installation

```bash
# Test the CLI tools
uv run pydocfmt --help
uv run pydocfmt check --help

# Run tests
uv run pytest -q
```

Pytest uses project-default multiprocessing through pytest-xdist. Add `-n 0` when a serial run is needed for debugging or a focused run avoids worker startup overhead.

## Making Changes

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b bugfix/issue-description
```

### Branch Naming Convention

- **Features:** `feature/description-of-feature`
- **Bug fixes:** `bugfix/issue-description`
- **Documentation:** `docs/what-you-are-documenting`
- **Tests:** `test/what-you-are-testing`

### 2. Make Your Changes

#### For Bug Fixes:
1. Write a test that reproduces the bug
2. Fix the bug
3. Ensure the test passes
4. Update documentation if needed

#### For New Features:
1. Discuss the feature in an issue first (for major changes)
2. Write tests for the new functionality
3. Implement the feature
4. Update documentation
5. Add examples if applicable

### 3. Code Guidelines

#### Python Code Style
- Follow PEP 8
- Use type hints for all function parameters and return values
- Write docstrings for all public functions and classes
- Keep functions focused and small
- Use descriptive variable and function names

#### Documentation Style
- Use Google-style docstrings
- Include examples in docstrings when helpful
- Keep line length to 88 characters
- Use proper Markdown formatting

## Testing

### Running Tests

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

### Writing Tests

- Write tests for all new functionality
- Include edge cases and error conditions
- Use descriptive test method names
- Follow the existing test patterns

#### Test File Structure
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

## Code Style

We use several tools to maintain code quality:

### Automated Formatting
- **Black:** Code formatting
- **isort:** Import sorting
- **pydocfmt:** Docstring and comment formatting (our own tool)

### Code Quality
- **MyPy:** Type checking
- **Pre-commit:** Automated checks

### Running Style Checks

```bash
# Format code
uv run black .
uv run isort .
uv run pydocfmt check --fix

# Check formatting without changes
uv run black --check .
uv run isort --check .
uv run pydocfmt check

# Type checking
uv run mypy

# Run the full local hook suite
uv run pre-commit run --all-files
```

## Submitting Changes

### 1. Before Submitting

- [ ] All tests pass
- [ ] Code follows style guidelines
- [ ] Documentation is updated
- [ ] Commit messages are clear and descriptive
- [ ] Changes are focused and atomic

### 2. Commit Message Format

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

### 3. Pull Request Process

1. **Push your branch** to your fork
2. **Create a Pull Request** on GitHub
3. **Fill out the PR template** completely
4. **Wait for review** and address feedback
5. **Ensure CI passes** on all checks

#### Pull Request Title Format
```
[Type] Brief description of changes

Examples:
[Feature] Add support for NumPy-style docstrings
[Bugfix] Fix comment wrapping edge case with special characters
[Docs] Update installation instructions
```

#### Pull Request Description Template
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

### 4. Review Process

- **All PRs require review** before merging
- **Address feedback promptly** and professionally
- **Keep discussions focused** on the code
- **Be open to suggestions** and alternative approaches

## Release Process

### Versioning

We follow [Semantic Versioning](https://semver.org/):
- **MAJOR:** Breaking changes
- **MINOR:** New features (backward compatible)
- **PATCH:** Bug fixes (backward compatible)

### Release Steps (for maintainers)

Follow the detailed [release checklist](RELEASE.md). At a high level:

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create release PR
4. After merge, tag the release
5. Create GitHub release
6. Publish to PyPI

## Development Tips

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

## Getting Help

### Communication Channels
- **GitHub Issues:** Bug reports and feature requests
- **GitHub Discussions:** General questions and ideas
- **Pull Request Comments:** Code-specific discussions

### Asking Good Questions
1. **Search existing issues** first
2. **Provide minimal reproducible examples**
3. **Include environment details** (Python version, OS, etc.)
4. **Be specific** about expected vs. actual behavior

### Useful Resources
- [Python Style Guide (PEP 8)](https://pep8.org/)
- [Google Style Docstrings](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)
- [Semantic Versioning](https://semver.org/)
- [Keep a Changelog](https://keepachangelog.com/)

---

### Need Help?
- Read the [README](README.md)
- [Report a bug](https://github.com/pallgeuer/pydocformatter/issues/new)
- [Request a feature](https://github.com/pallgeuer/pydocformatter/issues/new)
- [Start a discussion](https://github.com/pallgeuer/pydocformatter/discussions)
