# .env File Reference

Environment files (`.env`) provide a convenient way to configure logstory without setting environment variables manually. This page covers all supported variables, file format, and practical examples.

## File Format

.env files use a simple `KEY=VALUE` format:

```bash
# Comments start with #
LOGSTORY_CUSTOMER_ID=01234567-0123-4321-abcd-01234567890a
LOGSTORY_CREDENTIALS_PATH=/path/to/credentials.json

# Values with spaces should be quoted
LOGSTORY_USECASES_BUCKETS="gs://bucket1,gs://bucket2"

# Or without quotes if no special characters
LOGSTORY_REGION=US
```

## All Supported Variables

### Required for Replay Commands

| Variable | Description | Example |
|----------|-------------|---------|
| `LOGSTORY_CUSTOMER_ID` | SecOps tenant UUID4 | `01234567-0123-4321-abcd-01234567890a` |
| `LOGSTORY_CREDENTIALS_PATH` | Path to JSON credentials file | `/path/to/credentials.json` |

### Optional Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `LOGSTORY_REGION` | `US` | SecOps tenant region (`US`, `EU`, `ASIA`) |
| `LOGSTORY_USECASES_BUCKETS` | `gs://logstory-usecases-20241216` | Comma-separated source URIs |
| `LOGSTORY_LOCAL_LOG_DIR` | `/tmp/var/log/logstory` | Base directory for local file output |

## Complete .env Examples

### Production Environment

```bash
# .env.prod
# Production SecOps configuration

# Required: SecOps tenant credentials
LOGSTORY_CUSTOMER_ID=01234567-0123-4321-abcd-01234567890a
LOGSTORY_CREDENTIALS_PATH=/secure/prod/credentials.json
LOGSTORY_REGION=US

# Production usecase sources
LOGSTORY_USECASES_BUCKETS=gs://prod-usecases-secure

# Production log output (when using --local-file-output)
LOGSTORY_LOCAL_LOG_DIR=/var/log/logstory-prod
```

### Development Environment

```bash
# .env.dev
# Development configuration with local usecases

# Required: Development SecOps tenant
LOGSTORY_CUSTOMER_ID=01234567-0123-4321-abcd-01234567890a
LOGSTORY_CREDENTIALS_PATH=/dev/dev-credentials.json
LOGSTORY_REGION=US

# Mixed sources: local development + shared GCS
LOGSTORY_USECASES_BUCKETS=file:///Users/developer/custom-usecases,gs://dev-usecases

# Development log directory
LOGSTORY_LOCAL_LOG_DIR=/tmp/logstory-dev
```

### Chronicle Replay Use Cases

```bash
# .env.chronicle
# Configuration for Chronicle replay use cases

# Required: Your SecOps tenant
LOGSTORY_CUSTOMER_ID=your-tenant-uuid-here
LOGSTORY_CREDENTIALS_PATH=/path/to/your/chronicle-credentials.json
LOGSTORY_REGION=US

# Local Chronicle replay use cases directory
LOGSTORY_USECASES_BUCKETS=file:///Users/analyst/chronicle-replay-use-cases

# Optional: custom log output directory
LOGSTORY_LOCAL_LOG_DIR=/tmp/chronicle-logs
```

### Testing/Local Development

```bash
# .env.test
# Testing configuration with local files only

# Not required for local file output testing
# LOGSTORY_CUSTOMER_ID=test-uuid
# LOGSTORY_CREDENTIALS_PATH=/dev/null

# Local test usecases
LOGSTORY_USECASES_BUCKETS=file:///test/usecases

# Test output directory
LOGSTORY_LOCAL_LOG_DIR=/test/output

# Always use local file output for testing
# (Use --local-file-output flag when running commands)
```

### Staging Environment

