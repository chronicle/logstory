.PHONY: help
help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ''
	@echo 'Virtual Environment:'
	@echo '  - Run "make dev-setup" to create a venv and install dependencies'
	@echo '  - Run "make dev-setup-no-venv" to use your current Python environment'
	@echo '  - Commands will automatically use venv if it exists'

.DEFAULT_GOAL := help

# Define the Python build command
build: ## Build the Python package
	@if [ -d "$(VENV)" ]; then \
		$(PYTHON) -m build; \
	else \
		python -m build; \
	fi

clean: ## Clean build directories
	rm -rf dist/ build/ *.egg-info

clean-all: clean venv-clean ## Clean everything including virtual environment

rebuild: clean build ## Clean and rebuild the package

lint: ## Run ruff linting checks
	@if [ -d "$(VENV)" ] && [ -x "$(VENV)/bin/ruff" ]; then \
		$(VENV)/bin/ruff check .; \
	elif command -v ruff >/dev/null 2>&1; then \
		ruff check .; \
	else \
		echo "Error: ruff is not installed. Run 'make dev-setup' first."; exit 1; \
	fi

lint-fix: ## Run ruff with automatic fixes
	@if [ -d "$(VENV)" ] && [ -x "$(VENV)/bin/ruff" ]; then \
		$(VENV)/bin/ruff check . --fix; \
	elif command -v ruff >/dev/null 2>&1; then \
		ruff check . --fix; \
	else \
		echo "Error: ruff is not installed. Run 'make dev-setup' first."; exit 1; \
	fi

format: ## Format code with pyink (2-space indentation)
	@if [ -d "$(VENV)" ] && [ -x "$(VENV)/bin/pyink" ]; then \
		$(VENV)/bin/pyink .; \
	elif command -v pyink >/dev/null 2>&1; then \
		pyink .; \
	else \
		echo "Error: pyink is not installed. Run 'make dev-setup' first."; exit 1; \
	fi

format-check: ## Check code formatting without changes
	@if [ -d "$(VENV)" ] && [ -x "$(VENV)/bin/pyink" ]; then \
		$(VENV)/bin/pyink . --check; \
	elif command -v pyink >/dev/null 2>&1; then \
		pyink . --check; \
	else \
		echo "Error: pyink is not installed. Run 'make dev-setup' first."; exit 1; \
	fi

check: lint format-check ## Run all linting and format checks

fix: lint-fix format ## Fix all linting and formatting issues

pre-commit-install: ## Install pre-commit hooks
	@if [ -d "$(VENV)" ] && [ -x "$(VENV)/bin/pre-commit" ]; then \
		$(VENV)/bin/pre-commit install; \
	elif command -v pre-commit >/dev/null 2>&1; then \
		pre-commit install; \
	else \
		echo "Error: pre-commit is not installed. Run 'make dev-setup' first."; exit 1; \
	fi

pre-commit-run: ## Run pre-commit on all files
	@if [ -d "$(VENV)" ] && [ -x "$(VENV)/bin/pre-commit" ]; then \
		$(VENV)/bin/pre-commit run --all-files; \
	elif command -v pre-commit >/dev/null 2>&1; then \
		pre-commit run --all-files; \
	else \
		echo "Error: pre-commit is not installed. Run 'make dev-setup' first."; exit 1; \
	fi

pre-commit-update: ## Update pre-commit hooks to latest versions
	@if [ -d "$(VENV)" ] && [ -x "$(VENV)/bin/pre-commit" ]; then \
		$(VENV)/bin/pre-commit autoupdate; \
	elif command -v pre-commit >/dev/null 2>&1; then \
		pre-commit autoupdate; \
	else \
		echo "Error: pre-commit is not installed. Run 'make dev-setup' first."; exit 1; \
	fi

# Virtual environment variables
VENV := venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

venv: ## Create virtual environment
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip

venv-clean: ## Remove virtual environment
	rm -rf $(VENV)

dev-setup: venv ## Setup development environment (install deps + pre-commit)
	$(PIP) install -r requirements_dev.txt
	$(VENV)/bin/pre-commit install

dev-setup-no-venv: ## Setup dev environment without venv (use current environment)
	pip install -r requirements_dev.txt
	pre-commit install
