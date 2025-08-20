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
	@echo ''
	@echo 'Cloud Deployment:'
	@echo '  - Prerequisites:'
	@echo '    1. Enable APIs: make enable-apis'
	@echo '    2. Create secret: make create-secret CREDENTIALS_FILE=/path/to/credentials.json'
	@echo '    3. Setup permissions: make setup-permissions'
	@echo '    4. Set environment variables (or use .env file):'
	@echo '       export LOGSTORY_CUSTOMER_ID=your-uuid'
	@echo '       export LOGSTORY_PROJECT_ID=your-project-id  # For REST API'
	@echo '       export LOGSTORY_API_TYPE=rest               # Required: rest or legacy'
	@echo '       export LOGSTORY_REGION=US                   # Chronicle region: US, EUROPE, UK, ASIA, SYDNEY'
	@echo '       export LOGSTORY_GCP_REGION=us-central1      # Optional: GCP region (auto-mapped from LOGSTORY_REGION)'
	@echo '  - Then run "make deploy-cloudrun-job" for scheduled execution or "make deploy-cloudrun-service" for HTTP API'


.DEFAULT_GOAL := help

# Cloud deployment variables - read from environment or use defaults
ifdef LOGSTORY_PROJECT_ID
PROJECT_ID ?= $(LOGSTORY_PROJECT_ID)
else
PROJECT_ID ?= $(shell gcloud config get-value project)
endif

# Chronicle region (US, EUROPE, etc) for LOGSTORY_REGION env var
ifdef LOGSTORY_REGION
CHRONICLE_REGION ?= $(LOGSTORY_REGION)
else
CHRONICLE_REGION ?= US
endif

# GCP region for gcloud commands (us-central1, europe-west1, etc)
ifdef LOGSTORY_GCP_REGION
GCP_REGION ?= $(LOGSTORY_GCP_REGION)
else
# Map Chronicle regions to GCP regions
ifeq ($(CHRONICLE_REGION),US)
GCP_REGION ?= us-central1
else ifeq ($(CHRONICLE_REGION),EUROPE)
GCP_REGION ?= europe-west1
else ifeq ($(CHRONICLE_REGION),UK)
GCP_REGION ?= europe-west2
else ifeq ($(CHRONICLE_REGION),ASIA)
GCP_REGION ?= asia-southeast1
else ifeq ($(CHRONICLE_REGION),SYDNEY)
GCP_REGION ?= australia-southeast1
else
GCP_REGION ?= us-central1
endif
endif

CUSTOMER_ID ?= $(LOGSTORY_CUSTOMER_ID)

ifndef LOGSTORY_API_TYPE
$(error LOGSTORY_API_TYPE environment variable must be set to 'rest' or 'legacy')
endif
API_TYPE := $(LOGSTORY_API_TYPE)

ifdef LOGSTORY_FORWARDER_NAME
FORWARDER_NAME ?= $(LOGSTORY_FORWARDER_NAME)
else
FORWARDER_NAME ?= Logstory-REST-Forwarder
endif
SECRET_NAME ?= chronicle-api-key
PROJECT_NUMBER ?= $(shell gcloud projects describe $(PROJECT_ID) --format="value(projectNumber)")
SERVICE_ACCOUNT ?= $(PROJECT_NUMBER)-compute@developer.gserviceaccount.com

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

# ========== Cloud Run Deployment Targets ==========

.PHONY: check-cloudrun-env
check-cloudrun-env: ## Check required environment for Cloud Run deployment
	@if [ -z "$(CUSTOMER_ID)" ]; then \
		echo "Error: LOGSTORY_CUSTOMER_ID is not set."; \
		echo "Set it with: export LOGSTORY_CUSTOMER_ID=your-uuid"; \
		exit 1; \
	fi
	@if [ -z "$(PROJECT_ID)" ]; then \
		echo "Error: LOGSTORY_PROJECT_ID is not set."; \
		echo "Set it with: export LOGSTORY_PROJECT_ID=your-project-id"; \
		echo "Or it will default to: gcloud config get-value project"; \
		exit 1; \
	fi
	@if [ "$(API_TYPE)" = "rest" ] && [ -z "$(PROJECT_ID)" ]; then \
		echo "Error: REST API requires LOGSTORY_PROJECT_ID"; \
		exit 1; \
	fi
	@echo "Configuration:"
	@echo "  CUSTOMER_ID: $(CUSTOMER_ID)"
	@echo "  PROJECT_ID: $(PROJECT_ID)"
	@echo "  CHRONICLE_REGION: $(CHRONICLE_REGION) (for LOGSTORY_REGION)"
	@echo "  GCP_REGION: $(GCP_REGION) (for gcloud commands)"
	@echo "  API_TYPE: $(API_TYPE)"
	@if [ "$(API_TYPE)" = "rest" ]; then \
		echo "  FORWARDER_NAME: $(FORWARDER_NAME)"; \
	fi
	@echo "  SECRET_NAME: $(SECRET_NAME)"

