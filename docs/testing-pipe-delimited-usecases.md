# Testing Pipe-Delimited Usecase Filtering in Cloud Run

## Overview

This document provides testing instructions for the pipe-delimited usecase filtering functionality in Logstory's Cloud Run deployment. This feature allows you to filter which usecases are processed when using `replay all` by setting the `LOGSTORY_USECASES` environment variable.

## Feature Description

The `LOGSTORY_USECASES` environment variable filtering feature allows you to:

- Use `replay all` command with selective usecase processing
- Avoid gcloud argument parsing issues entirely
- Filter usecases using pipe-separated values (e.g., `NETWORK_ANALYSIS|GITHUB`)
- Maintain backward compatibility - no filtering variable means process all usecases

## Implementation

When `LOGSTORY_USECASES` is set, the `replay all` command:
1. Parses the pipe-separated usecase list
2. Validates that all requested usecases exist
3. Only processes the specified usecases instead of all available ones
4. Provides clear feedback about which usecases are being processed

## Local Testing

### Prerequisites

Set up your development environment:

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate

# Install in editable mode
pip install -e .

# Set required environment variables
export LOGSTORY_CUSTOMER_ID=your-uuid
export LOGSTORY_CREDENTIALS_PATH=/path/to/credentials.json
export LOGSTORY_REGION=US
export LOGSTORY_API_TYPE=rest
```

### Test Cases

#### 1. Test Normal Behavior (No Filtering)

```bash
# Should process all available usecases
logstory replay all --local-file-output

# Expected output: "Processing all usecases: NETWORK_ANALYSIS, RULES_SEARCH_WORKSHOP, ..."
```

#### 2. Test Single Usecase Filtering

```bash
# Filter to single usecase
LOGSTORY_USECASES=NETWORK_ANALYSIS logstory replay all --local-file-output

# Expected output: "Processing filtered usecases: NETWORK_ANALYSIS"
```

#### 3. Test Multiple Usecase Filtering

```bash
# Filter to multiple usecases
LOGSTORY_USECASES=NETWORK_ANALYSIS\|RULES_SEARCH_WORKSHOP logstory replay all --local-file-output

# Expected output: "Processing filtered usecases: NETWORK_ANALYSIS, RULES_SEARCH_WORKSHOP"
```

#### 4. Test Error Handling

```bash
# Test with invalid usecase
LOGSTORY_USECASES=INVALID_USECASE logstory replay all --local-file-output

# Expected: Error message listing available usecases
```

## Cloud Run Testing

### Prerequisites

Ensure your Cloud Run environment is set up:

```bash
# Set required environment variables
export LOGSTORY_API_TYPE=rest
export LOGSTORY_CUSTOMER_ID=your-uuid
export LOGSTORY_PROJECT_ID=your-project-id
export LOGSTORY_REGION=US

# Build and deploy updated Docker image
make build
make docker-build
```

### Test Cases

#### 1. Test Normal Cloud Run Behavior

```bash
# Process all usecases (no filtering)
gcloud run jobs execute logstory-replay \
  --region us-central1 \
  --args "logstory,replay,all" \
  --wait
```

#### 2. Test Single Usecase Filtering

```bash
# Filter to single usecase
gcloud run jobs execute logstory-replay \
  --region us-central1 \
  --args "logstory,replay,all" \
  --update-env-vars "LOGSTORY_USECASES=NETWORK_ANALYSIS" \
  --wait
```

#### 3. Test Multiple Usecase Filtering

```bash
# Filter to multiple usecases using pipe separator
gcloud run jobs execute logstory-replay \
  --region us-central1 \
  --args "logstory,replay,all" \
  --update-env-vars "LOGSTORY_USECASES=NETWORK_ANALYSIS|RULES_SEARCH_WORKSHOP" \
  --wait
