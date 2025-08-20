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
- `--entities`: Load Entities instead of Events

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
- `--usecases-bucket TEXT`: Usecase source URI (gs://bucket, git@repo, etc.) - overrides config list

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
- `--usecases-bucket TEXT`: Usecase source URI (gs://bucket, git@repo, etc.) - overrides config list

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
- `--credentials-path, -c TEXT`: Path to JSON credentials for Ingestion API Service account (env: `LOGSTORY_CREDENTIALS_PATH`)
- `--customer-id TEXT`: Customer ID for SecOps instance, found on `/settings/profile/` (env: `LOGSTORY_CUSTOMER_ID`)
- `--region, -r TEXT`: SecOps tenant's region (Default=US). Used to set ingestion API base URL (env: `LOGSTORY_REGION`)
- `--entities`: Load Entities instead of Events
- `--timestamp-delta TEXT`: Determines how datetimes in logfiles are updated. Expressed in any/all: days, hours, minutes (d, h, m) (Default=1d). Examples: [1d, 1d1h, 1h1m, 1d1m, 1d1h1m, 1m1h, ...]. Setting only `Nd` preserves the original HH:MM:SS but updates date. Nh/Nm subtracts an additional offset from that datetime, to facilitate running logstory more than 1x per day.
- `--local-file-output`: Write logs to local files instead of sending to API

### `logstory replay usecase`

Replay a specific usecase.

**Basic Usage:**
```bash
logstory replay usecase USECASE_NAME \
  --customer-id=01234567-0123-4321-abcd-01234567890a \
  --credentials-path=/path/to/credentials.json
```

**Options:** Same as `replay all`, plus:
- `--get/--no-get`: Download usecase if not already installed (env: `LOGSTORY_AUTO_GET`). Use `--no-get` to override environment variable.

**Examples:**
```bash
# Replay with custom environment
logstory replay usecase RULES_SEARCH_WORKSHOP --env-file .env.prod

# Auto-download and replay if not installed
logstory replay usecase OKTA --get \
  --customer-id=01234567-0123-4321-abcd-01234567890a \
  --credentials-path=/path/to/credentials.json

# Disable auto-download even if LOGSTORY_AUTO_GET is set
logstory replay usecase OKTA --no-get \
  --customer-id=01234567-0123-4321-abcd-01234567890a \
  --credentials-path=/path/to/credentials.json

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
- `--credentials-path, -c TEXT`: Path to JSON credentials for Ingestion API Service account (env: `LOGSTORY_CREDENTIALS_PATH`)
- `--customer-id TEXT`: Customer ID for SecOps instance, found on `/settings/profile/` (env: `LOGSTORY_CUSTOMER_ID`)
- `--region, -r TEXT`: SecOps tenant's region (Default=US). Used to set ingestion API base URL (env: `LOGSTORY_REGION`)

### Source Options
- `--usecases-bucket TEXT`: Usecase source URI (gs://bucket, git@repo, etc.) - overrides config list

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
| `--get` | `LOGSTORY_AUTO_GET` | Auto-download missing usecases (true/1/yes/on) |
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
