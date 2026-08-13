# Justfile for Logstory
# Run `just` or `just help` to see available recipes

set dotenv-load := true

# Global configuration variables - read from environment or use defaults

project_id := env_var_or_default("LOGSTORY_PROJECT_ID", `gcloud config get-value project 2>/dev/null || echo ''`)
customer_id := env_var_or_default("LOGSTORY_CUSTOMER_ID", "")
chronicle_region := env_var_or_default("LOGSTORY_REGION", "US")
gcp_region := env_var_or_default("LOGSTORY_GCP_REGION", if chronicle_region == "US" { "us-central1" } else if chronicle_region == "EUROPE" { "europe-west1" } else if chronicle_region == "UK" { "europe-west2" } else if chronicle_region == "ASIA" { "asia-southeast1" } else if chronicle_region == "SYDNEY" { "australia-southeast1" } else { "us-central1" })
api_type := env_var_or_default("LOGSTORY_API_TYPE", "rest")
forwarder_name := env_var_or_default("LOGSTORY_FORWARDER_NAME", "Logstory-REST-Forwarder")
secret_name := env_var_or_default("LOGSTORY_SECRET_NAME", "chronicle-api-key")
usecases_bucket := env_var_or_default("LOGSTORY_USECASES_BUCKET", "gs://logstory-usecases-20241216")
timestamp_delta := env_var_or_default("LOGSTORY_TIMESTAMP_DELTA", "1d")
venv_dir := "venv"

# Default recipe: display color-coded grouped help
default:
    #!/usr/bin/env python3
    import sys, os

    class C:
        RESET   = '\033[0m'
        BOLD    = '\033[1m'
        DIM     = '\033[2m'
        CYAN    = '\033[36m'
        BCYAN   = '\033[1;36m'
        GREEN   = '\033[32m'
        BGREEN  = '\033[1;32m'
        YELLOW  = '\033[33m'
        BYELLOW = '\033[1;33m'
        MAGENTA = '\033[35m'
        BMAGENTA= '\033[1;35m'
        BLUE    = '\033[34m'
        BBLUE   = '\033[1;34m'
        WHITE   = '\033[37m'
        BWHITE  = '\033[1;37m'
        GRAY    = '\033[90m'

    if not sys.stdout.isatty() and 'FORCE_COLOR' not in os.environ:
        for k in dir(C):
            if not k.startswith('_'):
                setattr(C, k, '')

    sections = [
        ('Google Cloud Setup', C.BCYAN, C.CYAN, [
            ('auth-login', '', 'Authenticate Google Cloud CLI (user login)'),
            ('auth-adc', '', 'Authenticate Application Default Credentials (for GCS)'),
            ('project-set', '<project>', 'Set active Google Cloud project ID'),
            ('project-get', '', 'Display currently active Google Cloud project'),
            ('apis-enable', '', 'Enable required APIs (Cloud Run, Cloud Build, Schedulers, Secrets)'),
        ]),
        ('Secret Manager', C.BMAGENTA, C.MAGENTA, [
            ('secret-create', '<file> [secret]', 'Create/update credentials secret & grant service account access'),
            ('secret-describe', '[secret]', 'Describe secret metadata in Secret Manager'),
            ('secret-list', '', 'List all secrets in the project'),
            ('secret-iam', '[secret]', 'Display IAM access policy for the secret'),
        ]),
        ('Cloud Run Deployment & Scheduling', C.BGREEN, C.GREEN, [
            ('cloudrun-env-check', '', 'Validate required environment variables (PROJECT_ID, CUSTOMER_ID, API_TYPE)'),
            ('permissions-setup', '', 'Grant Secret Manager accessor role to compute service account'),
            ('docker-build', '', 'Build package and push Docker image to GCR via Cloud Build (wheel)'),
            ('docker-build-pypi', '', 'Build package and push Docker image to GCR via Cloud Build (PyPI)'),
            ('cloudrun-job-deploy', '', 'Deploy single Cloud Run job for logstory replay'),
            ('cloudrun-service-deploy', '', 'Deploy Cloud Run HTTP service for logstory API'),
            ('cloudrun-schedule-all', '', 'Create all 4 default Cloud Schedulers (events/entities 24h & 3day)'),
            ('cloudrun-schedule-custom', '<name> <cron> <args>', 'Create a custom Cloud Scheduler targeting the replay job'),
        ]),
        ('Execution, Testing & Monitoring', C.BYELLOW, C.YELLOW, [
            ('cloudrun-job-run', '[args]', 'Execute the Cloud Run job immediately with custom arguments'),
            ('cloudrun-job-test', '', 'Trigger replay job execution on Cloud Run and wait for completion'),
            ('cloudrun-service-test', '', 'Test Cloud Run service health and version endpoints'),
            ('cloudrun-status', '', 'Show status table of job, service, executions, and schedulers'),
            ('cloudrun-logs', '', 'Stream/view logs from most recent Cloud Run job execution'),
            ('cloudrun-service-logs', '', 'View recent Cloud Run service HTTP logs'),
            ('cloudrun-delete-all', '', 'Delete Cloud Run job, service, and all schedulers'),
            ('api-detection-debug', '', 'Debug Chronicle REST / Legacy API detection locally'),
        ]),
        ('Development, Build & Code Quality', C.BBLUE, C.BLUE, [
            ('dev-setup', '', 'Create virtualenv and install dev dependencies (.[dev]) + pre-commit hooks'),
            ('dev-setup-no-venv', '', 'Install dev dependencies (.[dev]) in current Python environment'),
            ('deps-lock', '', 'Update uv.lock with latest compatible dependencies'),
            ('deps-compile', '', 'Compile src/logstory/requirements.txt from pyproject.toml'),
            ('package-build', '', 'Build Python source distribution (.tar.gz) and wheel (.whl)'),
            ('package-clean', '', 'Clean build artifacts (dist/, build/, *.egg-info)'),
            ('package-clean-all', '', 'Clean build artifacts and virtual environment'),
            ('package-rebuild', '', 'Clean and rebuild the package'),
            ('lint', '', 'Run ruff linting checks'),
            ('lint-fix', '', 'Run ruff with automatic fixes'),
            ('format', '', 'Format code using pyink (2-space indentation)'),
            ('format-check', '', 'Check formatting without modifying files'),
            ('check', '', 'Run all lint and format checks'),
            ('fix', '', 'Automatically fix all linting and formatting issues'),
            ('test', '[args]', 'Run test suite with pytest'),
            ('pre-commit-install', '', 'Install pre-commit hooks into git repository'),
            ('pre-commit-run', '', 'Run pre-commit hooks on all files'),
            ('pre-commit-update', '', 'Update pre-commit hooks to latest versions'),
        ]),
        ('Usecases & GCS Storage', C.BCYAN, C.CYAN, [
            ('usecase-publish', '<usecase> [bucket]', 'Sync a single local usecase to Google Cloud Storage bucket'),
            ('usecase-publish-all', '[dir] [bucket]', 'Sync all local usecases to Google Cloud Storage bucket'),
            ('usecase-list-gcs', '[bucket]', 'List usecases stored in Google Cloud Storage bucket'),
        ]),
        ('PyPI Publishing & Distribution', C.BYELLOW, C.YELLOW, [
            ('pypi-publish-test', '', 'Upload package to Test PyPI via twine'),
            ('pypi-test-install', '', 'Test installing published package from Test PyPI'),
            ('pypi-publish', '', 'Upload package to production PyPI via twine'),
        ]),
        ('Documentation', C.BMAGENTA, C.MAGENTA, [
            ('docs-build', '', 'Build Sphinx HTML documentation in docs/_build/html'),
            ('docs-live', '', 'Start Sphinx live-reloading preview server (localhost:8000)'),
            ('docs-clean', '', 'Clean documentation build directory'),
        ]),
        ('Local Docker', C.BCYAN, C.CYAN, [
            ('docker-build-local', '[file] [tag]', 'Build local Docker image for testing'),
            ('docker-run-local', '[tag] [args]', 'Run local Docker container with environment variables'),
        ]),
        ('Information & Help', C.BWHITE, C.WHITE, [
            ('info', '', 'Display resolved environment variables and configuration settings'),
            ('help', '', 'Show this color-coded grouped help menu'),
            ('cloudrun-help', '', 'Display comprehensive Cloud Run deployment guide'),
        ]),
    ]

    print()
    print(f'  {C.BCYAN}╔═════════════════════════════════════════════════════════════════════════════════╗{C.RESET}')
    print(f'  {C.BCYAN}║                            LogStory Command Runner                              ║{C.RESET}')
    print(f'  {C.BCYAN}╚═════════════════════════════════════════════════════════════════════════════════╝{C.RESET}')
    print(f'  {C.DIM}Usage:{C.RESET} {C.BOLD}{C.BWHITE}just{C.RESET} {C.BCYAN}<recipe>{C.RESET} {C.GRAY}[arguments...]{C.RESET}\n')

    for title, header_color, item_color, commands in sections:
        print(f'  {header_color}─── {title} {header_color}─' + ('─' * max(0, 70 - len(title))) + f'{C.RESET}')
        for name, args, desc in commands:
            arg_str = f' {C.GRAY}{args}{C.RESET}' if args else ''
            cmd_full = f'{item_color}{name}{C.RESET}{arg_str}'
            vis_len = len(name) + (len(args) + 1 if args else 0)
            pad = ' ' * max(2, 32 - vis_len)
            print(f'    {cmd_full}{pad}{C.DIM}{desc}{C.RESET}')
        print()

    print(f'  {C.GRAY}Tip:{C.RESET} Run {C.BCYAN}just info{C.RESET} to view active config, or {C.BCYAN}just <recipe> --help{C.RESET} for recipe options.')
    print()