.PHONY: docker-build
docker-build: build ## Build and push Docker image to GCR using Cloud Build
	@echo "Building and pushing Docker image to GCR..."
	gcloud builds submit --config cloudbuild-wheel.yaml --project=$(PROJECT_ID)
	@echo "Docker image pushed to: gcr.io/$(PROJECT_ID)/logstory:latest"

.PHONY: enable-apis
enable-apis: ## Enable required Google Cloud APIs for Cloud Run deployment
	@echo "Enabling required APIs for project $(PROJECT_ID)..."
	@gcloud services enable run.googleapis.com --project=$(PROJECT_ID)
	@gcloud services enable cloudbuild.googleapis.com --project=$(PROJECT_ID)
	@gcloud services enable cloudscheduler.googleapis.com --project=$(PROJECT_ID)
	@gcloud services enable secretmanager.googleapis.com --project=$(PROJECT_ID)
	@echo "APIs enabled successfully!"

.PHONY: setup-permissions
setup-permissions: ## Grant necessary permissions to the default compute service account
	@echo "Using default compute service account: $(SERVICE_ACCOUNT)"
	@echo "Granting Secret Manager accessor role..."
	@gcloud projects add-iam-policy-binding $(PROJECT_ID) \
		--member="serviceAccount:$(SERVICE_ACCOUNT)" \
		--role="roles/secretmanager.secretAccessor" || true
	@echo "Ensuring secret exists and has correct permissions..."
	@if gcloud secrets describe $(SECRET_NAME) --project=$(PROJECT_ID) >/dev/null 2>&1; then \
		gcloud secrets add-iam-policy-binding $(SECRET_NAME) \
			--member="serviceAccount:$(SERVICE_ACCOUNT)" \
			--role="roles/secretmanager.secretAccessor" \
			--project=$(PROJECT_ID) || true; \
	else \
		echo "Warning: Secret $(SECRET_NAME) does not exist. Run 'make create-secret' first."; \
	fi
	@echo "Permissions setup complete!"

.PHONY: create-secret
create-secret: ## Create or update the LOGSTORY_CREDENTIALS secret in Secret Manager
	@if [ -z "$(CREDENTIALS_FILE)" ]; then \
		echo "Error: CREDENTIALS_FILE is not set. Usage: make create-secret CREDENTIALS_FILE=/path/to/credentials.json"; \
		exit 1; \
	fi
	@if [ ! -f "$(CREDENTIALS_FILE)" ]; then \
		echo "Error: File $(CREDENTIALS_FILE) does not exist"; \
		exit 1; \
	fi
	@echo "Creating/updating secret $(SECRET_NAME) from $(CREDENTIALS_FILE)..."
	@if gcloud secrets describe $(SECRET_NAME) --project=$(PROJECT_ID) >/dev/null 2>&1; then \
		echo "Secret exists, adding new version..."; \
		gcloud secrets versions add $(SECRET_NAME) --data-file=$(CREDENTIALS_FILE) --project=$(PROJECT_ID); \
	else \
		echo "Creating new secret..."; \
		gcloud secrets create $(SECRET_NAME) --data-file=$(CREDENTIALS_FILE) --replication-policy=automatic --project=$(PROJECT_ID); \
	fi
	@echo "Granting access to default compute service account..."
	@PROJECT_NUMBER=$$(gcloud projects describe $(PROJECT_ID) --format="value(projectNumber)"); \
	gcloud secrets add-iam-policy-binding $(SECRET_NAME) \
		--member="serviceAccount:$$PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
		--role="roles/secretmanager.secretAccessor" \
		--project=$(PROJECT_ID)
	@echo "Secret $(SECRET_NAME) is ready!"

