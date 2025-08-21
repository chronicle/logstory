# Scripting the LogStory CLI

This guide covers how to automate LogStory operations using shell scripts and environment variables.

## Overview

LogStory's CLI is designed to be scriptable and automation-friendly. You can create shell scripts to:

- Batch process multiple use cases
- Automate regular replay operations
- Integrate with CI/CD pipelines
- Create custom workflows for different environments

## Environment Variables

LogStory supports several environment variables to simplify scripting:

| Variable | Description | Example |
|----------|-------------|---------|
| `LOGSTORY_CUSTOMER_ID` | Chronicle customer ID | `7e977ce4-f45d-43b2-aea0-52f8b66acd80` |
| `LOGSTORY_CREDENTIALS_PATH` | Path to service account JSON | `/path/to/credentials.json` |
| `LOGSTORY_REGION` | Chronicle region | `US`, `EUROPE`, `ASIA` |
| `LOGSTORY_USECASES_BUCKETS` | Comma-separated list of usecase sources | `gs://bucket1,file:///local/path` |

## Environment Files

For different environments (dev, staging, production), use environment files:

```bash
# .env.production
LOGSTORY_CUSTOMER_ID=prod-customer-id
LOGSTORY_CREDENTIALS_PATH=/path/to/prod-credentials.json
LOGSTORY_REGION=US

# .env.development  
LOGSTORY_CUSTOMER_ID=dev-customer-id
LOGSTORY_CREDENTIALS_PATH=/path/to/dev-credentials.json
LOGSTORY_REGION=US
```

Then use with the `--env-file` option:

```bash
logstory replay usecase SOME_CASE --env-file .env.production
```

## Batch Processing Scripts

### Example: Entity Replay Script

Here's an example script that processes multiple use cases for entity replay:

```bash
#!/bin/bash

# Configuration
BUCKET="file:///Users/user/Projects/usecases"
USECASES=("MALWARE_IOC" "NETWORK_ANALYSIS" "THREAT_HUNTING")

# Process each usecase
for usecase in "${USECASES[@]}"; do
  echo "Processing usecase: $usecase"

  # Replay the usecase with automatic download if missing
  LOGSTORY_USECASES_BUCKETS=$BUCKET \
  logstory replay usecase $usecase \
  --get \
  --credentials-path=/path/to/credentials.json \
  --customer-id=your-customer-id \
  --region=US \
  --timestamp-delta=1d \
  --entities \
  --local-file-output
done
```

### Example: Events Replay Script

For events replay across multiple use cases:

```bash
#!/bin/bash

BUCKET="gs://your-usecases-bucket"
USECASES=("GITHUB" "MALWARE_IOC" "O365_SECURITY")

for usecase in "${USECASES[@]}"; do
  echo "Processing usecase: $usecase"
  
  LOGSTORY_USECASES_BUCKETS=$BUCKET \
  logstory replay usecase $usecase \
  --get \
  --credentials-path=/path/to/credentials.json \
  --customer-id=your-customer-id \
  --region=US \
  --timestamp-delta=1d \
  --local-file-output
done
```

### Example: Using LOGSTORY_AUTO_GET

Instead of adding `--get` to every command, set the environment variable:

```bash
#!/bin/bash

# Enable auto-download globally
export LOGSTORY_AUTO_GET=true
export LOGSTORY_USECASES_BUCKETS="gs://usecases-bucket"

# Load other configuration from .env file
source .env.production

# Now all replay commands will auto-download if needed
USECASES=("OKTA" "AWS" "AZURE_AD")

for usecase in "${USECASES[@]}"; do
  echo "Processing $usecase (will auto-download if missing)"
  logstory replay usecase "$usecase" --timestamp-delta=1d
done
```

## Best Practices

### 1. Use Environment Files

Instead of hardcoding credentials in scripts:

```bash
# Good - use environment file
logstory replay usecase CASE_NAME --env-file .env.production

# Avoid - hardcoded credentials in script
logstory replay usecase CASE_NAME --customer-id=hardcoded-id
```

### 2. Error Handling

Add error handling to your scripts:

```bash
#!/bin/bash
set -e  # Exit on any error

for usecase in "${USECASES[@]}"; do
  echo "Processing usecase: $usecase"
  
  if ! logstory replay usecase "$usecase" --env-file .env.production; then
    echo "ERROR: Failed to process $usecase"
    exit 1
  fi
  
  echo "Successfully processed $usecase"
done
```

### 3. Logging and Monitoring

Capture output for monitoring:

```bash
#!/bin/bash

LOG_FILE="logstory-$(date +%Y%m%d-%H%M%S).log"

for usecase in "${USECASES[@]}"; do
  echo "$(date): Processing $usecase" | tee -a "$LOG_FILE"
  
  logstory replay usecase "$usecase" \
    --env-file .env.production \
    2>&1 | tee -a "$LOG_FILE"
done
```

### 4. Parallel Processing

For faster batch processing, use background jobs:

```bash
#!/bin/bash

MAX_JOBS=3
for usecase in "${USECASES[@]}"; do
  # Wait if we have too many background jobs
  while [ $(jobs -r | wc -l) -ge $MAX_JOBS ]; do
    sleep 1
  done
  
  # Start processing in background
  (
    echo "Processing $usecase"
    logstory replay usecase "$usecase" --env-file .env.production
  ) &
done

# Wait for all jobs to complete
wait
echo "All use cases processed"
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: LogStory Replay
on:
  schedule:
    - cron: '0 6 * * *'  # Daily at 6 AM

jobs:
  replay:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          
      - name: Install LogStory
        run: pip install logstory
        
      - name: Run Entity Replay
        env:
          LOGSTORY_CUSTOMER_ID: ${{ secrets.CHRONICLE_CUSTOMER_ID }}
          LOGSTORY_CREDENTIALS_PATH: ${{ secrets.CHRONICLE_CREDENTIALS_PATH }}
          LOGSTORY_REGION: US
        run: |
          logstory replay usecase MALWARE_IOC \
            --timestamp-delta=1d \
            --entities \
            --local-file-output
```

## Advanced Scripting

### Dynamic Use Case Discovery

Automatically discover and process available use cases:

```bash
#!/bin/bash

# Get list of available use cases
USECASES=$(logstory usecases list-installed --env-file .env.production | grep -v "^Available" | tail -n +2)

for usecase in $USECASES; do
  echo "Auto-processing discovered usecase: $usecase"
  logstory replay usecase "$usecase" --env-file .env.production
done
```

### Conditional Processing

Process use cases based on conditions:

```bash
#!/bin/bash

for usecase in "${USECASES[@]}"; do
  # Check if usecase has entities
  if logstory usecases list-installed --details | grep -A 5 "$usecase" | grep -q "entities"; then
    echo "Processing $usecase with entities"
    logstory replay usecase "$usecase" --entities --env-file .env.production
  else
    echo "Processing $usecase (events only)"
    logstory replay usecase "$usecase" --env-file .env.production
  fi
done
```

## Troubleshooting Scripts

### Debug Mode

Add debug output to scripts:

```bash
#!/bin/bash

DEBUG=${DEBUG:-false}

debug_log() {
  if [ "$DEBUG" = "true" ]; then
    echo "DEBUG: $1"
  fi
}

debug_log "Starting batch processing"
debug_log "Environment file: .env.production"

for usecase in "${USECASES[@]}"; do
  debug_log "Processing usecase: $usecase"
  # ... processing logic
done
```

Run with debug mode:

```bash
DEBUG=true ./replay_script.sh
```

### Validation

Validate environment before processing:

```bash
#!/bin/bash

validate_environment() {
  if [ ! -f ".env.production" ]; then
    echo "ERROR: Environment file .env.production not found"
    exit 1
  fi
  
  if ! command -v logstory >/dev/null 2>&1; then
    echo "ERROR: logstory command not found"
    exit 1
  fi
  
  echo "Environment validation passed"
}

validate_environment
# ... rest of script
```

## Security Considerations

1. **Never commit credentials** to version control
2. **Use environment files** stored outside the repository
3. **Set proper file permissions** on credential files (600)
4. **Use service accounts** with minimal required permissions
5. **Rotate credentials** regularly

## Related Documentation

- [Environment File Configuration](env-file.md)
- [CLI Reference](cli-reference.md)
- [Configuration Guide](configuration.md)