# Show help menu (alias for default)
help:
    @just default

# Show resolved configuration and environment settings
info:
    #!/usr/bin/env python3
    import os, sys

    class C:
        RESET   = '\033[0m'
        BOLD    = '\033[1m'
        DIM     = '\033[2m'
        CYAN    = '\033[36m'
        BCYAN   = '\033[1;36m'
        GREEN   = '\033[32m'
        BGREEN  = '\033[1;32m'
        YELLOW  = '\033[33m'
        MAGENTA = '\033[35m'
        BWHITE  = '\033[1;37m'
        WHITE   = '\033[37m'
        GRAY    = '\033[90m'

    if not sys.stdout.isatty() and 'FORCE_COLOR' not in os.environ:
        for k in dir(C):
            if not k.startswith('_'): setattr(C, k, '')

    project = "{{ project_id }}"
    customer = "{{ customer_id }}"
    chronicle_reg = "{{ chronicle_region }}"
    gcp_reg = "{{ gcp_region }}"
    api = "{{ api_type }}"
    forwarder = "{{ forwarder_name }}"
    secret = "{{ secret_name }}"
    bucket = "{{ usecases_bucket }}"
    delta = "{{ timestamp_delta }}"

    print(f"\n  {C.BCYAN}=== Logstory Active Configuration ==={C.RESET}")
    print(f"  {C.BOLD}LOGSTORY_PROJECT_ID:{C.RESET}      {C.GREEN if project else C.GRAY}{project or '(not set)'}{C.RESET}")
    print(f"  {C.BOLD}LOGSTORY_CUSTOMER_ID:{C.RESET}     {C.GREEN if customer else C.GRAY}{customer or '(not set)'}{C.RESET}")
    print(f"  {C.BOLD}LOGSTORY_REGION:{C.RESET}          {C.CYAN}{chronicle_reg}{C.RESET}")
    print(f"  {C.BOLD}LOGSTORY_GCP_REGION:{C.RESET}      {C.CYAN}{gcp_reg}{C.RESET}")
    print(f"  {C.BOLD}LOGSTORY_API_TYPE:{C.RESET}        {C.YELLOW}{api}{C.RESET}")
    print(f"  {C.BOLD}LOGSTORY_FORWARDER_NAME:{C.RESET}  {C.WHITE}{forwarder}{C.RESET}")
    print(f"  {C.BOLD}LOGSTORY_SECRET_NAME:{C.RESET}     {C.MAGENTA}{secret}{C.RESET}")
    print(f"  {C.BOLD}LOGSTORY_USECASES_BUCKET:{C.RESET} {C.CYAN}{bucket}{C.RESET}")
    print(f"  {C.BOLD}LOGSTORY_TIMESTAMP_DELTA:{C.RESET} {C.WHITE}{delta}{C.RESET}\n")

