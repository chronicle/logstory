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
export PROJECT_ID=dandye-0324-chronicle
export LOGSTORY_CUSTOMER_ID=7e977ce4-f45d-43b2-aea0-52f8b66acd80
export REGION=us-central1
```

## Complete Deployment Workflow

### 1. Create Secret in Secret Manager (if not already exists)

Store your service account credentials JSON in Secret Manager:

```bash
# Create the secret from a JSON file
gcloud secrets create LOGSTORY_CREDENTIALS \
  --data-file=/path/to/your/credentials.json \
  --replication-policy="automatic"

# Example with your file:
gcloud secrets create LOGSTORY_CREDENTIALS \
  --data-file=/Users/dandye/.ssh/dandye-0324-chronicle-9186fd423acb.json \
  --replication-policy="automatic"

# Or if the secret already exists, create a new version:
gcloud secrets versions add LOGSTORY_CREDENTIALS \
  --data-file=/path/to/your/credentials.json
```

### 2. Grant Secret Access to Compute Service Account

The default Compute Engine service account needs access to read the credentials from Secret Manager:

```bash
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")

gcloud secrets add-iam-policy-binding LOGSTORY_CREDENTIALS \
  --member="serviceAccount:$PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### 3. Build the Wheel File Locally

Build the Python wheel file with your latest changes:

```bash
make build
# or
python -m build --wheel
```

This creates `dist/logstory-*.whl` with your local changes, including LOGSTORY_CREDENTIALS support.

### 4. Build Container Image with Cloud Build

Build and push the Docker container using the local wheel file:

```bash
gcloud builds submit --config cloudbuild-wheel.yaml
```

This uses `Dockerfile.wheel` which installs from the local wheel file rather than PyPI.

### 5. Create Cloud Run Job

Create a Cloud Run Job with the new container image:

```bash
# Create a timestamp for unique naming
TS=$(date +"%Y%m%d-%H%M")

gcloud run jobs create logstory-$TS \
  --image "gcr.io/$PROJECT_ID/logstory:latest" \
  --region $REGION \
  --set-env-vars "LOGSTORY_API_TYPE=rest" \
  --set-env-vars "LOGSTORY_CUSTOMER_ID=$LOGSTORY_CUSTOMER_ID" \
  --set-env-vars "LOGSTORY_REGION=US" \
  --set-env-vars "LOGSTORY_PROJECT_ID=$PROJECT_ID" \
  --set-env-vars "TIMESTAMP_DELTA=1d" \
  --set-secrets "LOGSTORY_CREDENTIALS=LOGSTORY_CREDENTIALS:latest" \
  --memory 512Mi \
  --task-timeout 3600 \
  --max-retries 1 \
  --execute-now
```

Environment variables explained:
- `LOGSTORY_API_TYPE=rest` - Use the REST API (or `legacy` for malachite)
- `LOGSTORY_CUSTOMER_ID` - Your Chronicle customer UUID
- `LOGSTORY_REGION` - Chronicle region (US, EUROPE, etc.)
- `LOGSTORY_PROJECT_ID` - GCP project ID for REST API
- `TIMESTAMP_DELTA` - How far back to set timestamps (1d, 3d, etc.)
- `LOGSTORY_CREDENTIALS` - Service account JSON from Secret Manager

### 6. Schedule the Job

Create a Cloud Scheduler job to run periodically:

```bash
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")

# For testing - every 5 minutes
gcloud scheduler jobs create http "logstory-$TS-schedule" \
  --location $REGION \
  --schedule "*/5 * * * *" \
  --uri "https://$REGION-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT_ID/jobs/logstory-$TS:run" \
  --oauth-service-account-email "${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --http-method POST

# For production - daily at 8 AM
gcloud scheduler jobs create http "logstory-$TS-schedule" \
  --location $REGION \
  --schedule "0 8 * * *" \
  --uri "https://$REGION-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT_ID/jobs/logstory-$TS:run" \
  --oauth-service-account-email "${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --http-method POST
```

Schedule format (cron syntax):
- `*/5 * * * *` - Every 5 minutes
- `0 8 * * *` - Daily at 8 AM
- `0 */6 * * *` - Every 6 hours
- `0 8 */3 * *` - Every 3 days at 8 AM

## Complete Script

Save this as `deploy-cloud-run.sh`:

```bash
#!/bin/bash
set -e

# Configuration
PROJECT_ID=${PROJECT_ID:-dandye-0324-chronicle}
LOGSTORY_CUSTOMER_ID=${LOGSTORY_CUSTOMER_ID:-7e977ce4-f45d-43b2-aea0-52f8b66acd80}
REGION=${REGION:-us-central1}
TS=$(date +"%Y%m%d-%H%M")

echo "Deploying Logstory to Cloud Run..."
echo "Project: $PROJECT_ID"
echo "Timestamp: $TS"

# Get project number
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")

# Create or update secret (optional - skip if already exists)
echo "1. Creating/updating secret..."
if gcloud secrets describe LOGSTORY_CREDENTIALS &>/dev/null; then
  echo "Secret exists, skipping creation"
else
  echo "Creating secret from credentials file..."
  # Update this path to your credentials file
  CREDS_FILE="/path/to/your/credentials.json"
  gcloud secrets create LOGSTORY_CREDENTIALS \
    --data-file="$CREDS_FILE" \
    --replication-policy="automatic"
fi

# Grant secret access
echo "2. Granting secret access..."
gcloud secrets add-iam-policy-binding LOGSTORY_CREDENTIALS \
  --member="serviceAccount:$PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Build wheel
echo "3. Building wheel file..."
make build

# Build container
echo "4. Building container with Cloud Build..."
gcloud builds submit --config cloudbuild-wheel.yaml

# Create Cloud Run job
echo "5. Creating Cloud Run job..."
gcloud run jobs create logstory-$TS \
  --image "gcr.io/$PROJECT_ID/logstory:latest" \
  --region $REGION \
  --set-env-vars "LOGSTORY_API_TYPE=rest" \
  --set-env-vars "LOGSTORY_CUSTOMER_ID=$LOGSTORY_CUSTOMER_ID" \
  --set-env-vars "LOGSTORY_REGION=US" \
  --set-env-vars "LOGSTORY_PROJECT_ID=$PROJECT_ID" \
  --set-env-vars "TIMESTAMP_DELTA=1d" \
  --set-secrets "LOGSTORY_CREDENTIALS=LOGSTORY_CREDENTIALS:latest" \
  --memory 512Mi \
  --task-timeout 3600 \
  --max-retries 1 \
  --execute-now

# Schedule the job
echo "6. Creating schedule..."
read -p "Schedule frequency (1=every 5 min, 2=daily, 3=every 3 days): " choice
case $choice in
  1) SCHEDULE="*/5 * * * *" ;;
  2) SCHEDULE="0 8 * * *" ;;
  3) SCHEDULE="0 8 */3 * *" ;;
  *) SCHEDULE="0 8 * * *" ;;
esac

gcloud scheduler jobs create http "logstory-$TS-schedule" \
  --location $REGION \
  --schedule "$SCHEDULE" \
  --uri "https://$REGION-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT_ID/jobs/logstory-$TS:run" \
  --oauth-service-account-email "${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --http-method POST

echo "Deployment complete!"
echo "Job name: logstory-$TS"
echo "Schedule: $SCHEDULE"
```

## Managing Deployments

### View Jobs
```bash
gcloud run jobs list --region $REGION
```

### View Executions
```bash
gcloud run jobs executions list --job=logstory-$TS --region $REGION
```

### View Logs
```bash
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=logstory-$TS" --limit 50
```

### Delete a Job and Schedule
```bash
gcloud scheduler jobs delete "logstory-$TS-schedule" --location $REGION
gcloud run jobs delete logstory-$TS --region $REGION
```

## Different Deployment Variants

### Events with 24-hour offset
```bash
gcloud run jobs create logstory-events-24h \
  --set-env-vars "TIMESTAMP_DELTA=1d" \
  # ... other flags
```

### Events with 3-day offset
```bash
gcloud run jobs create logstory-events-3d \
  --set-env-vars "TIMESTAMP_DELTA=3d" \
  # ... other flags
```

### Entities with 24-hour offset
```bash
gcloud run jobs create logstory-entities-24h \
  --set-env-vars "TIMESTAMP_DELTA=1d" \
  --command "logstory" \
  --args "replay,all,--entities" \
  # ... other flags
```

### Specific usecase
```bash
gcloud run jobs create logstory-aws-only \
  --command "logstory" \
  --args "replay,usecase,AWS,--timestamp-delta=1d" \
  # ... other flags
```

## Troubleshooting

### Authentication Errors
If you get 401 errors from Cloud Scheduler:
1. Verify the service account email is correct
2. Check that the service account has `roles/run.invoker` permission
3. Try using the App Engine default service account: `$PROJECT_ID@appspot.gserviceaccount.com`

### Secret Access Errors
If you get errors accessing LOGSTORY_CREDENTIALS:
1. Verify the secret exists: `gcloud secrets list`
2. Check permissions: `gcloud secrets get-iam-policy LOGSTORY_CREDENTIALS`
3. Ensure the service account has `roles/secretmanager.secretAccessor`
4. View the secret value to verify it's valid JSON: `gcloud secrets versions access latest --secret="LOGSTORY_CREDENTIALS"`
5. To update the secret with a new credentials file: `gcloud secrets versions add LOGSTORY_CREDENTIALS --data-file=/path/to/new/credentials.json`

### Build Failures
If Cloud Build fails with "no source files":
1. Check that `dist/` directory contains the wheel file
2. Verify `.gcloudignore` doesn't exclude `dist/`
3. Consider creating a clean build directory as shown in the workflow

## Notes

- The wheel file approach ensures you're using your local changes immediately without waiting for PyPI publication
- Cloud Run Jobs are more appropriate than Cloud Run Services for scheduled batch tasks
- The default Compute Engine service account is used for simplicity, but consider creating dedicated service accounts for production
- Adjust memory and timeout based on your data volume