```

#### 4. Test with Additional Options

```bash
# Combine filtering with entities and custom timestamp delta
gcloud run jobs execute logstory-replay \
  --region us-central1 \
  --args "logstory,replay,all,--entities" \
  --update-env-vars "LOGSTORY_USECASES=NETWORK_ANALYSIS,LOGSTORY_TIMESTAMP_DELTA=3d" \
  --wait
```

## Validation Methods

### Check Execution Status

```bash
# Get the latest execution name
EXECUTION_NAME=$(gcloud run jobs executions list \
  --job logstory-replay \
  --region us-central1 \
  --limit 1 \
  --format "value(name)")

# Check if it completed successfully
gcloud run jobs executions describe $EXECUTION_NAME \
  --region us-central1 \
  --format "value(status.conditions[0].status)"
```

### Analyze Logs

```bash
# Install beta components if needed
gcloud components install beta --quiet

# View execution logs
gcloud beta run jobs executions logs read $EXECUTION_NAME --region us-central1
```

### Success Indicators

Look for these patterns in the logs:

**Filtered Processing:**
```
Processing filtered usecases: NETWORK_ANALYSIS, RULES_SEARCH_WORKSHOP
Processing usecase: NETWORK_ANALYSIS, logtype: BRO_JSON
Processing usecase: RULES_SEARCH_WORKSHOP, logtype: POWERSHELL
Successfully posted entries using RestIngestionBackend
```

**Normal Processing:**
```
Processing all usecases: NETWORK_ANALYSIS, RULES_SEARCH_WORKSHOP, THW2
```

**Error Handling:**
```
Error: Invalid usecases: INVALID_NAME
Available usecases: NETWORK_ANALYSIS, RULES_SEARCH_WORKSHOP, THW2
```

## Troubleshooting

### Common Issues

#### Issue: Container Exits with Error
**Solution:** Check execution logs for specific error messages and verify environment variables are set correctly.

#### Issue: All Usecases Processed Despite Filtering
**Solution:** Verify the Docker image was rebuilt and deployed after code changes. Check that `LOGSTORY_USECASES` environment variable is correctly set.

#### Issue: Invalid Usecase Error
**Solution:** Run `logstory usecases list-installed` to see available usecases, or check the error message for the list of valid options.

### Debugging Commands

```bash
# Check job configuration
gcloud run jobs describe logstory-replay --region us-central1

# List recent executions
gcloud run jobs executions list \
  --job logstory-replay \
  --region us-central1 \
  --limit 5

# Check environment variables in job
gcloud run jobs describe logstory-replay \
  --region us-central1 \
  --format "value(spec.template.template.spec.template.spec.containers[0].env[])"
```

## Benefits

1. **No gcloud parsing issues** - Environment variables avoid command-line argument parsing problems
2. **Clean command structure** - Simple `logstory,replay,all` arguments
3. **Flexible filtering** - Easy to specify any combination of usecases
4. **Backward compatible** - Existing behavior preserved when no filtering is specified
5. **Clear feedback** - Logs clearly show which usecases are being processed

## Usage Examples

### Development Workflow

```bash
# Test locally first
LOGSTORY_USECASES=NETWORK_ANALYSIS|RULES_SEARCH_WORKSHOP logstory replay all --local-file-output

# Deploy to Cloud Run
make build && make docker-build

# Test in Cloud Run
gcloud run jobs execute logstory-replay \
  --region us-central1 \
  --args "logstory,replay,all" \
  --update-env-vars "LOGSTORY_USECASES=NETWORK_ANALYSIS|RULES_SEARCH_WORKSHOP" \
  --wait
```

### Production Usage

```bash
# Set environment variables in .env file or Cloud Run job configuration
LOGSTORY_USECASES=PRODUCTION_USECASE_1|PRODUCTION_USECASE_2

# Deploy with scheduled execution
gcloud run jobs execute logstory-replay \
  --region us-central1 \
  --args "logstory,replay,all" \
  --wait
```

This implementation provides a clean, reliable solution for filtering usecases in Cloud Run deployments while maintaining full backward compatibility and avoiding all gcloud argument parsing issues.