# ==============================================================================
# Google Cloud Authentication and Configuration Setup
# ==============================================================================

# Authenticate Google Cloud CLI (user login)
auth-login:
    gcloud auth login

# Authenticate Application Default Credentials (needed for private GCS usecases buckets)
auth-adc:
    gcloud auth application-default login

# Set active Google Cloud project
project-set project:
    gcloud config set project {{ project }}

# Get currently active Google Cloud project
project-get:
    @gcloud config get-value project

# Enable all required Google Cloud APIs for Cloud Run deployment
apis-enable:
    @if [ -z "{{ project_id }}" ]; then \
        echo "Error: PROJECT_ID is not set. Set LOGSTORY_PROJECT_ID or run 'just project-set <id>'"; \
        exit 1; \
    fi
    @echo "Enabling required APIs for project {{ project_id }}..."
    @gcloud services enable run.googleapis.com --project={{ project_id }}
    @gcloud services enable cloudbuild.googleapis.com --project={{ project_id }}
    @gcloud services enable cloudscheduler.googleapis.com --project={{ project_id }}
    @gcloud services enable secretmanager.googleapis.com --project={{ project_id }}
    @gcloud services enable iam.googleapis.com --project={{ project_id }}
    @gcloud services enable cloudresourcemanager.googleapis.com --project={{ project_id }}
    @gcloud services enable artifactregistry.googleapis.com --project={{ project_id }}
    @echo "All required APIs enabled successfully!"

# ==============================================================================
# Virtual Environment and Dependency Management
# ==============================================================================

# Create virtual environment
venv-create:
    python3 -m venv {{ venv_dir }}
    {{ venv_dir }}/bin/pip install --upgrade pip

# Remove virtual environment
venv-clean:
    rm -rf {{ venv_dir }}

# Setup development environment (venv + dependencies + pre-commit hooks)
dev-setup: venv-create
    {{ venv_dir }}/bin/pip install -e ".[dev]"
    {{ venv_dir }}/bin/pre-commit install

# Setup development environment in current environment (without creating venv)
dev-setup-no-venv:
    pip install -e ".[dev]"
    pre-commit install

# Update uv.lock with latest compatible dependencies
deps-lock:
    uv lock --upgrade

# Compile src/logstory/requirements.txt directly from pyproject.toml
deps-compile:
    uv pip compile pyproject.toml -o src/logstory/requirements.txt


# ==============================================================================
# Build and Packaging
# ==============================================================================

# Build Python source distribution and wheel packages
package-build:
    @if [ -d "{{ venv_dir }}" ] && [ -x "{{ venv_dir }}/bin/python" ]; then \
        "{{ venv_dir }}/bin/python" -m build; \
    elif command -v uv >/dev/null 2>&1; then \
        uv build; \
    elif command -v python3 >/dev/null 2>&1; then \
        python3 -m build; \
    else \
        python -m build; \
    fi

# Clean build artifacts
package-clean:
    rm -rf dist/ build/ *.egg-info

# Clean everything including virtual environment
package-clean-all: package-clean venv-clean

# Clean and rebuild the package
package-rebuild: package-clean package-build

# ==============================================================================
# Code Quality, Linting, Formatting, and Pre-commit
# ==============================================================================

# Run ruff linting checks
lint:
    @if [ -d "{{ venv_dir }}" ] && [ -x "{{ venv_dir }}/bin/ruff" ]; then \
        "{{ venv_dir }}/bin/ruff" check .; \
    elif command -v ruff >/dev/null 2>&1; then \
        ruff check .; \
    else \
        echo "Error: ruff is not installed. Run 'just dev-setup' first."; \
        exit 1; \
    fi

# Run ruff with automatic fixes
lint-fix:
    @if [ -d "{{ venv_dir }}" ] && [ -x "{{ venv_dir }}/bin/ruff" ]; then \
        "{{ venv_dir }}/bin/ruff" check . --fix; \
    elif command -v ruff >/dev/null 2>&1; then \
        ruff check . --fix; \
    else \
        echo "Error: ruff is not installed. Run 'just dev-setup' first."; \
        exit 1; \
    fi

# Format code with pyink (2-space indentation)
format:
    @if [ -d "{{ venv_dir }}" ] && [ -x "{{ venv_dir }}/bin/pyink" ]; then \
        "{{ venv_dir }}/bin/pyink" .; \
    elif command -v pyink >/dev/null 2>&1; then \
        pyink .; \
    else \
        echo "Error: pyink is not installed. Run 'just dev-setup' first."; \
        exit 1; \
    fi

# Check code formatting without changes
format-check:
    @if [ -d "{{ venv_dir }}" ] && [ -x "{{ venv_dir }}/bin/pyink" ]; then \
        "{{ venv_dir }}/bin/pyink" . --check; \
    elif command -v pyink >/dev/null 2>&1; then \
        pyink . --check; \
    else \
        echo "Error: pyink is not installed. Run 'just dev-setup' first."; \
        exit 1; \
    fi

# Run all linting and format checks
check: lint format-check

# Fix all linting and formatting issues
fix: lint-fix format

