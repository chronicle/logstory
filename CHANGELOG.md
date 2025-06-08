# Changelog

<!--next-version-placeholder-->

## Unreleased

### Added
- Comprehensive pre-commit hooks configuration for code quality
  - Python linting with ruff
  - Python formatting with pyink (2-space indentation)
  - YAML validation with yamllint
  - Markdown linting with markdownlint
  - Shell script checking with shellcheck
  - Python type checking with mypy
  - Security scanning with bandit
  - Secret detection with detect-secrets
  - Custom validators for Chronicle rules and timestamp configurations
  - Terraform validation hooks
  - Protocol buffer linting
  - Spell checking with codespell
- Virtual environment support in Makefile
- Enhanced Makefile with:
  - Default help target showing all available commands
  - Automatic tool detection with helpful error messages
  - `dev-setup` command for easy development environment setup
  - `format` and `format-check` commands using pyink
  - Pre-commit integration commands
- Development configuration files:
  - `.markdownlint.yaml` for markdown standards
  - `.yamllint.yaml` for YAML linting rules
  - `.tflint.hcl` for Terraform linting
  - `.license-header.txt` for Apache 2.0 license headers
- Updated `CLAUDE.md` with development standards and pre-commit information

### Changed
- Switched from ruff formatting to pyink for 2-space indentation support
- Updated `.gitignore` to ensure `.pypirc` and `jpn_config.cfg` are not tracked
- Enhanced `requirements_dev.txt` with additional development tools

### Security
- Removed `.pypirc` from Git tracking (contains PyPI credentials)
- Added comprehensive secret detection in pre-commit hooks

## v0.1.4 (2025)

- Version bump for release

## v0.1.0 (13/11/2024)

- First release of `logstory`!
