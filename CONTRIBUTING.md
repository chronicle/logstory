# How to Contribute

We would love to accept your patches and contributions to this project.

## Before you begin

### Sign our Contributor License Agreement

Contributions to this project must be accompanied by a
[Contributor License Agreement](https://cla.developers.google.com/about) (CLA).
You (or your employer) retain the copyright to your contribution; this simply
gives us permission to use and redistribute your contributions as part of the
project.

If you or your current employer have already signed the Google CLA (even if it
was for a different project), you probably don't need to do it again.

Visit <https://cla.developers.google.com/> to see your current agreements or to
sign a new one.

### Review our Community Guidelines

This project follows [Google's Open Source Community
Guidelines](https://opensource.google/conduct/).

## Contribution process

### Code Reviews

All submissions, including submissions by project members, require review. We
use [GitHub pull requests](https://docs.github.com/articles/about-pull-requests)
for this purpose.

### Development Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/chronicle/logstory.git
   cd logstory
   ```

2. **Set up development environment**:
   ```bash
   python -m pip install --upgrade pip
   pip install -e .
   pip install ruff pytest pyyaml
   ```

3. **Install pre-commit hooks** (optional but recommended):
   ```bash
   pip install pre-commit
   pre-commit install
   ```

### Code Standards

- **Linting**: Ruff is available for code linting and formatting (currently non-enforced)
- **Testing**: Add tests for new functionality in the `tests/` directory
- **Documentation**: Update relevant documentation for user-facing changes

### Running Tests

```bash
# Run timestamp validation tests
cd tests
python test_yaml.py
python test_logstory.py

# Run linting
ruff check .
ruff format --check .
```

## Releases

This project uses an automated release process triggered by GitHub Releases. **Only maintainers can create releases.**

### For Contributors

- **No special release actions needed** - just submit quality pull requests
- All releases go through comprehensive quality gates automatically
- Follow standard Git workflow for contributions

### For Maintainers

#### Creating a Release

1. **Ensure main branch is ready**:
   ```bash
   # All desired changes should be merged to main
   git checkout main
   git pull origin main
   ```

2. **Create a GitHub Release**:
   ```bash
   # Using GitHub CLI (recommended)
   gh release create v1.2.3 --title "Release 1.2.3" --notes "
   ## New Features
   - Feature description

   ## Bug Fixes
   - Bug fix description

   ## Breaking Changes
   - Any breaking changes
   "

   # Or via GitHub web interface:
   # Go to: Releases → Draft a new release → Fill in details → Publish release
   ```

3. **Automation handles the rest**:
   - Runs comprehensive quality gates
   - Updates version in `pyproject.toml`
   - Builds Python package
   - Publishes to PyPI
   - Uploads build artifacts to GitHub release

#### Emergency Releases

For urgent fixes that need immediate release:

```bash
# Trigger workflow manually with specific version
gh workflow run release.yml -f version=1.2.4
```

#### Release Requirements

Before creating a release, ensure:

- ✅ All tests pass on main branch
- ✅ Version number follows [semantic versioning](https://semver.org/)
- ✅ Release notes describe changes clearly
- ✅ `PYPI_TOKEN` secret is configured in repository settings

#### Quality Gates

Every release automatically runs:

- **Code Quality**: Ruff linting and formatting checks (currently non-blocking)
- **Security**: Bandit security scanning and dependency vulnerability checks
- **Testing**: Full test suite across Python 3.9-3.12
- **Validation**: Timestamp configuration validation
- **Build**: Package building and installation verification

Currently, only testing, validation, and build failures will block releases. Code quality checks run but don't fail the pipeline yet.

For detailed technical documentation about the release pipeline, see [`docs/development/releases.md`](docs/development/releases.md).
