# Configuration

Logstory provides flexible configuration options through command line arguments, environment variables, and .env files. This page covers all configuration methods and options in detail.

## Configuration Methods

### 1. Command Line Options

Pass configuration directly on the command line:

```bash
logstory replay usecase RULES_SEARCH_WORKSHOP \
  --customer-id=01234567-0123-4321-abcd-01234567890a \
  --credentials-path=/path/to/credentials.json \
  --region=US \
  --timestamp-delta=1d
```

### 2. Environment Variables

Set environment variables in your shell:

```bash
export LOGSTORY_CUSTOMER_ID=01234567-0123-4321-abcd-01234567890a
export LOGSTORY_CREDENTIALS_PATH=/path/to/credentials.json
export LOGSTORY_REGION=US
export LOGSTORY_USECASES_BUCKETS=gs://my-bucket,file:///local/usecases
export LOGSTORY_AUTO_GET=true  # Auto-download missing usecases
export LOGSTORY_USECASES=NETWORK_ANALYSIS|GITHUB  # Filter usecases for 'replay all' command

# Now run commands without additional options
logstory replay usecase RULES_SEARCH_WORKSHOP  # Will auto-download if missing
logstory usecases list-available
```

### 3. Environment Files (.env)

Create .env files for different environments and load them with `--env-file`:

**`.env.prod`:**
```bash
LOGSTORY_CUSTOMER_ID=01234567-0123-4321-abcd-01234567890a
LOGSTORY_CREDENTIALS_PATH=/secure/prod-credentials.json
LOGSTORY_REGION=US
LOGSTORY_USECASES_BUCKETS=gs://prod-usecases
```

**`.env.dev`:**
```bash
LOGSTORY_CUSTOMER_ID=98765432-9876-5432-dcba-098765432109
LOGSTORY_CREDENTIALS_PATH=/dev/dev-credentials.json
LOGSTORY_REGION=US
LOGSTORY_USECASES_BUCKETS=file:///local/dev-usecases,gs://dev-usecases
LOGSTORY_LOCAL_LOG_DIR=/tmp/logstory-dev
LOGSTORY_AUTO_GET=true  # Auto-download missing usecases in dev
```

**Usage:**
```bash
# Use production environment
logstory replay usecase MONITORING --env-file .env.prod

# Use development environment  
logstory usecases list-available --env-file .env.dev
logstory replay usecase TEST_CASE --env-file .env.dev --local-file-output
```

## Configuration Priority

Configuration values are resolved in this order (highest to lowest priority):

1. **Command line options** - Always take precedence
2. **Environment variables** - Set in current shell session
3. **.env file values** - When `--env-file` is specified
4. **Default values** - Built-in defaults

**Example priority resolution:**
```bash
# .env file contains: LOGSTORY_REGION=EU
# Environment has: export LOGSTORY_REGION=US  
# Command line has: --region=ASIA

# Result: ASIA (command line wins)
logstory replay usecase TEST --env-file .env --region=ASIA
```

## Environment Variables Reference

### Required for Replay Commands

| Variable | Description | Example |
|----------|-------------|---------|
| `LOGSTORY_CUSTOMER_ID` | SecOps tenant UUID4 | `01234567-0123-4321-abcd-01234567890a` |
| `LOGSTORY_CREDENTIALS_PATH` | Path to JSON credentials file | `/path/to/credentials.json` |

### Optional Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `LOGSTORY_REGION` | `US` | SecOps tenant region |
| `LOGSTORY_USECASES_BUCKETS` | `gs://logstory-usecases-20241216` | Comma-separated source URIs |
| `LOGSTORY_LOCAL_LOG_DIR` | `/tmp/var/log/logstory` | Base directory for local file output |
| `LOGSTORY_AUTO_GET` | `false` | Auto-download missing usecases (true/1/yes/on) |

## Source Configuration

### Single Source

```bash
# GCS bucket
export LOGSTORY_USECASES_BUCKETS=gs://my-usecases

# Local file system
export LOGSTORY_USECASES_BUCKETS=file:///path/to/usecases
```

### Multiple Sources

```bash
# Multiple GCS buckets
export LOGSTORY_USECASES_BUCKETS=gs://prod-usecases,gs://team-usecases

# Mixed sources
export LOGSTORY_USECASES_BUCKETS=gs://prod-usecases,file:///local/custom-usecases

# Three sources with different types
export LOGSTORY_USECASES_BUCKETS=gs://public-usecases,gs://private-usecases,file:///local/dev-usecases
```

### Source URI Formats

| Format | Description | Authentication |
|--------|-------------|----------------|
| `gs://bucket-name` | Google Cloud Storage bucket | Application Default Credentials or anonymous |
| `file:///absolute/path` | Local file system directory | File system permissions |
| `git@host:repo.git` | Git repository (future) | SSH keys |
| `https://host/repo.git` | Git repository HTTPS (future) | HTTPS auth |

## Authentication Configuration

### Google Cloud Storage

**For public buckets:**
```bash
# No authentication required
export LOGSTORY_USECASES_BUCKETS=gs://public-bucket
```

**For private buckets:**
```bash
# Set up Application Default Credentials
gcloud auth application-default login

# Or use service account
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
export LOGSTORY_USECASES_BUCKETS=gs://private-bucket
```

### SecOps API

**Get credentials from SecOps console:**
1. Navigate to: `https://${tenant}.backstory.chronicle.security/settings/collection-agent`
2. Download the ingestion authentication file
3. Set the path:

```bash
export LOGSTORY_CREDENTIALS_PATH=/path/to/downloaded-credentials.json
```

