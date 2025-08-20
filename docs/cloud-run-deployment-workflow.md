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
export LOGSTORY_REGION=us-central1  # optional, defaults to us-central1
export LOGSTORY_API_TYPE=rest      # or 'legacy' for malachite API
```

## Deployment Method: Makefile vs Terraform

This project uses **Makefile** for Cloud Run deployment instead of Terraform because:
- **Simpler** - Direct gcloud commands, no HCL syntax
- **Faster** - No terraform plan/apply cycle
- **No state management** - No terraform state file issues
- **Transparent** - See exactly what commands run
- **Already integrated** - Makefile has all targets ready

Quick deployment:
```bash
make create-secret CREDENTIALS_FILE=/path/to/credentials.json  # One-time setup
make setup-permissions    # Grant permissions to default compute service account
make deploy-cloudrun-all  # Build Docker image and deploy the Cloud Run job
make schedule-cloudrun-all # Set up all 4 schedulers with different parameters
```

## Complete Deployment Workflow

### 1. Create Secret in Secret Manager (if not already exists)

Store your service account credentials JSON in Secret Manager:

```bash
# Using the Makefile (recommended):
make create-secret CREDENTIALS_FILE=/path/to/your/credentials.json

# Or manually:
gcloud secrets create chronicle-api-key \
  --data-file=/path/to/your/credentials.json \
  --replication-policy="automatic"

# If the secret already exists, create a new version:
gcloud secrets versions add chronicle-api-key \
  --data-file=/path/to/your/credentials.json
```

### 2. Setup Permissions

Grant necessary permissions to the default compute service account:

```bash
# Using the Makefile (recommended):
make setup-permissions

# This grants Secret Manager access to the default compute service account
# PROJECT_NUMBER-compute@developer.gserviceaccount.com
```

### 3. Deploy the Cloud Run Job

Deploy a single Cloud Run job that will be invoked with different parameters:

```bash
# Using the Makefile (builds Docker image and deploys):
make deploy-cloudrun-all

# This creates a single job called 'logstory-replay'
# The job uses the Docker image built from your local wheel file
```

### 4. Create Schedulers with Different Parameters

Create schedulers that invoke the same job with different arguments:

```bash
# Using the Makefile (creates all 4 schedulers):
make schedule-cloudrun-all
```

This creates 4 schedulers that all invoke the same `logstory-replay` job:

1. **events-24h**: Daily at 8 AM
   - Args: `replay all --timestamp-delta=1d`
   
2. **events-3day**: Every 3 days at 3 AM
   - Args: `replay all --timestamp-delta=3d`
   
3. **entities-24h**: Daily at 9 AM
   - Args: `replay all --entities --timestamp-delta=1d`
   
4. **entities-3day**: Every 3 days at 4 AM
   - Args: `replay all --entities --timestamp-delta=3d`

Each scheduler uses container argument overrides to pass different parameters to the same Cloud Run job.

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
make cloudrun-status

# View recent execution logs
make cloudrun-logs
```

### Test the Job
```bash
# Test with sample parameters
make test-cloudrun-all

# Or test manually with specific args
gcloud run jobs execute logstory-replay \
  --region us-central1 \
  --args "replay,all,--timestamp-delta=1d"
```

### Clean Up
```bash
# Delete all schedulers and the job
make delete-cloudrun-all
```

## Container Argument Overrides

The schedulers use container overrides to pass different arguments to the same job:

```json
// Example: entities-24h scheduler message body
{
  "overrides": {
    "containerOverrides": [{
      "args": ["replay", "all", "--entities", "--timestamp-delta=1d"]
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
gcloud scheduler jobs create http logstory-aws-daily \
  --location us-central1 \
  --schedule "0 10 * * *" \
  --uri "https://us-central1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT_ID/jobs/logstory-replay:run" \
  --http-method POST \
  --oauth-service-account-email "$SERVICE_ACCOUNT" \
  --headers "Content-Type=application/json" \
  --message-body '{"overrides":{"containerOverrides":[{"args":["replay","usecase","AWS","--timestamp-delta=1d"]}]}}'
```

## Testing Locally with Docker

```bash
# Build the image
docker build -t logstory-test -f Dockerfile.minimal .

# Run with environment variables
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
  logstory-test \
  logstory replay all --entities --timestamp-delta=3d
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

- **Command Arguments** (passed by each scheduler):
  - `--timestamp-delta`: How far back to set timestamps
  - `--entities`: Whether to enrich with entities
  - Specific usecase names if needed

## Troubleshooting

### Authentication Errors
If you get 401 errors from Cloud Scheduler:
1. Verify the service account is correct: `make setup-permissions`
2. The default compute service account should have necessary permissions
3. Check scheduler configuration: `gcloud scheduler jobs describe SCHEDULER_NAME`

### Secret Access Errors
If you get errors accessing the secret:
1. Verify the secret exists: `gcloud secrets list`
2. Check permissions were granted: `make setup-permissions`
3. View secret IAM policy: `gcloud secrets get-iam-policy chronicle-api-key`
4. Update the secret if needed: `make create-secret CREDENTIALS_FILE=/new/path.json`

### Container Override Errors
If schedulers fail to pass arguments:
1. Check the message body JSON is valid
2. Verify the args array format: `["replay", "all", "--timestamp-delta=1d"]`
3. Test manually: `gcloud run jobs execute logstory-replay --args "replay,all,--timestamp-delta=1d"`

## Notes

- **Single Job Pattern**: Using one job with parameter overrides is simpler than multiple jobs
- **Default Service Account**: Uses `PROJECT_NUMBER-compute@developer.gserviceaccount.com` for simplicity
- **Wheel-based Deployment**: Builds from local wheel file for immediate testing of changes
- **Memory Settings**: Default 1GB memory, adjust based on your data volume
- **Timeout**: 3600 seconds (1 hour) default, increase for large datasets
- **Makefile Automation**: All operations are wrapped in simple make commands for consistency