# Run test suite
test *args="tests/":
    @if [ -d "{{ venv_dir }}" ] && [ -x "{{ venv_dir }}/bin/pytest" ]; then \
        "{{ venv_dir }}/bin/pytest" {{ args }}; \
    elif command -v pytest >/dev/null 2>&1; then \
        pytest {{ args }}; \
    elif [ -d "{{ venv_dir }}" ] && [ -x "{{ venv_dir }}/bin/python" ]; then \
        "{{ venv_dir }}/bin/python" -m unittest discover tests/; \
    else \
        python3 -m unittest discover tests/; \
    fi

# Install pre-commit hooks
pre-commit-install:
    @if [ -d "{{ venv_dir }}" ] && [ -x "{{ venv_dir }}/bin/pre-commit" ]; then \
        "{{ venv_dir }}/bin/pre-commit" install; \
    elif command -v pre-commit >/dev/null 2>&1; then \
        pre-commit install; \
    else \
        echo "Error: pre-commit is not installed. Run 'just dev-setup' first."; \
        exit 1; \
    fi

# Run pre-commit hooks on all files
pre-commit-run:
    @if [ -d "{{ venv_dir }}" ] && [ -x "{{ venv_dir }}/bin/pre-commit" ]; then \
        "{{ venv_dir }}/bin/pre-commit" run --all-files; \
    elif command -v pre-commit >/dev/null 2>&1; then \
        pre-commit run --all-files; \
    else \
        echo "Error: pre-commit is not installed. Run 'just dev-setup' first."; \
        exit 1; \
    fi

# Update pre-commit hooks to latest versions
pre-commit-update:
    @if [ -d "{{ venv_dir }}" ] && [ -x "{{ venv_dir }}/bin/pre-commit" ]; then \
        "{{ venv_dir }}/bin/pre-commit" autoupdate; \
    elif command -v pre-commit >/dev/null 2>&1; then \
        pre-commit autoupdate; \
    else \
        echo "Error: pre-commit is not installed. Run 'just dev-setup' first."; \
        exit 1; \
    fi

# ==============================================================================
# Secret Manager Management
# ==============================================================================

# Create or update credentials secret in Secret Manager and grant access to compute service account
secret-create credentials_file secret=secret_name:
    @if [ ! -f "{{ credentials_file }}" ]; then \
        echo "Error: Credentials file '{{ credentials_file }}' does not exist"; \
        exit 1; \
    fi
    @if [ -z "{{ project_id }}" ]; then \
        echo "Error: PROJECT_ID is not set. Set LOGSTORY_PROJECT_ID or run 'just project-set <id>'"; \
        exit 1; \
    fi
    @echo "Creating/updating secret {{ secret }} from {{ credentials_file }}..."
    @if gcloud secrets describe {{ secret }} --project={{ project_id }} >/dev/null 2>&1; then \
        echo "Secret exists, adding new version..."; \
        gcloud secrets versions add {{ secret }} --data-file="{{ credentials_file }}" --project={{ project_id }}; \
    else \
        echo "Creating new secret..."; \
        gcloud secrets create {{ secret }} --data-file="{{ credentials_file }}" --replication-policy=automatic --project={{ project_id }}; \
    fi
    @echo "Granting access to default compute service account..."
    @PROJECT_NUMBER=$$(gcloud projects describe {{ project_id }} --format="value(projectNumber)"); \
    gcloud secrets add-iam-policy-binding {{ secret }} \
        --member="serviceAccount:$${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
        --role="roles/secretmanager.secretAccessor" \
        --project={{ project_id }}
    @echo "Secret '{{ secret }}' is ready!"

# Describe a secret in Secret Manager
secret-describe secret=secret_name:
    gcloud secrets describe {{ secret }} --project={{ project_id }}

# List all secrets in the project
secret-list:
    gcloud secrets list --project={{ project_id }}

# Show IAM policy for secret
secret-iam secret=secret_name:
    gcloud secrets get-iam-policy {{ secret }} --project={{ project_id }}

# ==============================================================================
# Cloud Run Deployment and Schedulers
# ==============================================================================

# Validate required environment variables for Cloud Run deployment
cloudrun-env-check:
    @if [ -z "{{ customer_id }}" ]; then \
        echo "Error: LOGSTORY_CUSTOMER_ID is not set."; \
        echo "Set it with: export LOGSTORY_CUSTOMER_ID=your-uuid"; \
        exit 1; \
    fi
    @if [ -z "{{ project_id }}" ]; then \
        echo "Error: LOGSTORY_PROJECT_ID is not set."; \
        echo "Set it with: export LOGSTORY_PROJECT_ID=your-project-id"; \
        echo "Or set default with: gcloud config set project your-project-id"; \
        exit 1; \
    fi
    @if [ "{{ api_type }}" = "rest" ] && [ -z "{{ project_id }}" ]; then \
        echo "Error: REST API requires LOGSTORY_PROJECT_ID"; \
        exit 1; \
    fi
    @echo "Configuration validated successfully:"
    @echo "  CUSTOMER_ID:      {{ customer_id }}"
    @echo "  PROJECT_ID:       {{ project_id }}"
    @echo "  CHRONICLE_REGION: {{ chronicle_region }}"
    @echo "  GCP_REGION:       {{ gcp_region }}"
    @echo "  API_TYPE:         {{ api_type }}"
    @if [ "{{ api_type }}" = "rest" ]; then \
        echo "  FORWARDER_NAME:   {{ forwarder_name }}"; \
    fi
    @echo "  SECRET_NAME:      {{ secret_name }}"