## ToDo: need to clean dist/ before b/c cannot handle multiple whl files
.PHONY: deploy-cloudrun-job
deploy-cloudrun-job: check-cloudrun-env docker-build ## Deploy single Cloud Run job for logstory
	@echo "Deploying Cloud Run job: logstory-replay"
	@gcloud run jobs create logstory-replay \
		--image gcr.io/$(PROJECT_ID)/logstory:latest \
		--region $(GCP_REGION) \
		--service-account $(SERVICE_ACCOUNT) \
		--set-env-vars "LOGSTORY_CUSTOMER_ID=$(CUSTOMER_ID)" \
		--set-env-vars "LOGSTORY_REGION=$(CHRONICLE_REGION)" \
		--set-env-vars "LOGSTORY_API_TYPE=$(API_TYPE)" \
		--set-env-vars "LOGSTORY_PROJECT_ID=$(PROJECT_ID)" \
		--set-env-vars "LOGSTORY_FORWARDER_NAME=$(FORWARDER_NAME)" \
		--set-secrets "LOGSTORY_CREDENTIALS=$(SECRET_NAME):latest" \
		--memory 1Gi \
		--task-timeout 3600 \
		--max-retries 1 \
		--parallelism 1 \
		|| (echo "Job exists, updating..." && \
		gcloud run jobs update logstory-replay \
		--image gcr.io/$(PROJECT_ID)/logstory:latest \
		--region $(GCP_REGION) \
		--set-env-vars "LOGSTORY_CUSTOMER_ID=$(CUSTOMER_ID)" \
		--set-env-vars "LOGSTORY_REGION=$(CHRONICLE_REGION)" \
		--set-env-vars "LOGSTORY_API_TYPE=$(API_TYPE)" \
		--set-env-vars "LOGSTORY_PROJECT_ID=$(PROJECT_ID)" \
		--set-env-vars "LOGSTORY_FORWARDER_NAME=$(FORWARDER_NAME)" \
		--set-secrets "LOGSTORY_CREDENTIALS=$(SECRET_NAME):latest")
	@echo "Cloud Run job deployed successfully!"

.PHONY: deploy-cloudrun-service
deploy-cloudrun-service: check-cloudrun-env docker-build ## Deploy Cloud Run service for logstory API
	@echo "Deploying Cloud Run service: logstory-service"
	@gcloud run deploy logstory-service \
		--image gcr.io/$(PROJECT_ID)/logstory:latest \
		--region $(GCP_REGION) \
		--service-account $(SERVICE_ACCOUNT) \
		--set-env-vars "LOGSTORY_CUSTOMER_ID=$(CUSTOMER_ID)" \
		--set-env-vars "LOGSTORY_REGION=$(CHRONICLE_REGION)" \
		--set-env-vars "LOGSTORY_API_TYPE=$(API_TYPE)" \
		--set-env-vars "LOGSTORY_PROJECT_ID=$(PROJECT_ID)" \
		--set-env-vars "LOGSTORY_FORWARDER_NAME=$(FORWARDER_NAME)" \
		--set-secrets "LOGSTORY_CREDENTIALS=$(SECRET_NAME):latest" \
		--memory 1Gi \
		--cpu 1 \
		--min-instances 0 \
		--max-instances 10 \
		--concurrency 80 \
		--timeout 3600 \
		--port 8080 \
		--allow-unauthenticated
	@echo "Cloud Run service deployed successfully!"
	@echo "Service URL: $$(gcloud run services describe logstory-service --region $(GCP_REGION) --format 'value(status.url)')"

.PHONY: deploy-cloudrun-all
deploy-cloudrun-all: deploy-cloudrun-job ## Deploy the Cloud Run job (simplified - just one job now)

