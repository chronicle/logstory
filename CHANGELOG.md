# Changelog

<!--next-version-placeholder-->

## v1.2.2 (2026-08-13)

### Changed
- Brought codebase into full compliance with Google Python Style Guide (Issue #11)
  - Hoisted all deferred imports to module top level
  - Added Google-style docstrings across all modules, classes, protocols, and public methods
  - Modernized test suite to use standard pytest assertions
  - Formatted repository with pyink (2-space indentation)
  - Tightened Ruff linter configuration to enforce Google Python style rules in CI

## v1.2.1 (2026-08-13)

### Changed
- Updated copyright year to 2026 across all Python source files, tests, documentation, and YAML configurations
- Added Apache 2.0 license headers to missing package init files (`src/logstory/usecases/__init__.py` and `src/logstory/usecases/NETWORK_ANALYSIS/__init__.py`)
- Updated codespell dictionary configuration in `.pre-commit-config.yaml` to ignore `thw`
- Resolved ruff lint annotations in `auth` and `ingestion` modules

## v1.2.0 (2026-08-13)

### Changed
- Migrated from `Makefile` to `Justfile` (`just`) for development and cloud workflows
  - Enables direct, robust gcloud setup and deployment recipes
  - Automatic `.env` loading and environment variable fallback support
  - Integrated recipes for Google Cloud setup (`auth-login`, `auth-adc`, `project-set`, `project-get`, `apis-enable`)
  - Integrated recipes for Secret Manager (`secret-create`, `secret-describe`, `secret-list`, `secret-iam`)
  - Integrated recipes for Cloud Run deployment & schedulers (`cloudrun-job-deploy`, `cloudrun-service-deploy`, `cloudrun-schedule-all`, `cloudrun-schedule-custom`, `cloudrun-status`, `cloudrun-logs`, `cloudrun-delete-all`)
  - Integrated recipes for Usecases / GCS bucket synchronization (`usecase-publish`, `usecase-publish-all`, `usecase-list-gcs`)
  - Integrated recipes for PyPI / TestPyPI publishing and testing (`pypi-publish-test`, `pypi-test-install`, `pypi-publish`)
  - Integrated recipes for Sphinx documentation (`docs-build`, `docs-live`, `docs-clean`)
  - Integrated recipes for local Docker testing (`docker-build-local`, `docker-run-local`)

## v1.1.2 (2026-08-13)

### Changed
- Modernized dependency management using `pyproject.toml` (PEP 621) as single source of truth
  - Replaced outdated pinned dependencies with modern version bounds (`>=`)
  - Consolidated development and documentation dependencies into `[project.optional-dependencies]`
  - Removed separate `requirements_dev.txt` in favor of `.[dev]` and `uv` workflows
  - Recompiled and pinned `src/logstory/requirements.txt` directly from `pyproject.toml`
  - Updated `uv.lock` with latest dependencies
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