# Grant necessary permissions to the default compute service account
permissions-setup:
    @if [ -z "{{ project_id }}" ]; then \
        echo "Error: PROJECT_ID is not set."; \
        exit 1; \
    fi
    @PROJECT_NUMBER=$$(gcloud projects describe {{ project_id }} --format="value(projectNumber)"); \
    SERVICE_ACCOUNT="$${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"; \
    echo "Using default compute service account: $$SERVICE_ACCOUNT"; \
    echo "Granting Secret Manager accessor role on project..."; \
    gcloud projects add-iam-policy-binding {{ project_id }} \
        --member="serviceAccount:$$SERVICE_ACCOUNT" \
        --role="roles/secretmanager.secretAccessor" || true; \
    echo "Ensuring secret exists and has correct permissions..."; \
    if gcloud secrets describe {{ secret_name }} --project={{ project_id }} >/dev/null 2>&1; then \
        gcloud secrets add-iam-policy-binding {{ secret_name }} \
            --member="serviceAccount:$$SERVICE_ACCOUNT" \
            --role="roles/secretmanager.secretAccessor" \
            --project={{ project_id }} || true; \
    else \
        echo "Warning: Secret '{{ secret_name }}' does not exist. Run 'just secret-create <path>' first."; \
    fi; \
    echo "Permissions setup complete!"

# Build and push Docker image to GCR using Cloud Build and local wheel
docker-build: package-build
    @echo "Building and pushing Docker image to GCR via Cloud Build..."
    gcloud builds submit --config cloudbuild-wheel.yaml --project={{ project_id }}
    @echo "Docker image pushed to: gcr.io/{{ project_id }}/logstory:latest"

# Build and push Docker image to GCR using published PyPI package
docker-build-pypi:
    @echo "Building and pushing Docker image from PyPI package..."
    gcloud builds submit --config cloudbuild.yaml --project={{ project_id }}
    @echo "Docker image pushed to: gcr.io/{{ project_id }}/logstory:latest"

# Deploy single Cloud Run job for logstory replay
cloudrun-job-deploy: cloudrun-env-check docker-build
    @echo "Deploying Cloud Run job: logstory-replay"
    @PROJECT_NUMBER=$$(gcloud projects describe {{ project_id }} --format="value(projectNumber)"); \
    SERVICE_ACCOUNT="$${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"; \
    gcloud run jobs create logstory-replay \
        --image gcr.io/{{ project_id }}/logstory:latest \
        --region {{ gcp_region }} \
        --service-account $$SERVICE_ACCOUNT \
        --set-env-vars "LOGSTORY_CUSTOMER_ID={{ customer_id }}" \
        --set-env-vars "LOGSTORY_REGION={{ chronicle_region }}" \
        --set-env-vars "LOGSTORY_API_TYPE={{ api_type }}" \
        --set-env-vars "LOGSTORY_PROJECT_ID={{ project_id }}" \
        --set-env-vars "LOGSTORY_FORWARDER_NAME={{ forwarder_name }}" \
        --set-env-vars "LOGSTORY_TIMESTAMP_DELTA={{ timestamp_delta }}" \
        --set-secrets "LOGSTORY_CREDENTIALS={{ secret_name }}:latest" \
        --memory 1Gi \
        --task-timeout 3600 \
        --max-retries 1 \
        --parallelism 1 \
        || (echo "Job exists, updating..." && \
        gcloud run jobs update logstory-replay \
        --image gcr.io/{{ project_id }}/logstory:latest \
        --region {{ gcp_region }} \
        --set-env-vars "LOGSTORY_CUSTOMER_ID={{ customer_id }}" \
        --set-env-vars "LOGSTORY_REGION={{ chronicle_region }}" \
        --set-env-vars "LOGSTORY_API_TYPE={{ api_type }}" \
        --set-env-vars "LOGSTORY_PROJECT_ID={{ project_id }}" \
        --set-env-vars "LOGSTORY_FORWARDER_NAME={{ forwarder_name }}" \
        --set-env-vars "LOGSTORY_TIMESTAMP_DELTA={{ timestamp_delta }}" \
        --set-secrets "LOGSTORY_CREDENTIALS={{ secret_name }}:latest")
    @echo "Cloud Run job deployed successfully!"

# Deploy Cloud Run service for logstory HTTP API
cloudrun-service-deploy: cloudrun-env-check docker-build
    @echo "Deploying Cloud Run service: logstory-service"
    @PROJECT_NUMBER=$$(gcloud projects describe {{ project_id }} --format="value(projectNumber)"); \
    SERVICE_ACCOUNT="$${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"; \
    gcloud run deploy logstory-service \
        --image gcr.io/{{ project_id }}/logstory:latest \
        --region {{ gcp_region }} \
        --service-account $$SERVICE_ACCOUNT \
        --set-env-vars "LOGSTORY_CUSTOMER_ID={{ customer_id }}" \
        --set-env-vars "LOGSTORY_REGION={{ chronicle_region }}" \
        --set-env-vars "LOGSTORY_API_TYPE={{ api_type }}" \
        --set-env-vars "LOGSTORY_PROJECT_ID={{ project_id }}" \
        --set-env-vars "LOGSTORY_FORWARDER_NAME={{ forwarder_name }}" \
        --set-env-vars "LOGSTORY_TIMESTAMP_DELTA={{ timestamp_delta }}" \
        --set-secrets "LOGSTORY_CREDENTIALS={{ secret_name }}:latest" \
        --memory 1Gi \
        --cpu 1 \
        --min-instances 0 \
        --max-instances 10 \
        --concurrency 80 \
        --timeout 3600 \
        --port 8080 \
        --allow-unauthenticated
    @echo "Cloud Run service deployed successfully!"
    @echo "Service URL: $$(gcloud run services describe logstory-service --region {{ gcp_region }} --format 'value(status.url)')"

