# Cloud Run Deployment Workflow

This document describes the complete workflow for deploying Logstory to Cloud Run with scheduled execution.

## Prerequisites

- Google Cloud Project with Cloud Run, Cloud Build, and Cloud Scheduler APIs enabled
- `gcloud` CLI configured and authenticated
- Service account credentials JSON file
- Python environment with build tools (`pip install build`)

## Environment Variables

Set these variables before starting:

```bash
export LOGSTORY_PROJECT_ID=your-gcp-project-id
export LOGSTORY_CUSTOMER_ID=your-chronicle-customer-uuid
export LOGSTORY_REGION=US  # optional, defaults to US
export LOGSTORY_API_TYPE=rest  # or 'legacy' for malachite API
```

## Deployment Method: Justfile vs Terraform

This project uses **Justfile** (`just`) for Cloud Run deployment instead of Terraform because:
- **Simpler** - Direct gcloud commands, no HCL syntax
- **Faster** - No terraform plan/apply cycle
- **No state management** - No terraform state file issues
- **Transparent** - See exactly what commands run
- **Already integrated** - Justfile has all recipes ready

Quick deployment:
```bash
just apis-enable          # Enable required Google Cloud APIs
just secret-create /path/to/credentials.json  # One-time setup
just permissions-setup    # Grant permissions to default compute service account
just cloudrun-job-deploy  # Build Docker image and deploy the Cloud Run job
just cloudrun-schedule-all # Set up all 4 schedulers with different parameters
```

## Complete Deployment Workflow

### 1. Enable Required APIs

Enable the necessary Google Cloud APIs:

```bash
just apis-enable
```

This enables:
- Cloud Run API
- Cloud Build API
- Cloud Scheduler API
- Secret Manager API
- IAM API
- Cloud Resource Manager API
- Artifact Registry API

### 2. Create Secret in Secret Manager

Store your service account credentials JSON in Secret Manager:

```bash
# Using the Justfile (recommended):
just secret-create /path/to/your/credentials.json

# Or manually:
gcloud secrets create chronicle-api-key \
  --data-file=/path/to/your/credentials.json \
  --replication-policy="automatic"

# If the secret already exists, create a new version:
gcloud secrets versions add chronicle-api-key \
  --data-file=/path/to/your/credentials.json
```

### 3. Setup Permissions

Grant necessary permissions to the default compute service account:

```bash
# Using the Justfile (recommended):
just permissions-setup

# This grants Secret Manager access to the default compute service account
# PROJECT_NUMBER-compute@developer.gserviceaccount.com
```

### 4. Deploy the Cloud Run Job

Deploy a single Cloud Run job that will be invoked with different parameters:

```bash
# Using the Justfile (builds Docker image and deploys):
just cloudrun-job-deploy

# This creates a single job called 'logstory-replay'
# The job uses the Docker image built from your local wheel file
```

### 5. Create Schedulers with Different Parameters

Create schedulers that invoke the same job with different arguments:

```bash
# Using the Justfile (creates all 4 schedulers):
just cloudrun-schedule-all
```

This creates 4 schedulers that all invoke the same `logstory-replay` job:

1. **events-24h**: Daily at 3:00 AM UTC
   - Args: `logstory replay all`

2. **events-3day**: Every 3 days at 3:00 AM UTC
   - Args: `logstory replay all`

3. **entities-24h**: Daily at 12:01 AM UTC
   - Args: `logstory replay all --entities`

4. **entities-3day**: Every 3 days at 12:01 AM UTC
   - Args: `logstory replay all --entities`

Each scheduler uses container argument overrides to pass different parameters to the same Cloud Run job. The timestamp delta is controlled by the `LOGSTORY_TIMESTAMP_DELTA` environment variable (default: 1d) set on the job itself.

## Simplified Architecture

The deployment uses a **single Cloud Run job** with **multiple schedulers** that pass different parameters:

```
┌─────────────────────────────────────────────────┐
│           Cloud Run Job: logstory-replay        │
│                                                  │
│  Environment Variables:                          │
│  - LOGSTORY_CUSTOMER_ID                         │
│  - LOGSTORY_PROJECT_ID                          │
│  - LOGSTORY_API_TYPE                            │
│  - LOGSTORY_CREDENTIALS (from Secret Manager)   │
└─────────────────────────────────────────────────┘
                    ▲
                    │ Invoked with different args
    ┌───────────────┼───────────────┬──────────────┐
    │               │               │              │
┌───▼────┐    ┌────▼────┐    ┌────▼────┐    ┌────▼────┐
│events  │    │events   │    │entities │    │entities │
│24h     │    │3day     │    │24h      │    │3day     │
│        │    │         │    │         │    │         │
│Daily   │    │Every    │    │Daily    │    │Every    │
│8 AM    │    │3 days   │    │9 AM     │    │3 days   │
│        │    │3 AM     │    │         │    │4 AM     │
└────────┘    └─────────┘    └─────────┘    └─────────┘
```

## Managing Deployments

### View Status
```bash
# Check job and scheduler status
just cloudrun-status

# View recent execution logs
just cloudrun-logs
```

### Test the Job
```bash
# Test with sample parameters
just cloudrun-job-test

# Or test with specific args via just
just cloudrun-job-run "logstory,replay,all"
```

