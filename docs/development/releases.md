# LogStory Automated Release Process

This document describes the automated release pipeline implemented for the LogStory project, addressing the requirements outlined in [GitHub Issue #15](https://github.com/chronicle/logstory/issues/15).

## Overview

The LogStory project now features a fully automated release pipeline that:

- ✅ Triggers on GitHub Release creation (manual control)
- ✅ Runs comprehensive quality gates
- ✅ Publishes to PyPI automatically
- ✅ Uploads build artifacts to GitHub releases
- ✅ Prevents human error in version management
- ✅ Provides complete release control and transparency

## Quick Start

### For Contributors

1. **Follow standard Git workflow**:
   ```bash
   git commit -m "feat(core): add new timestamp validation feature"
   git commit -m "fix(cli): resolve parsing issue with malformed dates"
   git commit -m "docs(readme): update installation instructions"
   ```

2. **Set up pre-commit hooks** (optional but recommended):
   ```bash
   pip install pre-commit
   pre-commit install
   ```

### For Maintainers

1. **Configure repository secrets** in GitHub:
   - `PYPI_TOKEN`: PyPI API token for publishing packages

2. **Create a GitHub Release** to trigger the automated pipeline:
   ```bash
   # Using GitHub CLI
   gh release create v1.2.3 --title "Release 1.2.3" --notes "Release notes here"
   
   # Or via GitHub web interface:
   # Go to Releases → Draft a new release → Create release
   ```

3. **Manual release** (emergency):
   ```bash
   # Trigger manual release via GitHub Actions with version input
   gh workflow run release.yml -f version=1.2.3
   ```

## Conventional Commits

The project uses [Conventional Commits](https://www.conventionalcommits.org/) specification:

### Format
```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### Types and Release Impact

| Type | Description | Release Impact |
|------|-------------|----------------|
| `feat` | New feature | Minor version bump |
| `fix` | Bug fix | Patch version bump |
| `perf` | Performance improvement | Patch version bump |
| `refactor` | Code refactoring | Patch version bump |
| `build` | Build system changes | Patch version bump |
| `security` | Security fixes | Patch version bump |
| `docs` | Documentation only | No release |
| `style` | Code style changes | No release |
| `test` | Test changes | No release |
| `ci` | CI/CD changes | No release |
| `chore` | Maintenance tasks | No release |

### Breaking Changes

Add `BREAKING CHANGE:` in the footer or `!` after the type to trigger a major version bump:

```bash
# Major version bump (1.0.0 -> 2.0.0)
git commit -m "feat!: remove deprecated timestamp format support"

# Or using footer
git commit -m "feat(core): update timestamp parsing

BREAKING CHANGE: deprecated timestamp format no longer supported"
```

### Examples

```bash
# Minor release (1.0.0 -> 1.1.0)
git commit -m "feat(core): add support for new log format"

# Patch release (1.0.0 -> 1.0.1)
git commit -m "fix(cli): resolve timezone parsing issue"

# No release
git commit -m "docs(readme): update installation guide"
git commit -m "test(core): add unit tests for timestamp validation"

# Major release with breaking change (1.0.0 -> 2.0.0)
git commit -m "feat!: redesign timestamp configuration format"
```

## Release Pipeline

### GitHub Release-Triggered Pipeline

The release pipeline triggers when a **GitHub Release is published** and:

1. **Quality Gates** - Runs comprehensive checks:
   - Code linting with Ruff
   - Security scanning with Bandit
   - Test suite across Python 3.9-3.12
   - Timestamp configuration validation
   - Package build and verification

2. **Version Extraction** - Gets version from release tag:
   - Extracts version from GitHub release tag (e.g., `v1.2.3` → `1.2.3`)
   - Updates `pyproject.toml` with the release version

3. **Build & Publish**:
   - Builds Python wheel and source distribution
   - Verifies package integrity
   - Publishes to PyPI
   - Uploads build artifacts to GitHub release

4. **Notifications** - Reports success/failure status

### Quality Gates

Before any release, the following quality gates must pass:

#### Code Quality
- **Ruff linting**: Enforces code style and catches common issues
- **Ruff formatting**: Ensures consistent code formatting
- **Security scanning**: Bandit checks for security vulnerabilities
- **Dependency scanning**: Safety checks for known vulnerabilities

#### Testing
- **Unit tests**: Core functionality tests across Python versions
- **Integration tests**: End-to-end timestamp processing tests
- **Configuration validation**: YAML syntax and schema validation

#### Build Verification
- **Package building**: Ensures clean wheel and source distribution
- **Installation test**: Verifies package can be installed and imported
- **CLI functionality**: Tests command-line interface

### Manual Release

For emergency releases or testing:

```bash
# Create a GitHub release (preferred method)
gh release create v1.2.3 --title "Release 1.2.3" --notes "Emergency fix for critical issue"

# Or trigger workflow directly with version
gh workflow run release.yml -f version=1.2.3

# Via GitHub web interface
# Navigate to Actions -> Release -> Run workflow -> Enter version
```

## File Structure

The automated release system adds the following files:

```
.
├── .releaserc.js              # Semantic-release configuration
├── .commitlintrc.js           # Commit message validation
├── .gitmessage                # Commit message template
├── .pre-commit-config.yaml    # Pre-commit hooks configuration
├── package.json               # Node.js dependencies for release tools
├── RELEASE_PROCESS.md         # This documentation
└── .github/workflows/
    ├── release.yml            # Main release pipeline
    └── quality-gates.yml      # Quality gate enforcement
```

## Configuration

### Semantic Release (.releaserc.js)

Key configuration options:

- **Branches**: `main` and `chronicle-main`
- **Plugins**: Changelog, version bumping, PyPI publishing, GitHub releases
- **Release rules**: Custom rules for LogStory project needs

### Pre-commit Hooks (.pre-commit-config.yaml)

Enforces code quality before commits:

- Code formatting and linting
- Conventional commit validation
- Security checks
- Timestamp configuration validation

### GitHub Actions

#### release.yml
- Triggers on pushes to main branches
- Runs quality gates before release
- Publishes to PyPI and GitHub

#### quality-gates.yml
- Runs on all pull requests and pushes
- Comprehensive testing and validation
- Prevents broken code from reaching main

## Troubleshooting

### Common Issues

**Release not triggering:**
- Ensure commits follow conventional format
- Check that changes include `feat`, `fix`, or other release-triggering types
- Verify no `[skip ci]` in commit messages

**PyPI publishing fails:**
- Check `PYPI_TOKEN` secret is configured
- Verify token has publish permissions
- Ensure version number doesn't already exist

**Quality gates failing:**
- Run tests locally: `cd tests && python test_yaml.py`
- Check linting: `ruff check .`
- Validate timestamps: `python -c "import yaml; yaml.safe_load(open('src/logstory/logtypes_events_timestamps.yaml'))"`

**Version bump not working:**
- Ensure `pyproject.toml` version format is correct
- Check semantic-release logs for parsing errors

### Manual Recovery

If the automated release fails midway:

1. **Check the failed step** in GitHub Actions logs
2. **Fix the issue** and push another commit
3. **Re-run the workflow** if needed
4. **Manual version bump** if automation failed:
   ```bash
   # Update version in pyproject.toml
   sed -i 's/version = ".*"/version = "1.2.3"/' pyproject.toml
   git add pyproject.toml
   git commit -m "chore(release): bump version to 1.2.3 [skip ci]"
   ```

### Getting Help

- **GitHub Issues**: [Report issues](https://github.com/chronicle/logstory/issues)
- **Workflow Logs**: Check Actions tab for detailed error messages
- **Local Testing**: Run quality gates locally before pushing

## Migration from Manual Releases

This automated system replaces the previous manual release process:

### Before (Manual)
1. Manually edit version in `pyproject.toml`
2. Manually write changelog entries
3. Create git tag manually
4. Build and upload to PyPI manually
5. Create GitHub release manually

### After (Automated)
1. Write conventional commit messages
2. Merge to main branch
3. Automation handles everything else

The new system eliminates human error and ensures consistent, reliable releases while maintaining full traceability and control.

## 🎯 Release Control Summary

### GitHub Release-Based Workflow
Releases are now **manually controlled** by creating GitHub Releases:

1. **Maintainer creates GitHub Release** with desired version tag
2. **Automation runs quality gates** and builds/publishes if they pass
3. **Full control** over when releases happen
4. **No surprise releases** from regular development commits

### Version Tagging
- Use semantic versioning: `v1.2.3` or `1.2.3`
- Pipeline handles both formats automatically
- Version is extracted and applied to `pyproject.toml`

### Benefits
- ✅ **Manual control** - releases only when you want them
- ✅ **Quality assured** - comprehensive testing before publish
- ✅ **Transparent** - clear release notes and artifacts
- ✅ **Safe** - no accidental releases from development work

### Typical Workflow
```bash
# 1. Development work (normal commits)
git commit -m "feat(core): add new timestamp parser"
git commit -m "fix(cli): resolve edge case bug"
git push origin main

# 2. When ready to release, create GitHub Release
gh release create v1.4.0 --title "Release 1.4.0" --notes "
## New Features
- Enhanced timestamp parsing capabilities

## Bug Fixes  
- Fixed edge case in CLI argument parsing
"

# 3. Automation takes over:
#    - Runs all quality gates
#    - Builds package
#    - Publishes to PyPI
#    - Uploads artifacts to GitHub release
```

This approach gives maintainers complete control over the release timing while ensuring all releases meet quality standards.