# Create all 4 default schedulers for the Cloud Run job
cloudrun-schedule-all: cloudrun-env-check
    @PROJECT_NUMBER=$$(gcloud projects describe {{ project_id }} --format="value(projectNumber)"); \
    SERVICE_ACCOUNT="$${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"; \
    echo "Creating scheduler: events-24h (daily at 3:00 AM UTC)"; \
    gcloud scheduler jobs create http logstory-events-24h \
        --location {{ gcp_region }} \
        --schedule "0 3 * * *" \
        --time-zone "UTC" \
        --uri "https://{{ gcp_region }}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/{{ project_id }}/jobs/logstory-replay:run" \
        --http-method POST \
        --oauth-service-account-email $$SERVICE_ACCOUNT \
        --headers "Content-Type=application/json" \
        --message-body '{"overrides":{"containerOverrides":[{"args":["logstory","replay","all"]}]}}' \
        || echo "Scheduler events-24h already exists"; \
    echo "Creating scheduler: events-3day (every 3 days at 3:00 AM UTC)"; \
    gcloud scheduler jobs create http logstory-events-3day \
        --location {{ gcp_region }} \
        --schedule "0 3 */3 * *" \
        --time-zone "UTC" \
        --uri "https://{{ gcp_region }}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/{{ project_id }}/jobs/logstory-replay:run" \
        --http-method POST \
        --oauth-service-account-email $$SERVICE_ACCOUNT \
        --headers "Content-Type=application/json" \
        --message-body '{"overrides":{"containerOverrides":[{"args":["logstory","replay","all"]}]}}' \
        || echo "Scheduler events-3day already exists"; \
    echo "Creating scheduler: entities-24h (daily at 12:01 AM UTC)"; \
    gcloud scheduler jobs create http logstory-entities-24h \
        --location {{ gcp_region }} \
        --schedule "1 0 * * *" \
        --time-zone "UTC" \
        --uri "https://{{ gcp_region }}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/{{ project_id }}/jobs/logstory-replay:run" \
        --http-method POST \
        --oauth-service-account-email $$SERVICE_ACCOUNT \
        --headers "Content-Type=application/json" \
        --message-body '{"overrides":{"containerOverrides":[{"args":["logstory","replay","all","--entities"]}]}}' \
        || echo "Scheduler entities-24h already exists"; \
    echo "Creating scheduler: entities-3day (every 3 days at 12:01 AM UTC)"; \
    gcloud scheduler jobs create http logstory-entities-3day \
        --location {{ gcp_region }} \
        --schedule "1 0 */3 * *" \
        --time-zone "UTC" \
        --uri "https://{{ gcp_region }}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/{{ project_id }}/jobs/logstory-replay:run" \
        --http-method POST \
        --oauth-service-account-email $$SERVICE_ACCOUNT \
        --headers "Content-Type=application/json" \
        --message-body '{"overrides":{"containerOverrides":[{"args":["logstory","replay","all","--entities"]}]}}' \
        || echo "Scheduler entities-3day already exists"; \
    echo "All schedulers created successfully!"

# Create a custom Cloud Scheduler job targeting the Cloud Run job
cloudrun-schedule-custom name schedule args: cloudrun-env-check
    @PROJECT_NUMBER=$$(gcloud projects describe {{ project_id }} --format="value(projectNumber)"); \
    SERVICE_ACCOUNT="$${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"; \
    echo "Creating custom scheduler: {{ name }} (schedule: {{ schedule }})"; \
    gcloud scheduler jobs create http {{ name }} \
        --location {{ gcp_region }} \
        --schedule "{{ schedule }}" \
        --time-zone "UTC" \
        --uri "https://{{ gcp_region }}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/{{ project_id }}/jobs/logstory-replay:run" \
        --http-method POST \
        --oauth-service-account-email $$SERVICE_ACCOUNT \
        --headers "Content-Type=application/json" \
        --message-body '{"overrides":{"containerOverrides":[{"args":{{ args }}}]}}'

# ==============================================================================
# Execution, Testing, and Monitoring
# ==============================================================================

# Execute the Cloud Run job with custom comma-separated arguments
cloudrun-job-run args="logstory,replay,all": cloudrun-env-check
    @echo "Executing Cloud Run job with args: {{ args }}"
    gcloud run jobs execute logstory-replay \
        --region {{ gcp_region }} \
        --args "{{ args }}" \
        --wait

# Test the Cloud Run job with default replay parameters
cloudrun-job-test: cloudrun-env-check
    @echo "Testing events replay on Cloud Run..."
    gcloud run jobs execute logstory-replay \
        --region {{ gcp_region }} \
        --args "logstory,replay,all" \
        --wait

# Test the Cloud Run service endpoints
cloudrun-service-test: cloudrun-env-check
    @echo "Testing Cloud Run service..."
    @SERVICE_URL=$$(gcloud run services describe logstory-service --region {{ gcp_region }} --format 'value(status.url)' 2>/dev/null); \
    if [ -n "$$SERVICE_URL" ]; then \
        echo "Service URL: $$SERVICE_URL"; \
        echo "Testing health endpoint..."; \
        curl -f "$$SERVICE_URL/health" || echo "Health endpoint not available"; \
        echo "Testing version endpoint..."; \
        curl -f "$$SERVICE_URL/version" || echo "Version endpoint not available"; \
    else \
        echo "Service not deployed. Run 'just cloudrun-service-deploy' first."; \
    fi

# Show status of Cloud Run job, service, and schedulers
cloudrun-status: cloudrun-env-check
    @echo "=== Cloud Run Job Status ==="
    @gcloud run jobs describe logstory-replay --region {{ gcp_region }} --format "table(metadata.name,status.conditions[0].type,status.conditions[0].status)" 2>/dev/null || echo "Job not deployed"
    @echo ""
    @echo "=== Recent Job Executions ==="
    @gcloud run jobs executions list --job logstory-replay --region {{ gcp_region }} --limit 5 --format "table(metadata.name,status.completionTime,status.conditions[0].status)" 2>/dev/null || echo "No executions found"
    @echo ""
    @echo "=== Cloud Run Service Status ==="
    @gcloud run services describe logstory-service --region {{ gcp_region }} --format "table(metadata.name,status.conditions[0].type,status.conditions[0].status,status.url)" 2>/dev/null || echo "Service not deployed"
    @echo ""
    @echo "=== Service Traffic ==="
    @gcloud run services describe logstory-service --region {{ gcp_region }} --format "table(status.traffic[*].revisionName:label=REVISION,status.traffic[*].percent:label=TRAFFIC%)" 2>/dev/null || echo "No service traffic info"
    @echo ""
    @echo "=== Scheduler Status ==="
    @gcloud scheduler jobs list --location {{ gcp_region }} --format "table(name.basename(),schedule,state,lastAttemptTime.date())" 2>/dev/null || echo "No schedulers found"

