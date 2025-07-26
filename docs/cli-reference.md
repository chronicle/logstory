# CLI Reference

The logstory CLI is organized into two main command groups with extensive options for configuration and customization.

## Command Structure

```bash
logstory <command-group> <command> [arguments] [options]
```

## Usecase Management Commands

### `logstory usecases list-installed`

List locally installed usecases and optionally their logtypes.

**Basic Usage:**
```bash
# List usecase names only
logstory usecases list-installed

# List with logtypes
logstory usecases list-installed --logtypes

# List with full markdown details
logstory usecases list-installed --details

# Open usecase in VS Code
logstory usecases list-installed --open NETWORK_ANALYSIS
```

**Options:**
- `--env-file TEXT`: Path to .env file to load environment variables from
- `--logtypes`: Show logtypes for each usecase
- `--details`: Show full markdown content for each usecase  
- `--open TEXT`: Open markdown file for specified usecase in VS Code
- `--entities`: Show entity logtypes instead of event logtypes

**Examples:**
```bash
# Use custom environment file
logstory usecases list-installed --env-file .env.prod

# List entities with logtypes
logstory usecases list-installed --logtypes --entities

# Get detailed view of all usecases
logstory usecases list-installed --details
```

### `logstory usecases list-available`

List usecases available for download from configured sources.

**Basic Usage:**
```bash
# List from default/configured sources
logstory usecases list-available

# List from specific source
logstory usecases list-available --usecases-bucket gs://my-bucket
```

**Options:**
- `--env-file TEXT`: Path to .env file to load environment variables from
- `--usecases-bucket TEXT`: Override configured sources with specific URI

**Examples:**
```bash
# Use custom environment file
logstory usecases list-available --env-file .env.dev

# List from local file system
logstory usecases list-available --usecases-bucket file:///path/to/usecases

# List from private GCS bucket
logstory usecases list-available --usecases-bucket gs://my-private-bucket
```

### `logstory usecases get`

Download a usecase from configured sources to local installation.

**Basic Usage:**
```bash
# Download from configured sources
logstory usecases get USECASE_NAME

# Download from specific source
logstory usecases get USECASE_NAME --usecases-bucket gs://specific-bucket
```

**Options:**
- `--env-file TEXT`: Path to .env file to load environment variables from
- `--usecases-bucket TEXT`: Override configured sources with specific URI

**Examples:**
```bash
# Download using custom environment
logstory usecases get EDR_WORKSHOP --env-file .env.prod

# Download from local file system
logstory usecases get MALWARE --usecases-bucket file:///path/to/usecases

# Download from specific GCS bucket
logstory usecases get AWS --usecases-bucket gs://my-custom-bucket
```

## Replay Commands

All replay commands require `--customer-id` and `--credentials-path` options unless using `--local-file-output`.

### `logstory replay all`

Replay all installed usecases.

**Basic Usage:**
```bash
logstory replay all \
  --customer-id=01234567-0123-4321-abcd-01234567890a \
  --credentials-path=/path/to/credentials.json
```

**Options:**
- `--env-file TEXT`: Path to .env file to load environment variables from
- `--customer-id TEXT`: Customer ID for SecOps instance (env: LOGSTORY_CUSTOMER_ID)
- `--credentials-path TEXT`: Path to JSON credentials file (env: LOGSTORY_CREDENTIALS_PATH)
- `--region TEXT`: SecOps tenant region (default: US, env: LOGSTORY_REGION)
- `--entities`: Load entities instead of events
- `--timestamp-delta TEXT`: Time offset (default: 1d)
- `--local-file-output`: Write logs to local files instead of sending to API

### `logstory replay usecase`

Replay a specific usecase.

**Basic Usage:**
```bash
logstory replay usecase USECASE_NAME \
  --customer-id=01234567-0123-4321-abcd-01234567890a \
  --credentials-path=/path/to/credentials.json
```

**Options:** Same as `replay all`

**Examples:**
```bash
# Replay with custom environment
logstory replay usecase RULES_SEARCH_WORKSHOP --env-file .env.prod

# Replay entities only
logstory replay usecase NETWORK_ANALYSIS --entities

# Write to local files for testing
logstory replay usecase AWS --local-file-output
```

### `logstory replay logtype`

Replay specific logtypes from a usecase.

**Basic Usage:**
```bash
logstory replay logtype USECASE_NAME LOGTYPE1,LOGTYPE2 \
  --customer-id=01234567-0123-4321-abcd-01234567890a \
  --credentials-path=/path/to/credentials.json
```

**Options:** Same as `replay all`

**Examples:**
```bash
# Replay specific logtypes
logstory replay logtype RULES_SEARCH_WORKSHOP POWERSHELL,WINDOWS_SYSMON \
  --env-file .env \
  --timestamp-delta=2d

# Replay to local files with custom delta
logstory replay logtype NETWORK_ANALYSIS BRO_JSON \
  --local-file-output \
  --timestamp-delta=1d1h
```

## Global Options

These options are available across different command groups:

### Configuration Options
- `--env-file TEXT`: Load environment variables from specified .env file
- `--customer-id TEXT`: SecOps tenant UUID4 (required for replay commands)
- `--credentials-path TEXT`: Path to JSON credentials file (required for replay commands)
- `--region TEXT`: SecOps tenant region (default: US)

### Source Options
- `--usecases-bucket TEXT`: Override configured usecase sources

### Data Options
- `--entities`: Work with entities instead of events
- `--timestamp-delta TEXT`: Time offset for timestamp updates (default: 1d)
- `--local-file-output`: Write to local files instead of API

### Display Options
- `--logtypes`: Show logtypes for usecases
- `--details`: Show full details/content
- `--open TEXT`: Open specified item in VS Code

## Environment Variables

All CLI options can be set via environment variables:

| CLI Option | Environment Variable | Description |
|------------|---------------------|-------------|
| `--customer-id` | `LOGSTORY_CUSTOMER_ID` | SecOps tenant UUID4 |
| `--credentials-path` | `LOGSTORY_CREDENTIALS_PATH` | Path to credentials JSON |
| `--region` | `LOGSTORY_REGION` | SecOps tenant region |
| `--usecases-bucket` | `LOGSTORY_USECASES_BUCKETS` | Comma-separated source URIs |
| N/A | `LOGSTORY_LOCAL_LOG_DIR` | Base directory for local file output |

## Configuration Priority

Configuration values are resolved in this order (highest to lowest priority):

1. Command line options
2. Environment variables  
3. .env file values (when `--env-file` is used)
4. Default values

## Exit Codes

- `0`: Success
- `1`: General error (missing parameters, file not found, etc.)
- Other: Specific error codes from underlying operations

## Examples by Use Case

### Development/Testing
```bash
# Test with local usecases and file output
export LOGSTORY_USECASES_BUCKETS=file:///path/to/local/usecases
logstory usecases list-available
logstory replay usecase TEST_CASE --local-file-output

# Use different environments
logstory usecases get DEV_USECASE --env-file .env.dev
logstory replay usecase DEV_USECASE --env-file .env.dev --local-file-output
```

### Production Usage
```bash
# Production replay with proper credentials
logstory replay all --env-file .env.prod

# Scheduled daily replay
logstory replay usecase MONITORING --env-file .env.prod --timestamp-delta=1d
```

### Mixed Sources
```bash
# Use both GCS and local sources
export LOGSTORY_USECASES_BUCKETS=gs://prod-usecases,file:///local/custom-usecases
logstory usecases list-available
logstory usecases get CUSTOM_USECASE
```