**Get customer ID:**
1. Navigate to: `https://${tenant}.backstory.chronicle.security/settings/profile`
2. Copy the Customer ID (UUID4 format)
3. Set the ID:

```bash
export LOGSTORY_CUSTOMER_ID=01234567-0123-4321-abcd-01234567890a
```

## Local File Output Configuration

### Basic Configuration

```bash
# Use default directory (/tmp/var/log/logstory)
logstory replay usecase TEST --local-file-output

# Use custom directory
export LOGSTORY_LOCAL_LOG_DIR=/custom/log/path
logstory replay usecase TEST --local-file-output
```

### Directory Structure

Logs are organized in a realistic directory structure:

```
/tmp/var/log/logstory/
├── AUDITD.log
├── AWS_CLOUDTRAIL.log  
├── Library/
│   ├── CS/logs/
│   │   ├── CS_DETECTS.log
│   │   └── CS_EDR.log
│   └── Logs/Microsoft/PowerShell/
│       └── POWERSHELL.log
├── opt/fireeye/agent/log/
│   └── FIREEYE_HX.log
└── usr/local/zeek/logs/current/
    └── BRO_JSON.log
```

## Advanced Configuration Examples

### Multi-Environment Setup

Create environment-specific configurations:

**`config/prod.env`:**
```bash
LOGSTORY_CUSTOMER_ID=01234567-0123-4321-abcd-01234567890a
LOGSTORY_CREDENTIALS_PATH=/secure/prod/credentials.json
LOGSTORY_REGION=US
LOGSTORY_USECASES_BUCKETS=gs://prod-usecases-secure
```

**`config/staging.env`:**
```bash
LOGSTORY_CUSTOMER_ID=11111111-2222-3333-4444-555555555555
LOGSTORY_CREDENTIALS_PATH=/secure/staging/credentials.json
LOGSTORY_REGION=US
LOGSTORY_USECASES_BUCKETS=gs://staging-usecases,file:///staging/custom-usecases
```

**`config/dev.env`:**
```bash
LOGSTORY_CUSTOMER_ID=99999999-8888-7777-6666-555555555555
LOGSTORY_CREDENTIALS_PATH=/dev/dev-credentials.json
LOGSTORY_REGION=US
LOGSTORY_USECASES_BUCKETS=file:///dev/usecases
LOGSTORY_LOCAL_LOG_DIR=/dev/logs
```

**Usage scripts:**
```bash
#!/bin/bash
# deploy-prod.sh
logstory replay all --env-file config/prod.env --timestamp-delta=1d

#!/bin/bash  
# test-staging.sh
logstory replay usecase INTEGRATION_TEST --env-file config/staging.env

#!/bin/bash
# dev-local.sh
logstory replay usecase DEV_TEST --env-file config/dev.env --local-file-output
```

### CI/CD Configuration

**GitHub Actions example:**
```yaml
# .github/workflows/logstory-deploy.yml
env:
  LOGSTORY_CUSTOMER_ID: ${{ secrets.LOGSTORY_CUSTOMER_ID }}
  LOGSTORY_CREDENTIALS_PATH: ./credentials.json
  LOGSTORY_REGION: US
  LOGSTORY_USECASES_BUCKETS: gs://ci-usecases

steps:
  - name: Setup credentials
    run: echo "${{ secrets.LOGSTORY_CREDENTIALS }}" > credentials.json
    
  - name: Deploy usecases
    run: logstory replay all --timestamp-delta=1d
```

### Docker Configuration

**Dockerfile:**
```dockerfile
FROM python:3.12-slim
RUN pip install logstory

# Copy configuration
COPY .env.docker /app/.env
COPY credentials.json /app/credentials.json
WORKDIR /app

# Default command
CMD ["logstory", "replay", "all", "--env-file", ".env"]
```

**`.env.docker`:**
```bash
LOGSTORY_CUSTOMER_ID=01234567-0123-4321-abcd-01234567890a
LOGSTORY_CREDENTIALS_PATH=/app/credentials.json
LOGSTORY_REGION=US
LOGSTORY_USECASES_BUCKETS=gs://docker-usecases
```

## Troubleshooting Configuration

### Common Issues

**1. Missing credentials:**
```bash
# Error: Missing required parameters: --credentials-path
# Solution: Set environment variable or use --credentials-path
export LOGSTORY_CREDENTIALS_PATH=/path/to/credentials.json
```

**2. Invalid customer ID:**
```bash
# Error: 'invalid-id' is not a valid UUID4
# Solution: Use proper UUID4 format
export LOGSTORY_CUSTOMER_ID=01234567-0123-4321-abcd-01234567890a
```

**3. .env file not found:**
```bash
# Warning: Specified .env file not found: missing.env
# Solution: Check file path and permissions
logstory usecases list-available --env-file .env.prod
```

**4. Source access issues:**
```bash
# Error: Could not access source 'gs://private-bucket'
# Solution: Set up authentication
gcloud auth application-default login
```

### Debug Configuration

**Enable verbose logging:**
```bash
PYTHONLOGLEVEL=DEBUG logstory replay usecase TEST --env-file .env
```

**Check current configuration:**
```bash
# List available usecases (shows which sources are accessible)
logstory usecases list-available --env-file .env

# Test local file output (doesn't require credentials)
logstory replay usecase TEST --env-file .env --local-file-output
```

**Validate .env file:**
```bash
# Check .env file syntax
cat .env | grep -v '^#' | grep '='

# Source .env file manually to test
source .env && env | grep LOGSTORY
```