# View logs from the most recent Cloud Run job execution
cloudrun-logs: cloudrun-env-check
    @gcloud run jobs executions list \
        --job logstory-replay \
        --region {{ gcp_region }} \
        --limit 1 \
        --format "value(name)" | xargs -I {} \
        gcloud run jobs executions logs {} \
        --region {{ gcp_region }}

# View logs from the Cloud Run service
cloudrun-service-logs: cloudrun-env-check
    @gcloud logs read "resource.type=cloud_run_revision AND resource.labels.service_name=logstory-service" \
        --project={{ project_id }} \
        --limit=50 \
        --order=desc \
        --format="table(timestamp,severity,textPayload)"

# Delete Cloud Run job, service, and all schedulers
cloudrun-delete-all: cloudrun-env-check
    @echo "Deleting schedulers..."
    @gcloud scheduler jobs delete logstory-events-24h --location {{ gcp_region }} --quiet 2>/dev/null || true
    @gcloud scheduler jobs delete logstory-events-3day --location {{ gcp_region }} --quiet 2>/dev/null || true
    @gcloud scheduler jobs delete logstory-entities-24h --location {{ gcp_region }} --quiet 2>/dev/null || true
    @gcloud scheduler jobs delete logstory-entities-3day --location {{ gcp_region }} --quiet 2>/dev/null || true
    @echo "Deleting Cloud Run job..."
    @gcloud run jobs delete logstory-replay --region {{ gcp_region }} --quiet 2>/dev/null || true
    @echo "Deleting Cloud Run service..."
    @gcloud run services delete logstory-service --region {{ gcp_region }} --quiet 2>/dev/null || true
    @echo "All Cloud Run resources deleted."

# Debug API type detection locally
api-detection-debug: cloudrun-env-check
    @echo "Testing API detection locally..."
    @echo "Environment variables:"
    @echo "  LOGSTORY_API_TYPE:   {{ api_type }}"
    @echo "  LOGSTORY_PROJECT_ID: {{ project_id }}"
    @echo "  LOGSTORY_REGION:     {{ chronicle_region }}"
    @python3 -c "import sys; sys.path.insert(0, 'src'); from logstory.auth import detect_auth_type; print(f'Detected API type: {detect_auth_type()}')"

# Show Cloud Run deployment help
cloudrun-help:
    @echo "Cloud Run Deployment Guide"
    @echo "=========================="
    @echo ""
    @echo "Prerequisites:"
    @echo "  1. Set environment variables:"
    @echo "     export LOGSTORY_PROJECT_ID=your-gcp-project-id"
    @echo "     export LOGSTORY_CUSTOMER_ID=your-chronicle-customer-uuid"
    @echo "     export LOGSTORY_REGION=US            # Chronicle region: US, EUROPE, UK, ASIA, SYDNEY"
    @echo "     export LOGSTORY_GCP_REGION=us-central1  # Optional: GCP region (auto-mapped)"
    @echo "     export LOGSTORY_API_TYPE=rest        # Required: rest or legacy"
    @echo ""
    @echo "  2. Authenticate and enable APIs:"
    @echo "     just auth-login"
    @echo "     just apis-enable"
    @echo ""
    @echo "  3. Create secret in Secret Manager:"
    @echo "     just secret-create /path/to/credentials.json"
    @echo ""
    @echo "  4. Setup permissions for default compute service account:"
    @echo "     just permissions-setup"
    @echo ""
    @echo "Quick Start - Job Deployment (scheduled execution):"
    @echo "  just apis-enable"
    @echo "  just secret-create /path/to/creds.json"
    @echo "  just permissions-setup"
    @echo "  just cloudrun-job-deploy"
    @echo "  just cloudrun-schedule-all"
    @echo "  just cloudrun-job-test"
    @echo ""
    @echo "Quick Start - Service Deployment (HTTP API):"
    @echo "  just apis-enable"
    @echo "  just secret-create /path/to/creds.json"
    @echo "  just permissions-setup"
    @echo "  just cloudrun-service-deploy"
    @echo "  just cloudrun-service-test"
    @echo ""
    @echo "Monitoring:"
    @echo "  just cloudrun-status"
    @echo "  just cloudrun-logs"
    @echo "  just cloudrun-service-logs"
    @echo ""
    @echo "Cleanup:"
    @echo "  just cloudrun-delete-all"

# ==============================================================================
# Usecases and Storage Bucket Management
# ==============================================================================

# Publish a single local usecase to the Google Cloud Storage bucket
usecase-publish usecase bucket=usecases_bucket:
    @if [ -d "usecases/{{ usecase }}" ]; then \
        echo "Publishing usecase '{{ usecase }}' to {{ bucket }}/{{ usecase }}..."; \
        gcloud storage rsync --recursive "usecases/{{ usecase }}" "{{ bucket }}/{{ usecase }}"; \
    elif [ -d "src/logstory/usecases/{{ usecase }}" ]; then \
        echo "Publishing usecase '{{ usecase }}' to {{ bucket }}/{{ usecase }}..."; \
        gcloud storage rsync --recursive "src/logstory/usecases/{{ usecase }}" "{{ bucket }}/{{ usecase }}"; \
    else \
        echo "Error: Usecase '{{ usecase }}' not found in usecases/ or src/logstory/usecases/"; \
        exit 1; \
    fi
    @echo "Usecase '{{ usecase }}' published successfully!"

# Publish all local usecases to the Google Cloud Storage bucket
usecase-publish-all local_dir="usecases" bucket=usecases_bucket:
    @if [ ! -d "{{ local_dir }}" ]; then \
        echo "Error: Local directory '{{ local_dir }}' does not exist."; \
        exit 1; \
    fi
    @echo "Publishing all usecases from '{{ local_dir }}' to {{ bucket }}..."
    gcloud storage rsync --recursive "{{ local_dir }}" "{{ bucket }}"
    @echo "All usecases published successfully!"