.PHONY: schedule-cloudrun-all
schedule-cloudrun-all: check-cloudrun-env ## Create all schedulers for the single Cloud Run job
	@echo "Creating scheduler: events-24h (daily at 8 AM)"
	@gcloud scheduler jobs create http logstory-events-24h \
		--location $(GCP_REGION) \
		--schedule "0 8 * * *" \
		--time-zone "America/New_York" \
		--uri "https://$(GCP_REGION)-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$(PROJECT_ID)/jobs/logstory-replay:run" \
		--http-method POST \
		--oauth-service-account-email $(SERVICE_ACCOUNT) \
		--headers "Content-Type=application/json" \
		--message-body '{"overrides":{"containerOverrides":[{"args":["replay","all","--timestamp-delta=1d"]}]}}' \
		|| echo "Scheduler events-24h already exists"

	@echo "Creating scheduler: events-3day (every 3 days at 3 AM)"
	@gcloud scheduler jobs create http logstory-events-3day \
		--location $(GCP_REGION) \
		--schedule "0 3 */3 * *" \
		--time-zone "America/New_York" \
		--uri "https://$(GCP_REGION)-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$(PROJECT_ID)/jobs/logstory-replay:run" \
		--http-method POST \
		--oauth-service-account-email $(SERVICE_ACCOUNT) \
		--headers "Content-Type=application/json" \
		--message-body '{"overrides":{"containerOverrides":[{"args":["replay","all","--timestamp-delta=3d"]}]}}' \
		|| echo "Scheduler events-3day already exists"

	@echo "Creating scheduler: entities-24h (daily at 9 AM)"
	@gcloud scheduler jobs create http logstory-entities-24h \
		--location $(GCP_REGION) \
		--schedule "0 9 * * *" \
		--time-zone "America/New_York" \
		--uri "https://$(GCP_REGION)-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$(PROJECT_ID)/jobs/logstory-replay:run" \
		--http-method POST \
		--oauth-service-account-email $(SERVICE_ACCOUNT) \
		--headers "Content-Type=application/json" \
		--message-body '{"overrides":{"containerOverrides":[{"args":["replay","all","--entities","--timestamp-delta=1d"]}]}}' \
		|| echo "Scheduler entities-24h already exists"

	@echo "Creating scheduler: entities-3day (every 3 days at 4 AM)"
	@gcloud scheduler jobs create http logstory-entities-3day \
		--location $(GCP_REGION) \
		--schedule "0 4 */3 * *" \
		--time-zone "America/New_York" \
		--uri "https://$(GCP_REGION)-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$(PROJECT_ID)/jobs/logstory-replay:run" \
		--http-method POST \
		--oauth-service-account-email $(SERVICE_ACCOUNT) \
		--headers "Content-Type=application/json" \
		--message-body '{"overrides":{"containerOverrides":[{"args":["replay","all","--entities","--timestamp-delta=3d"]}]}}' \
		|| echo "Scheduler entities-3day already exists"

	@echo "All schedulers created successfully!"

.PHONY: test-cloudrun-all
test-cloudrun-all: check-cloudrun-env ## Test the Cloud Run job with different parameters
	@echo "Testing events 24h..."
	@gcloud run jobs execute logstory-replay \
		--region $(GCP_REGION) \
		--args "replay,all,--timestamp-delta=1d" \
		--wait

.PHONY: debug-api-detection
debug-api-detection: check-cloudrun-env ## Debug API type detection locally
	@echo "Testing API detection locally..."
	@echo "Environment variables:"
	@echo "  LOGSTORY_API_TYPE: $(API_TYPE)"
	@echo "  LOGSTORY_PROJECT_ID: $(PROJECT_ID)"
	@echo "  LOGSTORY_REGION: $(CHRONICLE_REGION)"
	@cd /tmp && LOGSTORY_PROJECT_ID=$(PROJECT_ID) LOGSTORY_REGION=$(CHRONICLE_REGION) LOGSTORY_API_TYPE=$(API_TYPE) \
	python -c "import sys; sys.path.insert(0, '/Users/dandye/Projects/logstory__worktrees/rest_api/src'); \
	from logstory.auth import detect_auth_type; \
	result = detect_auth_type(); \
	print(f'Detected API type: {result}')"

.PHONY: test-cloudrun-service
test-cloudrun-service: check-cloudrun-env ## Test the Cloud Run service with HTTP requests
	@echo "Testing Cloud Run service..."
	@SERVICE_URL=$$(gcloud run services describe logstory-service --region $(GCP_REGION) --format 'value(status.url)' 2>/dev/null); \
	if [ -n "$$SERVICE_URL" ]; then \
		echo "Service URL: $$SERVICE_URL"; \
		echo "Testing health endpoint..."; \
		curl -f "$$SERVICE_URL/health" || echo "Health endpoint not available"; \
		echo "Testing version endpoint..."; \
		curl -f "$$SERVICE_URL/version" || echo "Version endpoint not available"; \
	else \
		echo "Service not deployed. Run 'make deploy-cloudrun-service' first."; \
	fi

