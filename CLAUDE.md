- Remember not to use 'Co-Author' on commits because it breaks my CLA requirement.

# Development Standards

## Code Formatting

- Python code uses **2-space indentation** (enforced by pyink)
- All files must end with a newline character
- Use ruff for linting (but NOT formatting)
- Use pyink for formatting with Google style guide

## Pre-commit Hooks

This project uses pre-commit hooks for code quality. To set up:

```bash
make dev-setup  # Creates venv and installs all dependencies including pre-commit
```

Key pre-commit checks include:

- pyink: Python formatting with 2-space indentation
- ruff: Python linting (not formatting)
- yamllint: YAML file validation
- markdownlint: Markdown formatting
- shellcheck: Shell script validation
- mypy: Python type checking
- bandit: Security vulnerability scanning
- detect-secrets: Prevent committing secrets
- Custom validators for Chronicle rules and timestamp configs

## Makefile Commands

- `make` - Show help with all available commands
- `make dev-setup` - Set up virtual environment and pre-commit hooks
- `make lint` - Run ruff linting
- `make format` - Format code with pyink (2-space indentation)
- `make check` - Run all checks (lint + format-check)
- `make pre-commit-run` - Run all pre-commit hooks on all files
