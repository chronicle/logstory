# UDM Search Integration for Logstory

## Overview

Implemented **Option 1: Extend `_get_log_content()` to support UDM Search queries**.

This feature allows logstory to fetch UDM events directly from Chronicle via UDM search queries, then replay them with updated timestamps into the ingestion pipeline—without needing pre-existing `.log` files.

## Changes Made

### 1. Core Logic (`src/logstory/main.py`)

#### New Function: `_search_udm()`
- Executes UDM search queries against Chronicle API
- Parameters:
  - `http_client`: Authenticated HTTP session
  - `customer_id`: Chronicle customer ID  
  - `query`: UDM search query string
  - `start_time`, `end_time`: Time range for search (defaults to last 30 days)
  - `region`: Chronicle region (US or EU)
- Returns results as JSON lines (one UDM event per line)
- Handles API errors and logging

#### Modified Function: `_get_log_content()`
- Now accepts optional UDM search parameters:
  - `udm_query`: UDM search query to execute
  - `http_client`: Authenticated client for the query
  - `customer_id`: For API calls
  - `region`: Chronicle region
- Logic flow:
  - If `udm_query` provided → execute UDM search and return results
  - Otherwise → fall back to existing file-based logic (GCS or local filesystem)
- Maintains full backward compatibility

#### Modified Function: `usecase_replay_logtype()`
- Added parameters to support UDM queries
- Passes UDM parameters down to `_get_log_content()`
- Works seamlessly with existing timestamp replacement and ingestion pipeline

### 2. CLI Commands (`src/logstory/logstory.py`)

#### New Command: `replay from-udm-search`
```bash
logstory replay from-udm-search "<UDM_QUERY>" \
  --customer-id=<ID> \
  --credentials-path=<PATH> \
  --timestamp-delta=1d
```

Example:
```bash
logstory replay from-udm-search "metadata.event_type='PROCESS_EXECUTION'" \
  --customer-id=01234567-0123-4321-abcd-01234567890a \
  --credentials-path=/path/to/credentials.json
```

#### New Internal Function: `_replay_from_udm()`
- Orchestrates UDM query execution and replay
- Applies timestamp shifting via existing pipeline
- Injects ingestion labels identifying the source as UDM search
- Outputs verification query for finding replayed events in Chronicle

### 3. Configuration (`src/logstory/logtypes_events_timestamps.yaml`)

Added timestamp configuration for UDM events:
```yaml
UDM_EVENTS:
  api: udmevents
  timestamps:
    - name: created_time
      base_time: true
      pattern: '("created_time":\s*"?)(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(.\d+Z?\s*"?)'
      dateformat: "%Y-%m-%dT%H:%M:%S"
      group: 2
    - name: generic_event_timestamp
      pattern: '("(?:event_time|timestamp|created_at|time)":\s*"?)(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(.\d+Z?\s*"?)'
      dateformat: "%Y-%m-%dT%H:%M:%S"
      group: 2
```

- **api**: `udmevents` (uses native UDM ingestion)
- **timestamps**: Pattern matching for common timestamp field names in UDM events
- Supports ISO 8601 format timestamps (RFC 3339)

### 4. Tests (`tests/test_udm_search.py`)

Created comprehensive test suite:
- `test_search_udm_formats_results_as_jsonl()` - Verifies UDM API results conversion
- `test_get_log_content_with_udm_query()` - Tests UDM query path in content retrieval
- `test_get_log_content_without_udm_query()` - Ensures backward compatibility
- `test_udm_query_requires_http_client()` - Validates error handling

## Data Flow

```
UDM Search Query
    ↓
_search_udm() → Chronicle API
    ↓
JSON Lines (one UDM event per line)
    ↓
usecase_replay_logtype()
    ↓
Timestamp extraction & replacement (via existing regex patterns)
    ↓
post_entries() → Ingestion API (udmevents)
    ↓
Chronicle with updated timestamps
    ↓
Ingestion Labels:
  - log_replay: true
  - replayed_from: logstory
  - source_type: udm_search
```

## Key Design Decisions

1. **No new file dependencies**: UDM results flow directly through logstory's existing replay pipeline
2. **Backward compatible**: Existing file-based replay unchanged; UDM is additive
3. **Timestamp handling**: Reuses pattern matching from YAML configs; ISO 8601 patterns added
4. **API abstraction**: Uses authenticated `http_client` from existing auth system
5. **User-facing**: CLI command is simple and discoverable

## Usage Examples

### Basic UDM search replay
```bash
logstory replay from-udm-search "metadata.event_type='PROCESS_EXECUTION'"
```

### With custom timestamp shift
```bash
logstory replay from-udm-search "event.principal.ip_address='192.168.1.1'" \
  --timestamp-delta=7d
```

### With environment variables
```bash
export LOGSTORY_CUSTOMER_ID=<ID>
export LOGSTORY_CREDENTIALS_PATH=/path/to/credentials.json
logstory replay from-udm-search "metadata.ingestion_time >= '2024-01-01'"
```

## Verification

To find replayed logs:
```
metadata.ingested_timestamp.seconds >= <LOGSTORY_EXECUTION_TIME>
metadata.ingestion_labels["source_type"]="udm_search"
```

## Future Enhancements

- Support for UDM Search time range parameters in CLI
- Batch processing for large result sets
- Result pagination support
- Custom timestamp field mapping per query
- CSV export option (phase 2 of original issue)