.PHONY: cloudrun-status
cloudrun-status: check-cloudrun-env ## Show status of Cloud Run job, service, and schedulers
	@echo "=== Cloud Run Job Status ==="
	@gcloud run jobs describe logstory-replay --region $(GCP_REGION) --format "table(metadata.name,status.conditions[0].type,status.conditions[0].status)" 2>/dev/null || echo "Job not deployed"
	@echo ""
	@echo "=== Recent Job Executions ==="
	@gcloud run jobs executions list --job logstory-replay --region $(GCP_REGION) --limit 5 --format "table(metadata.name,status.completionTime,status.conditions[0].status)" 2>/dev/null || echo "No executions found"
	@echo ""
	@echo "=== Cloud Run Service Status ==="
	@gcloud run services describe logstory-service --region $(GCP_REGION) --format "table(metadata.name,status.conditions[0].type,status.conditions[0].status,status.url)" 2>/dev/null || echo "Service not deployed"
	@echo ""
	@echo "=== Service Traffic ==="
	@gcloud run services describe logstory-service --region $(GCP_REGION) --format "table(status.traffic[*].revisionName:label=REVISION,status.traffic[*].percent:label=TRAFFIC%)" 2>/dev/null || echo "No service traffic info"
	@echo ""
	@echo "=== Scheduler Status ==="
	@gcloud scheduler jobs list --location $(GCP_REGION) --format "table(name.basename(),schedule,state,lastAttemptTime.date())" 2>/dev/null || echo "No schedulers found"

.PHONY: cloudrun-logs
cloudrun-logs: check-cloudrun-env ## View logs from the most recent Cloud Run job execution
	@gcloud run jobs executions list \
		--job logstory-replay \
		--region $(GCP_REGION) \
		--limit 1 \
		--format "value(name)" | xargs -I {} \
		gcloud run jobs executions logs {} \
		--region $(GCP_REGION)

.PHONY: cloudrun-service-logs
cloudrun-service-logs: check-cloudrun-env ## View logs from the Cloud Run service
	@gcloud logs read "resource.type=cloud_run_revision AND resource.labels.service_name=logstory-service" \
		--project=$(PROJECT_ID) \
		--limit=50 \
		--order=desc \
		--format="table(timestamp,severity,textPayload)"

.PHONY: delete-cloudrun-all
delete-cloudrun-all: check-cloudrun-env ## Delete Cloud Run job, service, and all schedulers
	@echo "Deleting schedulers..."
	@gcloud scheduler jobs delete logstory-events-24h --location $(GCP_REGION) --quiet 2>/dev/null || true
	@gcloud scheduler jobs delete logstory-events-3day --location $(GCP_REGION) --quiet 2>/dev/null || true
	@gcloud scheduler jobs delete logstory-entities-24h --location $(GCP_REGION) --quiet 2>/dev/null || true
	@gcloud scheduler jobs delete logstory-entities-3day --location $(GCP_REGION) --quiet 2>/dev/null || true
	@echo "Deleting Cloud Run job..."
	@gcloud run jobs delete logstory-replay --region $(GCP_REGION) --quiet 2>/dev/null || true
	@echo "Deleting Cloud Run service..."
	@gcloud run services delete logstory-service --region $(GCP_REGION) --quiet 2>/dev/null || true
	@echo "All Cloud Run resources deleted"

.PHONY: cloudrun-help
cloudrun-help: ## Show Cloud Run deployment help
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
	@echo "  2. Enable required Google Cloud APIs:"
	@echo "     make enable-apis"
	@echo ""
	@echo "  3. Create secret in Secret Manager:"
	@echo "     make create-secret CREDENTIALS_FILE=/path/to/credentials.json"
	@echo ""
	@echo "  4. Setup permissions for default compute service account:"
	@echo "     make setup-permissions"
	@echo ""
	@echo "Quick Start - Job Deployment (scheduled execution):"
	@echo "  make enable-apis               # Enable required APIs"
	@echo "  make create-secret CREDENTIALS_FILE=/path/to/creds.json"
	@echo "  make setup-permissions         # Grant permissions"
	@echo "  make deploy-cloudrun-job       # Deploy the Cloud Run job"
	@echo "  make schedule-cloudrun-all     # Set up all schedulers"
	@echo "  make test-cloudrun-all         # Test the job"
	@echo ""
	@echo "Quick Start - Service Deployment (HTTP API):"
	@echo "  make enable-apis               # Enable required APIs"
	@echo "  make create-secret CREDENTIALS_FILE=/path/to/creds.json"
	@echo "  make setup-permissions         # Grant permissions"
	@echo "  make deploy-cloudrun-service   # Deploy the Cloud Run service"
	@echo "  make test-cloudrun-service     # Test the service"
	@echo ""
	@echo "Monitoring:"
	@echo "  make cloudrun-status           # Check job/service status"
	@echo "  make cloudrun-logs             # View recent job logs"
	@echo "  make cloudrun-service-logs     # View recent service logs"
	@echo ""
	@echo "Cleanup:"
	@echo "  make delete-cloudrun-all  # Remove job and schedulers"