```bash
# .env.staging
# Staging environment configuration

# Required: Staging tenant credentials
LOGSTORY_CUSTOMER_ID=01234567-0123-4321-abcd-01234567890a
LOGSTORY_CREDENTIALS_PATH=/staging/credentials.json
LOGSTORY_REGION=US

# Multiple staging sources
LOGSTORY_USECASES_BUCKETS=gs://staging-usecases,file:///staging/custom-usecases

# Staging log directory
LOGSTORY_LOCAL_LOG_DIR=/var/log/logstory-staging
```

### CI/CD Environment

```bash
# .env.ci
# CI/CD pipeline configuration

# Required: CI tenant (often same as staging)
LOGSTORY_CUSTOMER_ID=01234567-0123-4321-abcd-01234567890a
LOGSTORY_CREDENTIALS_PATH=/ci/credentials.json
LOGSTORY_REGION=US

# CI-specific usecase sources
LOGSTORY_USECASES_BUCKETS=gs://ci-usecases,file:///ci/test-usecases

# CI log output
LOGSTORY_LOCAL_LOG_DIR=/ci/logs
```

## Usage Patterns

### Basic Usage

```bash
# Create your .env file
cat > .env << 'EOF'
LOGSTORY_CUSTOMER_ID=01234567-0123-4321-abcd-01234567890a
LOGSTORY_CREDENTIALS_PATH=/path/to/credentials.json
LOGSTORY_USECASES_BUCKETS=file:///path/to/usecases
EOF

# Use with any command
logstory usecases list-available --env-file .env
logstory usecases get MY_USECASE --env-file .env
logstory replay usecase MY_USECASE --env-file .env
```

### Multiple Environment Files

```bash
# Different environments
logstory replay usecase MONITORING --env-file .env.prod
logstory replay usecase TEST_CASE --env-file .env.dev
logstory usecases list-available --env-file .env.staging
```

### Override Specific Values

```bash
# Load .env but override specific values
logstory replay usecase TEST \
  --env-file .env.dev \
  --local-file-output \
  --timestamp-delta=2d
```

## Source URI Formats

### Single Sources

```bash
# Single GCS bucket
LOGSTORY_USECASES_BUCKETS=gs://my-usecases

# Single local directory
LOGSTORY_USECASES_BUCKETS=file:///path/to/usecases

# Single bucket (legacy format, auto-prefixed with gs://)
LOGSTORY_USECASES_BUCKETS=my-bucket-name
```

### Multiple Sources

```bash
# Multiple GCS buckets
LOGSTORY_USECASES_BUCKETS=gs://bucket1,gs://bucket2,gs://bucket3

# Mixed sources
LOGSTORY_USECASES_BUCKETS=gs://remote-bucket,file:///local/usecases

# Complex example
LOGSTORY_USECASES_BUCKETS=gs://prod-usecases,gs://team-usecases,file:///custom/usecases,file:///dev/test-usecases
```

### Quoting Rules

```bash
# No spaces - quotes optional
LOGSTORY_USECASES_BUCKETS=gs://bucket1,gs://bucket2

# With spaces - quotes required
LOGSTORY_USECASES_BUCKETS="gs://bucket with spaces,file:///path/with spaces"

# Mixed - quotes around entire value
LOGSTORY_USECASES_BUCKETS="gs://bucket1,file:///path/with spaces,gs://bucket2"
```

## File Paths

### Absolute Paths Required

```bash
# Correct - absolute paths
LOGSTORY_CREDENTIALS_PATH=/home/user/credentials.json
LOGSTORY_LOCAL_LOG_DIR=/var/log/logstory
LOGSTORY_USECASES_BUCKETS=file:///home/user/usecases

# Incorrect - relative paths not supported
# LOGSTORY_CREDENTIALS_PATH=./credentials.json
# LOGSTORY_USECASES_BUCKETS=file://./usecases
```

### Platform-Specific Examples

**Linux/macOS:**
```bash
LOGSTORY_CREDENTIALS_PATH=/home/analyst/.chronicle/credentials.json
LOGSTORY_USECASES_BUCKETS=file:///opt/chronicle/usecases
LOGSTORY_LOCAL_LOG_DIR=/var/log/chronicle
```