### Clean Up
```bash
# Delete all schedulers and the job
just cloudrun-delete-all
```

## Container Argument Overrides

The schedulers use container overrides to pass different arguments to the same job:

```json
// Example: entities-24h scheduler message body
{
  "overrides": {
    "containerOverrides": [{
      "args": ["logstory", "replay", "all", "--entities"]
    }]
  }
}
```

This allows one job to handle multiple use cases:
- Events ingestion with different time windows
- Entity enrichment with different time windows
- Different usecases (if needed)

### Creating Custom Schedulers

To add a new scheduler for a specific usecase:

```bash
# Using Justfile:
just cloudrun-schedule-custom logstory-aws-daily "0 10 * * *" '["logstory","replay","usecase","AWS"]'

# Or manually:
gcloud scheduler jobs create http logstory-aws-daily \
  --location us-central1 \
  --schedule "0 10 * * *" \
  --uri "https://us-central1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT_ID/jobs/logstory-replay:run" \
  --http-method POST \
  --oauth-service-account-email "$SERVICE_ACCOUNT" \
  --headers "Content-Type=application/json" \
  --message-body '{"overrides":{"containerOverrides":[{"args":["logstory","replay","usecase","AWS"]}]}}'
```

## Testing Locally with Docker

```bash
# Build the image using Justfile
just docker-build-local

# Run with environment variables using Justfile
just docker-run-local

# Or manually:
docker run \
  -e LOGSTORY_CUSTOMER_ID="your-uuid" \
  -e LOGSTORY_CREDENTIALS="$(cat credentials.json)" \
  -e LOGSTORY_REGION="US" \
  -e TIMESTAMP_DELTA="1d" \
  logstory-test

# Or override the command
docker run \
  -e LOGSTORY_CUSTOMER_ID="your-uuid" \
  -e LOGSTORY_CREDENTIALS="$(cat credentials.json)" \
  -e LOGSTORY_TIMESTAMP_DELTA="3d" \
  logstory-test \
  logstory replay all --entities
```

## Dockerfile Options

### Dockerfile.minimal (Production - from PyPI)
```dockerfile
FROM python:3.11-slim
RUN pip install --no-cache-dir logstory>=1.0.0
WORKDIR /app
CMD ["logstory", "replay", "all"]
```

### Dockerfile.wheel (Testing - from local wheel)
```dockerfile
FROM python:3.11-slim
COPY dist/logstory-*.whl /tmp/
RUN pip install --no-cache-dir /tmp/logstory-*.whl && rm /tmp/logstory-*.whl
WORKDIR /app
CMD ["logstory", "replay", "all"]
```

### Dockerfile.uvx (Dynamic - always latest)
```dockerfile
FROM python:3.11-slim
RUN pip install --no-cache-dir uv
WORKDIR /app
CMD ["uvx", "logstory", "replay", "all"]
```

## Key Benefits of Single Job Approach

1. **Simplicity**: One job to deploy and manage instead of four
2. **Consistency**: All schedulers use the same base configuration
3. **Efficiency**: Updates only need to be applied once
4. **Flexibility**: Easy to add new schedulers with different parameters
5. **Cost**: Reduced complexity means fewer resources to manage

## Environment Variables vs Arguments

- **Environment Variables** (set once on the job):
  - `LOGSTORY_CUSTOMER_ID`: Chronicle customer UUID
  - `LOGSTORY_PROJECT_ID`: GCP project for REST API
  - `LOGSTORY_API_TYPE`: API type (rest or legacy)
  - `LOGSTORY_CREDENTIALS`: Service account JSON from Secret Manager
  - `LOGSTORY_TIMESTAMP_DELTA`: How far back to set timestamps (default: 1d)

- **Command Arguments** (passed by each scheduler):
  - `--entities`: Whether to enrich with entities
  - Specific usecase names if needed
  - Optional overrides like `--timestamp-delta` if different from environment variable

## Troubleshooting

### Authentication Errors
If you get 401 errors from Cloud Scheduler:
1. Verify the service account is correct: `just permissions-setup`
2. The default compute service account should have necessary permissions
3. Check scheduler configuration: `gcloud scheduler jobs describe SCHEDULER_NAME`

### Secret Access Errors
If you get errors accessing the secret:
1. Verify the secret exists: `just secret-list`
2. Check permissions were granted: `just permissions-setup`
3. View secret IAM policy: `just secret-iam`
4. Update the secret if needed: `just secret-create /new/path.json`

### Container Override Errors
If schedulers fail to pass arguments:
1. Check the message body JSON is valid
2. Verify the args array format: `["logstory", "replay", "all", "--entities"]`
3. Test manually: `just cloudrun-job-run "logstory,replay,all"`

## Notes

- **Single Job Pattern**: Using one job with parameter overrides is simpler than multiple jobs
- **Default Service Account**: Uses `PROJECT_NUMBER-compute@developer.gserviceaccount.com` for simplicity
- **Wheel-based Deployment**: Builds from local wheel file for immediate testing of changes
- **Memory Settings**: Default 1GB memory, adjust based on your data volume
- **Timeout**: 3600 seconds (1 hour) default, increase for large datasets
- **Justfile Automation**: All operations are wrapped in simple `just` recipes for consistency