# List usecases stored in Google Cloud Storage bucket
usecase-list-gcs bucket=usecases_bucket:
    gcloud storage ls "{{ bucket }}"

# ==============================================================================
# PyPI Publishing and Package Distribution
# ==============================================================================

# Upload build artifacts to Test PyPI
pypi-publish-test: package-rebuild
    @if [ -d "{{ venv_dir }}" ] && [ -x "{{ venv_dir }}/bin/twine" ]; then \
        "{{ venv_dir }}/bin/twine" upload --repository testpypi dist/*; \
    elif command -v twine >/dev/null 2>&1; then \
        twine upload --repository testpypi dist/*; \
    else \
        echo "Error: twine is not installed. Run 'just dev-setup' first."; \
        exit 1; \
    fi

# Test installation from Test PyPI
pypi-test-install:
    pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ logstory

# Upload build artifacts to production PyPI
pypi-publish: package-rebuild
    @if [ -d "{{ venv_dir }}" ] && [ -x "{{ venv_dir }}/bin/twine" ]; then \
        "{{ venv_dir }}/bin/twine" upload dist/*; \
    elif command -v twine >/dev/null 2>&1; then \
        twine upload dist/*; \
    else \
        echo "Error: twine is not installed. Run 'just dev-setup' first."; \
        exit 1; \
    fi

# ==============================================================================
# Documentation
# ==============================================================================

# Build Sphinx HTML documentation
docs-build:
    @if [ -d "{{ venv_dir }}" ] && [ -x "{{ venv_dir }}/bin/sphinx-build" ]; then \
        "{{ venv_dir }}/bin/sphinx-build" -b html docs docs/_build/html; \
    elif command -v sphinx-build >/dev/null 2>&1; then \
        sphinx-build -b html docs docs/_build/html; \
    else \
        echo "Error: sphinx-build is not installed. Run 'pip install -r docs/requirements.txt' first."; \
        exit 1; \
    fi
    @echo "Docs built at: docs/_build/html/index.html"

# Run Sphinx live-reloading documentation server
docs-live:
    @if [ -d "{{ venv_dir }}" ] && [ -x "{{ venv_dir }}/bin/sphinx-autobuild" ]; then \
        "{{ venv_dir }}/bin/sphinx-autobuild" -b html docs docs/_build/html; \
    elif command -v sphinx-autobuild >/dev/null 2>&1; then \
        sphinx-autobuild -b html docs docs/_build/html; \
    else \
        echo "Error: sphinx-autobuild is not installed. Run 'pip install sphinx-autobuild' first."; \
        exit 1; \
    fi

# Clean documentation build directory
docs-clean:
    rm -rf docs/_build

# ==============================================================================
# Local Docker Testing
# ==============================================================================

# Build local Docker image
docker-build-local dockerfile="Dockerfile.minimal" tag="logstory-test":
    docker build -t {{ tag }} -f {{ dockerfile }} .

# Run local Docker container with environment variables
docker-run-local tag="logstory-test" args="logstory replay all":
    docker run \
        -e LOGSTORY_CUSTOMER_ID="{{ customer_id }}" \
        -e LOGSTORY_PROJECT_ID="{{ project_id }}" \
        -e LOGSTORY_REGION="{{ chronicle_region }}" \
        -e LOGSTORY_API_TYPE="{{ api_type }}" \
        -e LOGSTORY_TIMESTAMP_DELTA="{{ timestamp_delta }}" \
        {{ tag }} \
        {{ args }}

# ==============================================================================
# Backward-Compatibility Aliases
# ==============================================================================
# Google Cloud

alias set-project := project-set
alias get-project := project-get
alias enable-apis := apis-enable
alias api-enable := apis-enable

# Secrets

alias create-secret := secret-create
alias describe-secret := secret-describe
alias list-secrets := secret-list
alias get-secret-iam := secret-iam
alias secret-get-iam := secret-iam

# Permissions & Environment

alias setup-permissions := permissions-setup
alias check-cloudrun-env := cloudrun-env-check

# Cloud Run Deployment

alias deploy-cloudrun-job := cloudrun-job-deploy
alias deploy-cloudrun-service := cloudrun-service-deploy
alias deploy-cloudrun-all := cloudrun-job-deploy
alias cloudrun-deploy-job := cloudrun-job-deploy
alias cloudrun-deploy-service := cloudrun-service-deploy
alias cloudrun-deploy-all := cloudrun-job-deploy

# Cloud Run Scheduling

alias schedule-cloudrun-all := cloudrun-schedule-all
alias schedule-custom := cloudrun-schedule-custom

# Cloud Run Execution & Testing

alias run-job := cloudrun-job-run
alias cloudrun-run-job := cloudrun-job-run
alias test-cloudrun-all := cloudrun-job-test
alias cloudrun-test-all := cloudrun-job-test
alias cloudrun-test-job := cloudrun-job-test
alias test-cloudrun-service := cloudrun-service-test
alias cloudrun-test-service := cloudrun-service-test
alias delete-cloudrun-all := cloudrun-delete-all
alias debug-api-detection := api-detection-debug

# Dev & Build Shorthands

alias venv := venv-create
alias build := package-build
alias clean := package-clean
alias clean-all := package-clean-all
alias rebuild := package-rebuild
alias lock := deps-lock
alias compile-requirements := deps-compile

# Usecases & Storage

alias publish-usecase := usecase-publish
alias publish-all-usecases := usecase-publish-all
alias list-gcs-usecases := usecase-list-gcs

# PyPI

alias publish-testpypi := pypi-publish-test
alias testpypi-publish := pypi-publish-test
alias test-testpypi-install := pypi-test-install
alias publish-pypi := pypi-publish