**Windows:**
```bash
LOGSTORY_CREDENTIALS_PATH=C:/Users/analyst/.chronicle/credentials.json
LOGSTORY_USECASES_BUCKETS=file:///C:/data/chronicle/usecases
LOGSTORY_LOCAL_LOG_DIR=C:/logs/chronicle
```

## Security Best Practices

### File Permissions

```bash
# Set secure permissions on .env files
chmod 600 .env*

# Verify permissions
ls -la .env*
# Should show: -rw------- (readable by owner only)
```

### Credentials Security

```bash
# Store credentials securely
chmod 600 /path/to/credentials.json

# Use secure directories
LOGSTORY_CREDENTIALS_PATH=/secure/credentials/chronicle.json

# Never commit credentials to version control
echo "*.json" >> .gitignore
echo ".env*" >> .gitignore
```

### Environment Isolation

```bash
# Use different credentials for each environment
# .env.prod
LOGSTORY_CREDENTIALS_PATH=/secure/prod/credentials.json

# .env.dev
LOGSTORY_CREDENTIALS_PATH=/dev/dev-credentials.json

# .env.staging
LOGSTORY_CREDENTIALS_PATH=/staging/staging-credentials.json
```

## Common Patterns

### Project-Based Configuration

```bash
# Directory structure
project/
├── .env.prod
├── .env.dev
├── .env.test
├── usecases/
│   ├── CUSTOM_USECASE/
│   └── PROJECT_SPECIFIC/
└── scripts/
    ├── deploy-prod.sh
    ├── test-dev.sh
    └── validate.sh
```

**deploy-prod.sh:**
```bash
#!/bin/bash
logstory replay all --env-file .env.prod --timestamp-delta=1d
```

**test-dev.sh:**
```bash
#!/bin/bash
logstory replay usecase TEST_CASE --env-file .env.dev --local-file-output
```

### Docker Configuration

**Dockerfile:**
```dockerfile
FROM python:3.12-slim
RUN pip install logstory

# Copy environment file
COPY .env.docker /app/.env
WORKDIR /app

CMD ["logstory", "replay", "all", "--env-file", ".env"]
```

**.env.docker:**
```bash
LOGSTORY_CUSTOMER_ID=01234567-0123-4321-abcd-01234567890a
LOGSTORY_CREDENTIALS_PATH=/app/credentials.json
LOGSTORY_REGION=US
LOGSTORY_USECASES_BUCKETS=gs://docker-usecases
```

### CI/CD Integration

**GitHub Actions:**
```yaml
# .github/workflows/deploy.yml
- name: Deploy usecases
  env:
    LOGSTORY_CUSTOMER_ID: ${{ secrets.CUSTOMER_ID }}
    LOGSTORY_CREDENTIALS_PATH: ./credentials.json
  run: |
    echo "${{ secrets.CREDENTIALS_JSON }}" > credentials.json
    logstory replay all --env-file .env.ci
```

**.env.ci:**
```bash
# Customer ID and credentials come from GitHub secrets
# LOGSTORY_CUSTOMER_ID - set via environment
# LOGSTORY_CREDENTIALS_PATH - set via environment

LOGSTORY_REGION=US
LOGSTORY_USECASES_BUCKETS=gs://ci-usecases
LOGSTORY_LOCAL_LOG_DIR=/tmp/ci-logs
```

## Troubleshooting

### Common Issues

**1. File not found:**
```bash
# Error: Specified .env file not found: .env.prod
# Solution: Check file path and current directory
ls -la .env*
pwd
```

**2. Invalid UUID format:**
```bash
# Error: 'invalid-id' is not a valid UUID4
# Solution: Use proper UUID4 format
LOGSTORY_CUSTOMER_ID=01234567-0123-4321-abcd-01234567890a
```

