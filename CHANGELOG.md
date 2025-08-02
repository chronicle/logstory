# Changelog

<!--next-version-placeholder-->

## Unreleased

### Changed
- **BREAKING**: Migrated CLI from Abseil to Typer with command groups and subcommands
  - Command structure now uses groups: `logstory usecases COMMAND` and `logstory replay COMMAND`
  - Flag names changed to use hyphens: `--customer-id` instead of `--customer_id`
  - Improved help system with auto-generated documentation
  - Better error handling and validation
  - See README.md for command migration guide
- Improved `list-installed` command with better default behavior
  - Default now shows just usecase names (clean and scannable)
  - `--details` flag shows full markdown content (previous default behavior)
  - `--logtypes` flag shows logtypes with clean indentation

### Added
- `--open` flag for `usecases list-installed` to open markdown files in VS Code
- `--details` flag for `usecases list-installed` to show full markdown content
- Environment file support with `--env-file` option for configuration management
- Support for environment variables: `LOGSTORY_CUSTOMER_ID`, `LOGSTORY_CREDENTIALS_PATH`, `LOGSTORY_REGION`
- Automatic loading of `.env` file if present in working directory
- Multiple environment configuration support (e.g., `.env.prod`, `.env.dev`)
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
- Removed `jpn_config.cfg` from Git tracking
- Added comprehensive secret detection in pre-commit hooks

## v0.1.4 (2025)

- Version bump for release

## v0.1.0 (13/11/2024)

- First release of `logstory`!