**3. Credentials file not found:**
```bash
# Error: File does not exist: /path/to/credentials.json
# Solution: Use absolute path and verify file exists
LOGSTORY_CREDENTIALS_PATH=/absolute/path/to/credentials.json
ls -la /absolute/path/to/credentials.json
```

**4. Permission denied:**
```bash
# Error: Permission denied accessing file
# Solution: Check file permissions
chmod 600 .env
chmod 600 /path/to/credentials.json
```

### Validation Commands

**Test .env file loading:**
```bash
# Test if .env loads correctly
logstory usecases list-available --env-file .env

# Check what variables are set
source .env && env | grep LOGSTORY
```

**Validate configuration:**
```bash
# Test without credentials (uses local file output)
logstory replay usecase TEST --env-file .env --local-file-output

# Test source access
logstory usecases list-available --env-file .env
```

**Debug environment resolution:**
```bash
# Enable debug logging to see variable resolution
PYTHONLOGLEVEL=DEBUG logstory usecases list-available --env-file .env
```

### Syntax Validation

**Check for common syntax errors:**
```bash
# Validate .env syntax
grep -n '[^=]*=[^=]*' .env

# Check for missing quotes
grep -n ' ' .env | grep -v '^#'

# Verify no Windows line endings
file .env
# Should show: ASCII text, not CRLF
```

## Template .env Files

### Minimal Template

```bash
# .env.template
# Copy this file and fill in your values

# Required for replay commands
LOGSTORY_CUSTOMER_ID=your-tenant-uuid-here
LOGSTORY_CREDENTIALS_PATH=/path/to/your/credentials.json

# Optional configuration
LOGSTORY_REGION=US
LOGSTORY_USECASES_BUCKETS=gs://your-bucket-or-file:///path/to/usecases
LOGSTORY_LOCAL_LOG_DIR=/tmp/var/log/logstory
```

### Complete Template

```bash
# .env.complete
# Complete template with all possible variables

# Required: SecOps tenant configuration
LOGSTORY_CUSTOMER_ID=01234567-0123-4321-abcd-01234567890a
LOGSTORY_CREDENTIALS_PATH=/path/to/credentials.json

# Optional: Tenant region (US, EU, ASIA)
LOGSTORY_REGION=US

# Optional: Usecase sources (comma-separated)
# Supports: gs://bucket, file:///path, bare-bucket-name
LOGSTORY_USECASES_BUCKETS=gs://bucket1,file:///local/usecases

# Optional: Local file output directory
LOGSTORY_LOCAL_LOG_DIR=/tmp/var/log/logstory

# Note: All paths should be absolute
# Note: Values with spaces should be quoted
# Note: Comments start with #
```

## Integration Examples

### VS Code Integration

**.vscode/settings.json:**
```json
{
  "terminal.integrated.env.linux": {
    "LOGSTORY_ENV_FILE": "${workspaceFolder}/.env.dev"
  },
  "terminal.integrated.env.osx": {
    "LOGSTORY_ENV_FILE": "${workspaceFolder}/.env.dev"
  }
}
```

**Usage in VS Code terminal:**
```bash
logstory usecases list-available --env-file $LOGSTORY_ENV_FILE
```

### Shell Integration

**Add to ~/.bashrc or ~/.zshrc:**
```bash
# Logstory aliases with env files
alias logstory-prod='logstory --env-file ~/.config/logstory/.env.prod'
alias logstory-dev='logstory --env-file ~/.config/logstory/.env.dev'
alias logstory-test='logstory --env-file ~/.config/logstory/.env.test'

# Function to switch environments
logstory-env() {
  if [ -f ".env.$1" ]; then
    export LOGSTORY_CURRENT_ENV=".env.$1"
    echo "Using logstory environment: $1"
  else
    echo "Environment file .env.$1 not found"
  fi
}

# Usage: logstory-env prod
# Then: logstory usecases list-available --env-file $LOGSTORY_CURRENT_ENV
```